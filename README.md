# Audio Durations

Align a transcript to any audio file and get precise timestamps for every sentence — including silence between segments. Just paste the full transcript; the app splits it into sentences automatically.

![Python](https://img.shields.io/badge/python-3.8+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000, upload audio, paste transcript, click **Align sentences**.

## Usage

1. **Upload** an audio file (WAV, MP3, M4A, OGG, FLAC, WebM)
2. **Paste** your full transcript — the app splits it into sentences automatically
3. Click **Align sentences** — transcription and alignment happen in one step
4. Results show start time, end time (with trailing silence), and duration per sentence
5. Download as CSV or JSON

### CLI

```bash
python align.py audio.wav transcript.txt small
```

The transcript file should contain one sentence per line.

## Features

- **Auto-split** — paste raw transcript, the app handles sentence boundaries (`.` `!` `?`)
- **Fuzzy matching** — handles minor differences between your transcript and the transcription
- **Silence included** — each sentence's end time extends to the start of the next sentence
- **Concurrent queue** — handles multiple users with a configurable semaphore (`MAX_CONCURRENT`)
- **AdSense ready** — ad slots placed at high-visibility, non-intrusive positions
- **Contact form** — wired to email via SMTP (optional env vars)

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `PORT` | `5000` | Web server port |
| `MAX_CONCURRENT` | `2` | Max parallel alignments |
| `CONTACT_EMAIL` | — | Email to receive contact form messages |
| `SMTP_HOST` | — | SMTP server for contact form |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP login |
| `SMTP_PASS` | — | SMTP password |

## AdSense

Ad slots are placed above the form, between upload and results, and below results.

1. Open `templates/index.html`
2. Replace `ca-pub-0000000000000000` with your AdSense publisher ID
3. Replace slot IDs (`1234567890`, etc.) with your ad unit IDs

## Tech

- **faster-whisper** — word-level transcription (CTranslate2, CPU-optimized)
- **Flask** — web framework
- **difflib** — fuzzy sentence matching
- **Gunicorn** — production WSGI server

## License

MIT
