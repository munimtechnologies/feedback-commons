# Feedback Commons

Feedback Commons is a local-first writing-feedback assistant for teachers. It runs on your own computer, so student work never leaves your device.

- **Feedback tied to the text.** It drafts rubric-aligned feedback with a small open model running on your computer through [Ollama](https://ollama.com). Every comment has to quote the student's own words. If the quote isn't actually in the text, the comment is flagged.
- **The teacher decides.** You accept, edit or reject each comment, in the terminal or on a simple web page that only your computer can open. Nothing reaches a student without your approval.
- **In the student's language.** Comments can be written in Spanish, Vietnamese, Somali or any language your model handles, for the whole class or student by student. Each one comes with an English gloss so you can still judge it before you approve it.
- **Your rubric, from a spreadsheet.** Save your rubric as CSV, one row per criterion and one column per level, and use it as-is.
- **What to teach next.** A class summary shows, for each rubric criterion, how many students you sent a comment on it, so you can see what calls for a whole-class mini-lesson and what calls for a small group.
- **Did it help?** When students hand in a revision, Feedback Commons checks whether they changed the passages your comments pointed to.
- **An open dataset, with consent.** Your decisions are logged on your machine. With consent, they can be exported as a de-identified dataset of "AI draft → teacher-approved feedback" pairs. Shared openly, such data can show which feedback teachers keep and which feedback students act on.
- **For developers: an MCP tool server.** Other AI apps and agents can use the drafting, quote checks, revision checks and class summary through the Model Context Protocol. No tool approves feedback; that stays with the teacher.

**Status: early prototype (v0.5.0).** It has no classroom users yet, and we're looking for teachers who want to try it and tell us what's wrong. Open an issue or email munimversion2@gmail.com.

## How it works
Each comment follows a well-known feedback design ("feed up, feed back, feed forward"):
- **quote:** a short passage copied from the student's text
- **feed up:** what good work looks like for this criterion
- **feed back:** how this passage measures up
- **feed forward:** one concrete next step

## Install
You need Python 3.8+ and Ollama with a small model (default `llama3.2:3b`). No other packages are required. Either download `feedback_commons.py` and run it with `python feedback_commons.py ...`, or install the `feedback-commons` command:

```
pip install git+https://github.com/munimv2/feedback-commons
ollama pull llama3.2:3b
```

## Use
```
python feedback_commons.py draft sample_rubric.json essays/ --grade 8 --out drafts.json
python feedback_commons.py serve drafts.json --log events.jsonl
python feedback_commons.py summary drafts.json --log events.jsonl --rubric sample_rubric.json --out summary.md
python feedback_commons.py uptake drafts.json revised/ --log events.jsonl
python feedback_commons.py export events.jsonl --roster roster.txt --consented consented.txt --out dataset.jsonl
```

- **Essays:** `essays/` holds one `.txt` file per student. The file name is the student's name. To try the tool first without any student work, use the made-up sample essays in `examples/essays/`.
- **Review:** `serve` opens a review page at http://127.0.0.1:8765/. It shows one comment at a time, flags quotes that aren't in the text, and lets you accept, edit or reject. You can stop at any point and pick up where you left off. If you'd rather work in the terminal, `review drafts.json --log events.jsonl` does the same thing there.
- **Class summary:** `summary` writes a table with one row per criterion (see below).
- **Revisions:** `uptake` reads the revised essays in `revised/`, which use the same file names as `essays/`. For each comment you sent, it logs whether the student changed the quoted passage. That's a rough signal, not a grade.
- **Roster:** `roster.txt` lists every student name, one per line. Export uses it to scrub names.
- **Consent:** `export` only includes students listed in `consented.txt`. Put a name there only after you have permission under your school's rules.

### Feedback in the student's language
For the whole class, add `--language`:

```
python feedback_commons.py draft sample_rubric.json essays/ --language Spanish --out drafts.json
```

For some students only, list them in a CSV file with one `student,language` row each (the names match the essay file names; see `examples/languages.csv`). Everyone else gets English, or the `--language` you give:

```
python feedback_commons.py draft sample_rubric.json essays/ --languages languages.csv --out drafts.json
```

- The quote stays exactly as the student wrote it, so the quote check still works.
- Feed up, feed back and feed forward are written in the chosen language. Each comment also carries a **gloss**, the model's English translation of the feed forward, shown on the review page as "In English, for you". Students see only the feed forward.
- The gloss is the model's translation, not a checked one. Small models write some languages much better than others. Before you use a language with students, run `eval` with `--language` on sample essays, and if you can, ask a colleague who reads the language to look at a few comments.

### Rubrics from a spreadsheet
Save your rubric as CSV (in Google Sheets: File → Download → CSV; in Excel: Save As → CSV UTF-8) and pass the `.csv` file wherever a rubric goes. `examples/sample_rubric.csv` shows the layout:

| Criterion | 4 - Exceeds | 3 - Meets | 2 - Approaching | 1 - Beginning |
|---|---|---|---|---|
| Clear claim | States a precise, arguable position… | States a clear position | … | … |

- One row per criterion. The criterion's name is in the column headed Criterion, Name, Category, Trait or Skill, or in the first column if none of those headings is used. The top-left cell may be blank.
- Every other column with a heading is a level, and the level descriptions become part of the criterion's description. Optional `ID` and `Description` columns are used as they are.
- To see what Feedback Commons made of your rubric, convert it and read the result: `python feedback_commons.py rubric my-rubric.csv --out rubric.json`.

### The class summary
`summary` turns your review decisions into a picture of the class, one row per rubric criterion:
- **Students sent a comment:** how many students you sent (accepted or edited) at least one comment on this criterion. The model's drafts alone don't count; your decisions do.
- **Comments sent, rejected, not reviewed:** your decisions so far.
- **Quote not found:** drafted comments whose quote wasn't in the student's text.
- **Revised / unchanged:** after you run `uptake`, how many sent comments led to a change in the quoted passage.
- **Suggestion:** a rule of thumb. If half the class or more got a comment on a criterion, it suggests a whole-class mini-lesson; if fewer did, a small group. You decide.

Under the table it lists which students got a comment on each criterion, so you can form groups. The summary names students, so keep it on your computer. For a later round, add `--draft-number 2`.

### Which model should I use?
`eval` checks how reliably the local models on your computer draft usable, grounded feedback for your rubric:

```
python feedback_commons.py eval sample_rubric.json essays/ --models llama3.2:3b,qwen2.5:3b,gemma3:4b --out eval.json
```

For each model it reports:
- **usable_rate:** the share of replies that could be read
- **grounded_rate:** the share of comments whose quote really appears in the essay
- **seconds_per_request:** how long each reply takes

Add `--language Spanish` (or another language) to check the models in that language. `eval` doesn't judge whether the advice is good. That's your call. Run it on essays you're allowed to use, such as public sample essays, before you run it on your students' work.

### What export removes
`export` swaps each student for a random pseudonym that changes with every export. It removes:
- roster names (full names and each part)
- email addresses
- phone numbers
- long ID numbers

Automatic de-identification is never perfect, so **read the export yourself before sharing it**.

## MCP tool server (for developers)
`mcp` runs Feedback Commons as a [Model Context Protocol](https://modelcontextprotocol.io) server on stdio, so an AI app or agent can call its steps as tools:

```
python feedback_commons.py mcp --data-dir /path/to/class-folder
```

| Tool | What it does |
|---|---|
| `build_feedback_prompt` | Chat messages that ask any model for rubric-aligned, quote-grounded feedback on one criterion, optionally in another `language` |
| `check_feedback` | Reads a model's reply (or a list of comments) and marks each comment grounded only if its quote is really in the student's text |
| `draft_feedback` | Drafts and checks feedback with the Ollama model on this computer, optionally in another `language` |
| `revision_uptake` | For quotes from sent comments: did the revised text change each passage? |
| `class_summary` | The class summary above, from drafts and review events given inline or as files in `--data-dir`; `hide_names` swaps names for pseudonyms |

To add it to an MCP client, point the client at the command. Most clients use a config like this:

```json
{
  "mcpServers": {
    "feedback-commons": {
      "command": "python",
      "args": ["/path/to/feedback_commons.py", "mcp", "--data-dir", "/path/to/class-folder"]
    }
  }
}
```

If you installed it with pip, use `"command": "feedback-commons"` and `"args": ["mcp", "--data-dir", "/path/to/class-folder"]`.

- **Teacher approval isn't a tool.** No tool accepts, edits or sends feedback for the teacher. Decisions are made with `serve` or `review`, and only those decisions count in `class_summary`.
- **Where the data goes.** The server itself only talks to your Ollama server. But whatever a tool returns goes to the app that called it, and that app may send it to a cloud model. If student work must stay on the device, use the server only with an app that runs a local model, or pass `hide_names` and anonymized text.
- **Files.** `class_summary` reads files only inside `--data-dir` and refuses paths outside it. Without `--data-dir` it reads no files.
- **Model and host.** `draft_feedback` uses the `--model` and `--host` you start the server with. A caller may pick another model name, but not another host.
- **Languages.** A `language` must be a plain language name (letters, spaces, brackets, hyphens and apostrophes, 40 characters at most), so it can't carry other instructions into the prompt.
- **Protocol versions.** It supports MCP 2026-07-28 (the version goes in each request's `_meta`) and the older `initialize` handshake (2024-11-05 to 2025-11-25).

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
- **0.5.0:**
  - Added `--language` and `--languages` to write comments in each student's language, with an English gloss for the teacher on the review page and in the terminal. `eval` and the MCP tools take a language too.
  - Rubrics can be spreadsheets saved as CSV, and the new `rubric` command shows what was read.
  - Added `pyproject.toml`, so `pip install git+https://github.com/munimv2/feedback-commons` installs a `feedback-commons` command.
- **0.4.0:** Added `mcp`, an MCP tool server on stdio, with tools for prompts, quote checks, local drafting, revision checks and the class summary. It speaks MCP 2026-07-28 and the older handshake.
- **0.3.0:** Added `summary`, a class-level table per rubric criterion: who got a comment, what you sent or rejected, and what students revised, with a whole-class or small-group suggestion.
- **0.2.0:**
  - Added a local web review page (`serve`), and both review modes now resume where you left off.
  - Added `uptake` to track whether a revision changed the passages you commented on.
  - Added `eval` to compare how reliably local models draft grounded feedback.
  - Added made-up sample essays for trying the tool.
- **0.1.0:** First prototype, with `draft`, terminal `review` and consent-gated `export`.

## Plans
- An open benchmark that scores small local models' rubric-aligned feedback against teacher-approved feedback, using openly licensed essay datasets.
- More subjects than argument writing.
- A first real classroom trial, with a teacher who tells us what to fix.

## About
Feedback Commons was made by MV2 of Munim, Inc. The code and docs were written with AI agents working in MV2's name. MIT license.
