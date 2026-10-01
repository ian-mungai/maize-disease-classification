/** Verify the historical source without importing or running its application code. */
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifestPath = join(root, "docs/source_manifest.json");
// The source manifest stays local. GitHub CI runs without it: per-file hash checks are skipped there,
// while the outgoing-tree, notebook and model checks below still run. Locally the manifest is required.
const inCi = process.env.CI === "true";
if (!existsSync(manifestPath) && !inCi) {
    process.stderr.write("docs/source_manifest.json is missing; the local archive check needs it.\n");
    process.exit(1);
}
const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, "utf8")) : { source_commit: null, files: [] };
const assertions = [];
const record = (scenario, pass, observed) => assertions.push({ scenario, status: pass ? "pass" : "fail", observed });
const digest = (data) => createHash("sha256").update(data).digest("hex");
const modelFiles = {
    "flask-app/model/keras_metadata.pb": "0807cda6ee63f4f6cdecd9549e84ec55b5cbc381971f28ac24ed5f807ffa3025",
    "flask-app/model/saved_model.pb": "fa1d0d1b6869bede46f47122f34a56b02bda3a8dfe04f606f51676ccd88ab429",
    "flask-app/model/variables/variables.index": "427517639547a69de390d2ab4818cae59705f60ef4e9d7c023137339dd6f3388",
    "flask-app/model/variables/variables.data-00000-of-00001": "8644cfac537f29062872e2528907e983d63f9084f75a49539582268e4c52e212",
};

for (const file of manifest.files) {
    const target = join(root, file.path);
    if (file.treatment === "excluded_local_noise") {
        record(`excluded ${file.path}`, !existsSync(target), "file must be absent");
    } else if (file.treatment === "preserved") {
        const matches = existsSync(target) && digest(readFileSync(target)) === file.sha256;
        record(`preserved ${file.path}`, matches, matches ? file.sha256 : "file missing or changed");
    }
}

function inspect(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
        if ([".git", ".agent_handoff", ".enjoy-logs", ".venv", ".tools"].includes(entry.name)) continue;
        if (directory === root && entry.isDirectory() && [".mypy_cache", ".ruff_cache"].includes(entry.name)) continue;
        const path = join(directory, entry.name);
        if (entry.isSymbolicLink()) {
            record("no outgoing symlink", false, path.slice(root.length + 1));
        } else if (entry.isDirectory()) {
            if (["node_modules", "vendor", "__pycache__"].includes(entry.name)) record("no generated dependency directory", false, entry.name);
            else inspect(path);
        } else if (/\.sql$|\.sqlite$|\.db$|\.pem$|\.key$|\.pyc$|\.log$|^\.DS_Store$|^\.env$/.test(entry.name)) {
            record("no private or generated file", false, path.slice(root.length + 1));
        }
    }
}
inspect(root);

const notebook = JSON.parse(readFileSync(join(root, "Maize_Diseases_Detection_Model.ipynb"), "utf8"));
record("notebook remains parseable", notebook.nbformat === 4 && notebook.cells.length === 19, "nbformat 4, 19 cells expected");
for (const [path, sha256] of Object.entries(modelFiles)) {
    const target = join(root, path);
    const matches = existsSync(target) && digest(readFileSync(target)) === sha256;
    record(`original model file ${path}`, matches, matches ? sha256 : "file missing or changed");
}
const report = {
    source_commit: manifest.source_commit,
    manifest: manifest.files.length ? "checked" : "absent in CI: per-file hash checks skipped",
    assertions,
    failed: assertions.filter((item) => item.status === "fail").length,
    boundary: "Source-preservation verification only. Separate model-format review does not establish application execution, inference behavior, retraining, fresh accuracy or image redistribution rights.",
    reproduction: "node scripts/verify_archive.mjs",
};
const reportPath = join(root, "artifacts/e2e/archive_review/report.json");
mkdirSync(dirname(reportPath), { recursive: true });
writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
process.stdout.write(`Archive assertions: ${assertions.length - report.failed}/${assertions.length} passed${manifest.files.length ? "" : " (manifest absent in CI; per-file hash checks skipped)"}\n`);
process.exitCode = report.failed ? 1 : 0;
