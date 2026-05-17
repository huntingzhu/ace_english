---
name: add-english-words
description: Append new English vocabulary entries (single words, phrases, idioms, or example sentences) to Hunting's flashcard database at databases/vocab.csv in the ace_english repo, enriched with IPA pronunciation, Simplified Chinese translation, a natural example sentence, and an auto-detected category. Use this skill whenever Hunting wants to save, add, remember, log, or memorize new English vocabulary — including casual phrasings like "add these to my flashcards", "I learned X today", "help me remember Y", "save this to my vocab", "记一下这些词", or when Hunting pastes a list of words/phrases they want to study. Also trigger when Hunting references the flashcard tool or vocab.csv in the context of adding new material. Do NOT trigger for standalone translation questions, grammar help, or English usage questions that don't involve persisting to the flashcard database.
---

# Add English Words to Hunting's Flashcard Database

This skill appends new vocabulary entries to `databases/vocab.csv` at the root of the `ace_english` repo — the CSV database that powers the flashcard tool (`apps/flashcards.html`).

**Canonical path**: `<repo-root>/databases/vocab.csv` (i.e. `/Users/hongzhaozhu/Documents/code/ace_english/databases/vocab.csv`). The bundled script resolves this relative to its own location, so it stays valid even if the repo moves. Override by setting the `VOCAB_PATH` environment variable.

Each entry is enriched with pronunciation, a Simplified Chinese translation, a natural example sentence, and a category.

## Schema

`vocab.csv` has these columns, every field wrapped in double quotes:

| column | meaning |
|---|---|
| `date_added` | `YYYY-MM-DD` in local time — defaults to today |
| `word` | the word / phrase / idiom / sentence as-is |
| `pronunciation` | IPA-style phonetic transcription wrapped in slashes, e.g. `/prɑːd/` |
| `translation` | Simplified Chinese; multiple meanings separated by `；` (Chinese semicolon); brief parenthetical context is welcome, e.g. `生产环境（production 的口语缩写）` |
| `example` | one natural English example sentence that actually illustrates the meaning in context |
| `category` | one of `word` / `phrase` / `idiom` / `sentence` |
| `status` | always `new` for fresh entries (the HTML tool updates this to `learning` / `known` later) |

### Category guide

- `word` — a single word (e.g. `dilemma`, `bureaucracy`).
- `phrase` — multi-word collocation with a *literal* compositional meaning (e.g. `spin up`, `rule out`, `head out`).
- `idiom` — multi-word with a *figurative* / non-literal meaning (e.g. `kick the bucket`, `spill the beans`, `break a leg`).
- `sentence` — a full sentence or sentence pattern Hunting wants to remember (e.g. `Since this is prod, we'll deploy it tomorrow morning.`).

When torn between `phrase` and `idiom`, ask: "does the meaning follow from the individual words?" If yes → `phrase`. If no → `idiom`.

## Workflow

### 1. Collect the candidates

Extract every word / phrase / sentence Hunting wants to save. If the input is a loose list, parse it into discrete entries. If it's ambiguous (e.g. "add these" with no clear list), briefly confirm before enriching.

### 2. Check for duplicates

Read `databases/vocab.csv` first (resolved relative to the repo root). If a candidate's `word` (case-insensitive) is already there, surface it and skip by default. Never overwrite — Hunting's flashcard progress (the `learning` / `known` states) would be clobbered and the re-entry wouldn't teach anything new.

### 3. Enrich each entry

For each candidate, produce:

- **pronunciation** — IPA in slashes. Use General American for US-English words, Received Pronunciation for British-tinged words, and keep foreign-origin pronunciations (e.g. `Hermès` → `/erˈmɛz/`).
- **translation** — Simplified Chinese. Keep it tight and precise. If the word has multiple distinct senses Hunting is likely to encounter, include them separated by `；`. Add a brief parenthetical when the Chinese word alone could mislead (e.g. `pod` → `Pod（Kubernetes 中的最小部署单元）`).
- **example** — a natural sentence that makes the meaning self-evident. If Hunting already provided a sentence in their message, use it verbatim (just clean up obvious typos). Prefer contexts Hunting will actually encounter — software engineering, casual conversation, work situations — over textbook English.
- **category** — per the guide above.

