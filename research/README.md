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

### Exploratory results (added 2026-10-15)

**Exploratory, not preregistered.** The analysis declared above ran on 2026-10-15 (job
`error-conditioned-v1`, 11:21 to 11:24 UTC). Its offline tests passed. A copy check
re-derived every quote's classification from the study's raw records and found 0
mismatches in 337 quotes. 335 quotes were placed in the essay; the other 2 (not in text, too
short) have no passage. The full tables are in `results/error-conditioned-summary.md` and
`.json`.

**Misspelled words inside quotes were almost always kept.** The quotes contained 172
occurrences of words the spell checker does not know (the same essay word can be counted
once per quote that contains it). 167 of them (97.1%) were kept exactly as the student wrote
them:

| Model | Feedback language | Misspelled words kept |
|---|---|---|
| llama3.2:3b | English | 46 of 47 (98%) |
| llama3.2:3b | Spanish | 28 of 29 (97%) |
| qwen2.5:3b | English | 33 of 36 (92%) |
| qwen2.5:3b | Spanish | 60 of 60 (100%) |

**Misspelled versus clean passages.** For each model and language, the verbatim rate of
quotes from misspelled passages minus that of quotes from clean passages, with 95% essay
bootstrap intervals (2,000 resamples):

| Model | Feedback language | Misspelled minus clean |
|---|---|---|
| llama3.2:3b | English | -0.020 [-0.152, +0.066] |
| llama3.2:3b | Spanish | -0.104 [-0.272, +0.027] |
| qwen2.5:3b | English | -0.034 [-0.167, +0.048] |
| qwen2.5:3b | Spanish | 0.000 (every quote verbatim) |

No interval excludes zero.

**Split by band** (pooled over models and languages; our hand sums of the published cells,
with no interval computed):

| Band | Passage | Quotes | Verbatim |
|---|---|---|---|
| Low | misspelled | 59 | 57 (96.6%) |
| Low | clean | 104 | 100 (96.2%) |
| High | misspelled | 22 | 20 (90.9%) |
| High | clean | 150 | 150 (100%) |

On average, 2.8% of the words in a low-band essay were unknown to the spell checker, against
0.8% in a high-band essay.

**Reading, by the rule declared above.** The declaration said: if the band gap disappears once
passages are split, it is mostly "more misspellings to fix"; if a gap remains among clean
passages, something else is going on. Here the gap remains among clean passages: 4 of the 6
altered low-band quotes came from passages in which the spell checker found nothing to
correct, while in the high band the only 2 altered quotes came from misspelled passages. This
fits the post hoc reading above, where the low-band changes included joining two words the
student wrote apart, a change to a word's grammatical form and changed first words, none of which a
spell checker can see. It is 8 altered quotes in all, so this is a description of this
sample, not evidence of a difference between bands.

**What it changes.** For a tool, the lesson is practical: a check that compares a quote with
the student's own words catches these changes; a check that looks for corrected misspellings
would have missed 4 of the 6 on low-band essays. A larger follow-up study should count joins,
real-word changes and edits at the edges of a quote separately, as `edit_types.py` now does.

#### Edit types in the altered quotes (added 2026-10-15)

**Exploratory, not preregistered; 8 quotes, so this describes the sample only.** Job
`edit-types-v1` (finished 20:12 UTC on 2026-10-15; offline tests passed) placed each of the 8
altered quotes back in its essay and compared them word by word with `edit_types.py`. It first
recomputed every recorded similarity score: 8 rechecked, 0 mismatches. Every altered quote had
at least one edit the classifier could name. Aggregates are in `results/edit-types-summary.md`
and `.json` (no essay text).

| Edit type | Low band | High band | All | At an end of the quote |
|---|---|---|---|---|
| Spelling corrected | 3 (1 quote) | 2 (2 quotes) | 5 | 0 |
| Word form changed (inflection) | 2 (1 quote) | 0 | 2 | 0 |
| Two words joined | 2 (2 quotes) | 0 | 2 | 2 |
| Word inserted | 3 (3 quotes, all function words) | 0 | 3 | 3 |
| Word swapped for a different word | 0 | 0 | 0 | - |
| Word dropped | 0 | 0 | 0 | - |
| Words split, apostrophe, other | 0 | 0 | 0 | - |
| **Total** | **10 (6 quotes)** | **2 (2 quotes)** | **12** | **5** |

