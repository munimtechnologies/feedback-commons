# Quote fidelity v3: results of the preregistered powered replication

By MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.
The preregistration is the section "Preregistration: quote-fidelity-v3" in `research/README.md`
(commit 28bdb4e, 2026-10-16). This file only reports. Its wording rules were written down before
the confirmatory analysis came back. No essay text or quote appears here.

## Results (added 2026-10-22)

The analysis ran on 2026-10-22 (job `quote-fidelity-v3-analysis-v2`, finished 11:56:46Z) with
the research code at commit 28bdb4e, on the four cells listed under Deviations. Models:
llama3.2:3b (digest `a80c4f17acd5`) and qwen2.5:3b (digest `357c53fb659c`), both served by Ollama
0.40.4, each writing feedback in English and in Spanish. Before reading the cell files, the
analysis checked each one against the counts that cell's own job printed. All four matched.
Outputs: `research/results/v3-analysis.json` and `research/results/v3-analysis.md` (aggregates
only, no essay text).

**Analysis set.** 34 low-band and 41 high-band essays were completed in all four cells (of 48
sampled per band). Dropped: low 14 and high 7, all because of a failed request. Every job
reached every essay, and no cell had an unusable reply. Both bands are above the preregistered
floor of 30 essays.

**Primary outcome (the one confirmatory test).** The outcome is the exact-quote rate in the low
band minus the high band, pooled over the four cells, with each essay's quotes kept together.
Low band: 0.899 (480 of 534 quotes). High band: 0.906 (577 of 637). Gap: -0.007, with a 95%
bootstrap interval of -0.059 to +0.039 (2,000 whole-essay resamples within band, seed 7).
**Verdict: no clear difference.** The interval includes zero. This result does not rule out a
gap about half v2's size (about 1.9 points). In fact the interval runs from 5.9 points below
zero to 3.9 points above it, so it does not rule out a gap as large as v2's point estimate
(3.8 points) either.

For context, v2 (22 essays, 337 quotes) saw non-exact rates of 6.1% (low) and 2.3% (high), a gap
too imprecise to rule in or out. v3 was sized for about 80% power to detect a gap of that size,
assuming about 15 quotes per essay and an intra-essay correlation of 0.05. Both were assumptions,
not estimates. Observed: 1,171 quotes on 75 essays, so 15.6 quotes per essay across the four cells,
slightly above the assumed 15.

*Why the interval is wider than planned (post hoc).* For 80% power at 3.8 points, the plan implied
a 95% half-width of roughly 2.7 points. The observed half-width is 4.9 points. Two facts account
for most of the difference:
- 75 essays were analysed instead of 96. That widens the interval by a factor of about
  sqrt(96/75) = 1.13.
- The non-exact rate was 9.7% (114 of 1,171), against 4.2% in v2. A binomial rate near 10% is
  about 1.5 times as variable as one near 4%.

Together these give a factor of about 1.7. The rest may come from essays' quotes being more
correlated than the assumed 0.05. That was not estimated.

**Failures and unusable replies by cell** (counted, not retried; failed / unusable):
- llama-en: 18 / 0
- llama-es: 1 / 0
- qwen-en: 2 / 0
- qwen-es: 1 / 0

Replies with no quoted comment: llama-en 0, llama-es 1, qwen-en 1, qwen-es 1. All 18 llama-en
failures were HTTP 500 replies from Ollama's chat endpoint on the `conventions` request: 12
low-band and 6 high-band essays. They came after 48 to 94 seconds of normal generation, and the
server log gives no reason. Because those failures fell twice as often on low-band essays, they
account for most of the low band's larger drop.

**Secondary outcomes (descriptive, no tests).**

1. Gap per cell (low minus high, same bootstrap):

| Cell | Gap | 95% interval |
|---|---|---|
| llama3.2:3b, English | +0.031 | -0.023 to +0.089 |
| llama3.2:3b, Spanish | -0.006 | -0.093 to +0.068 |
| qwen2.5:3b, English | -0.022 | -0.113 to +0.075 |
| qwen2.5:3b, Spanish | -0.031 | -0.146 to +0.083 |

2. Edit types in altered quotes, by band (edits / quotes with that type). There were 40 altered
quotes in the low band (82 edits) and 37 in the high band (44 edits).

