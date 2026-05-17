---
name: add-english-sentences
description: Append new sentences with grammar corrections to Hunting's sentence-study database at databases/sentences.csv in the ace_english repo. Each entry stores the original sentence, a grammar-checked corrected version, an explanation of the mistakes, and a mistake_type tag (tense, agreement, article, word_choice, syntax, preposition, etc.). Use this skill whenever Hunting wants to save, log, remember, or memorize a sentence — including phrasings like "save this sentence", "remember this grammar mistake", "add this to my sentence flashcards", "fix this and remember it", "记一下这句话", or when Hunting pastes sentences to grammar-check and store. Also trigger when Hunting references sentences.csv or sentence_flashcards.html in the context of saving sentence-level material. Do NOT trigger for single-word/phrase additions (use add-english-words instead) or for pure grammar Q&A that doesn't involve persisting to the database.
---

# Add English Sentences to Hunting's Grammar-Memorization Database

This skill appends grammar-checked sentence entries to `databases/sentences.csv` at the root of the `ace_english` repo — the CSV database that powers the sentence flashcard tool (`apps/sentence_flashcards.html`).

**Canonical path**: `<repo-root>/databases/sentences.csv` (i.e. `/Users/hongzhaozhu/Documents/code/ace_english/databases/sentences.csv`). The bundled script resolves this relative to its own location, so it stays valid even if the repo moves. Override by setting the `SENTENCES_PATH` environment variable.

Each entry stores the user's original sentence (warts and all), the corrected version, a clear written explanation of what was wrong, and a mistake-type tag for filtering.

## Schema

`sentences.csv` has these columns, every field wrapped in double quotes:

| column | meaning |
|---|---|
| `date_added` | `YYYY-MM-DD` in local time — defaults to today |
| `timestamp` | ISO 8601 local time, e.g. `2026-05-16T14:30:00` — defaults to now |
| `original_sentence` | the sentence as Hunting wrote / asked it, including mistakes |
| `corrected_sentence` | the grammar-checked, natural-English version |
| `mistakes` | a human-readable explanation of what was wrong and why the correction is right — multiple mistakes separated by `；` (Chinese semicolon) or numbered |
| `mistake_type` | controlled vocabulary tag (see list below). Multiple tags separated by `;` |
| `status` | always `new` for fresh entries (the HTML tool updates this to `learning` / `known` later) |

### Mistake type vocabulary

Pick the tag(s) that best describe the primary error. Keep this list tight — Hunting filters by it in the flashcard UI.

- `tense` — wrong tense or aspect (e.g. simple past vs present perfect)
- `agreement` — subject-verb or pronoun-antecedent agreement
- `article` — missing / wrong / extra `a`, `an`, `the`
- `preposition` — wrong or missing preposition (`in`, `on`, `at`, `for`, `to`, etc.)
- `word_choice` — wrong word for the meaning (incl. confusables like `affect`/`effect`)
- `word_form` — wrong form (verb vs adjective vs noun, e.g. `agree` vs `agreed`)
- `comparative` — comparative/superlative errors (`more taller`, `most best`)
- `syntax` — word order or sentence structure (e.g. `explain me this` → `explain this to me`)
- `plural` — singular/plural form errors
- `pronoun` — wrong pronoun (case, reference, ambiguity)
- `conditional` — `if`-clause and conditional structure
- `modal` — modal verb usage (`can`/`could`/`may`/`might`/`should`/`would`)
- `punctuation` — comma splices, missing commas, apostrophe misuse
- `spelling` — pure spelling, not a wrong-word choice
- `register` — too formal / too informal / awkward phrasing that's grammatical but unnatural
- `redundancy` — needless repetition (`return back`, `free gift`)

If a sentence has multiple problems, list multiple tags joined with `;` (e.g. `tense;agreement`). If nothing on the list fits cleanly, use `other` and explain in the `mistakes` column.

If the original sentence is already correct, set `corrected_sentence` equal to `original_sentence`, set `mistakes` to something like `No mistakes — saved for reference.`, and set `mistake_type` to `none`. (Hunting may want to remember a *good* example sentence too.)

## Workflow

### 1. Collect the candidates

Extract every sentence Hunting wants to save. If the input is a list, parse it into discrete entries. If only one sentence is in the message and it's ambiguous whether they want it saved or just checked, briefly confirm.

### 2. Check for duplicates