If Hunting explicitly provided a translation or example, honor it — don't override. For proper nouns with diacritics (Hermès, café, naïve), preserve them.

### 4. Confirm briefly

Show Hunting a compact preview — one line per entry with word → translation and the example. Ask "add these?" unless they already said something like "just add them" or "no need to confirm."

Keep the preview lean. A wall of text here defeats the purpose of a quick capture tool.

### 5. Append via the bundled script

Use `scripts/append_words.py`. The script:

- Wraps every field in double quotes (matching existing CSV style).
- Fills in `date_added` (today, local time) and `status` (`new`) automatically.
- Skips duplicates (case-insensitive match on `word`).
- Rewrites the file atomically with `csv.QUOTE_ALL`, so embedded commas, Chinese punctuation, and apostrophes are all safely escaped.

Never write to `databases/vocab.csv` with the Write or Edit tool directly — that's how quoting gets inconsistent and opens bugs when Hunting later opens the file in Excel or Numbers. Always go through this script (or, as a fallback, a one-off Python snippet using `csv.writer(..., quoting=csv.QUOTE_ALL)`).

Invocation:

```bash
python3 "$SKILL_DIR/scripts/append_words.py" << 'JSON'
[
  {
    "word": "ramp up",
    "pronunciation": "/ræmp ʌp/",
    "translation": "逐步增加；扩大规模",
    "example": "We need to ramp up hiring next quarter.",
    "category": "phrase"
  }
]
JSON
```

In practice, locate the script relative to this SKILL.md — it's at `scripts/append_words.py` in the same skill folder. The skill folder path is visible in the "Base directory for this skill" line when this skill is loaded.

### 6. Report back

Tell Hunting how many were added and skipped. Include a link to the flashcard tool so they can immediately flip through the new cards:

`[Open flashcards](apps/flashcards.html)`

Keep the report compact — a count and a short list, not a paragraph per entry.

## Design principles

- **Preserve Hunting's progress.** The CSV is a living database — never truncate, reorder, or rewrite existing rows' content. Only append.
- **Quality over quantity.** Three well-enriched entries beat twenty with generic examples or vague translations. If an entry needs real thought (obscure idiom, multi-sense word), take it.
- **Match the house style.** Before enriching, glance at the last few rows of `vocab.csv`. Match tone — concise translations with optional parenthetical context, examples that sound like Hunting's actual life (software work, everyday conversation), semicolons to separate meanings.
- **Be defensive with CSV.** Always use `QUOTE_ALL` quoting so Hunting can open the file in Excel / Numbers / a text editor without rows breaking on commas or Chinese punctuation.

## Examples

### Input: a quick list

> "Add 'ramp up' and 'flaky test' to my vocab."

Enriched preview:

- `ramp up` → `逐步增加；扩大规模` — *We need to ramp up hiring next quarter.* (phrase)
- `flaky test` → `不稳定的测试（时通过时失败）` — *This flaky test keeps blocking the build.* (phrase)

"Add these? (y/n)"

### Input: user gave a translation

> "I learned 'burn the midnight oil' today, it means 开夜车."

First check vocab.csv. If present → flag as duplicate. If not → honor the user's translation (`开夜车`), fill in pronunciation (`/bɜːrn ðə ˈmɪdnaɪt ɔɪl/`), an example (`She burned the midnight oil to finish the report.`), and category `idiom`.

### Input: a sentence pattern

> "Save this: 'Let's just rule it out.'"

Category is `sentence` if Hunting wants to remember the whole pattern, or `phrase` (`rule out`) if just the verb. Ask if ambiguous, default to `sentence` if they quoted it as a full line.
