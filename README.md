# Audio Durations — Sentence Aligner

Align your transcript to any audio file and get precise timestamps for every sentence — including silence between segments.

![screenshot](https://img.shields.io/badge/status-working-brightgreen)

## Quick start (web)

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

## Usage

1. **Upload** an audio file (WAV, MP3, M4A, OGG, FLAC, WebM)
2. **Paste** your sentence-by-sentence transcript (one sentence per line, in order)
3. **Click** "Align sentences" — the app transcribes the audio with Whisper and matches your sentences
4. **Results** show start time, end time (with trailing silence), and duration for each sentence
5. **Download** as CSV or JSON

### CLI (optional)

```bash
python align.py audio.wav sentences.txt small
```

## Google AdSense

Ad slots are placed above the form, between upload and results, and below results.

1. Open `templates/index.html` and replace:
   - `ca-pub-0000000000000000` → your AdSense publisher ID
   - `data-ad-slot="1234567890"` etc. → your ad unit slot IDs
2. Uncomment the AdSense script tag (or keep it as-is after updating)


## Oracle Cloud Free Tier deployment

### 1. Provision an instance

Create an **Ampere A1** (ARM) instance with Ubuntu 22.04+ (4 OCPUs, 24 GB RAM free). Open inbound ports **80** and **443** in the security list.

### 2. Install dependencies

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
```

### 3. Clone & set up

```bash
git clone https://github.com/ziad0ayman/audio-durations.git
cd audio-durations
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Important:** Whisper models are cached in `~/.cache/huggingface/`. The ARM model cache is compatible — `small` works well on 4 OCPUs.

### 4. Run with systemd

Create `/etc/systemd/system/audio-durations.service`:

```ini
[Unit]
Description=Audio Durations
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/audio-durations
ExecStart=/home/ubuntu/audio-durations/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 --timeout 300 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now audio-durations
```

### 5. Reverse proxy (nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

## Notes

- Audio files are processed in memory and deleted immediately — no data stored.
- Max upload size: 500 MB.
- Models are cached after first download (~1-2 GB depending on size).

## Tech

- **faster-whisper** — word-level transcription (CPU-optimized with CTranslate2)
- **Flask** — web framework
- **difflib** — fuzzy sentence matching
