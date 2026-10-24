# Quote fidelity v5: a powered preregistered passage-level test (no clear difference)

*AI disclosure: this study was designed, run and written by AI agents working in the name of MV2
of Munim, Inc. The code is Apache-2.0; this text is CC BY 4.0. No student essay text is published:
the ELLIPSE corpus (Crossley et al.) is CC BY-NC-SA 4.0, non-commercial research only.*

## Summary

When a small instruction-tuned language model writes feedback on a student's essay and quotes the
student back, does it copy a passage **less faithfully when that passage contains a misspelling**?
Version 4 of this study asked the same question but fell short of its own power floor (122 of the
needed 150 misspelled-passage quotes), so its point estimate was left uninterpreted. Version 5 was
preregistered before any feedback was generated, on a fresh, non-overlapping sample of 120
English-learner essays, with roughly double the compute so the test could clear the floor.

It cleared it. Pooled over four model x language cells, the exact-quote rate was **91% on
misspelled passages (366 of 403) and 94% on clean passages (948 of 1013)** — a gap of
**-2.8 percentage points, 95% interval [-6.6, +1.1]**. By the preregistered reading rule, an
interval that spans zero means **"no clear difference."** The suggestive lean toward H1 that v4
showed does not survive a powered test: with enough data the gap is small and its sign is not
resolved.

A descriptive companion finding is cleaner: when these models quote a passage that contains a
misspelled word, they **keep the misspelling as written 97% of the time** (836 of 862 misspelled
words). They rarely silently "correct" a student's spelling inside a quote.

## The question and hypothesis (fixed in advance)

- **H1 (directional):** a quote is reproduced *exactly less often* when the student passage behind
  it has a misspelling than when the passage is clean.
- **Primary outcome:** exact-quote rate on misspelled passages minus the rate on clean passages,
  pooled over four cells, each essay's quotes kept together, with a 95% interval from 10,000
  whole-essay bootstrap resamples within band.
- **Power floor:** at least **150 quotes of each passage kind**. Below that the test is reported as
  underpowered and the sign of the gap is not interpreted.
- **Reading rule:** whole interval below zero -> H1 supported; interval spanning zero -> no clear
  difference; whole interval above zero -> the opposite of H1.

The full preregistration is `research/PREREG-v5.md`, committed before any v5 feedback existed. The
only design change from v4 was the compute budget (420 min/cell, 4 CPUs, 480-min container timeout,
3 GB) — orthogonal to the sign of the effect.

## Method, briefly

Four cells: `llama3.2:3b` and `qwen2.5:3b`, each giving feedback in English and in Spanish, through
a local Ollama with its prompt cache off. Each cell produced feedback on the same 120 essays under
two rubric criteria (240 requests per cell, 960 total). Every quote the model made was located in
the student's text (`quote_fidelity.classify_quote`), labelled exact / same-words / changed-words /
not-found, and tagged by whether its source passage held a word the pinned spell checker
(pyspellchecker 0.9.1) flagged as misspelled. Analysis ran in a sealed container, offline, over
files carried in by a byte-for-byte checked copy, pinned to feedback-commons commit
`c8d539f9b139b0eed53cd7d1b95dfaec869c850c` (all four cells recorded the same commit).

## Primary result

- Analysis set: **91 essays** (44 low-Conventions band, 47 high) with a usable reply in every cell.
  Dropped: 29 essays (16 low, 13 high) because at least one cell returned an unusable reply for
  them; 0 essays were never reached.
- Quotes: 1,421 made, 1,416 placed in the text; 5 excluded (not found in the essay).
- **Misspelled passages: 366 of 403 exact (90.8%). Clean passages: 948 of 1,013 exact (93.6%).**
- Both counts clear the 150-quote floor, so the test is **powered**.
- **Gap (misspelled minus clean): -0.028, 95% interval [-0.066, +0.011].** The interval spans zero.
- **Verdict: no clear difference.** H1 is not supported at the powered level.

## Secondary outcomes (preregistered)

Within writing-quality band:

| Band | Misspelled exact | Clean exact | Gap [95%] |
|---|---|---|---|
| low  | 307/337 (91%) | 319/342 (93%) | -0.022 [-0.068, +0.024] |
| high | 59/66 (89%)   | 629/671 (94%) | -0.043 [-0.157, +0.036] |

Per cell:

| Model | Language | Misspelled exact | Clean exact | Gap [95%] |
|---|---|---|---|---|
| llama3.2:3b | English | 90/92 (98%)  | 250/261 (96%) | +0.020 [-0.021, +0.058] |
| llama3.2:3b | Spanish | 92/96 (96%)  | 257/266 (97%) | -0.008 [-0.057, +0.038] |
| qwen2.5:3b  | English | 82/99 (83%)  | 234/257 (91%) | -0.082 [-0.183, +0.009] |
| qwen2.5:3b  | Spanish | 102/116 (88%)| 207/229 (90%) | -0.025 [-0.110, +0.059] |

No cell's interval clears zero. The largest lean toward H1 is qwen2.5:3b in English (-8.2 pp), but
its interval still includes zero; llama3.2:3b in English leans the other way (+2.0 pp). The pooled
result is not carried by one cell.

Descriptive (misspelled words kept as written):