Read `databases/sentences.csv` first (resolved relative to the repo root). If a candidate's `original_sentence` (case-insensitive, whitespace-normalized) is already there, surface it and skip by default. Never overwrite — Hunting's flashcard progress would be clobbered.

### 3. Grammar-check and explain each entry

For each candidate, produce:

- **corrected_sentence** — the most natural, idiomatic correction. Don't rewrite to taste; fix only what's wrong. Preserve Hunting's voice and word choice when both options are acceptable.
- **mistakes** — a short explanation of *what* was wrong and *why* the fix is right. If there are multiple issues, number them or separate with `；`. Quote the problematic words in `""` (double quotes — they'll be escaped by the CSV writer). Aim for one or two sentences of explanation per mistake — enough to teach, not a lecture.
- **mistake_type** — pick from the controlled vocabulary above. Use `;` to join multiple tags. Use `none` if the sentence is already correct.

If Hunting explicitly provided a correction or explanation, honor it — don't override.

### 4. Confirm briefly

Show Hunting a compact preview — one block per entry:

```
1. Original:  He don't like coffee.
   Corrected: He doesn't like coffee.
   Type:      agreement
   Mistakes:  Subject-verb agreement — third-person singular "he" takes "doesn't".
```

Ask "save these?" unless they already said something like "just save them" or "no need to confirm."

### 5. Append via the bundled script

Use `scripts/append_sentences.py`. The script:

- Wraps every field in double quotes (matching existing CSV style).
- Fills in `date_added` (today, local time), `timestamp` (now, ISO 8601 local time), and `status` (`new`) automatically.
- Skips duplicates (case-insensitive + whitespace-normalized match on `original_sentence`).
- Rewrites the file atomically with `csv.QUOTE_ALL`, so embedded commas, Chinese punctuation, and apostrophes are all safely escaped.

Never write to `databases/sentences.csv` with the Write or Edit tool directly — that's how quoting gets inconsistent. Always go through this script (or, as a fallback, a one-off Python snippet using `csv.writer(..., quoting=csv.QUOTE_ALL)`).

Invocation:

```bash
python3 "$SKILL_DIR/scripts/append_sentences.py" << 'JSON'
[
  {
    "original_sentence": "He don't like coffee.",
    "corrected_sentence": "He doesn't like coffee.",
    "mistakes": "Subject-verb agreement: third-person singular \"he\" takes \"doesn't\", not \"don't\".",
    "mistake_type": "agreement"
  }
]
JSON
```

The skill folder path is visible in the "Base directory for this skill" line when this skill is loaded.

### 6. Report back

Tell Hunting how many were saved and skipped. Include a link to the sentence flashcard tool:

`[Open sentence flashcards](apps/sentence_flashcards.html)`

Keep the report compact — a count and a short list, not a paragraph per entry.

## Design principles

- **Preserve Hunting's progress.** The CSV is a living database — never truncate, reorder, or rewrite existing rows' content. Only append.
- **Teach in the mistakes column.** That column is the actual lesson — it's what Hunting will see on the back of every flashcard. Be specific, name the rule, and quote the offending words.
- **Match the controlled vocabulary.** Don't invent new mistake_type tags on the fly; pick from the list. If something truly doesn't fit, use `other` and explain in `mistakes`.
- **Be defensive with CSV.** Always use `QUOTE_ALL` quoting so Hunting can open the file in Excel / Numbers / a text editor without rows breaking on commas or Chinese punctuation.

## Examples

### Input: one sentence, ambiguous mistake

> "Check this and save it: 'I have went to Paris last summer.'"

Enriched preview:

- Original: `I have went to Paris last summer.`
- Corrected: `I went to Paris last summer.`
- Type: `tense`
- Mistakes: `1) "have went" is never correct — the past participle of "go" is "gone". 2) With a definite past-time marker ("last summer"), use simple past "went", not present perfect.`

"Save this? (y/n)"

### Input: multiple sentences pasted in

> "Save these:
> 1. She don't know.
> 2. Can you explain me this?"

Two entries, both straightforward — agreement and syntax respectively. After previewing both, append in one script call.

### Input: an already-correct sentence

> "I want to remember this sentence: 'Let's bite the bullet and ship it.'"

If the sentence is grammatically correct, save it with `corrected_sentence` == `original_sentence`, `mistake_type` = `none`, and `mistakes` = `No mistakes — saved for reference.` Hunting may want to memorize the *pattern*, not a correction.
