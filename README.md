# Audio Sentence Aligner

Align your own sentence-by-sentence transcript to an audio file and get start time, end time, and duration (including trailing silence) for each sentence.

## How it works

1. Transcribes the audio with word-level timestamps using [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
2. Matches each of your sentences against the transcription using fuzzy text alignment
3. Extends each sentence's end time to include any silence before the next sentence
4. Outputs a table with start, end, and duration for every sentence

## Requirements

- Python 3.8+
- `pip install -r requirements.txt`

## Usage

```
python align.py <audio_file> <sentences.txt> [model_size] [--debug]
```

### Arguments

| Argument       | Description |
|----------------|-------------|
| `audio_file`   | Path to audio file (WAV, MP3, etc.) |
| `sentences.txt` | Text file with **one sentence per line**, covering **all words** in the audio in order |
| `model_size`   | Whisper model size: `tiny`, `base`, `small` (default), `medium`, `large-v3` |
| `--debug`      | Print the raw Whisper transcription for troubleshooting |

### Example

```
python align.py lecture.wav my_sentences.txt medium
```

Output:

```
Sentence                                                        Start          End   Duration
------------------------------------------------------------------------------------------------
The bridge that connects our safety goals to actual daily...     0:00.000     0:08.280    8.280s
In the early 1970s, the United States established a basel...     0:08.280     0:20.280   12.000s
```

Times are in `m:ss.fff` or `h:mm:ss.fff` format. Duration is in seconds.

### Sentences file format

```
The bridge that connects our safety goals to actual daily results is a structured management system.
In the early 1970s, the United States established a baseline for this with the Occupational Safety and Health Act.
```

## Model sizes

| Model | Notes |
|-------|-------|
| `tiny`  | Fastest, least accurate |
| `base`  | Good for clean audio |
| `small` | **Recommended** — good balance |
| `medium`| Slower, more accurate |
| `large-v3` | Most accurate, slowest |

Models are downloaded automatically on first run. For GPU support: `pip install faster-whisper[cuda]`.
