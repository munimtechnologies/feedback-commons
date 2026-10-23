# Quote fidelity v4: results of the preregistered passage-level test

By MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.
The preregistration is `research/PREREG-v4.md` (commit `b1d2d08`, 2026-10-22). This file only
reports. Its wording rules were written down before the confirmatory analysis came back
(`RESULTS-v4-deviations-draft.md`, education run 181, 2026-10-23 ~17:30Z). No essay text or quote
appears here.

## What v4 asked

v3's preregistered band test found no clear difference, but one of its **post hoc** (not
preregistered) contrasts stood out: for the qwen2.5:3b Spanish cell, quotes that covered a passage
containing a misspelling were reproduced verbatim less often than quotes over a clean passage
(difference -0.124, 95% interval -0.219 to -0.044 — the only such interval that excluded zero). v3
called this "a lead for a future preregistered study, not a finding." v4 is that study.

**H1 (preregistered, directional).** On a fresh, non-overlapping essay sample, a quote is
reproduced exactly **less** often when the student passage behind it contains a misspelling than
when it is clean. The primary outcome is the exact-quote rate on misspelled passages minus the rate
on clean passages, pooled over the four model x language cells, with each essay's quotes kept
together, and a 95% interval from 10,000 whole-essay bootstrap resamples within band (seed
`v4-boot-20261022`). The reading rule fixed in advance:
- the whole interval below zero -> H1 supported (misspelled passages quoted exactly less often);
- the interval spanning zero -> no clear difference;
- the whole interval above zero -> the opposite of H1;
- **and a power floor: at least 150 quotes of each passage kind. Below it, the test is reported as
  underpowered and the sign of the gap is not interpreted.**

Prior art was re-checked before v4 ran (run 180): VerbatimEval, E-Bench and PEARL exist, but none
tests whether a student passage's misspelling changes how verbatim an AI feedback quote is. The
novelty holds.

## Results (added 2026-10-23)

The analysis ran on 2026-10-23 (job `qf-v4-analysis-v1`, finished 17:47:16Z) with the research code
at commit `b1d2d08`, on the four cells listed under Deviations: llama3.2:3b and qwen2.5:3b, each
writing feedback in English and in Spanish, served by Ollama. The job's offline unit tests passed
(v3 + v4 suites) and its copy check re-derived every cell file against the counts that cell's own
job printed before reading any of them; all four matched. Outputs:
`research/v4/analysis.json` and `research/v4/analysis.md` (aggregates only, no essay text).

**Analysis set.** Of the 120 preregistered essays (60 per band), 29 were completed in all four
cells: 12 low-band and 17 high-band. Dropped, by band and reason: low 30 never reached by a
time-limited cell and 18 with an unusable reply; high 30 never reached and 13 unusable. The sample
is small because cells ran on CPU within a fixed time budget and an essay counts only if every cell
returned a usable reply for it (see Deviations 2-3).

**Quotes.** The 29 essays produced 455 quotes across the four cells; 453 were placed in the essay
and 2 were not in the text (0 too short, 0 unplaceable). Of the 453 matched quotes, **122 covered a
passage with at least one misspelled word and 331 covered a clean passage.**

**Primary outcome (the one confirmatory test).** Exact-quote rate, misspelled passages minus clean
passages, pooled over the four cells:
- misspelled passages: 110 of 122 exact (90.2%)
- clean passages: 314 of 331 exact (94.9%)
- gap: **-0.047, 95% bootstrap interval -0.125 to +0.036** (10,000 whole-essay resamples within
  band, seed `v4-boot-20261022`)

**Verdict: underpowered. The sign of the gap is not interpreted.** With only 122 misspelled-passage
quotes, the study is below its preregistered floor of 150 quotes per passage kind, so by the rule
written in advance the result is reported as underpowered and its direction is not read as evidence.
For the record, the point estimate (-0.047) and three of the four per-cell estimates below are in
H1's direction, but the study was not built to carry that weight and we make no claim from it. The
interval spans zero in any case.

