# verbatim-quote-check

A tiny, dependency-free checker: when an AI writing-feedback tool quotes a student's own
words back to them, did it copy them faithfully?

Part of [Feedback Commons](https://github.com/munimtechnologies/feedback-commons), by
MV2 of Munim, Inc. Made with AI agents working in his name. Code licensed Apache-2.0.

For teachers there is also [quote-check](https://github.com/munimtechnologies/quote-check):
the same checker as one offline HTML page, nothing to install.

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

## Many quotes at once

`quote_batch.py` runs the same check over a JSONL file, one record per line, so a school or
a developer can audit a feedback tool on many essays at once. Each record holds the student's
text in `source` and the quotes in exactly one of `quote` (one string), `quotes` (a list) or
`feedback` (the whole feedback text: every passage in "double", “curly”, «guillemet» or
„low-high“ quotation marks is checked, as on the quote-check page; single quotes are skipped
because they double as apostrophes). `id` is optional (default: the line number).

```bash
cat > feedback.jsonl <<'EOF'
{"id": "s1", "source": "Last year it was the best day of the hole year! We went home.", "feedback": "You wrote \"it was the best day of the whole year\", and \"We went home.\" is fine. \"last year it was\" needs a comma. \"flying cars\" is not in it."}
EOF
python quote_batch.py feedback.jsonl --out rows.jsonl
# -> 1 records (0 without quotes), 4 quotes: 2 keep the student's words (50.0%; 1 exact,
#    1 punctuation_or_whitespace), 1 altered, 1 not_found.
```

(The example text is made up.) `rows.jsonl` gets one row per quote with `id`, `index`,
`category` and `similarity`. The quote's own text is left out unless you add `--with-text`,
so the rows can be shared without the students' writing. `--json` prints the summary as JSON.
The exit code is the worst quote's (`0`, `1`, `2` as above), or `3` if the input cannot be
read, naming the first bad line.

## Tests

```bash
python -m unittest -v test_verbatim_quote_check.py test_quote_batch.py
```

See `TUTORIAL.md` for the ideas behind each matching choice.
