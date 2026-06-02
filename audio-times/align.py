import sys
import re
from pathlib import Path
from difflib import SequenceMatcher

from faster_whisper import WhisperModel


def transcribe_with_words(audio_path: str, model_size: str = "small"):
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
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


def normalize(text: str):
    """Lowercase, strip punctuation, collapse whitespace."""
    t = re.sub(r"[^\w'\s]", " ", text).strip().lower()
    return re.sub(r"\s+", " ", t)


def tokenize(text: str):
    return normalize(text).split()


def best_match_start(query_tokens: list[str], word_list: list[str], start_pos: int = 0):
    """Find where query_tokens best matches word_list using ratio scoring."""
    best_ratio = 0.0
    best_idx = start_pos
    q = " ".join(query_tokens)

    search_end = max(start_pos, len(word_list) - len(query_tokens) - 5)
    for i in range(start_pos, search_end + 1):
        chunk = word_list[i : i + len(query_tokens)]
        c = " ".join(chunk)
        ratio = SequenceMatcher(None, q, c).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i
        if ratio == 1.0:
            break

    return best_idx, best_ratio


def align_sentences(sentences: list[str], words: list[dict]):
    word_texts = [w["word"] for w in words]
    total_duration = words[-1]["end"] if words else 0

    results = []
    word_cursor = 0

    for i, sentence in enumerate(sentences):
        tokens = tokenize(sentence)
        if not tokens:
            continue

        idx, ratio = best_match_start(tokens, word_texts, word_cursor)

        if ratio < 0.5:
            print(f"Warning: poor match ({ratio:.0%}) for sentence {i+1}: {sentence[:50]}...", file=sys.stderr)

        end_idx = min(idx + len(tokens) - 1, len(words) - 1)
        sent_start = words[idx]["start"]
        sent_end = words[end_idx]["end"]

        # include trailing silence up to the start of the next matching sentence
        if i < len(sentences) - 1:
            next_tokens = tokenize(sentences[i + 1])
            if next_tokens:
                next_idx, _ = best_match_start(next_tokens, word_texts, end_idx + 1)
                sent_end = words[next_idx]["start"]
            else:
                sent_end = total_duration
        else:
            sent_end = total_duration

        duration = sent_end - sent_start
        results.append((sentence, sent_start, sent_end, duration))
        word_cursor = end_idx + 1

    return results


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:06.3f}"
    return f"{m}:{s:06.3f}"


def debug_transcription(words: list[dict]):
    """Print the full transcription for debugging."""
    full = " ".join(w["word"] for w in words)
    print("\n--- Whisper transcription ---", file=sys.stderr)
    print(full, file=sys.stderr)
    print("--- end transcription ---\n", file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print("Usage: python align.py <audio_file> <sentences.txt> [model_size]")
        print()
        print("  sentences.txt: one sentence per line, covering all words in the audio.")
        print("  model_size:    tiny / base / small / medium / large-v3  (default: small)")
        sys.exit(1)

    audio_path = sys.argv[1]
    sentences_path = sys.argv[2]
    model_size = sys.argv[3] if len(sys.argv) > 3 else "small"

    if not Path(audio_path).exists():
        print(f"Error: audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(sentences_path).exists():
        print(f"Error: sentences file not found: {sentences_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Transcribing {audio_path} with model '{model_size}' ...", file=sys.stderr)
    words = transcribe_with_words(audio_path, model_size)
    print(f"  -> {len(words)} words detected", file=sys.stderr)

    debug = "--debug" in sys.argv
    if debug:
        debug_transcription(words)

    sentences = read_sentences(sentences_path)
    print(f"Loaded {len(sentences)} sentences from {sentences_path}", file=sys.stderr)

    results = align_sentences(sentences, words)

    print()
    print(f"{'Sentence':<60} {'Start':>12} {'End':>12} {'Duration':>10}")
    print("-" * 96)
    for sentence, start, end, dur in results:
        display = sentence[:57] + "..." if len(sentence) > 60 else sentence
        print(f"{display:<60} {format_time(start):>12} {format_time(end):>12} {dur:>8.3f}s")


if __name__ == "__main__":
    main()
