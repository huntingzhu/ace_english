#!/usr/bin/env python3
"""
Append new sentence entries to Hunting's sentences.csv.

Reads a JSON array of entry objects from stdin. Each object should have:
    original_sentence, corrected_sentence, mistakes, mistake_type
Optional keys (defaults applied):
    date_added — defaults to today's local date (YYYY-MM-DD)
    timestamp  — defaults to now in ISO 8601 local time
    status     — defaults to "new"

Behavior:
    - Loads existing sentences.csv (preserving all existing rows and progress)
    - Skips entries whose `original_sentence` already exists
      (case-insensitive + whitespace-normalized match)
    - Appends new entries
    - Rewrites the file with csv.QUOTE_ALL so every field is double-quoted —
      this defends against Excel/Numbers misparsing rows with embedded commas,
      apostrophes, or Chinese punctuation
    - Prints a human-readable summary to stdout

Usage:
    python3 append_sentences.py << 'JSON'
    [
      {"original_sentence": "He don't like coffee.",
       "corrected_sentence": "He doesn't like coffee.",
       "mistakes": "Subject-verb agreement: \"he\" takes \"doesn't\".",
       "mistake_type": "agreement"}
    ]
    JSON

Override the CSV path by setting the SENTENCES_PATH environment variable.
"""
import csv
import json
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path


# Resolve the sentences.csv path portably:
#   1. honor $SENTENCES_PATH if set (escape hatch for non-default setups)
#   2. otherwise look for the HuntingEnglish folder under the current
#      session's mount root (Claude's $HOME points to that root, e.g.
#      /sessions/<session-id>/), so the path stays valid across sessions
#   3. fall back to a glob across all session dirs as a last resort
def _resolve_default_sentences_path() -> Path:
    home = os.environ.get("HOME", "")
    if home:
        candidate = Path(home) / "mnt" / "HuntingEnglish" / "sentences.csv"
        if candidate.exists() or candidate.parent.exists():
            return candidate
    matches = sorted(Path("/sessions").glob("*/mnt/HuntingEnglish/sentences.csv"))
    if matches:
        return matches[-1]
    return Path(home or "/sessions/current") / "mnt" / "HuntingEnglish" / "sentences.csv"


DEFAULT_SENTENCES_PATH = _resolve_default_sentences_path()
HEADERS = [
    "date_added",
    "timestamp",
    "original_sentence",
    "corrected_sentence",
    "mistakes",
    "mistake_type",
    "status",
]


def _normalize_for_dedup(s: str) -> str:
    """Lowercase, collapse whitespace, strip terminal punctuation for dedup match."""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".?!。？！")
    return s


def load_existing(path: Path):
    """Return (data_rows, existing_originals_normalized_set). Empty if file missing."""
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
        orig_idx = file_headers.index("original_sentence")
    except ValueError:
        orig_idx = 2  # Fallback to schema position
    seen = {
        _normalize_for_dedup(r[orig_idx])
        for r in data_rows
        if len(r) > orig_idx and r[orig_idx].strip()
    }
    return data_rows, seen


def normalize(candidate: dict, today: str, now: str):
    """Map a JSON entry into a CSV row in HEADERS order."""
    return [
        (candidate.get("date_added") or today).strip(),
        (candidate.get("timestamp") or now).strip(),
        (candidate.get("original_sentence") or "").strip(),
        (candidate.get("corrected_sentence") or "").strip(),
        (candidate.get("mistakes") or "").strip(),
        (candidate.get("mistake_type") or "other").strip(),
        (candidate.get("status") or "new").strip(),
    ]


def main() -> int:
    sent_path = Path(os.environ.get("SENTENCES_PATH", str(DEFAULT_SENTENCES_PATH)))

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

    existing_rows, seen_originals = load_existing(sent_path)
    today = date.today().isoformat()
    now = datetime.now().replace(microsecond=0).isoformat()

    added = []
    skipped = []
    for c in candidates:
        if not isinstance(c, dict):
            skipped.append(("<non-object entry>", "invalid"))
            continue
        original = (c.get("original_sentence") or "").strip()
        if not original:
            skipped.append(("<missing 'original_sentence' field>", "invalid"))
            continue
        norm = _normalize_for_dedup(original)
        if norm in seen_originals:
            skipped.append((original, "duplicate"))
            continue
        # Default corrected_sentence to the original if not provided (assume correct)
        if not (c.get("corrected_sentence") or "").strip():
            c["corrected_sentence"] = original
        existing_rows.append(normalize(c, today, now))
        seen_originals.add(norm)
        added.append(original)

    # Atomic-ish rewrite: write to a sibling temp file then rename
    sent_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = sent_path.with_suffix(sent_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(HEADERS)
        writer.writerows(existing_rows)
    tmp_path.replace(sent_path)

    print(f"Added {len(added)} entries to {sent_path}.")
    for s in added:
        preview = s if len(s) <= 80 else s[:77] + "..."
        print(f"  + {preview}")
    if skipped:
        print(f"Skipped {len(skipped)} entries.")
        for s, reason in skipped:
            preview = s if len(s) <= 80 else s[:77] + "..."
            print(f"  - {preview} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