Why the sample came up short: v4 kept v3's per-cell time budget (290 minutes for requests on CPU),
but the analysis set is the intersection of four cells, and the slowest cell (qwen2.5:3b in English,
147 s per request on a 2-CPU host) reached only part of the sample. The intersection of four partly
completed cells, minus unusable replies, left 29 essays and, within them, 122 misspelled-passage
quotes.

**Secondary outcomes (descriptive, no tests, on the analysis set).**

1. The same gap within each Conventions band (misspelled minus clean):

| Band | Misspelled exact | Clean exact | Gap | 95% interval |
|---|---|---|---|---|
| low (<= 2.5) | 72 of 81 (88.9%) | 103 of 106 (97.2%) | -0.083 | -0.192 to +0.014 |
| high (>= 4.0) | 38 of 41 (92.7%) | 211 of 225 (93.8%) | -0.011 | -0.092 to +0.094 |

2. The same gap for each cell (misspelled minus clean):

| Cell | Misspelled exact | Clean exact | Gap | 95% interval |
|---|---|---|---|---|
| llama3.2:3b, English | 21 of 25 (84.0%) | 84 of 90 (93.3%) | -0.093 | -0.292 to +0.071 |
| llama3.2:3b, Spanish | 31 of 32 (96.9%) | 77 of 82 (93.9%) | +0.030 | -0.061 to +0.120 |
| qwen2.5:3b, English | 26 of 32 (81.2%) | 77 of 80 (96.3%) | -0.150 | -0.346 to +0.036 |
| qwen2.5:3b, Spanish | 32 of 33 (97.0%) | 76 of 79 (96.2%) | +0.008 | -0.077 to +0.083 |

   No interval excludes zero. The qwen2.5:3b English cell is the largest single-cell estimate in
   H1's direction, consistent with v3's qwen-es lead being cell- and language-specific rather than
   general, but every interval is wide and spans zero.

3. Misspelled words inside quotes, and how often they were kept as the student wrote them:

| Band | Matched quotes | Misspelled passages | Share | Misspelled words | Kept | Not kept | Kept rate |
|---|---|---|---|---|---|---|---|
| low | 187 | 81 | 43.3% | 205 | 177 | 28 | 86.3% |
| high | 266 | 41 | 15.4% | 51 | 49 | 2 | 96.1% |
| all | 453 | 122 | 26.9% | 256 | 226 | 30 | 88.3% |

   Low-band essays carried most of the misspelled words (205 of 256), as expected, and their
   misspelled words were kept as written slightly less often (86.3% vs 96.1%). This is descriptive;
   no test is attached.

**Failures and replies with no quote, by cell** (counted, not retried; requests / failed /
unusable / no quote):
- llama3.2:3b, English: 202 / 28 / 0 / 1
- llama3.2:3b, Spanish: 176 / 5 / 0 / 0
- qwen2.5:3b, English: 120 / 10 / 0 / 1
- qwen2.5:3b, Spanish: 192 / 10 / 0 / 1

No cell had an unusable reply; the dropped essays were lost to failed requests and to cells not
reaching every essay in time.

## What this does and does not show

Two small open models (3B parameters), one prompt, one request seed, two feedback languages, and 120
preregistered ELLIPSE essays of which 29 were completed in all four cells. v4 set out to confirm, on
fresh essays, that quotes over a misspelled passage are reproduced verbatim less often. **It did not
have the data to decide.** The point estimate leans in H1's direction and the qwen-en cell leans
hardest, but the study fell below its own preregistered precision floor, so it neither confirms nor
refutes H1. Taken with v2 and v3, the stable finding across all three studies remains that these
models usually quote English learners verbatim (about nine times in ten here), and no study has shown
that weaker passages are quoted less faithfully. An honest underpowered result is still the outcome:
it says the v3 qwen-es lead is not yet replicated, and it sizes what a v5 would need (see below).

**What a conclusive v5 would need.** The binding constraint was quote count, not essay count: 122
misspelled-passage quotes against a 150 floor. Reaching the floor needs either a larger sample or
cells that finish it. The slowest cell (qwen2.5:3b, English) needs about twice the request budget or
double the CPU to complete all 120 essays; matching cell speeds would also shrink how much the
four-cell intersection costs. A v5 should budget from v4's measured seconds per request (below) so
every cell reaches every essay, lifting the misspelled-passage count above the floor.

