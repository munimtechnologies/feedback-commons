"""quote-fidelity-v6: run one model x language x condition cell (research/PREREG-v6.md).

v6 asks whether one added sentence telling the model to quote the student's
exact words raises the exact-quote rate. Each cell is a v5 cell run again on the
same 120 essays (v5/essays.json), under one prompt condition:

  c  control: the v3/v4/v5 feedback prompt, byte-for-byte (Feedback Commons
     0.5.0's build_messages, unchanged)
  q  quote-exactly: the same messages with INSTRUCTION added as its own line of
     the user message, after "Give at most 2 comments." and just before the
     student text

Everything else is v3_run.py's run: temperature 0.2, request seed 1, the same
rubric criteria, budget and summary files. Each line of requests.jsonl also
carries "condition", so v6_analyze.py can pair the cells. Standard library
only. By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import hashlib
import json
import os
import sys

import quote_fidelity as qf
import v3_run as v3r

fc = qf.fc
STUDY, SAMPLE = "quote-fidelity-v6", "quote-fidelity-v5"
CONDITIONS = ("c", "q")
ESSAYS, PER_BAND = 120, 60
# Fixed verbatim in PREREG-v6.md; test_v6_run checks the two agree.
INSTRUCTION = ("When you quote the student, copy their words exactly as the student wrote them — the same "
               "spelling, the same punctuation and the same capitalization, even if something looks wrong "
               "— and put the copied words inside quotation marks.")
MARKER = "\nStudent text:\n<<<\n"


def add_instruction(messages):
    """The messages with INSTRUCTION as its own line of the user message, just before the student text."""
    out = [dict(m) for m in messages]
    user = out[-1]
    head, marker, tail = user["content"].partition(MARKER)
    if user.get("role") != "user" or not marker:
        raise ValueError("not Feedback Commons feedback messages: the last message has no student text")
    user["content"] = head + "\n" + INSTRUCTION + marker + tail
    return out


def condition_ask(ask, condition):
    """ask(messages, model) for one condition: ask itself for c, with INSTRUCTION added for q."""
    if condition == "c":
        return ask
    if condition == "q":
        return lambda messages, model: ask(add_instruction(messages), model)
    raise ValueError("the condition must be c or q, not %r" % (condition,))


class Tagged:
    """The file run_study writes to, with the cell's condition added to every JSON line."""

    def __init__(self, out, condition):
        self.out, self.condition = out, condition

    def write(self, line):
        rec = json.loads(line)
        rec["condition"] = self.condition
        self.out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def flush(self):
        self.out.flush()


def check_selection(selection):
    """ValueError unless this is v5's selection: its study tag, 120 unique essays, 60 in each band."""
    if selection.get("study") != SAMPLE:
        raise ValueError("v6 reuses the %s essays; this selection is %r" % (SAMPLE, selection.get("study")))
    essays = selection.get("essays", [])
    ids = [e["id"] for e in essays]
    bands = [e["band"] for e in essays]
    if (len(ids) != ESSAYS or len(set(ids)) != ESSAYS
            or bands.count("low") != PER_BAND or bands.count("high") != PER_BAND):
        raise ValueError("the v5 selection holds %d unique essays, %d low and %d high, not %d, %d and %d"
                         % (len(set(ids)), bands.count("low"), bands.count("high"),
                            ESSAYS, PER_BAND, PER_BAND))
    if not selection.get("data_sha256"):
        raise ValueError("the selection does not record the ELLIPSE file's SHA-256")


def file_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def cmd_run(args):
    selection = v3r.read_selection(args.essays)
    try:
        check_selection(selection)
    except ValueError as err:
        sys.exit(str(err))
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)
    try:
        essays = v3r.load_essays(args.data_dir, selection)
    except ValueError as err:
        sys.exit(str(err))
    wanted = v3r._split(args.criteria)
    criteria = [c for c in fc.load_rubric(args.rubric)["criteria"] if c["id"] in wanted]
    if len(criteria) != len(wanted):
        sys.exit("the rubric lacks a criterion of %s" % ", ".join(wanted))
    language = "" if args.language.strip().lower() in fc.ENGLISH else fc.check_language(args.language)
    known = qf.spell_checker()
    meta = {"study": STUDY, "sample": selection["study"], "essays_sha256": file_sha256(args.essays),
            "condition": args.condition, "instruction": INSTRUCTION if args.condition == "q" else None,
            "feedback_commons": fc.__version__, "model": args.model,
            "language": qf.language_label(language), "criteria": wanted, "temperature": v3r.TEMPERATURE,
            "request_seed": v3r.REQUEST_SEED, "timeout_seconds": v3r.TIMEOUT,
            "ollama_context_length": os.environ.get("OLLAMA_CONTEXT_LENGTH"),
            "server": v3r.server_info(args.host, args.model), "essays_selected": len(essays),
            "low_max": 2.5, "high_min": 4.0, "spell_checker": known is not None, "data": qf.ELLIPSE_URL,
            "data_sha256": selection["data_sha256"], "data_license": v3r.LICENSE,
            "budget_minutes": args.budget_minutes, "started": v3r._now()}
    print("%d essays, %s, %s, condition %s" % (len(essays), args.model, meta["language"], args.condition),
          file=sys.stderr)
    ask = condition_ask(v3r.seeded_ask(args.host), args.condition)
    with open(os.path.join(args.out_dir, "requests.jsonl"), "w", encoding="utf-8") as out:
        records = qf.run_study(essays, criteria, [args.model], [language], ask, Tagged(out, args.condition),
                               args.budget_minutes * 60, known=known)
    meta["essays_done"] = len({r["essay"] for r in records})
    meta["finished"] = v3r._now()
    summary = qf.summarize(records)
    summary["failures"] = v3r.failures(records)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(dict(meta=meta, **summary), f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(qf.render_markdown(summary, meta))
    print(json.dumps(summary["overall"]), file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--essays", required=True, help="v5/essays.json")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--language", required=True, help="English or Spanish")
    p.add_argument("--condition", required=True, choices=CONDITIONS)
    p.add_argument("--rubric", default="sample_rubric.json")
    p.add_argument("--criteria", default=v3r.CRITERIA)
    p.add_argument("--budget-minutes", type=float, default=420)
    p.add_argument("--host", default=fc.DEFAULT_HOST)
    cmd_run(p.parse_args(argv))


if __name__ == "__main__":
    main()
