"""Evaluate the bundled model on the notebook's held-out test folder and write a repeatable report.

Run from the repository root with the Flask service's environment, which has TensorFlow:

    TF_CPP_MIN_LOG_LEVEL=2 flask-app/.venv/bin/python scripts/evaluate_model.py --test-dir <DATASET>/test --train-dir <DATASET>/train \
        --source-zip <KAGGLE_ZIP> [--flask-url http://127.0.0.1:4040/disease-analyzer]

Two passes classify every test image:

1. Notebook pipeline: ``tf.keras.utils.image_dataset_from_directory`` with the notebook's image size (256 x 256) and
   class order, then the SavedModel's ``serving_default`` signature. Accuracy and sparse categorical cross-entropy are
   computed the way ``model.evaluate`` reports them, so they compare directly with the notebook's saved test result.
2. Service (with ``--flask-url``): each image's bytes go to the running Flask endpoint as a multipart upload, as
   Laravel sends them. The report records agreement with pass 1.

Inputs are recorded by SHA-256: the four model files, every test image, the train/test byte overlap and, with
``--source-zip``, which test images are byte-identical to an entry of the public Kaggle archive. The report lands in
``artifacts/e2e/model_eval_<RUN_ID>/report.json`` and ``report.md``; each run writes a new folder and reads its inputs
only, so reruns are safe. Images and reports stay local.

Failure modes this run guards against:

1. Class folders map to the wrong label index: folder names are normalized and must sort into the notebook's order.
2. A different model is evaluated: the four model-file hashes must equal the pinned ones.
3. Images are silently skipped: the inventory must hold the notebook's 628 files and every file must get a prediction.
4. Train/test leakage goes unreported: byte-identical files across the two folders are counted and listed.
5. The service and the offline pass disagree unnoticed: every service prediction is compared with pass 1.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import platform
import sys
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import tensorflow as tf
from process import run_command

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "flask-app" / "model"
CLASS_NAMES = ("Blight", "Common Rust", "Gray Leaf Spot", "Healthy")
IMAGE_SIZE = (256, 256)
BATCH_SIZE = 32
EXPECTED_TEST_COUNT = 628
NOTEBOOK = {"test_accuracy": 0.8105095624923706, "test_loss": 2.938377618789673, "test_images": 628, "train_images": 3560}
MODEL_SHA256 = {
    "saved_model.pb": "fa1d0d1b6869",
    "keras_metadata.pb": "0807cda6ee63",
    "variables/variables.index": "427517639547",
    "variables/variables.data-00000-of-00001": "8644cfac537f",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
EPSILON = 1e-7  # Keras clips probabilities to [EPSILON, 1 - EPSILON] before the cross-entropy.


def sha256(data: bytes) -> str:
    """Hex SHA-256 of a byte string."""
    return hashlib.sha256(data).hexdigest()


def normalize(name: str) -> str:
    """Folder name in the service's class spelling: Common_Rust and Common Rust both become Common Rust."""
    return name.replace("_", " ")


def inventory(folder: Path) -> list[dict[str, Any]]:
    """Every image file below the class folders, in the sorted order Keras uses, with label, hash and size."""
    classes = sorted(p.name for p in folder.iterdir() if p.is_dir())
    if tuple(normalize(c) for c in classes) != CLASS_NAMES:
        raise SystemExit(f"{folder}: class folders {classes} do not sort into {CLASS_NAMES}")
    files = []
    for label, name in enumerate(classes):
        for path in sorted((folder / name).iterdir()):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                data = path.read_bytes()
                files.append({"path": f"{name}/{path.name}", "label": label, "sha256": sha256(data), "bytes": len(data)})
    return files


def model_hashes() -> dict[str, dict[str, str | bool]]:
    """SHA-256 of each model file and whether it starts with the pinned prefix."""
    result: dict[str, dict[str, str | bool]] = {}
    for name, prefix in MODEL_SHA256.items():
        digest = sha256((MODEL_DIR / name).read_bytes())
        result[name] = {"sha256": digest, "matches_pinned": digest.startswith(prefix)}
    return result


def notebook_pass(test_dir: Path) -> tuple[list[str], list[list[float]]]:
    """File paths and class probabilities from the notebook's loading pipeline and the serving signature."""
    dataset = tf.keras.utils.image_dataset_from_directory(test_dir, image_size=IMAGE_SIZE, batch_size=BATCH_SIZE, shuffle=False, verbose=False)
    predict = tf.saved_model.load(str(MODEL_DIR)).signatures["serving_default"]
    probabilities: list[list[float]] = []
    for images, _ in dataset:
        probabilities.extend(predict(tf.cast(images, tf.float32))["dense"].numpy().tolist())
    paths = [str(Path(p).relative_to(test_dir)) for p in dataset.file_paths]
    return paths, probabilities