Altered quotes were longer in the low band (mean 31.3 words, 6 quotes) than in the high band
(13.0 words, 2 quotes).

**What this does and does not show.** No altered quote had a word swapped for a different
word or a word dropped, so in this sample no change altered what the student meant. But the
changes are not neutral either. Most of them quietly *correct* the student: a misspelling
fixed, a word put into a different grammatical form, two words the student wrote apart run
together. A teacher reading that feedback sees a cleaner sentence than the one the student
wrote, which matters most when the feedback is about conventions, and 10 of the 12 edits were
in low-conventions essays. The other kind, a function word added at the start or end, looks like
the model smoothing the edge of the quote into its own sentence. With 8 quotes we can't say
whether these rates differ between bands; a larger study should count each type separately, as
`edit_types.py` does.

**For a tool:** a check that compares each quote with the student's exact words, as
`feedback_commons.py` does, catches all five kinds. A check that only looks for corrected
misspellings would have caught 5 of these 12 edits.

#### Closest prior work (added 2026-10-15)

The closest published measurement we found is **Jia et al. (2024), "On Assessing the
Faithfulness of LLM-generated Feedback on Student Assignments" (EDM 2024)**. It measures whether
the *content* of feedback is supported by the student's work (sentence-level, intrinsic and
extrinsic hallucination). It does not measure whether a model reproduces the student's own
words *verbatim* when it quotes them, and it does not split results by the writer's
conventions level. **Mah et al. (2025), "LLM and Teacher Feedback on Student Writing"**, is a
secondary neighbour: it asks the model for an exact excerpt from the essay but codes the
feedback's stance rather than checking the excerpt, and its "verbatim" is a feedback category
(a suggested replacement sentence), not a fidelity measure. An automated text search of Mah et
al. (job `prior-art-grep-v1`, 2026-10-15) confirmed both points. SEFORA (Peyghambari Oskoui et
al., 2026, arXiv 2607.00274, §A.3) notes informally that LLM-based re-paragraphing of student
essays added or dropped tokens, which led the authors to a deterministic parser; it reports no
rate and does not check quotations in feedback. We found no published measurement of verbatim
quote fidelity split by conventions band; that absence is from our search, not proof that none
exists.

*Made by AI agents working in MV2's name (MV2 of Munim, Inc.). ELLIPSE corpus: Crossley et al.,
CC BY-NC-SA 4.0; only aggregates are published here. Text: CC BY 4.0.*

---

## Preregistration: quote-fidelity-v3 (powered replication), registered 2026-10-16 before any v3 data were generated

**Why a v3.** v2 (22 essays, 337 quotes) found no clear gap in exact-quote rate between the low and
high Conventions bands; its point estimates (6.1% vs 2.3% non-exact) were too imprecise to rule a
gap in or out. v3 asks the same question with about four times the essays, one pooled primary test
instead of four per-cell tests, and an essay sample that does not overlap v2's.

**Question.** When small local models write rubric feedback that quotes an English learner's essay,
are quotes from essays with weaker writing conventions reproduced verbatim less often than quotes
from essays with stronger conventions?

**Data.** ELLIPSE training file (Crossley et al., 2023; github.com/scrosseye/ELLIPSE-Corpus,
CC BY-NC-SA 4.0), fetched at run time, never redistributed. Only aggregates are published; no essay
text, quote, or before/after pair is published. The runs check that the file's SHA-256 matches the
one in `research/v3/essays.json`, and stop if it does not.

**Bands and eligibility (unchanged from v2).** Low band: human Conventions score <= 2.5. High band:
>= 4.0. Essays of 150-450 words only. **Excluded: all 30 essays v2 selected** (regenerated with v2's
own `select_essays`, 15 per band, seed 2026, and checked against the 22 essays v2 finished),
whether or not v2 finished them.

**Sample.** From the remaining eligible essays, `select_essays` with 48 per band and seed 2027
(sorted by `text_id_kaggle`, then `random.Random(2027).sample`, alternating bands in processing
order as v2 did). If a band has fewer than 48 eligible essays, all of them are taken; essays.json
says so. The list, made by `research/v3_select.py`, is `research/v3/essays.json`, committed with
this section. The selection job (`v3-select-v1`, 2026-10-16; its 8 offline tests passed) read
3,911 rows, regenerated v2's selection exactly, and found 799 low-band and 299 high-band eligible
essays after the exclusion, so neither band is short: 48 were taken from each. It wrote essay IDs
and bands only; no feedback had been generated.

