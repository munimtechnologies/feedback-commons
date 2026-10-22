# Quote fidelity v4: preregistration

By MV2 of Munim, Inc., made with AI agents working in MV2's name.
Text licensed CC BY 4.0; code Apache-2.0.

**Status: preregistration. Written and committed before any v4 data exists.** No v4 essay has
been selected or run at the time of this commit. This file states the design, sample, outcome and
analysis in full; the confirmatory analysis (RESULTS-v4.md) will report against it and list every
deviation. Commit this file, then generate data, then analyse.

## 1. Question

In studies v2 and v3 we tested whether small local models reproduce quotes from *weaker writers'*
essays less faithfully than from stronger writers', split by the human **Conventions** band. Both
found **no clear difference** at the essay-band level (v3 gap -0.7 points, 95% CI [-5.9, +3.9]).

But v3 surfaced a finer, passage-level signal, **post hoc**: within the qwen2.5:3b cells, quotes
whose matched source passage **contained a misspelling** were reproduced exactly **less often**
than quotes over clean passages (qwen-es difference -0.124, 95% CI [-0.219, -0.044]; qwen-en
pointed the same way). The essay band is a blunt proxy; the thing a model actually "smooths" is a
specific misspelled token, which varies passage to passage even inside one essay. A passage-level
test is therefore better powered and more mechanistically direct.

Because that signal was **found in** the v3 qwen data, testing it on the same data would be
circular. v4 is a **confirmatory replication on new essays**.

**Hypothesis (H1, directional):** Pooled across model x language cells, a feedback quote whose
best-matching essay passage contains at least one misspelled token is reproduced **exactly less
often** than a quote whose matched passage contains none.

## 2. Design (identical to v3 except the sample and the analysis unit)

- **Tool:** Feedback Commons at the tag committed for v4 (recorded in RESULTS-v4.md), Apache-2.0.
- **Models:** `llama3.2:3b` and `qwen2.5:3b`, served by Ollama on CPU. Exact digests and Ollama
  version recorded per cell, as in v3.
- **Languages:** feedback requested in English and in Spanish; quotes requested verbatim in the
  student's own words in both.
- **Cells:** the four model x language combinations (llama-en, llama-es, qwen-en, qwen-es).
- **Request seed:** a single fixed seed, declared in the harness, reused across cells, as in v3.
- **Corpus:** ELLIPSE (Crossley et al., 2023; CC BY-NC-SA 4.0), grades 8-12 English learners.
  Only aggregate numbers are published; no essay text, ever.

## 3. Sample (fixed now, before selection)

- **Eligible pool:** ELLIPSE essays within the same length window used in v2/v3, from the lowest
  Conventions band (score <= 2.5) and the highest (score >= 4.0).
- **Exclusions:** every essay used in v2 **or** v3 is removed (identified by ELLIPSE `text_id`;
  the excluded id list is written into the harness before selection and saved with the results).
- **Selection:** with declared seed `v4-select-20261022`, randomly draw **60 low-band and 60
  high-band** essays (120 total) from the post-exclusion pool. The pool is large enough (v3 noted
  ~799 low / ~299 high eligible, minus the <=126 already used), so no essay is reused.
- **Completion rule (as v3):** an essay enters the analysis set only if it produced a usable reply
  in **all four** cells. Dropped essays and the reason (e.g. HTTP 500) are counted per cell.

## 4. Unit of analysis and the passage classification

- **Unit:** one quote emitted by a model (the same quote records v2/v3 produce).
- **Matched passage:** the essay substring the tool's existing matcher aligns a quote to when it
  classifies the quote (the same alignment that yields exact / punctuation / altered). Quotes the
  tool labels **not-in-text** or **too-short** have no reliable matched passage and are **excluded**
  from v4 (counted and reported).
- **Misspelled-passage flag:** the matched passage is flagged `misspelled` if it contains >= 1
  token not recognised by the preregistered spell checker, else `clean`. **Checker, fixed now:**
  `pyspellchecker` (PyPI `pyspellchecker`), English dictionary for English-language source text;
  the library's Spanish dictionary is **not** used because ELLIPSE essays are in English. Tokens
  are the checker's own word tokens; the exact version is pinned in the analysis code and recorded
  in RESULTS-v4.md. This mirrors v3's exploratory "words a standard spell checker does not
  recognise" definition so the two are comparable.

## 5. Primary analysis (one test)

- **Outcome:** exact-quote rate (the tool's `exact` label; punctuation-only does **not** count as
  exact here, matching v3's primary) among quotes with a matched passage.
- **Primary estimand:** `rate(misspelled-passage quotes) - rate(clean-passage quotes)`, **pooled
  across all four cells**.
- **Interval:** cluster bootstrap resampling **essays** (not quotes), 10,000 resamples, declared
  seed `v4-boot-20261022`; 95% percentile interval.
- **Decision rule (fixed):**
  - CI entirely **below 0** -> H1 supported: misspelled-passage quotes are reproduced exactly less
    often.
  - CI **includes 0** -> no clear difference.
  - CI entirely **above 0** -> opposite of H1.
- **Analysis floor:** proceed only if the analysis set has **>= 150 misspelled-passage quotes and
  >= 150 clean-passage quotes**. If either falls short, report the study as **underpowered** and do
  not interpret the sign.

## 6. Secondary analyses (declared, not decisive)

1. The same difference computed **within each Conventions band** (low-only, high-only), to show any
   effect is not merely the band confound (misspelled passages cluster in low-band essays).
2. Per-cell estimates (four differences with CIs), for a generalisation check across model and
   language.
3. Descriptive: the share of matched passages flagged `misspelled`, overall and by band, and the
   count of misspelled tokens reproduced exactly vs. altered (the v3 exploratory quantity).

## 7. What would make the result wrong, and the deviations policy

- Essays, models, prompt, seeds, checker and analysis are fixed above. Any departure forced by the
  shared machine (a cell re-run, a re-filed job) is logged in RESULTS-v4.md and must not change any
  of these. A cell that cannot complete is reported as missing, never silently dropped.
- Known threats we will state plainly: the checker misses errors it cannot see (joined words, wrong
  word forms), so `clean` passages are only "clean to a dictionary"; two 3B models and one corpus
  limit generalisation; passage matching for altered quotes is approximate.

## 8. Prior art

We know of no published measurement of verbatim quote fidelity split by whether the quoted passage
contains a misspelling. Jia et al. (2024) check whether feedback content is supported by the
student's work, not whether quotes reproduce the student's words; Mah et al. (2025) prompt for
exact excerpts but analyse feedback qualitatively. This reflects our search, not proof none exists.