def service_prediction(url: str, path: Path) -> tuple[str | None, str | None]:
    """Upload one image to the loopback Flask endpoint as a multipart field named image; return (class, error)."""
    parts = urlsplit(url)
    if parts.scheme != "http" or parts.hostname != "127.0.0.1" or parts.port is None:
        raise SystemExit(f"--flask-url must be http://127.0.0.1:<PORT>/<PATH>; got {url}")
    boundary = uuid.uuid4().hex
    head = f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
    body = head.encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=60)
    try:
        connection.request("POST", parts.path, body=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        response = connection.getresponse()
        payload = response.read()
    except OSError as exc:
        return None, f"connection failed: {exc}"
    finally:
        connection.close()
    if response.status != 200:
        return None, f"HTTP {response.status}: {payload[:200].decode(errors='replace')}"
    return str(json.loads(payload)["prediction"]), None


def metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    """Accuracy, confusion matrix (rows are true classes) and per-class precision, recall and F1."""
    size = len(CLASS_NAMES)
    matrix = [[0] * size for _ in range(size)]
    for truth, guess in zip(labels, predictions, strict=True):
        matrix[truth][guess] += 1
    per_class = {}
    for index, name in enumerate(CLASS_NAMES):
        true_positive = matrix[index][index]
        predicted = sum(row[index] for row in matrix)
        actual = sum(matrix[index])
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {"support": actual, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    correct = sum(matrix[i][i] for i in range(size))
    return {"images": len(labels), "correct": correct, "accuracy": correct / len(labels), "confusion_matrix": matrix, "per_class": per_class}


def zip_lineage(source_zip: Path, files: list[dict[str, Any]]) -> dict[str, Any]:
    """How many test images are byte-identical to an entry of the source archive, and the archive's own hash."""
    hashes = set()
    with zipfile.ZipFile(source_zip) as archive:
        for entry in archive.infolist():
            if not entry.is_dir():
                hashes.add(sha256(archive.read(entry)))
    matched = sum(f["sha256"] in hashes for f in files)
    return {"zip_sha256": sha256(source_zip.read_bytes()), "zip_bytes": source_zip.stat().st_size, "test_images_in_zip": matched, "test_images": len(files)}


def git_state() -> dict[str, Any]:
    """Code revision and uncommitted paths at run time."""
    revision = run_command("git", ["rev-parse", "HEAD"], cwd=ROOT, timeout=30, check=True).stdout.strip()
    status = run_command("git", ["status", "--porcelain"], cwd=ROOT, timeout=30, check=True).stdout.splitlines()
    return {"revision": revision, "uncommitted_paths": [line[3:] for line in status]}


def check(name: str, expected: Any, observed: Any, passed: bool) -> dict[str, Any]:
    """One assertion row for the report."""
    return {"check": name, "expected": expected, "observed": observed, "status": "pass" if passed else "fail"}


def write_markdown(report: dict[str, Any], path: Path) -> None:
    """Human-readable summary of the JSON report."""
    offline = report["notebook_pipeline"]
    lines = [
        f"# Model Evaluation {report['run_id']}",
        "",
        f"Revision `{report['git']['revision']}`; TensorFlow {report['environment']['tensorflow']}; Python {report['environment']['python']}.",
        "",
        "## Checks",
        "",
        "| Check | Expected | Observed | Status |",
        "| --- | --- | --- | --- |",
        *(f"| {c['check']} | {c['expected']} | {c['observed']} | {c['status']} |" for c in report["checks"]),
        "",
        "## Notebook Pipeline",
        "",
        f"Accuracy {offline['accuracy']:.4f} ({offline['correct']}/{offline['images']}); loss {offline['loss']:.4f}. "
        f"Notebook saved output: accuracy {NOTEBOOK['test_accuracy']:.4f}, loss {NOTEBOOK['test_loss']:.4f}.",
        "",
        "| True class | " + " | ".join(CLASS_NAMES) + " | Precision | Recall | F1 |",
        "| --- | " + " | ".join("---" for _ in CLASS_NAMES) + " | --- | --- | --- |",
    ]
    for index, name in enumerate(CLASS_NAMES):
        row, stats = offline["confusion_matrix"][index], offline["per_class"][name]
        lines.append(f"| {name} | " + " | ".join(str(v) for v in row) + f" | {stats['precision']:.4f} | {stats['recall']:.4f} | {stats['f1']:.4f} |")
    if report.get("service"):
        service = report["service"]
        lines += [
            "",
            "## Flask Service",
            "",
            f"Accuracy {service['accuracy']:.4f} ({service['correct']}/{service['images']}); errors {service['errors']}; "
            f"agreement with the notebook pipeline {service['agreement']}/{service['images']}.",
        ]
    lines += ["", "## Reproduce", "", "```bash", report["command"], "```", "", "## Limits", "", *(f"- {item}" for item in report["limits"]), ""]
    path.write_text("\n".join(lines))


def main() -> int:
    """Run both passes, check the inputs and write the report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--train-dir", type=Path)
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument("--flask-url")
    args = parser.parse_args()

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "artifacts" / "e2e" / f"model_eval_{run_id}"
    output.mkdir(parents=True, exist_ok=False)
    files = inventory(args.test_dir)
    hashes = model_hashes()
    paths, probabilities = notebook_pass(args.test_dir)
    by_path = {f["path"]: f for f in files}
    labels = [by_path[p]["label"] for p in paths]
    predictions = [max(range(len(CLASS_NAMES)), key=row.__getitem__) for row in probabilities]
    loss = sum(-math.log(min(max(row[label], EPSILON), 1 - EPSILON)) for row, label in zip(probabilities, labels, strict=True)) / len(labels)
    offline = {**metrics(labels, predictions), "loss": loss}
    for path, row, guess in zip(paths, probabilities, predictions, strict=True):
        by_path[path]["notebook_pipeline"] = {"prediction": CLASS_NAMES[guess], "probabilities": [round(p, 6) for p in row]}

    checks = [
        check("test images found", EXPECTED_TEST_COUNT, len(files), len(files) == EXPECTED_TEST_COUNT),
        check("every image classified by the notebook pipeline", len(files), len(paths), sorted(paths) == sorted(by_path)),
        check(
            "model files equal the pinned hashes",
            "4/4",
            f"{sum(bool(h['matches_pinned']) for h in hashes.values())}/4",
            all(h["matches_pinned"] for h in hashes.values()),
        ),
    ]
    report: dict[str, Any] = {"run_id": run_id, "started_utc": run_id, "git": git_state(), "model_files": hashes, "notebook_saved_output": NOTEBOOK}
    if args.train_dir:
        train = inventory(args.train_dir)
        train_hashes = {f["sha256"] for f in train}
        overlap = [f["path"] for f in files if f["sha256"] in train_hashes]
        report["train_test_overlap"] = {"train_images": len(train), "test_images_identical_to_a_train_image": len(overlap), "paths": overlap}
        checks.append(check("train images found", NOTEBOOK["train_images"], len(train), len(train) == NOTEBOOK["train_images"]))
    if args.source_zip:
        report["source_zip"] = zip_lineage(args.source_zip, files)
        checks.append(
            check(
                "test images byte-identical to the source archive",
                len(files),
                report["source_zip"]["test_images_in_zip"],
                report["source_zip"]["test_images_in_zip"] == len(files),
            )
        )
    if args.flask_url:
        service_labels, service_guesses, agreement, errors = [], [], 0, 0
        for path in paths:
            prediction, failure = service_prediction(args.flask_url, args.test_dir / path)
            by_path[path]["service"] = {"prediction": prediction, "error": failure}
            if prediction is None:
                errors += 1
                continue
            service_labels.append(by_path[path]["label"])
            service_guesses.append(CLASS_NAMES.index(prediction))
            agreement += prediction == by_path[path]["notebook_pipeline"]["prediction"]
        report["service"] = {**metrics(service_labels, service_guesses), "errors": errors, "agreement": agreement, "url": args.flask_url}
        checks.append(check("every image classified by the Flask service", len(files), len(service_labels), errors == 0))

    command = "TF_CPP_MIN_LOG_LEVEL=2 flask-app/.venv/bin/python scripts/evaluate_model.py --test-dir <DATASET>/test"
    command += " --train-dir <DATASET>/train" if args.train_dir else ""
    command += " --source-zip <KAGGLE_ZIP>" if args.source_zip else ""
    command += f" --flask-url {args.flask_url}" if args.flask_url else ""
    report.update(
        {
            "environment": {"python": platform.python_version(), "tensorflow": tf.__version__, "platform": platform.platform()},
            "command": command,
            "inputs": {"test_dir": "<DATASET>/test", "image_size": list(IMAGE_SIZE), "batch_size": BATCH_SIZE, "class_names": list(CLASS_NAMES)},
            "checks": checks,
            "notebook_pipeline": offline,
            "images": files,
            "limits": [
                "The test folder is the notebook's held-out folder; its public images may resemble training images without being byte-identical.",
                "One run on one machine; the model was saved with TensorFlow 2.7.0 and runs here on the TensorFlow version above.",
                "Accuracy on this dataset is not field accuracy: no farm images, no agronomist labels and no recommendation validation.",
                "Dataset paths are replaced by placeholders; images and this report stay local and are not committed.",
            ],
        }
    )
    (output / "report.json").write_text(json.dumps(report, indent=2))
    write_markdown(report, output / "report.md")
    failed = [c["check"] for c in checks if c["status"] != "pass"]
    sys.stdout.write(f"model evaluation {run_id}: accuracy {offline['accuracy']:.4f}, loss {loss:.4f}; {len(checks) - len(failed)}/{len(checks)} checks pass\n")
    sys.stdout.write(f"report: {output.relative_to(ROOT)}/report.md\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
