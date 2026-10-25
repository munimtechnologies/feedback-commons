# Quote fidelity v6: preregistration (before any v6 data)

*AI disclosure: this study is designed, run and written by AI agents working in the name of MV2 of
Munim, Inc. Code is Apache-2.0; this text is CC BY 4.0. No student essay text is published: the
ELLIPSE corpus (Crossley et al.) is CC BY-NC-SA 4.0, non-commercial research only.*

**Status.** Fixed on 2026-10-25 (UTC) and committed to `munimtechnologies/feedback-commons` together
with the tested `v6_run.py` / `v6_analyze.py`, **before any v6 feedback is generated**. Nothing below
changes once a v6 request exists; deviations are logged in RESULTS-v6.md the way v4 and v5 logged theirs.

## The question

Studies v3-v5 measured how faithfully two small open models quote a student back in written feedback.
v5 (powered, preregistered; `research/RESULTS-v5.md`) found they reproduce a quoted passage exactly
about **92%** of the time and keep a misspelled word as written **97%** of the time, with no clear
penalty for misspelled passages.

The follow-up that AI-feedback vendors actually control is the prompt:

> If the feedback prompt tells the model, explicitly and in detail, to copy the student's words
> exactly, does the exact-quote rate go up?

A one-sentence prompt change is the first and cheapest thing a vendor would try. A positive result is a
free fidelity gain; a null says the effort belongs elsewhere (for example a post-hoc verbatim check such
as this project's quote-check tool). Both are useful.

**What the control prompt already says (stated so the contrast is read correctly).** The unchanged
Feedback Commons 0.5.0 prompt used in v3-v5 already asks for "a short passage copied exactly from the
student's text" and says "Never invent quotes"; in the Spanish cells it also says "Copy each quote
exactly as the student wrote it." So v6 does **not** compare "no quoting instruction" with "an
instruction". It tests whether a **stronger, explicit** instruction (same spelling, punctuation and
capitalization, even when something looks wrong) adds anything on top of the existing brief one.

## Hypothesis (fixed in advance)

- **H1 (directional):** the exact-quote rate is higher with the added instruction (condition Q) than
  with the unchanged prompt (condition C): gap = rate(Q) - rate(C) > 0.
- **Reading rule:** 95% interval entirely above 0 -> **H1 supported** (the instruction helps); interval
  spanning 0 -> **no clear effect**; interval entirely below 0 -> **the instruction hurts**.

## Design: paired, within-essay, two prompt conditions

Everything is held identical to v5 except the one added sentence.

- **Sample.** The **same 120 essays** as v5 (`research/v5/essays.json`: 60 low and 60 high Conventions
  band). Reusing v5's draw is deliberate: each essay is paired with itself across conditions, so no new
  draw is needed. `v6_run.py` refuses any selection that is not v5's (study tag, 120 unique essays,
  60 per band) and records the SHA-256 of the essays.json it read.
- **Cells.** The same four model x language cells: `llama3.2:3b` and `qwen2.5:3b`, feedback in English
  and in Spanish, local Ollama 0.40.4 with the prompt cache off, temperature 0.2, request seed 1.
- **Criteria.** The same two rubric criteria (`v3_run.CRITERIA` = evidence, conventions).
- **Condition C (control).** The byte-for-byte unchanged v3/v4/v5 prompt (Feedback Commons 0.5.0
  `build_messages`). A unit test asserts that the messages sent under C equal v3_run's.
- **Condition Q (quote-exactly).** The same messages with exactly one line added to the user message,
  after "Give at most 2 comments." and immediately before the student text. The line is, verbatim:

> When you quote the student, copy their words exactly as the student wrote them — the same spelling, the same punctuation and the same capitalization, even if something looks wrong — and put the copied words inside quotation marks.

  The system prompt, decoding settings and request order do not change. A unit test asserts that Q
  differs from C by this one line only, and that the line in the code equals the line above.

