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

1. **Hardware (2026-10-14, before any output existed).** The job queued at 08:30 UTC
   (`quote-fidelity-v1`) asked the shared runner for 8 CPU cores and 8 GB of memory, and it
   was never scheduled: no job asking for more than 6 cores or 6 GB had run there. It was
   re-filed at about 14:10 UTC as `quote-fidelity-v2` with **4 CPU cores and 6 GB**. The
   models, prompt, sample, seed, criteria, languages, 210-minute budget and analysis are
   unchanged. Fewer cores means slower requests, so fewer than 30 essays may finish within
   the budget. Essays are taken whole and the bands alternate, so a shorter run stays
   balanced, and the number of essays finished will be reported with the results. The job
   now runs the study before the tool's sample-essay check, and that check covers English
   only. No output from either job had been seen when this change was made.

## Exploratory analysis declared before results

Added on 2026-10-14 at about 19:40 UTC. The study job was still running on the runner, and
none of its output had been seen. This analysis is **exploratory**. It is not part of the
preregistered analysis above, and it will be labelled exploratory wherever it is reported.

**Why.** A lower exact-quote rate in the low Conventions band could have two different
causes. Low-band essays have more misspellings, so a model has more chances to "fix" a word
while quoting. Or models could treat the same kind of passage differently when the essay is
weaker. The preregistered band gap cannot tell these apart.

**What `error_conditioned.py` does.** It reads the study's `requests.jsonl` and selects the
same essays (same seed). For every quote the study placed in the essay (exact, punctuation or
altered), it finds the student's own passage behind the quote with the study's matching rule
(`best_window`). The passage counts as *misspelled* if pyspellchecker does not know at least
one of its words. Words with digits are ignored, and a contraction counts as known if its
first part is. Then, for each model × language:

- the verbatim rate (exact or punctuation-only) of quotes from misspelled passages and from
  clean passages, and their difference, pooled over quotes, with a 95% interval from 2,000
  bootstrap resamples of whole essays (seed 7);
- the same two rates within each Conventions band;
- the share of misspelled words that the quote kept as the student wrote them;
- per band, the mean share of essay words the spell checker does not know.

Quotes not placed in the essay (not_in_text, too_short) have no passage and are only counted.
Only aggregate numbers are written (`error_conditioned.json` and `.md`), never essay text.
`test_error_conditioned.py` holds its offline tests.

**How to read it.** Suppose quotes from misspelled passages are much less often verbatim, and
the two bands look alike once passages are split this way. Then the band gap is mostly "more
misspellings to fix". If a band gap remains among clean passages, something else is going on.
No threshold is set in advance, and every interval is reported as it is.

**Limits.** A spell checker flags proper nouns and rare words and misses real-word errors
(there/their), so "misspelled" is a rough label. The analysis inherits the study's small
sample and mechanical matching.

**Prior art, re-checked at the same time.** Mah, Tan, Phalen, Sparks and Demszky
(EdWorkingPaper 25-1193, 2025) asked models for an exact excerpt from the essay with each
comment. Their analysis is a qualitative comparison with expert teachers' feedback, and as
far as we found it reports no rate of altered excerpts. Almousa et al. (arXiv 2609.28026,
2026) classify the focus of feedback, not its quotes. Neither changes the novelty statement
above.
