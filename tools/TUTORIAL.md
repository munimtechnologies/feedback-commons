# How to check whether AI feedback quotes a student word for word

A short, self-contained tutorial. By MV2 of Munim, Inc. Made with AI agents working in his
name. Text licensed CC BY 4.0; the accompanying code (`verbatim_quote_check.py`) Apache-2.0.

You can read this on its own, or run the tool alongside it. No account, no data download and
no third-party packages are needed — only Python 3.9+ from the standard library.

## 1. The problem, in one sentence

When an AI tool gives a student feedback and quotes the student's own writing back to them,
the quote should be *the student's words* — not a cleaned-up version of them.

Why it matters: formative feedback works by pointing a learner at something concrete they
wrote. "You wrote 'their going to the store' — check the spelling of *their*" only helps if
the tool actually quotes `their`, misspelling and all. If the model quietly "corrects" the
quote to `they're`, the student never sees their error, and the feedback is now describing
writing that does not exist. So before trusting a tool's quotes, it is worth measuring how
faithfully it copies.

## 2. Four outcomes, not two

"Did it quote correctly?" is really a spectrum. This tutorial (and the tool) uses four
buckets, from most to least faithful:

1. **exact** — the quote appears in the source verbatim, character for character.
2. **punctuation or whitespace** — the *words* match, in order, but punctuation, spacing or
   capitalisation differ. The tool tidied the surface but kept the wording.
3. **altered** — the words themselves changed: one was added, dropped or swapped. This is
   where silent "corrections" live.
4. **not found** — the quote cannot be located in the source at all (the model may have
   invented it, or paraphrased so heavily that nothing lines up).

Collapsing these to a yes/no hides the interesting middle. A tool that lands mostly in
bucket 2 is reliable about *wording* but reformats; one that drifts into bucket 3 is
rewriting students. Keeping them separate lets you see which.

## 3. How to decide each bucket

### exact: just look for the substring

The simplest and strongest test. After trimming surrounding quotation marks and whitespace,
is the quote a literal substring of the source?

```python
cleaned = quote.strip().strip('"\'')   # the tool strips curly quotes too
if cleaned in source:
    return "exact"
```

No tokenising, no normalising — a true verbatim match. Everything below only runs when this
fails.

### words, not characters, for the next three

To tell "only punctuation changed" from "a word changed", compare the two as sequences of
*words*. A word here is a run of letters or digits, lower-cased; punctuation and spacing are
dropped on comparison:

```python
import re
WORD = re.compile(r"[^\W_]+")          # letters/digits, no underscore
def words(text):
    return [m.group(0).lower() for m in WORD.finditer(text)]
```

So `"apples, oranges"` and `"apples oranges"` both become `["apples", "oranges"]`.

### punctuation or whitespace: words match exactly, in order

If the quote's word list appears as a **contiguous run** inside the source's word list, the
words are all there in the right order — the only differences were the punctuation, spacing
or case that `words()` threw away:

```python
def contiguous(src, q):
    return any(src[i:i+len(q)] == q for i in range(len(src) - len(q) + 1))
```

### altered vs not found: measure similarity

If the words do not line up exactly, how close are they? Slide a window the size of the
quote (and a little shorter and longer, so a single inserted or dropped word still counts)
across the source, and take the best word-level similarity using Python's own
`difflib.SequenceMatcher`:

```python
import difflib
best = max(
    difflib.SequenceMatcher(None, src[i:i+w], q).ratio()
    for w in range(len(q) - 2, len(q) + 3) if w >= 1
    for i in range(0, max(1, len(src) - w + 1))
)
```

A high best-similarity means the quote is a lightly **altered** version of a real span; a
low one means it is **not found**. The tool's default cut-off is `0.6`; raise it with
`--threshold` if you want to call only very close near-misses "altered".

## 4. Run it on your own example

```bash
python verbatim_quote_check.py \
  --source "Their going to the libary after school." \
  --quote "they're going to the library"
# -> altered   0.73   (the model fixed 'Their' and 'libary' — the student won't see either)
```

Try swapping in a quote you copied straight from the source (you should get `exact`), then
change only a comma (`punctuation_or_whitespace`), then change one word (`altered`).

## 5. Choices, and their limits

Every measurement tool makes judgement calls. Naming them is part of being honest about what
a number means:

- **Case and punctuation are treated as surface, not substance.** That is a choice. For a
  spelling-focused rubric you might instead treat case as meaningful; the tool keeps the two
  buckets separate precisely so you can decide.
- **The similarity cut-off is arbitrary.** `0.6` is a reasonable default, not a law. Report
  it whenever you report results.
- **Window slack is small (±2 words).** A quote that stitches together two far-apart spans
  of the source will read as `not_found`, which is usually the right call for a "quote".
- **It judges faithfulness, not correctness.** A faithful quote of a confused sentence is
  still `exact`. Whether the feedback itself is *good* is a separate question.

## 6. Where this comes from

This method is the core of three preregistered studies on whether small local models quote
English-language-learner essays verbatim, published in the same repository
(see `research/RESULTS-v3.md` and `research/RESULTS-v4.md`). Across them the stable finding
is that these models usually quote verbatim — about nine times in ten — which is reassuring,
but worth checking yourself for any tool you rely on. This tutorial hands you the method so
you can.

---

*Made with AI agents working in MV2's name, by MV2 of Munim, Inc. Text CC BY 4.0.*