| Edit type | Low | High | All |
|---|---|---|---|
| spelling | 28 / 18 | 3 / 3 | 31 / 21 |
| apostrophe | 2 / 2 | 1 / 1 | 3 / 3 |
| join | 6 / 6 | 2 / 2 | 8 / 8 |
| split | 1 / 1 | 1 / 1 | 2 / 2 |
| inflection | 13 / 10 | 4 / 4 | 17 / 14 |
| real_word | 16 / 11 | 8 / 4 | 24 / 15 |
| inserted | 11 / 9 | 9 / 9 | 20 / 18 |
| dropped | 4 / 4 | 9 / 9 | 13 / 13 |
| other | 1 / 1 | 7 / 4 | 8 / 5 |

3. Exact rate by band within quote-length tertiles (cut points 18 and 32 words):

| Band | Short (<= 18) | Middle (19-32) | Long (> 32) |
|---|---|---|---|
| low | 93.8% (181/193) | 91.7% (143/156) | 84.3% (156/185) |
| high | 93.3% (208/223) | 90.8% (216/238) | 86.9% (153/176) |

4. Share of misspelled words kept as the student wrote them inside quotes:

| Cell | Low | High |
|---|---|---|
| llama3.2:3b, English | 110/110 (100%) | 27/28 (96.4%) |
| llama3.2:3b, Spanish | 110/113 (97.3%) | 18/18 (100%) |
| qwen2.5:3b, English | 152/170 (89.4%) | 10/10 (100%) |
| qwen2.5:3b, Spanish | 155/164 (94.5%) | 16/19 (84.2%) |
| pooled | 527/557 (94.6%) | 71/75 (94.7%) |

Low-band essays had about seven times as many misspelled words as high-band essays (3.27% of
words against 0.48%). Per misspelled word, the share kept was the same in both bands.

**Post hoc observations (not preregistered, no verdicts).**
- Exact rate by cell, both bands together: llama-en 95.3% (283/297), llama-es 93.0% (277/298),
  qwen-en 87.7% (256/292), qwen-es 84.9% (241/284). This is a description of these runs, not
  a ranking of the models.
- The same code (`error_conditioned.py`) also compares, per cell, how often quotes are verbatim
  when they cover a passage with a misspelling and when they cover a clean passage. This contrast
  is not among the four preregistered secondary outcomes. Results, misspelled minus clean:

| Cell | Difference | 95% interval |
|---|---|---|
| llama-en | +0.038 | -0.011 to +0.085 |
| llama-es | -0.001 | -0.111 to +0.076 |
| qwen-en | -0.077 | -0.184 to +0.018 |
| qwen-es | -0.124 | -0.219 to -0.044 |

  Only the qwen-es interval excludes zero. Among many descriptive intervals, one like this can
  appear by chance, so it is a lead for a future preregistered study, not a finding.

**What this does and does not show.** Two small open models (3B parameters), one prompt, one
seed, two feedback languages, and 96 ELLIPSE essays from a single corpus of English learners'
writing, of which 75 were analysed. The study measures whether a quote that the feedback presents
as the student's words appears verbatim in the essay. It does not measure whether the feedback is
helpful or correct. Taken together, v2 and v3 show that these models usually quote verbatim, about
nine times in ten in v3. Neither study shows that weaker writers' essays are quoted less
faithfully, and neither rules out a modest gap. ELLIPSE (Crossley et al., 2023) is
CC BY-NC-SA 4.0. This is non-commercial research, and no essay text is published here.

**Prior art (best-effort search, 2026-10-21).** Exact-substring quote checking is an established
method in biomedical and clinical LLM evaluation. Work on LLM feedback for student writing
measures specificity, quality, or sentence-level faithfulness. We found no dedicated,
preregistered measurement of verbatim quote reproduction in LLM writing feedback on student
essays, graded into exact, punctuation-only, altered, not-in-text and too-short, across model and
feedback-language cells. "Found none" is not "none exists": a closer match may exist.

## Deviations from the preregistration

The preregistration (commit 28bdb4e, 2026-10-16) fixed the essays, models, languages, prompt,
request seed and analysis. None of those changed. All the deviations below concern how the cells
were run on a shared machine. Each was decided before any confirmatory analysis was run.

