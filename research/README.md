# Quote fidelity on English learners' essays: preregistered design

By MV2 of Munim, Inc. Written with AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.

**Status (2026-10-14): results added 2026-10-14, below the unchanged design.** The study job was queued on
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

Added on 2026-10-14. The job `quote-fidelity-v2` ran on the shared runner from 17:51 to
21:25 UTC. Its offline tests passed (15 of 15) before the study started. **22 of the 30
essays finished within the 210-minute budget, 11 in each band** (see Deviations 2). That
gave 176 requests and 337 quotes. The full aggregate tables are in
[`results/quote-fidelity-summary.md`](results/quote-fidelity-summary.md) and
[`results/quote-fidelity-summary.json`](results/quote-fidelity-summary.json), exactly as the
job wrote them. They contain no essay text.

### Primary outcome: exact-quote rate, low band minus high band

| Model | Feedback language | Low band exact | High band exact | Gap (low − high) | 95% interval (essay bootstrap) | Reading |
|---|---|---|---|---|---|---|
| llama3.2:3b | English | 41 of 43 (95%) | 43 of 44 (98%) | −0.024 | [−0.093, +0.045] | no clear difference |
| llama3.2:3b | Spanish | 41 of 44 (93%) | 43 of 44 (98%) | −0.045 | [−0.136, +0.023] | no clear difference |
| qwen2.5:3b | English | 34 of 37 (92%) | 44 of 44 (100%) | −0.081 | [−0.190, +0.000] | no clear difference |
| qwen2.5:3b | Spanish | 38 of 40 (95%) | 39 of 41 (95%) | −0.001 | [−0.098, +0.091] | no clear difference |

**No gap is clear by the preregistered rule**: no interval lies wholly below zero. All four
point estimates are negative, which is the expected direction, but the study was not built
to test that pattern and we do not claim it. The qwen2.5:3b English interval reaches zero
but does not go below it. Every one of that model's 44 high-band quotes in English was exact,
and its 3 non-exact low-band quotes came from just 2 essays. In about one bootstrap resample
in nine, neither of those essays is drawn, so the upper limit sits at zero.

### Secondary outcomes (descriptive)

**Kinds of quote.** Of 337 quotes, 323 were exact (95.8%), 4 differed only in punctuation
(1.2%), 8 were altered (2.4%), 1 was not in the text (0.3%) and 1 was too short (0.3%). So
97.0% kept the student's words verbatim. Pooled over models and languages:

| Band | Quotes | Exact | Punctuation only | Altered | Not in text | Too short |
|---|---|---|---|---|---|---|
| Low (Conventions ≤ 2.5) | 164 | 154 (93.9%) | 3 | 6 | 0 | 1 |
| High (Conventions ≥ 4.0) | 173 | 169 (97.7%) | 1 | 2 | 1 | 0 |

The split by criterion and language is in the summary tables.

