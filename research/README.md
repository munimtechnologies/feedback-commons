# Quote fidelity on English learners' essays: preregistered design

By MV2 of Munim, Inc. Written with AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.

**Status (2026-10-14): design fixed, results pending.** The study job was queued on
2026-10-14 at about 08:30 UTC, and this file was committed before any of its output had
been seen. The commit history of this folder is the record of that. Results will be added
below the design, and nothing above the "Results" heading will change except to fix typos.
Any deviation from this plan will be listed under "Deviations".

## Question

Feedback Commons makes every comment quote the student's own words, and flags a comment
when the quote cannot be found in the essay. When small local models write those quotes on
essays by English language learners:

1. How often is the quote exact, and how often does the model quietly change the student's
   words, for example by fixing a misspelling inside the quote?
2. Does that happen more often on essays with weaker conventions (spelling, punctuation,
   capitalization)? If so, a plain exact-match check flags more comments on exactly those
   students' essays. That gives their teachers more to review, and it hides the student's
   real error behind a corrected "quote".
3. Does it change when the feedback is written in Spanish instead of English? The prompt
   asks the model to copy the quote exactly as the student wrote it.

## Why this is new (prior art checked 2026-10-14)

- Jia et al. (EDM 2024) found about 29% of LLM feedback sentences on student reports were
  unfaithful to the document. They measured faithfulness of content, not verbatim quotes.
- "Marked Pedagogies" (arXiv 2603.12471) shows that feedback labelled for English learners
  shifts toward grammar. That is about content bias, not quote fidelity.
- SEFORA (arXiv 2607.00274) and LLM essay scoring on ELLIPSE (arXiv 2604.00259) measure
  agreement with instructors and with human scores.
- Learning Commons' "Student Response Specificity" evaluator judges with a model whether
  feedback is grounded in the student's response. It does not check verbatim quotes
  mechanically.

To our knowledge, no published study measures whether AI feedback quotes students verbatim,
or how often it normalizes their words inside quotes, by writing-conventions level.

## Design

- **Essays:** the ELLIPSE corpus (Crossley et al., 2023), English language learners in
  grades 8-12, training file from github.com/scrosseye/ELLIPSE-Corpus (CC BY-NC-SA 4.0).
  It is used for non-commercial research only. It is downloaded at run time and never
  redistributed, and only aggregate numbers are published, never essay text.
- **Sample:** essays of 150-450 words. Up to 15 have a human Conventions score of 2.5 or
  lower (the low band) and up to 15 have 4.0 or higher (the high band). Within each band
  they are drawn with `random.Random(2026).sample` from the essays sorted by `text_id_kaggle`,
  and the two bands alternate. See `select_essays`.
- **Models:** `llama3.2:3b` and `qwen2.5:3b` through Ollama on CPU (8 cores, 8 GB),
  with a 4,096-token context. They use Feedback Commons' own request settings: temperature 0.2,
  JSON output mode, and a 300-second timeout per request.
- **Prompt:** exactly what Feedback Commons v0.5.0 sends (`build_messages`): the rubric
  criterion, grade, at most 2 comments, and for Spanish the instruction to write the
  feedback in Spanish while copying each quote exactly as the student wrote it.
- **Criteria:** `evidence` and `conventions` from `sample_rubric.json`.
- **Languages:** English and Spanish.
- **Budget:** 210 minutes. Essays are processed whole: every model, language and criterion
  is run for an essay before the next one starts, so a run that stops early stays balanced.

## Classifying each quote (`classify_quote`)

| Kind | Rule |
|---|---|
| exact | Found by Feedback Commons' own check, which ignores case, spacing and curly quotes |
| punctuation | The same word sequence appears in the essay, and only the punctuation differs |
| altered | The best-matching run of essay words (quote length ±2) has word-level similarity ≥ 0.7, but the words differ. Each changed word pair is recorded, and a change counts as a spelling correction when pyspellchecker does not know the student's word(s) but knows the quote's |
| not_in_text | Nothing in the essay reaches 0.7 similarity (invented, paraphrased or translated) |
| too_short | Under 3 characters, which Feedback Commons never accepts |

## Outcomes and analysis (fixed in advance)

- **Primary:** for each model × language, the exact-quote rate in the low band minus the
  rate in the high band, pooled over quotes. Its 95% interval comes from 2,000 bootstrap
  resamples of whole essays within each band (seed 7), because one essay's comments are not
  independent.
- **Directional expectation:** the gap is negative, so low-band essays get fewer exact quotes.
  We call a gap clear only when its whole interval is below zero. All four gaps are reported
  whatever they show, with no correction for multiple comparisons, and a gap whose interval
  crosses zero is reported as "no clear difference".
- **Secondary (descriptive):**
  - the share of quotes of each kind, by band, model, language and criterion;
  - among altered quotes, the share containing at least one spelling correction;
  - the share of model replies that could not be used (not JSON, or no comment with a quote);
  - seconds per request on CPU.
- **Not tested:** whether the feedback is good. This study is only about whether quotes are
  the student's words.

## Limits known in advance

- At most 30 essays, two 3B models, one prompt and one run each (no repeated sampling).
  Results are evidence about this setup, not about large hosted models.
- ELLIPSE's Conventions score is a human rating of the whole essay, not a count of errors.
- The 0.7 threshold and the spell-checker rule are mechanical. Some "altered" quotes will
  be paraphrases rather than corrections. The changed word pairs are recorded so this can be
  checked, but they are not published because they contain essay text.
- A Spanish reply that translates the quote counts as not_in_text. That is the correct
  result for a teacher, but it is not the same failure as an invented quote.

## Files

- `quote_fidelity.py` is the study. It is the code the job ran, except for an import
  fallback added so it also runs from this folder.
- `test_quote_fidelity.py` holds the offline tests, which need no model or network.
- Run it with `python research/quote_fidelity.py --data-dir data --out-dir out --rubric sample_rubric.json`
  from the repo root, with Ollama running.

## Results

Pending.

## Deviations

None so far.
