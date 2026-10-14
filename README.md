# Feedback Commons

Feedback Commons is a local-first writing-feedback assistant for teachers. It runs on your own computer, so student work never leaves your device.

- **Feedback tied to the text.** It drafts rubric-aligned feedback with a small open model running on your computer through [Ollama](https://ollama.com). Every comment has to quote the student's own words. If the quote isn't actually in the text, the comment is flagged.
- **The teacher decides.** You accept, edit or reject each comment, in the terminal or on a simple web page that only your computer can open. Nothing reaches a student without your approval.
- **Did it help?** When students hand in a revision, Feedback Commons checks whether they changed the passages your comments pointed to.
- **An open dataset, with consent.** Your decisions are logged on your machine. With consent, they can be exported as a de-identified dataset of "AI draft → teacher-approved feedback" pairs. Shared openly, such data can show which feedback teachers keep and which feedback students act on.

**Status: early prototype (v0.2.0).** It has no classroom users yet, and we're looking for teachers who want to try it and tell us what's wrong. Open an issue or email munimversion2@gmail.com.

## How it works
Each comment follows a well-known feedback design ("feed up, feed back, feed forward"):
- **quote:** a short passage copied from the student's text
- **feed up:** what good work looks like for this criterion
- **feed back:** how this passage measures up
- **feed forward:** one concrete next step

## Use
You need Python 3.8+ and Ollama with a small model (default `llama3.2:3b`). No other packages are required.

```
ollama pull llama3.2:3b
python feedback_commons.py draft sample_rubric.json essays/ --grade 8 --out drafts.json
python feedback_commons.py serve drafts.json --log events.jsonl
python feedback_commons.py uptake drafts.json revised/ --log events.jsonl
python feedback_commons.py export events.jsonl --roster roster.txt --consented consented.txt --out dataset.jsonl
```

- **Essays:** `essays/` holds one `.txt` file per student. The file name is the student's name. To try the tool first without any student work, use the made-up sample essays in `examples/essays/`.
- **Review:** `serve` opens a review page at http://127.0.0.1:8765/. It shows one comment at a time, flags quotes that aren't in the text, and lets you accept, edit or reject. You can stop at any point and pick up where you left off. If you'd rather work in the terminal, `review drafts.json --log events.jsonl` does the same thing there.
- **Revisions:** `uptake` reads the revised essays in `revised/`, which use the same file names as `essays/`. For each comment you sent, it logs whether the student changed the quoted passage. That's a rough signal, not a grade.
- **Roster:** `roster.txt` lists every student name, one per line. Export uses it to scrub names.
- **Consent:** `export` only includes students listed in `consented.txt`. Put a name there only after you have permission under your school's rules.

### Which model should I use?
`eval` checks how reliably the local models on your computer draft usable, grounded feedback for your rubric:

```
python feedback_commons.py eval sample_rubric.json essays/ --models llama3.2:3b,qwen2.5:3b,gemma3:4b --out eval.json
```

For each model it reports:
- **usable_rate:** the share of replies that could be read
- **grounded_rate:** the share of comments whose quote really appears in the essay
- **seconds_per_request:** how long each reply takes

It doesn't judge whether the advice is good. That's your call. Run it on essays you're allowed to use, such as public sample essays, before you run it on your students' work.

### What export removes
`export` swaps each student for a random pseudonym that changes with every export. It removes:
- roster names (full names and each part)
- email addresses
- phone numbers
- long ID numbers

Automatic de-identification is never perfect, so **read the export yourself before sharing it**.

### Privacy and safety
- The review page listens only on 127.0.0.1. It refuses requests addressed to any other host name, and each form carries a per-session token.
- The only network calls go to your own Ollama server, which is `http://localhost:11434` by default.

### Before you start
Check that your computer can run a local model with [local-ai-checkup](https://github.com/munimv2/local-ai-checkup).

## Tests
```
python -m unittest -v
```
The tests run offline and don't need Ollama.

## Changes
- **0.2.0:**
  - Added a local web review page (`serve`), and both review modes now resume where you left off.
  - Added `uptake` to track whether a revision changed the passages you commented on.
  - Added `eval` to compare how reliably local models draft grounded feedback.
  - Added made-up sample essays for trying the tool.
- **0.1.0:** First prototype, with `draft`, terminal `review` and consent-gated `export`.

## Plans
- An open benchmark that scores small local models' rubric-aligned feedback against teacher-approved feedback.
- More languages and subjects.

## About
Feedback Commons was made by MV2 of Munim, Inc. The code and docs were written with AI agents working in MV2's name. MIT license.
