# Quote fidelity v5: preregistration of the powered passage-level test

By MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.
This file is written and committed **before any v5 feedback is generated**. It fixes the sample,
the one confirmatory test, the reading rule and every analysis decision in advance. No essay text
or quote appears here or in any v5 output; only IDs, bands and aggregates are published.

## Why v5

v4 (`research/PREREG-v4.md`, `research/RESULTS-v4.md`, release v0.7.0) ran the first confirmatory
passage-level test and came back **underpowered**: only 122 misspelled-passage quotes against the
preregistered floor of 150, so by its own rule the sign of the gap was not interpreted. The shortfall
was operational, not a property of the question. v4 analyses the **intersection** of four cells (an
essay counts only if every cell returned a usable reply for it), and the slowest cell — qwen2.5:3b
writing English feedback, 147 s per request on a 2-CPU host — reached only 120 of its 240 requests
inside the 290-minute per-cell budget, so the four-cell intersection fell to 29 essays. v4 itself
stated the fix: "the slowest cell needs about twice the request budget or double the CPU to complete
all 120 essays." v5 is that study: the **same question and the same analysis as v4**, on a **fresh,
non-overlapping** essay sample, with a larger per-cell compute budget so the cells complete the
sample. The only changes from v4 are the fresh sample and the compute budget; nothing about the
models, prompt, decoding, seeds-discipline or the analysis changes.

## Hypothesis

**H1 (directional).** On a fresh essay sample that overlaps none of v2's, v3's or v4's essays, a
quote is reproduced **exactly less often** when the student passage behind it contains a misspelling
than when that passage is clean.

## Primary outcome and reading rule (identical to v4)

The primary outcome is the **exact-quote rate on misspelled passages minus the exact-quote rate on
clean passages**, pooled over the four model x language cells, with each essay's quotes kept
together, and a 95% interval from **10,000 whole-essay bootstrap resamples within band**, seed
`v5-boot-20261023`. The analysis set is the essays with a usable reply for every criterion **in all
four cells** (the same intersection rule as v4; `v3_run.analysis_set`). Dropped essays are counted
per band and reason. "Misspelled passage", "matched quote", tokenization and the bootstrap are
defined exactly as in `research/v5_analyze.py` at this commit, which is byte-for-byte v4's analysis
logic with only the study name and the bootstrap seed changed.

The reading rule, fixed in advance:

- the whole 95% interval below zero -> **H1 supported** (misspelled passages quoted exactly less often);
- the interval spanning zero -> **no clear difference**;
- the whole interval above zero -> **the opposite of H1**;
- **and a power floor: at least 150 quotes of each passage kind.** Below it, the test is reported as
  **underpowered** and the sign of the gap is **not interpreted** (`FLOOR = 150` in `v5_analyze.py`).

## Sample (fixed by `v5_select.py` before any feedback is generated)

120 ELLIPSE training essays of 150-450 words: **60 low band** (Conventions <= 2.5) and **60 high
band** (Conventions >= 4.0), drawn with `quote_fidelity.select_essays` and seed `v5-select-20261023`,
alternating low/high, **excluding every essay used by v2, v3 and v4**. v2's, v3's and v4's selections
are regenerated deterministically and checked against the committed `research/v3/essays.json` and
`research/v4/essays.json` before the draw; `v5_select.py` stops if either fails to regenerate or if
the ELLIPSE file's SHA-256 does not match what those files record. The eligible pool after removing
v2+v3+v4 is ample (reported live as ~691 low / ~191 high before v5's draw, from v4's recorded pool of
751 low / 251 high minus v4's 60+60), so both bands fill. `v5_select.py` writes `research/v5/essays.json`
with IDs and bands only — never essay text. The cells rebuild the essays, text included, with
`v3_run.py run --essays v5/essays.json`.

## Cells and the one compute change

Four cells, each generated exactly as v3's and v4's by `v3_run.py run --essays v5/essays.json`:
llama3.2:3b and qwen2.5:3b, each writing feedback in **English** and in **Spanish**, served by Ollama
0.40.4 with the prompt cache off (`LLAMA_ARG_CACHE_RAM=0`), context 4096, one model loaded, one
request in flight. Two criteria (evidence, conventions) => 240 requests per cell. Prompt, decoding
and seeds are v3's and v4's, unchanged.

**The only design change from v4** is the compute budget, sized from v4's measured seconds per
request so every cell completes all 120 essays:

- per-cell request budget raised from **290 to 420 minutes** (`--budget-minutes 420` in `run.sh`);
- every cell given **4 CPU** (v4's slow cell ran on 2);
- container timeout 480 minutes; memory 3 GB (v3/v4 cells peaked under 2.5 GB).

This is a power fix and is **orthogonal to the sign** of the effect: a longer budget changes how many
essays are completed, not which quotes are exact. If a cell is pre-empted by shared-machine
maintenance (exit 143/SIGTERM), it is re-filed **unchanged**, keeping its place in line; no output of
an interrupted attempt is used, and all four cells pin the same research commit.

## Limits fixed before the data (from `v5_analyze.py` at this commit; same as v4)

- **Tokenization:** the words checked are the tool's own word tokens (`quote_fidelity.bare_words`),
  each looked up with pyspellchecker 0.9.1's English dictionary. Words with digits never count, and
  "don't" counts as known when "don" is.
- **Edge-trim bias against H1:** `best_window` can leave a corrected word out of the matched passage
  when it sits at the quote's edge, so some altered quotes over a misspelling count as "clean". That
  works against H1, not for it.
- Misspellings the dictionary knows as real words (e.g. "their/there") are not detected. Spanish
  feedback still quotes the English essays, so the checker is the English one in every cell.
- Two 3B models and one corpus (ELLIPSE, CC BY-NC-SA 4.0). Results are not claims about other models
  or about students' writing.

## Prior art (best-effort search; re-checked for v4, run 180)

VerbatimEval, E-Bench and PEARL measure verbatim reproduction or faithfulness in other settings; none
tests whether a student passage's misspelling changes how verbatim an AI feedback quote is, split by
writing-conventions band. "Found none" is not "none exists."

## What will be reported

`research/RESULTS-v5.md` with `research/v5/analysis.{json,md}` (aggregates only): the one primary
test with its verdict under the floor, the same secondary descriptives as v4 (per band, per cell,
misspelled-words-kept), per-cell failure counts, and a deviations section written before the sealed
analysis job returns any number.

ELLIPSE (Crossley et al., 2023) is CC BY-NC-SA 4.0; this is non-commercial research and no essay text
is published. Made with AI agents working in MV2's name; by MV2 of Munim, Inc.
