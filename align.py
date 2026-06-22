import sys
import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import Optional

from faster_whisper import WhisperModel


_model: Optional[WhisperModel] = None


def get_model(model_size: str = "small"):
    global _model
    if _model is None:
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe_with_words(audio_path: str, model_size: str = "small"):
    model = get_model(model_size)
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for seg in segments:
        for w in seg.words:
            words.append({
                "word": w.word.strip().lower(),
                "start": w.start,
                "end": w.end,
            })
    return words


def read_sentences(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def split_sentences(text: str) -> list[str]:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [s.strip() for s in parts if s.strip()]
    return [s for s in parts if s not in (".", "!", "?")]


def normalize(text: str):
    t = re.sub(r"[^\w'\s]", " ", text).strip().lower()
    return re.sub(r"\s+", " ", t)


def tokenize(text: str):
    return normalize(text).split()


def best_match_start(query_tokens: list[str], word_list: list[str]):
    best_ratio = 0.0
    best_idx = 0
    q = " ".join(query_tokens)
    n = len(query_tokens)

    for i in range(len(word_list) - n + 1):
        chunk = word_list[i : i + n]
        c = " ".join(chunk)
        ratio = SequenceMatcher(None, q, c).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i
        if ratio == 1.0:
            break

    return best_idx, best_ratio


def diff_words(user_tokens: list[str], audio_tokens: list[str]) -> str:
    matcher = SequenceMatcher(None, user_tokens, audio_tokens)
    parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for w in audio_tokens[j1:j2]:
                parts.append(f"<span class='dw-match'>{w}</span>")
        elif tag == "replace":
            for w in audio_tokens[j1:j2]:
                parts.append(f"<span class='dw-diff'>{w}</span>")
        elif tag == "delete":
            pass
        elif tag == "insert":
            for w in audio_tokens[j1:j2]:
                parts.append(f"<span class='dw-extra'>{w}</span>")
    return " ".join(parts)


def align_sentences(sentences: list[str], words: list[dict]):
    word_texts = [w["word"] for w in words]
    total_duration = words[-1]["end"] if words else 0

    # find best position for each sentence independently
    candidates = []
    for i, sentence in enumerate(sentences):
        tokens = tokenize(sentence)
        if not tokens:
            continue
        idx, ratio = best_match_start(tokens, word_texts)
        candidates.append((idx, i, sentence, tokens, ratio))

    candidates.sort(key=lambda x: x[0])

    # each sentence ideally claims pos .. pos+len(tokens)
    spans = []
    for k, (pos, sen_idx, sentence, tokens, ratio) in enumerate(candidates):
        ideal_end = min(pos + len(tokens), len(words))
        spans.append((pos, ideal_end, sen_idx, sentence, tokens, ratio))

    # resolve overlaps: split overlapping region at midpoint
    resolved = []
    prev_end = 0
    for k, (pos, ideal_end, sen_idx, sentence, tokens, ratio) in enumerate(spans):
        start = max(pos, prev_end)

        if k < len(spans) - 1:
            next_pos = spans[k + 1][0]
            if ideal_end > next_pos:
                # overlap: split halfway between the two start positions
                split = (pos + next_pos) // 2
                end = max(start, split)
            else:
                end = ideal_end
        else:
            end = len(words)

        if start >= end:
            end = ideal_end
        if start >= len(words):
            break

        resolved.append((start, end, sen_idx, sentence, tokens, ratio))
        prev_end = end

    results = []
    for start, end, sen_idx, sentence, tokens, ratio in resolved:
        sent_start = words[start]["start"]
        if end < len(words):
            sent_end = words[end]["start"]
        else:
            sent_end = total_duration

        duration = sent_end - sent_start
        matched_words = [w["word"] for w in words[start:end]]
        matched_text = " ".join(matched_words)
        diff = diff_words(tokens, matched_words)

        results.append({
            "number": len(results) + 1,
            "sentence": sentence,
            "matched_text": matched_text,
            "diff_html": diff,
            "confidence": round(ratio, 3),
            "start": sent_start,
            "end": sent_end,
            "duration": round(duration, 3),
        })

    return results


def align(audio_path: str, sentences: list[str], model_size: str = "small") -> list[dict]:
    words = transcribe_with_words(audio_path, model_size)
    return align_sentences(sentences, words)


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:06.3f}"
    return f"{m}:{s:06.3f}"


def main():
    if len(sys.argv) < 3:
        print("Usage: python align.py <audio_file> <transcript.txt> [model_size] [--split]")
        print()
        print("  transcript.txt:  one sentence per line, or a full transcript with --split")
        print("  model_size:      tiny / base / small / medium / large-v3  (default: small)")
        print("  --split:         split the file into sentences by punctuation automatically")
        sys.exit(1)

    audio_path = sys.argv[1]
    text_path = sys.argv[2]
    model_size = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "small"
    do_split = "--split" in sys.argv

    if not Path(audio_path).exists():
        print(f"Error: audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(text_path).exists():
        print(f"Error: file not found: {text_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Transcribing {audio_path} with model '{model_size}' ...", file=sys.stderr)

    if do_split:
        with open(text_path, "r", encoding="utf-8") as f:
            raw = f.read()
        sentences = split_sentences(raw)
    else:
        sentences = read_sentences(text_path)

    print(f"Loaded {len(sentences)} sentences", file=sys.stderr)

    results = align(audio_path, sentences, model_size)
    print(f"  -> {len(results)} sentences aligned", file=sys.stderr)

    debug = "--debug" in sys.argv
    if debug:
        words = transcribe_with_words(audio_path, model_size)
        full = " ".join(w["word"] for w in words)
        print("\n--- Whisper transcription ---", file=sys.stderr)
        print(full, file=sys.stderr)
        print("--- end transcription ---\n", file=sys.stderr)

    print()
    header = f"{'#':>3} {'Your sentence':<55} {'Match':>6} {'Start':>12} {'End':>12} {'Duration':>10}"
    print(header)
    print("-" * len(header))
    for i, r in enumerate(results, 1):
        display = r["sentence"][:52] + "..." if len(r["sentence"]) > 55 else r["sentence"]
        print(f"{i:>3} {display:<55} {r['confidence']*100:>5.0f}% {format_time(r['start']):>12} {format_time(r['end']):>12} {r['duration']:>8.3f}s")

    print(file=sys.stderr)
    print("Shown: your sentence | match confidence | start | end | duration", file=sys.stderr)
    print("To see what the audio actually said, use the web UI or download CSV/JSON.", file=sys.stderr)


if __name__ == "__main__":
    main()