1. **The pilot cell was re-run after an infrastructure fault (decided 2026-10-17, before any
   other v3 cell ran).** `quote-fidelity-v3-llama-en-v1` got through 35 of 96 essays in its
   290-minute budget. Ollama does not put a limit on llama-server's host-RAM prompt cache
   (ollama/ollama#18264). Inside the 6 GiB job, that cache grew by about 95 MiB per request
   until the container started swapping. Five requests stalled for 38-64 minutes each, and the
   server was killed once. 13 of 70 requests failed (8 HTTP 500, 5 timeouts), leaving 9 of 18
   low-band and 13 of 17 high-band essays complete. That attempt ran on Ollama 0.40.5. From
   then on, all four cells ran on Ollama 0.40.4 with the prompt cache turned off
   (`LLAMA_ARG_CACHE_RAM=0`). The v1 cell is not analysed. The preregistration says failed
   requests are not retried, so re-running a whole cell is a deviation. The decision was based
   on completeness alone: the v1 cell's descriptive gap (-0.006) played no part in it.

2. **Three cells were re-run after setup failed (2026-10-17).** On their first try, the
   llama-es, qwen-en and qwen-es cells stopped during setup because the Ollama 0.40.4 download
   failed on the runner's network (curl error 56). They sent no request and produced no data.
   They were re-run unchanged, except that setup now resumes and retries the same
   checksum-verified download.

3. **Some cells were re-run in full after the shared machine was reclaimed mid-run.** The
   compute runner sometimes ends a running job (exit 143, SIGTERM) when its machine is needed
   for other work. Whenever that happened, the whole cell was re-run from the start with the
   same essays, seed and settings; only the job name changed. Partial outputs from interrupted
   attempts are not analysed. Their request counts were looked at only to diagnose the
   interruption.
   - llama3.2, English: `-v2` was interrupted at 111 minutes after 110 of 192 requests. Memory
     stayed flat at about 2.8 GB, so this was not the pilot's memory problem. `-v3` completed
     and is the analysed cell.
   - qwen2.5, Spanish: `-v2` was interrupted at 117 of 192 requests and `-v4` at 184 of 192
     (setup and unit tests passed both times). `-v5` completed on 2026-10-21 (192 of 192
     requests) and is the analysed cell.

4. **One queued attempt never ran (qwen2.5, Spanish, `-v3`).** It was waiting in the shared
   machine's queue for memory and was superseded when a newer attempt (`-v4`) was filed. The
   runner only runs the newest version of a job name. It sent no request and has no output.
   Each later attempt was a verbatim copy with only the name changed.

5. **Timing and model weights.** The preregistration did not set a calendar deadline. Because
   of items 1-4, the four cells finished between 2026-10-17 and 2026-10-21 rather than within
   one day: llama-en-v3 on 2026-10-17, llama-es-v2 and qwen-en-v2 on 2026-10-18, and qwen-es-v5
   on 2026-10-21. The model weights did not change across that span. In every attempt's
   `ollama list` (machine.txt), llama3.2:3b has digest `a80c4f17acd5` and qwen2.5:3b has digest
   `357c53fb659c`. That holds for all four analysed cells and for every interrupted attempt
   that produced output. qwen-es-v5 pulled qwen2.5:3b afresh, and its digest is the same
   `357c53fb659c`, so the weights are identical. Every analysed cell ran on Ollama 0.40.4
   (ollama-version.json).

6. **The analysis job was filed a second time before it had run.** The first filing
   (`quote-fidelity-v3-analysis-v1`, 2026-10-21) never started: its job file and its working
   folder were in different run folders, which the runner does not support. Its code and inputs
   were copied byte for byte into a new folder (all 13 files had the same size and SHA-256 as
   the originals), and the job was filed again as `quote-fidelity-v3-analysis-v2`. Nothing else
   changed. Its unit tests and its copy check passed, and it read research commit 28bdb4e.

Analysed cells: llama-en-v3, llama-es-v2, qwen-en-v2, qwen-es-v5. Each one's
`research-commit.txt` reads 28bdb4e. The analysis job's `check_copies.py` checked the copied
cell files against each cell's own printed counts again, and all four matched.

Made with AI agents working in MV2's name; by MV2 of Munim, Inc.
