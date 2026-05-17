#!/usr/bin/env python3
"""
Append new vocabulary entries to Hunting's vocab.csv.

Reads a JSON array of entry objects from stdin. Each object should have:
    word, pronunciation, translation, example, category
Optional keys (defaults applied):
    date_added — defaults to today's local date (YYYY-MM-DD)
    status     — defaults to "new"

Behavior:
    - Loads existing vocab.csv (preserving all existing rows and progress)
    - Skips entries whose `word` already exists (case-insensitive match)
    - Appends new entries
    - Rewrites the file with csv.QUOTE_ALL so every field is double-quoted —
      this defends against Excel/Numbers misparsing rows with embedded commas
      or Chinese punctuation
    - Prints a human-readable summary to stdout

Usage:
    python3 append_words.py << 'JSON'
    [
      {"word": "ramp up", "pronunciation": "/ræmp ʌp/",
       "translation": "逐步增加", "example": "We need to ramp up hiring.",
       "category": "phrase"}
    ]
    JSON

Override the CSV path by setting the VOCAB_PATH environment variable.
"""
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path

# Resolve the vocab.csv path portably:
#   1. honor $VOCAB_PATH if set (escape hatch for non-default setups)
#   2. otherwise look for the HuntingEnglish folder under the current
#      session's mount root (Claude's $HOME points to that root, e.g.
#      /sessions/<session-id>/), so the path stays valid across sessions
#   3. fall back to a glob across all session dirs as a last resort
def _resolve_default_vocab_path() -> Path:
    home = os.environ.get("HOME", "")
    if home:
        candidate = Path(home) / "mnt" / "HuntingEnglish" / "databases" / "vocab.csv"
        if candidate.exists() or candidate.parent.exists():
            return candidate
    # Last-ditch: glob /sessions/*/mnt/HuntingEnglish/databases/vocab.csv
    matches = sorted(Path("/sessions").glob("*/mnt/HuntingEnglish/databases/vocab.csv"))
    if matches:
        return matches[-1]
    # Nothing exists yet — return the most likely future path so error msgs
    # point somewhere useful
    return Path(home or "/sessions/current") / "mnt" / "HuntingEnglish" / "databases" / "vocab.csv"


DEFAULT_VOCAB_PATH = _resolve_default_vocab_path()
HEADERS = [
    "date_added",
    "word",
    "pronunciation",
    "translation",
    "example",
    "category",
    "status",
]


def load_existing(path: Path):
    """Return (data_rows, existing_words_lowercase_set). Empty if file missing."""
    if not path.exists():
        return [], set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return [], set()
    file_headers = rows[0]
    data_rows = rows[1:]
    try:
        word_idx = file_headers.index("word")
    except ValueError:
        word_idx = 1  # Fallback to schema position
    seen = {
        r[word_idx].strip().lower()
        for r in data_rows
        if len(r) > word_idx and r[word_idx].strip()
    }
    return data_rows, seen


def normalize(candidate: dict, today: str):
    """Map a JSON entry into a CSV row in HEADERS order."""
    word = (candidate.get("word") or "").strip()
    return [
        (candidate.get("date_added") or today).strip(),
        word,
        (candidate.get("pronunciation") or "").strip(),
        (candidate.get("translation") or "").strip(),
        (candidate.get("example") or "").strip(),
        (candidate.get("category") or "word").strip(),
        (candidate.get("status") or "new").strip(),
    ]


def main() -> int:
    vocab_path = Path(os.environ.get("VOCAB_PATH", str(DEFAULT_VOCAB_PATH)))

    raw = sys.stdin.read().strip()
    if not raw:
        print("ERROR: no JSON provided on stdin", file=sys.stderr)
        return 1
    try:
        candidates = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON on stdin — {e}", file=sys.stderr)
        return 1
    if not isinstance(candidates, list):
        print("ERROR: expected a JSON array at the top level", file=sys.stderr)
        return 1

    existing_rows, seen_words = load_existing(vocab_path)
    today = date.today().isoformat()

    added = []
    skipped = []
    for c in candidates:
        if not isinstance(c, dict):
            skipped.append(("<non-object entry>", "invalid"))
            continue
        word = (c.get("word") or "").strip()
        if not word:
            skipped.append(("<missing 'word' field>", "invalid"))
            continue
        if word.lower() in seen_words:
            skipped.append((word, "duplicate"))
            continue
        existing_rows.append(normalize(c, today))
        seen_words.add(word.lower())
        added.append(word)

    # Atomic-ish rewrite: write to a sibling temp file then rename
    vocab_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = vocab_path.with_suffix(vocab_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(HEADERS)
        writer.writerows(existing_rows)
    tmp_path.replace(vocab_path)

    print(f"Added {len(added)} entries to {vocab_path}.")
    for w in added:
        print(f"  + {w}")
    if skipped:
        print(f"Skipped {len(skipped)} entries.")
        for w, reason in skipped:
            print(f"  - {w} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
