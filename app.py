import os
import tempfile
import json
import time
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import secrets

from align import align, format_time

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = Path(tempfile.gettempdir()) / "audio-durations-uploads"
app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]

MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", 2))
_concurrency = threading.BoundedSemaphore(MAX_CONCURRENT)
_queue_count = 0
_queue_lock = threading.Lock()


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            return jsonify({"error": "All fields required"}), 400
        app.logger.info("Contact from %s (%s): %s", name, email, message[:100])
        return jsonify({"ok": True})
    return render_template("contact.html")


def cleanup_old_files():
    import time
    now = time.time()
    for f in app.config["UPLOAD_FOLDER"].iterdir():
        if f.is_file() and now - f.stat().st_mtime > 3600:
            f.unlink(missing_ok=True)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", model_sizes=MODEL_SIZES)


@app.route("/align", methods=["POST"])
def do_align():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "No audio file selected"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported format: {ext}. Allowed: {', '.join(ALLOWED_EXT)}"}), 400

    import re as _re

    raw = request.form.get("sentences", "").strip()
    if not raw:
        return jsonify({"error": "No transcript provided"}), 400

    raw = raw.replace("\n", " ")
    raw = _re.sub(r"\s+", " ", raw)

    sentences = _re.split(r"(?<=[.!?])\s+", raw)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentences = [s for s in sentences if s not in (".", "!", "?")]

    if not sentences:
        return jsonify({"error": "No sentences found in transcript"}), 400

    model_size = request.form.get("model_size", "small")
    if model_size not in MODEL_SIZES:
        model_size = "small"

    filename = secure_filename(file.filename) or "audio" + ext
    audio_path = app.config["UPLOAD_FOLDER"] / f"{secrets.token_hex(8)}_{filename}"
    file.save(str(audio_path))

    global _queue_count
    with _queue_lock:
        position = _queue_count + 1
        _queue_count += 1

    acquired = _concurrency.acquire(blocking=False)
    if not acquired:
        return jsonify({"error": "Server is busy", "queue": position}), 503

    try:
        with _queue_lock:
            _queue_count -= 1
        results_raw = align(str(audio_path), sentences, model_size)
    except Exception as e:
        return jsonify({"error": f"Alignment failed: {str(e)}"}), 500
    finally:
        _concurrency.release()
        audio_path.unlink(missing_ok=True)
        cleanup_old_files()

    results = []
    for r in results_raw:
        results.append({
            "sentence": r["sentence"],
            "start": r["start"],
            "end": r["end"],
            "duration": r["duration"],
            "start_fmt": format_time(r["start"]),
            "end_fmt": format_time(r["end"]),
        })

    return jsonify({"results": results, "total": len(results)})


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    if not data or "results" not in data:
        return jsonify({"error": "No results provided"}), 400

    fmt = data.get("format", "csv")
    results = data["results"]

    if fmt == "json":
        import json as json_lib
        body = json_lib.dumps(results, indent=2, ensure_ascii=False)
        return body, 200, {"Content-Type": "application/json", "Content-Disposition": "attachment; filename=alignment.json"}
    elif fmt == "csv":
        import io
        import csv
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(["Sentence", "Start (s)", "End (s)", "Duration (s)", "Start", "End"])
        for r in results:
            cw.writerow([r["sentence"], r["start"], r["end"], r["duration"], r["start_fmt"], r["end_fmt"]])
        return (
            si.getvalue(),
            200,
            {
                "Content-Type": "text/csv",
                "Content-Disposition": "attachment; filename=alignment.csv",
            },
        )
    return jsonify({"error": "Unsupported format"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