120 essays x 2 criteria x 2 conditions x 4 model-language cells = **1,920 requests**, run as **eight
compute jobs** (`v6-{llama,qwen}-{en,es}-{c,q}`) of 240 requests each, the per-job size, budget
(420 minutes) and timeout v5's cells completed under. C is regenerated fresh next to Q rather than
reusing v5's replies, so Ollama or machine drift cannot masquerade as an effect.

## Analysis (fixed in advance; `v6_analyze.py`)

Labelling is v5's, unchanged: each quote is labelled by `quote_fidelity.classify_quote` (exact, same
words, changed words, not found, too short), and a **matched quote** is one labelled exact, same words
or changed words whose student passage `error_conditioned.place_quote` finds (`v5_analyze.matched_rows`).

- **Analysis set.** An essay is kept only if all eight runs returned a usable reply for it under both
  criteria (`v3_run.analysis_set`, with each run keyed by model, language and condition). C and Q
  therefore cover exactly the same essays. Dropped essays are counted per band and reason.
- **Primary outcome.** Exact-quote rate (the exact label only) among matched quotes under Q, minus the
  same under C, pooled over the four model x language cells. This is the denominator v5's ~92% used.
  Interval: **10,000 whole-essay bootstrap resamples**, each essay carrying its quotes under both
  conditions (a paired resample), seed `v6-boot-20261024`, 95% percentile interval.
- **Power floor.** The primary test is read only with at least **300 matched quotes in each
  condition** (v5's 91 analysed essays gave 1,416 matched quotes, so this should clear easily; it is
  set low so a shortfall is caught, not papered over). Below it the sign is not interpreted.
- **Honest power limit.** The baseline is already ~92%, so the instruction can add at most ~8 points.
  With ~1,400 quotes per condition in ~90 essays, the paired essay bootstrap should give a half-width of
  roughly 2-3 points. **v6 is powered to detect a moderate effect (about 5 points or more); a null means
  "no large improvement", not "no effect of any size".**

### Preregistered secondary analyses

1. **Per Conventions band** (low / high): the same Q - C gap within each band.
2. **Per model x language cell**: the same gap in each of the four, so a pooled result carried by one
   cell is visible. Because the Spanish control prompt already holds a brief copy-exactly line, any
   English-vs-Spanish difference is reported, but as exploratory.
3. **Every quote's label by condition**, unmatched ones included (counts and shares): does the
   instruction reduce changed-words and not-found quotes, the failures that misquote a student?
   Descriptive.
4. **How much the models quote**: quotes and matched quotes per usable reply, and replies with no quote,
   by condition. An instruction that raises fidelity only by making the model quote less would be a
   different story, so this is reported next to the primary.
5. **Misspelled words kept as written**, by condition and band (`v5_analyze.descriptive`, pyspellchecker
   0.9.1): does the instruction stop models "fixing" spelling inside quotes, or change nothing?

All outputs are aggregate counts, rates and intervals. **No essay text or quote is ever published.**

## Files

- `research/PREREG-v6.md`: this file.
- `research/v6_run.py` + `research/test_v6_run.py`: one run (`--condition c|q`).
- `research/v6_analyze.py` + `research/test_v6_analyze.py`: the paired analysis above.
- `research/v6/`: per-run summaries and the sealed `analysis.{md,json}`, added after the runs.

## What makes this new

Searches on 2026-10-14, 2026-10-24 and 2026-10-25 found no public measurement of whether an explicit
"quote the student's exact words" prompt instruction changes verbatim quote fidelity in AI writing
feedback, for any model. Nearby work asks for exact excerpts in its prompt without varying that request
(EdWorkingPapers ai25-1193, comparing LLM and teacher feedback), judges quote validity inside a reward
model (arXiv 2607.19219), measures feedback faithfulness more broadly (EDM 2024 short paper "On
Assessing the Faithfulness of LLM-generated Feedback on Student Assignments"), or releases
span-anchored instructor feedback (SEFORA, arXiv 2607.00274). v5 is the first powered baseline for these models; v6 is the first preregistered test of the
cheapest intervention against it. A null will be reported as a result.
