import os
import json
import time
import smtplib
import threading
import tempfile
import secrets
from pathlib import Path
from email.message import EmailMessage
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename

from align import align, split_sentences, format_time

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


def send_contact_email(name, email, message):
    to = os.environ.get("CONTACT_EMAIL", "")
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not to or not smtp_host:
        app.logger.info("Contact from %s (%s): %s", name, email, message[:100])
        return

    msg = EmailMessage()
    msg["Subject"] = f"Audio Durations contact from {name}"
    msg["From"] = smtp_user
    msg["To"] = to
    msg.set_content(f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")

    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            return jsonify({"error": "All fields required"}), 400
        try:
            send_contact_email(name, email, message)
        except Exception as e:
            app.logger.error("Failed to send contact email: %s", e)
            return jsonify({"error": "Failed to send. Try again later."}), 500
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

    raw = request.form.get("sentences", "").strip()
    if not raw:
        return jsonify({"error": "No transcript provided"}), 400

    mode = request.form.get("mode", "auto")
    if mode == "auto":
        sentences = split_sentences(raw)
    else:
        sentences = [s.strip() for s in raw.split("\n") if s.strip()]

    if not sentences:
        return jsonify({"error": "No sentences found in transcript"}), 400

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
            "number": r["number"],
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
        body = json.dumps(results, indent=2, ensure_ascii=False)
        return body, 200, {"Content-Type": "application/json", "Content-Disposition": "attachment; filename=alignment.json"}
    elif fmt == "csv":
        import io
        import csv
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(["#", "Sentence", "Start (s)", "End (s)", "Duration (s)", "Start", "End"])
        for r in results:
            cw.writerow([r["number"], r["sentence"], r["start"], r["end"], r["duration"], r["start_fmt"], r["end_fmt"]])
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
