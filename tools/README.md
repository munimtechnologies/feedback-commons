# verbatim-quote-check

A tiny, dependency-free checker: when an AI writing-feedback tool quotes a student's own
words back to them, did it copy them faithfully?

Part of [Feedback Commons](https://github.com/munimtechnologies/feedback-commons), by
MV2 of Munim, Inc. Made with AI agents working in his name. Code licensed Apache-2.0.

## Why

Good formative feedback shows students their *own* words so they can see and fix what they
wrote. If a tool silently tidies a misspelled or awkward phrase when it quotes it, the
student never sees the error and the feedback misreports their writing. This tool measures
that, one quote at a time. It grew out of three preregistered studies of quote fidelity in
small local models (see `research/RESULTS-v3.md` and `research/RESULTS-v4.md`).

## What it reports

Given the source text (the student's essay) and a quote a tool claims to take from it:

| Category | Meaning |
|---|---|
| `exact` | the quote is a verbatim substring of the source |
| `punctuation_or_whitespace` | the words match in order; only punctuation, spacing or case differ |
| `altered` | the quote best-matches a span of the source but with word-level changes |
| `not_found` | the quote cannot be located in the source |

Only the standard library is used, so it runs anywhere and is easy to read and audit.

## Use

As a command (exit code: `0` words faithful, `1` altered, `2` not found — usable in CI):

```bash
python verbatim_quote_check.py --source "The cat sat on the mat." --quote "cat sat on"
# -> exact   1.000

python verbatim_quote_check.py --source-file essay.txt --quote-file quote.txt --json
# -> {"category": "altered", "similarity": 0.75}
```

As a library:

```python
from verbatim_quote_check import check

r = check(student_essay, model_quote)
if not r.faithful_words:
    print(f"quote not verbatim: {r.category} (similarity {r.similarity:.2f})")
```

`--threshold` sets the minimum word similarity for `altered` rather than `not_found`
(default `0.6`).

## Tests

```bash
python -m unittest -v test_verbatim_quote_check.py
```

See `TUTORIAL.md` for the ideas behind each matching choice.