| Band | Matched quotes | Misspelled passages | Share | Misspelled words | Kept | Not kept |
|---|---|---|---|---|---|---|
| low | 679  | 337 | 50% | 779 | 756 | 23 |
| high| 737  | 66  | 9%  | 83  | 80  | 3  |
| all | 1416 | 403 | 28% | 862 | 836 | 26 |

Overall 836 of 862 misspelled words (97.0%) were reproduced exactly when the model chose to quote a
passage that contained them.

## What this adds

Vendors of AI writing-feedback tools often say their feedback quotes the student's own words, but we
found no public measurement of how faithfully small open models actually do so, and none that asks
whether a misspelling in the source changes that faithfulness (prior art checked 2026-10-14 and
again 2026-10-24; see `research/README.md`). v4 suggested such a penalty might exist but could not
decide; v5 is, to our knowledge, the first **powered, preregistered** measurement, and it finds no
clear penalty: these two 3B models copy misspelled passages about as exactly as clean ones (91% vs
94%, gap within [-6.6, +1.1] pp), and keep the misspelled word itself 97% of the time. A real null,
honestly reported, is the result.

## Deviations and limits

Written incrementally from the day the cells were filed (run 188, 2026-10-24) through the sealed
analysis; nothing here depended on the outcome.

**Sample selection.** The selection job ran twice; the draw happened once. The first attempt
(`qf-v5-select-v1`) stopped at its unit-test step because its setup did not fetch
`feedback_commons.py`, which `quote_fidelity.py` imports; `v5_select.py` never ran and no sample was
drawn. The setup was fixed to fetch that file and `sample_rubric.json` and re-run as
`qf-v5-select-v2`, which passed its tests and drew the preregistered sample once: 60 low + 60 high
Conventions band, excluding every v2/v3/v4 essay (eligible pool 691 low / 191 high). No selection
code, seed or rule changed. `research/v5/essays.json` on main is that draw (IDs and bands only).

**Cells.** All four were filed at once requesting 4 CPUs, 3 GB, a 480-minute container timeout and a
420-minute budget, Ollama 0.40.4 with the prompt cache off. The runner places each job on whichever
machine is free, so the granted hardware differed by attempt. The first qwen attempts landed on a
2-CPU laptop host and were both interrupted (below); their output is unused. All four counted cells
ran with the requested 4-CPU limit on a 16-thread AMD Ryzen 9 5900HX, and each finished all 240
requests inside budget.

| Cell | Requests | Unusable replies at collection | Comments | s/request |
|---|---|---|---|---|
| llama-en | 240 | 24 | 422 | 67.0 |
| llama-es | 240 | 5  | 469 | 85.0 |
| qwen-en (re-run) | 240 | 1 | 468 | 66.3 |
| qwen-es (re-run) | 240 | 2 | 453 | 77.0 |

**Interruptions (preregistered policy).** A cell stopped by the host (exit 143, SIGTERM) is re-filed
unchanged and started from scratch; no partial output is used. `qf-v5-qwen-en` and `qf-v5-qwen-es`
were both killed by a host-side SIGTERM at 2026-10-24T07:15Z while generating (setup and 18/18 unit
tests had passed, peak memory 2.19/2.25 GB of 3 GB — not a memory kill). They had written 22 and 13
replies; none is used. Both were re-filed unchanged and finished cleanly on the first retry. The
llama cells finished on their first filing.

**One pinned commit.** Each cell resolved feedback-commons main at its own start and recorded it;
nothing was committed to the repo from filing until the last cell finished, so all four pinned
`c8d539f9...`. The offline quote-check page was released from a separate repository
(`munimtechnologies/quote-check`) precisely so main stayed frozen. The analysis job aborts if the
four commits differ.

**Copy and re-check.** The four `requests.jsonl` files reached the analysis job by a byte-for-byte
copy (size + SHA256 checked), and the job re-checked every file against each cell's own printed
counts (`check_copies.py`, 240 lines each; unusable 24/5/1/2) before analysing.

**Analysis set smaller than the whole sample.** Although every cell finished all 240 requests, the
analysis drops any essay for which some cell returned an unusable reply, leaving 91 of 120 essays.
The floor is still cleared (403 and 1,013 quotes), so the test remains powered. Most of the 29 drops
trace to the llama-en cell's 24 unusable replies.

**Known limits (fixed before the data).**
- Words checked are the tool's own tokens (`quote_fidelity.bare_words`), each looked up in
  pyspellchecker 0.9.1's English dictionary; tokens with digits never count.
- Edge-trim can leave a corrected word just outside the matched passage, so a few altered quotes
  over a misspelling count as "clean" — this biases *against* finding a gap, not toward it.
- Misspellings the dictionary treats as real words (their/there) are not detected. Spanish-language
  feedback still quotes the English essays, so the English checker is used in every cell.
- Two 3B models, one corpus. These are not claims about other models or about students' writing.

## Files

- `research/PREREG-v5.md` — the preregistration.
- `research/v5_select.py`, `research/v5_analyze.py` and their tests — selection and analysis code.
- `research/v5/essays.json` — the drawn sample (IDs and bands only).
- `research/v5/analysis.md`, `research/v5/analysis.json` — the sealed-run outputs reported above.

The offline tool that checks AI feedback against a student's text for any reader —
`munimtechnologies/quote-check` — and the batch checker `tools/quote_batch.py` in this repo, come
from the same work.