**Spelling corrections among altered quotes.** 3 of the 8 altered quotes (38%) contained at
least one spelling correction by the preregistered rule, 5 corrected words in all. One was
a low-band quote (qwen2.5:3b, English feedback: 3 misspellings corrected in an 87-word quote
that kept the student's grammar). The other two came from one high-band essay: llama3.2:3b
corrected the same misspelled word in its English and its Spanish feedback.

**Unusable replies.** 1 of 176 requests (0.6%). It was an HTTP 500 error from the local
Ollama server, not a malformed reply (Deviations 3). Every reply that arrived could be used.

**Speed.** 72.8 seconds per request on average on 4 CPU cores (llama3.2:3b 75.7 s in
English and 76.3 s in Spanish; qwen2.5:3b 62.1 s and 77.2 s).

### What the altered quotes were (post hoc, not preregistered)

We read the recorded change pairs for the 8 altered quotes (they stay unpublished because
they contain essay text). This reading was not planned in advance.

- 3 corrected misspellings (above).
- 2, one from each model on the same low-band essay with English feedback, joined two
  words the student wrote apart into one standard word. Both models quoted the same sentence
  this way, and the student's own spelling of that sentence appears verbatim in other
  quotes of the same essay.
- 1 (llama3.2:3b, low band, English) changed two real words toward standard grammar, a
  pronoun and a plural.
- 2 (llama3.2:3b, two low-band essays, Spanish feedback) changed only the quote's first
  word: one put "I" in front of the student's sentence, the other replaced "the" with
  "that". The matcher records these as an added word, not a replaced one. Other quotes of
  the same essays show the student's own wording.

So **6 of 337 quotes (1.8%) changed the student's words toward standard English**, 4 of them
on low-band essays. The preregistered spelling rule counts only 3 of those 6, because it
requires the student's own word to be unknown to the spell checker. Joined words and
real-word grammar changes pass that check. A reuse of this measure should count them
separately.

### Answers to the three questions, for this setup

1. **Quotes are almost always the student's exact words.** 95.8% were exact and 97.0%
   verbatim apart from punctuation. Silent correction inside a quote happened, but rarely:
   6 of 337 quotes by the post hoc reading, 3 by the preregistered spelling rule.
   Many of the exact quotes were full of misspellings, kept as written.
2. **No clear difference by Conventions band.** Low-band essays had a somewhat lower exact
   rate in every model and language (93.9% vs 97.7% pooled), but no preregistered interval
   excludes zero. With 11 essays per band, the study can rule out only large gaps: a drop of
   more than about 9 to 19 points in the exact rate on low-band essays, depending on the cell.
3. **Spanish feedback did not clearly change quote fidelity.** The one quote not found in
   the text was a phrase written in Spanish (qwen2.5:3b, high band). The one too-short quote
   ("...") also came with Spanish feedback.

**What this means for teachers using small local models:** a plain exact-match check, the
one Feedback Commons uses, would flag about 4 comments in every 100 in this setup (14 of
337), a few more on weaker writers' essays (10 of 164 against 4 of 173). Since version 0.6.0, Feedback Commons sorts those
flags into "punctuation only", "the model changed the student's words" and "not in the
text", and shows the teacher what the student actually wrote.

### Related work and discussion

Models' tendency to "smooth" text they copy is documented in other settings: as a
length-dependent failure to transcribe verbatim in code generation (arXiv:2601.03640), as
spelling over-correction (arXiv:2410.04027), and as the motivation for "deterministic
quoting" designs that insert quotations by lookup instead of trusting generated text.
Quotation and citation faithfulness also has its own survey (Schreieder, Schopf and Färber,
arXiv:2508.15396). As far as we found, none measures what happens when the quoted text is
an English learner's own sentence, or compares writers by conventions level. In this small
study on CPU, two 3B models kept learners' words verbatim in about 97% of quotes. Correction
inside quotes was real but rare (about 2%), and we found no clear difference by band (11
essays per band). Rates may differ for longer quotes, other prompts and larger hosted
models, which this study did not test.

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
2. **Essays finished (recorded with the results).** 22 of 30 essays (11 low, 11 high)
   finished within the 210-minute budget. The study started at 17:51:50 UTC; the last essay
   began inside the budget and ended at 21:25:21 UTC. Requests averaged 72.8 seconds on 4
   cores. The essays that finished are the first 22 of the preregistered, alternating order.
3. **One server error counted as unusable.** The design defines an unusable reply as "not
   JSON, or no comment with a quote". One request (qwen2.5:3b, English feedback,
   conventions, low band) got an HTTP 500 error from the local Ollama server instead. The
   code records any failed request as unusable, so it is counted there.
4. **Versions not fixed in the design.** Ollama 0.40.4. Models pulled at run time:
   llama3.2:3b (ID a80c4f17acd5) and qwen2.5:3b (ID 357c53fb659c). The container listed the
   host's 16 cores; the runner limited the job to 4 cores and 6 GB (memory limit
   6,442,450,944 bytes, read inside the container).
5. **Status line.** The bold status line at the top was changed from "results pending" to
   say results were added. No other text above "Results" changed.

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

**Status (2026-10-14, results time).** The exploratory job has been queued on the shared
runner. Since only 10 of 337 quotes were not verbatim, a split by misspelled passage will be
thin. Its most useful number is likely the share of misspelled words the quotes kept.
Its numbers will be added here, labelled exploratory.
