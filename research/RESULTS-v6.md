# Quote fidelity v6: does telling the model to "copy the student's words exactly" make its quotes more exact?

*Made with AI agents working in the name of MV2 of Munim, Inc. Code Apache-2.0, text CC BY 4.0. No essay text,
quote or essay id is published: the essays come from the ELLIPSE corpus (non-commercial licence), so only
aggregate counts are released.*

Preregistration: [`PREREG-v6.md`](PREREG-v6.md), locked on 2026-10-25 before any v6 output existed, at research
commit `ed04103497a1fc0e264edfc2ee0798ac42da2733`. Analysis code: [`v6_analyze.py`](v6_analyze.py) (same commit).
Outputs: [`v6/analysis.md`](v6/analysis.md) and [`v6/analysis.json`](v6/analysis.json).

## Question

Our earlier studies (v3-v5) found that two small local models already quote students exactly about nine times
in ten when the prompt asks for "a short passage copied exactly from the student's text". v6 asked whether a
stronger, explicit line, placed just before the student's text ("When you quote the student, copy their words
exactly as the student wrote them", plus identical spelling, punctuation and capitalization, even when
something looks wrong) raises the exact-quote rate further. This is a test of a cheap fix a teacher or tool
builder could apply today.

**H1 (preregistered):** exact-quote rate with the extra line (Q) minus without it (C) is above zero.

## Answer: no clear effect (H1 not supported)

| | Exact quotes / matched quotes | Exact rate |
|---|---|---|
| With the extra line (Q) | 905 / 962 | 94.1% |
| Without it (C) | 923 / 979 | 94.3% |
| **Gap Q - C** | | **-0.2 points, 95% CI [-2.7, +2.2]** |

The floor (at least 300 matched quotes in each condition) was met with room to spare, so the verdict stands:
**no clear effect**. The interval rules out a gain larger than about 2 points. As the preregistration said
in advance, the models were already near the ceiling (about 94% exact), so this is evidence of "no large
improvement", not of "no effect of any size".

## Secondary results (preregistered, no verdicts)

**By Conventions band.** Low band: 457/489 (93.5%) with vs 455/493 (92.3%) without, gap +1.2 [-2.7, +4.7].
High band: 448/473 (94.7%) vs 468/486 (96.3%), gap -1.6 [-4.6, +1.4].

**By model and language** (any English/Spanish difference is exploratory):

| Cell | With the line | Without | Gap (points) and 95% CI |
|---|---|---|---|
| llama3.2:3b, English | 236/239 (98.7%) | 238/245 (97.1%) | +1.6 [-0.1, +3.6] |
| llama3.2:3b, Spanish | 251/254 (98.8%) | 249/251 (99.2%) | -0.4 [-2.0, +1.2] |
| qwen2.5:3b, English | 217/241 (90.0%) | 221/245 (90.2%) | -0.2 [-5.7, +5.3] |
| qwen2.5:3b, Spanish | 201/228 (88.2%) | 215/238 (90.3%) | -2.2 [-8.7, +4.2] |

No cell's interval clears zero. The model matters far more than the instruction: llama3.2:3b quotes exactly
about 98-99% of the time in both languages, qwen2.5:3b about 88-90%.

**Every quote's label.** Without / with the line: exact 923 / 905, same words but different punctuation or
case 22 / 28, changed words 34 / 29, not found in the essay 1 / 1.

**How much the models quote.** 504 usable replies in each condition; 1.944 quotes per reply without the line
and 1.911 with it. With the line, 4 replies (all qwen2.5:3b) gave no quote at all; without it, none did.

**Misspelled words kept as the student wrote them** (descriptive): 680 of 696 (97.7%) without the line and
719 of 726 (99.0%) with it. Nearly all misspellings are in the low band (675 and 704).

## Method in brief

v5's 120 ELLIPSE essays (60 low and 60 high Conventions band), two criteria (evidence, conventions), two small
models (llama3.2:3b and qwen2.5:3b, local Ollama 0.40.4, temperature 0.2, seed 1), each giving feedback in
English and in Spanish: four cells, each run once with the unchanged v3-v5 prompt (C) and once with the extra
line (Q), eight sealed jobs of up to 240 requests. Quotes were labelled with `quote_fidelity.classify_quote`
as in v5. The primary interval is a paired, essay-level percentile bootstrap (10,000 replicates, seed
`v6-boot-20261024`) over the essays completed in all eight runs. The analysis ran in a sealed container
pinned to the research commit above; the eight request files were copied into it with size and SHA-256
checks, and no one read them.

## Deviations and honest limits

- **Smaller analysis set than planned.** Only 63 of 120 essays (32 low, 31 high) were completed in all eight
  runs. 9 were not reached because three runs hit their time budget before all 240 requests (234, 222 and
  236 requests), and 48 had a failed request in at least one of the eight runs. Most failed requests (47 of
  75) were in llama3.2:3b English. The floor was still met (962 and 979 matched quotes).
- **Two runs were stopped by a host maintenance shutdown** on 2026-10-25 (qwen2.5:3b Spanish without the line,
  and llama3.2:3b Spanish with it) and were re-run unchanged.
- **Ceiling.** With about 94% exact at baseline, the most any instruction could add is about 6 points; the
  study can rule out large gains, not small ones.
- **Narrow scope.** Two 3B models, one corpus of English-learner essays, one wording of the instruction.
  Bigger or different models may respond differently. Related work used a similar verbatim constraint for a
  lead-extraction task without testing its effect against a baseline (*Scalable Argumentative Writing
  Support*, EDM 2026 poster); we found no earlier public test of whether such an instruction changes quote
  fidelity in feedback.
- **The checker cannot tell a deliberate correction from a slip.** A changed quote may be a silent fix of the
  student's error or a misquote.

## What this means for teachers and tool builders

Adding "copy the student's words exactly" to a feedback prompt is not a fix that shows up in the numbers: for
these two models it changed nothing measurable. Choosing the model mattered much more (about 98-99% exact
against 88-90%). Checking quotes after the fact, for example with the free offline
[quote-check](https://github.com/munimtechnologies/quote-check) page, remains the reliable way to catch the
quotes that do change a student's words.

-- MV2, Munim, Inc., mv2@munimtech.com
