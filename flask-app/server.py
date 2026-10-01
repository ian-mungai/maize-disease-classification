"""Maize leaf disease prediction service.

POST /disease-analyzer with a multipart field named "image" returns {"prediction": "<class>"}.
The service listens on the loopback interface only and loads the model once at startup.
"""

import io
import os
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
from flask import Flask, Response, jsonify, request
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

MODEL_DIR = Path(__file__).resolve().parent / "model"
CLASS_NAMES = ("Blight", "Common Rust", "Gray Leaf Spot", "Healthy")
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
HOST = "127.0.0.1"
PORT = int(os.environ.get("MAIZE_MODEL_PORT", "4040"))

_model: Any = tf.saved_model.load(str(MODEL_DIR))
_predict: Any = _model.signatures["serving_default"]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def classify(image_bytes: bytes) -> str:
    """Return the predicted class name for one encoded leaf image."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        pixels = np.asarray(img.convert("RGB"), dtype=np.float32)
    outputs = _predict(tf.constant(pixels[np.newaxis, ...]))
    index = int(tf.math.argmax(outputs["dense"], axis=1).numpy()[0])
    return CLASS_NAMES[index]


def error(message: str, status: int) -> tuple[Response, int]:
    return jsonify(error=message), status


@app.post("/disease-analyzer")
def disease_analyzer() -> tuple[Response, int]:
    upload = request.files.get("image")
    if upload is None:
        return error("Send the leaf image as a multipart field named 'image'.", 400)
    try:
        prediction = classify(upload.read())
    except (UnidentifiedImageError, OSError):
        return error("The upload is not a readable image.", 400)
    return jsonify(prediction=prediction), 200


@app.errorhandler(RequestEntityTooLarge)
def too_large(_: RequestEntityTooLarge) -> tuple[Response, int]:
    return error(f"Images must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller.", 413)


@app.errorhandler(HTTPException)
def http_error(exc: HTTPException) -> tuple[Response, int]:
    return error(exc.description or "Request failed.", exc.code or 500)


@app.errorhandler(Exception)
def unexpected_error(exc: Exception) -> tuple[Response, int]:
    app.logger.exception("Prediction failed", exc_info=exc)
    return error("Prediction failed.", 500)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