**Prior art (best-effort search, re-checked run 180).** VerbatimEval, E-Bench and PEARL measure
verbatim reproduction or faithfulness in other settings; none tests whether a student passage's
misspelling changes how verbatim an AI feedback quote is, split by writing-conventions band. "Found
none" is not "none exists."

## Deviations and per-cell counts

The following is `RESULTS-v4-deviations-draft.md`, written in education run 181 (2026-10-23 ~17:30Z)
before `qf-v4-analysis-v1` produced any number. Nothing in it depends on the outcome.

### Cells (all four pinned to research commit `b1d2d08f538f61df74f313c9a4b48c8b1142a066`)

| Cell | Job | Requests | Unusable | Comments | Exact | Punct. | Altered | Not in text | Too short | s/request |
|---|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b, English | qf-v4-llama-en-v1 | 202 | 28 | 335 | 313 | 1 | 19 | 0 | 2 | 86.2 |
| llama3.2:3b, Spanish | qf-v4-llama-es-v1 | 176 | 5 | 342 | 322 | 4 | 13 | 3 | 0 | 99.7 |
| qwen2.5:3b, English | qf-v4-qwen-en-v1 | 120 | 10 | 215 | 202 | 3 | 10 | 0 | 0 | 147.2 |
| qwen2.5:3b, Spanish | qf-v4-qwen-es-v2 | 192 | 10 | 346 | 328 | 3 | 13 | 1 | 1 | 91.4 |

These are each cell's own printed counts, quote-level and over ALL requests. They are not the
preregistered test, which uses only essays completed in all four cells (see the Results above).

### Deviations

1. **The qwen2.5:3b Spanish cell was re-run twice, both times because the machine was stopped, not
   because of a code problem.** qf-v4-qwen-es-v1 (started 07:39Z) was interrupted at 08:23Z
   (exit 143, SIGTERM). Its first re-file under the name qf-v4-qwen-es-v2 was stopped by a planned
   maintenance shutdown of the compute machine at 10:39Z (exit 143). It was re-filed unchanged and
   ran 11:49-16:46Z to completion. Each attempt started from scratch with the same essays, model,
   prompt, seed, settings and research commit. No output of an interrupted attempt was used.
2. **Cells ran on two machines.** qwen-en ran on a 2-CPU host and the other three on a 4-CPU host,
   all in the same python:3.12 + Ollama container setup with a 3 GB memory cap. Speed differs (and
   so how many essays a cell reached in its 290-minute budget). Model, prompt and decoding settings
   do not.
3. **Not every cell reached all 120 essays in the 290-minute budget** (the qwen English cell had the
   fewest requests, 120). This is the preregistered completion rule at work: an essay counts only if
   it has a usable reply in all four cells. The analysis reports essays not reached and unusable
   replies per band, so none are silently dropped. This shrinks the analysis set, and the 150-quote
   floor decides whether the primary test is read at all.
4. **Copy step.** The four requests.jsonl files reached the analysis job by a byte-for-byte copy
   (PowerShell Copy-Item, size + SHA256 checked). The job then re-checks every file against the
   counts above (check_copies.py) before analysing.

### Limits fixed before the data (from v4_analyze.py at `b1d2d08`)

- **Tokenization:** the words checked are the tool's own word tokens (quote_fidelity.bare_words),
  each looked up with pyspellchecker 0.9.1's English dictionary. Words with digits never count, and
  "don't" counts as known when "don" is.
- **Edge-trim bias against H1:** best_window can leave a corrected word out of the matched passage
  when it sits at the quote's edge. Some altered quotes over a misspelling then count as "clean",
  which makes a gap harder to find, not easier.
- Misspellings the dictionary knows as real words (e.g. "their/there") are not detected.
  Spanish-language feedback still quotes English essays, so the checker is the English one in every cell.
- Two 3B models and one corpus (ELLIPSE, CC BY-NC-SA 4.0). Results are not claims about other
  models or about students' writing.

ELLIPSE (Crossley et al., 2023) is CC BY-NC-SA 4.0; this is non-commercial research and no essay
text is published here. Made with AI agents working in MV2's name; by MV2 of Munim, Inc.
