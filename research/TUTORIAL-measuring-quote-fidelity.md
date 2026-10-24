# A study guide: how to measure whether an AI tutor quotes a student exactly

*By MV2, Munim, Inc. This guide was written with AI agents working in MV2's name. The
worked examples below are invented for teaching; no real student writing appears here.
Text is licensed CC BY 4.0; the code it describes (Feedback Commons) is Apache-2.0.*

## Why this matters

When an AI writing tutor gives a student feedback, it often quotes the student back to
themselves: *"In the sentence 'I goes to school', the verb should agree with the subject."*
A quote is a promise. It tells the student *these are your exact words*. If the tool
silently repairs the quote first — writing *"I go to school"* and then "correcting" it —
the feedback is about a sentence the student never wrote. For a beginner, and especially
for an English learner, that is confusing and can erode trust.

So there is a measurable, testable question hiding inside every AI feedback tool:

> **When the tool quotes the student, does it reproduce the words exactly, or does it edit
> them first — and does it edit more often exactly where the student needs the most help
> (the passages with spelling or convention errors)?**

This guide teaches a reproducible way to answer that question for *any* model. It is the
method behind Feedback Commons' preregistered quote-fidelity studies. You can apply it to
your own tutor, your own rubric, and your own corpus.

## Step 1 — Collect the quotes

Run the model on a set of essays with a fixed rubric, and capture every quoted span the
model produces. A "quote" is any run of the student's words the model presents as the
student's own. Store the quote and the source essay; store nothing else you don't need.

## Step 2 — Classify each quote into one of five buckets

For each quote, compare it to the essay and place it in exactly one bucket. These are the
buckets Feedback Commons uses (`classify_quote`), in order of fidelity:

1. **exact** — the quote matches the essay text under a forgiving check that ignores
   letter case, spacing, and curly-vs-straight quotation marks.
   - Essay: `She didn't know.`  Quote: `she didnt know` → **exact** (case and the apostrophe
     are ignored; the word sequence is identical).

2. **punctuation** — the same sequence of *words* appears, but the punctuation differs.
   - Essay: `Wait, stop!`  Quote: `Wait stop` → **punctuation**.

3. **altered** — the quote lines up with a stretch of the essay (see Step 3), but at least
   one *word* is different. Every changed word pair is recorded. A change is flagged as a
   **spelling correction** when a spell checker does *not* recognize the student's original
   word but *does* recognize the word the model substituted.
   - Essay: `I recieved the gift.`  Quote: `I received the gift` → **altered**, and because
     a spell checker rejects *recieved* but accepts *received*, this is a spelling correction.

4. **not_in_text** — nothing in the essay is similar enough to the quote. The model
   invented it, paraphrased it, or translated it.
   - Essay (Spanish-language feedback): student wrote `Me gusta leer`, quote reads
     `I like to read` → **not_in_text** (a translation, not a quote).

5. **too_short** — the quote is under 3 characters, which the tool rejects as too small to
   judge. (`a`, `I` on its own, etc.)

The five buckets are mutually exclusive, so every quote lands in exactly one, and the
counts always sum to the number of quotes collected.

## Step 3 — How a quote is matched to the essay (the hard part)

Students misspell, drop words, and run sentences together, so you cannot match quotes by
exact string search. Feedback Commons slides a window across the essay's words
(`best_window`) and finds the stretch that best fits the quote, allowing the window to be
up to **±2 words** longer or shorter than the quote. It then measures **word-level
similarity** between that best window and the quote.

- If similarity is **≥ 0.7**, the quote is treated as *located in the essay*. If the words
  match perfectly it is **exact** (or **punctuation**); if not, it is **altered**.
- If the best window still falls **below 0.7**, the quote is **not_in_text**.

The 0.7 threshold is a deliberate choice: high enough that a genuinely different sentence
is rejected, low enough that a quote with one or two student typos still matches the
passage it came from. When you reuse this method, keep the threshold fixed *before* you
look at results, and report it.

## Step 4 — Break down the edits (optional, exploratory)

Once a quote is **altered**, a second tool (`edit_types.py`) says *how* it changed. Each
changed word pair is labelled: **spelling corrected**, **word form / inflection changed**
(`go` → `goes`), **two words joined** (`alot` → `a lot`), **word inserted**, **word
swapped**, **word dropped**, or **split / apostrophe / other**. This turns "the model
edited the quote" into a specific, countable claim: *the model silently fixed the
student's spelling in N of M altered quotes.*

## Step 5 — Decide how many essays you need *before* you run (power)

This is the step most informal "AI evals" skip, and it is why their conclusions don't
hold up. A small sample can only detect a *huge* effect; a null result on a small sample
tells you nothing.

Feedback Commons sizes its samples on purpose:

- **v2** used only ~11 essays per writing-quality band. That is enough to catch a large
  gap and nothing subtler.
- **v3** scaled up. With roughly 15 quotes per essay and an assumed intra-essay
  correlation of 0.05, **48 essays per band gives about 80% power** to detect a gap the
  size of v2's estimate (about 3.8 percentage points in the exact-quote rate). A gap half
  that size would need roughly **four times** as many essays, and failing to find it would
  *not* rule it out.

The general lesson: pick the smallest effect worth caring about, estimate how noisy your
measure is (here, the clustering of quotes inside an essay), and compute the sample size
*first*. Write down a **floor** — a minimum number of observations below which you will
report the test as *underpowered* and refuse to interpret the direction of the result.
Feedback Commons' v4/v5 studies use a floor of 150 quotes per passage kind for exactly
this reason. Honoring a floor you set in advance is what stops a weak study from being
dressed up as a finding.

## Step 6 — Preregister, then seal the analysis

Before collecting data, write down: the question, the buckets, the matching threshold, the
primary test, the sample size, the floor, and the exact decision rule ("if the floor is
not met, report underpowered"). Fix your random seeds. Then run the data collection and
the analysis without changing the plan. If you must deviate, record every deviation
*before* you see the number. This is ordinary science applied to AI behavior, and it is
what separates a result you can cite in a grant from a demo you can't.

## A worked mini-study you can run yourself

1. Pick 20 short pieces of writing you have permission to use (or synthetic ones).
2. Ask your model, with a fixed rubric, to give feedback that quotes the writer.
3. Extract every quote and run Steps 2–4 by hand on the first few to get a feel for the
   buckets, then script the rest.
4. Report: exact rate, punctuation rate, altered rate (and of those, the spelling-fix
   rate), not_in_text rate. Say plainly whether you had enough quotes to trust the gap.

Twenty pieces will almost certainly be *underpowered* for a subtle gap — and saying so
clearly is the right answer, not a failure. That honesty is the whole point.

## Where the real code and studies live

- **Feedback Commons** (open source, Apache-2.0): the `classify_quote`, `best_window`, and
  `edit_types.py` tools, plus a stricter standalone `verbatim-quote-check`.
- **Preregistered studies v2–v5** with results write-ups (`RESULTS-v3.md`, `RESULTS-v4.md`)
  in the same repository's `research/` directory.

Repository: github.com/munimtechnologies/feedback-commons

---

*This is a methods tutorial, not individual educational or clinical advice. Validate any
measure on your own data before relying on it.*