**Models, languages, settings.** `llama3.2:3b` and `qwen2.5:3b` through Ollama on CPU
(OLLAMA_CONTEXT_LENGTH=4096; model digests and Ollama version recorded with the results); feedback
in English and in Spanish; criteria `evidence` and `conventions`; temperature 0.2, JSON output,
300 s timeout, **request seed 1** (new: v2 set none); one request per essay x criterion x cell, no
reruns except as stated under "Failures". Prompt: `build_messages` of Feedback Commons 0.5.0, the
version v2 ran. Code: `research/v3_run.py run`, one job per cell.

**Runs.** Four jobs, one per model x language cell, each at most 330 minutes on 4 CPU, with 290
minutes for requests; essays are processed in essays.json order and taken whole. Each job fetches
this folder's code and `v3/essays.json` from the commit on main when it starts, refuses to run
unless that commit's README contains this section, and records the commit's SHA with its results.
**Analysis set: essays completed in all four cells.** An essay is completed in a cell when every
one of its requests in that cell returned usable JSON; a usable reply with no quoted comment still
counts. Essays dropped from the analysis set are counted by band and reason (never reached by a
time-limited job; a failed request or unusable reply).

**Quote classes (unchanged).** Exact / punctuation-only / altered / not in text / too short, as
defined by `classify_quote` in `research/quote_fidelity.py`.

**Primary outcome and test (one test).** Exact-quote rate, low band minus high band, pooled over all
four cells, with every quote of an essay kept together: `bootstrap_diff` on per-essay (exact, total)
counts summed over the four cells, in essays.json order, 2,000 resamples of whole essays within
each band (seed 7), 95% percentile interval. Expected direction: negative. The gap is "clear" only
if the whole interval is below zero. If the analysis set has fewer than 30 essays in either band,
the primary test is reported as underpowered and the result as descriptive only. Code:
`research/v3_run.py analyze`.

**What v3 can and cannot detect (stated in advance).** With ~15 quotes per essay and an assumed
intra-essay correlation of 0.05 (an assumption, not estimated), 48 essays per band gives about 80%
power for a gap the size of v2's point estimate (3.8 points). A gap half that size would need about
four times as many essays; a null v3 does not rule it out.

**Secondary outcomes (descriptive, no tests), all on the analysis set.**
1. The same gap for each of the four cells, with the same bootstrap.
2. Edit types in altered quotes, by band, from `research/edit_types.py` as published: spelling,
   apostrophe, join, split, inflection, real_word, inserted, dropped, other (an altered quote can
   have several). Reported as counts of edits and of quotes with each type.
3. Exact-quote rate by band within quote-length tertiles. Length is the number of words
   (`bare_words`); with the n pooled v3 quotes sorted by length, the cut points are the lengths at
   positions ceil(n/3) and ceil(2n/3); short is <= the first, middle <= the second, long above it
   (ties can make the thirds unequal).
4. Kept-rate of misspelled words inside quotes, by band, with `research/error_conditioned.py` as in
   the v2 exploratory analysis, per cell and pooled over the cells.

**Failures.** Failed requests (HTTP or server errors, timeouts) and unusable replies (not JSON, or no
comments list) are counted separately by cell and are not retried. Usable replies with no quoted
comment are counted as "no quote", not as failures.

**Nothing else is a confirmatory result.** Any other cut of the data is labelled post hoc.

**Files.** `v3_select.py` (selection) and `v3_run.py` (one cell, and the analysis), with offline
tests in `test_v3_select.py` and `test_v3_run.py` (18 tests, passed on the shared runner on
2026-10-16 in job `v3-run-tests-v1`, against this folder's code and Feedback Commons 0.5.0).

**Known limits.** Two 3B models, CPU, one prompt, one temperature, one corpus (grades 8-12 English
learners); human Conventions scores are a proxy for error density; a pooled test assumes the gap has
the same sign across cells. Written with AI agents working in MV2's name.
