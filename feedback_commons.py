"""Feedback Commons: local-first, teacher-approved writing feedback.

Drafts rubric-aligned feedback on student writing with a small open model
running on the school's own computer (Ollama), so student work never leaves
the device. Every comment must quote the student's text; comments whose quote
cannot be found are flagged. The teacher accepts, edits or rejects each one,
in the terminal or on a local web page, and those decisions are logged
locally. With consent, the log can be exported as a de-identified dataset.

Standard library only. By MV2 of Munim, Inc.
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

__version__ = "0.2.0"

SCHEMA = "feedback-commons/1"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_HOST = "http://localhost:11434"

SYSTEM_PROMPT = (
    "You draft feedback on a student's writing for a teacher to review. "
    "The teacher decides what the student sees. Write for the student, "
    "kindly and specifically, at their grade level. For each comment give: "
    "quote (a short passage copied exactly from the student's text), "
    "feed_up (what good work looks like for this criterion), "
    "feed_back (how this passage does against it), and "
    "feed_forward (one concrete next step). "
    "Never invent quotes. Never comment on the student as a person. "
    'Reply with JSON only: {"comments": [{"quote": "...", "feed_up": "...", '
    '"feed_back": "...", "feed_forward": "..."}]}'
)

FIELDS = ("quote", "feed_up", "feed_back", "feed_forward")


# --- rubric and prompt -----------------------------------------------------

def load_rubric(path):
    """Read a rubric JSON file: {"title": ..., "criteria": [{"id", "name", "description"}]}."""
    with open(path, encoding="utf-8") as f:
        rubric = json.load(f)
    validate_rubric(rubric)
    return rubric


def validate_rubric(rubric):
    criteria = rubric.get("criteria") if isinstance(rubric, dict) else None
    if not criteria:
        raise ValueError("rubric needs a non-empty 'criteria' list")
    seen = set()
    for c in criteria:
        if not c.get("id") or not c.get("name"):
            raise ValueError("every criterion needs an 'id' and a 'name'")
        if c["id"] in seen:
            raise ValueError("duplicate criterion id: %s" % c["id"])
        seen.add(c["id"])
    return True


def build_messages(criterion, student_text, grade="", max_comments=2):
    """Chat messages asking for feedback on one rubric criterion."""
    lines = ["Criterion: %s" % criterion["name"]]
    if criterion.get("description"):
        lines.append("What it means: %s" % criterion["description"])
    if grade:
        lines.append("Grade level: %s" % grade)
    lines.append("Give at most %d comments." % max_comments)
    lines.append("Student text:\n<<<\n%s\n>>>" % student_text.strip())
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


def call_ollama(messages, model=DEFAULT_MODEL, host=DEFAULT_HOST, timeout=300):
    """Send messages to a local Ollama server and return the reply text."""
    body = json.dumps({"model": model, "messages": messages, "stream": False,
                       "format": "json", "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))["message"]["content"]


# --- parsing and grounding -------------------------------------------------

def parse_comments(raw):
    """Parse a model reply into a list of comment dicts. Raises ValueError."""
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("reply is not JSON: %s" % e)
    if isinstance(data, dict):
        data = data.get("comments")
    if not isinstance(data, list):
        raise ValueError("reply has no 'comments' list")
    comments = []
    for item in data:
        if not isinstance(item, dict):
            continue
        c = {k: str(item.get(k) or "").strip() for k in FIELDS}
        if c["quote"] and c["feed_forward"]:
            comments.append(c)
    return comments


def _norm(s):
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    return " ".join(s.lower().split())


def quote_found(quote, text):
    """True if the quote appears in the text (ignoring case, curly quotes and spacing)."""
    q = _norm(quote).strip(" .\"'")
    return len(q) >= 3 and q in _norm(text)


def ground(comments, text):
    """Mark each comment grounded or not; ungrounded ones are shown to the teacher flagged."""
    return [dict(c, grounded=quote_found(c["quote"], text)) for c in comments]


def revision_uptake(quote, revised_text):
    """Crude uptake signal: did the quoted passage change in the next draft?"""
    return "unchanged" if quote_found(quote, revised_text) else "revised"


# --- model reliability check -----------------------------------------------

def _rate(n, d):
    return round(n / d, 3) if d else None


def evaluate(rubric, essays, ask, grade="", clock=time.monotonic):
    """How reliable is one model as a feedback drafter on these essays?

    essays maps a name to its text; ask(messages) returns the model's reply.
    Counts replies that could not be used, comments whose quote is really in
    the essay, and seconds per request. It does not judge whether the advice
    is good: that is the teacher's call.
    """
    requests = unusable = comments = grounded = 0
    seconds = 0.0
    for name in sorted(essays):
        text = essays[name]
        for c in rubric["criteria"]:
            start = clock()
            raw = ask(build_messages(c, text, grade))
            seconds += clock() - start
            requests += 1
            try:
                got = ground(parse_comments(raw), text)
            except ValueError:
                unusable += 1
                continue
            comments += len(got)
            grounded += sum(1 for g in got if g["grounded"])
    return {"essays": len(essays), "requests": requests, "unusable_replies": unusable,
            "usable_rate": _rate(requests - unusable, requests),
            "comments": comments, "grounded_comments": grounded,
            "grounded_rate": _rate(grounded, comments),
            "seconds_per_request": round(seconds / requests, 2) if requests else None}


# --- teacher review --------------------------------------------------------

def review(comment, choose):
    """Apply a teacher decision. choose(comment) returns ("accept"|"reject", None) or ("edit", text)."""
    action, text = choose(comment)
    if action not in ("accept", "edit", "reject"):
        raise ValueError("unknown action: %s" % action)
    draft = comment["feed_forward"]
    final = {"accept": draft, "edit": text, "reject": ""}[action]
    return {"action": action, "draft": draft, "final": final}


def log_event(path, kind, **fields):
    event = {"schema": SCHEMA, "ts": datetime.datetime.now(datetime.timezone.utc)
             .strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": kind}
    event.update(fields)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_events(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _events_if_any(path):
    return read_events(path) if os.path.exists(path) else []


def reviewed_keys(events, draft_number=1):
    """(student, criterion, item) of every comment already decided in this draft round."""
    return {(e.get("student"), e.get("criterion"), e.get("item")) for e in events
            if e.get("kind") == "review" and e.get("draft_number", 1) == draft_number}


def pending(drafts, events, draft_number=1):
    """Drafted comments not yet decided, as (student, criterion, item, comment)."""
    done = reviewed_keys(events, draft_number)
    out = []
    for student, per in drafts.items():
        for criterion, comments in per.items():
            for i, c in enumerate(comments):
                if (student, criterion, i) not in done:
                    out.append((student, criterion, i, c))
    return out


def uptake_events(drafts, events, revised, draft_number=1):
    """For each comment the teacher sent (accepted or edited), did the next draft change that passage?"""
    sent = {(e.get("student"), e.get("criterion"), e.get("item")) for e in events
            if e.get("kind") == "review" and e.get("action") in ("accept", "edit")
            and e.get("draft_number", 1) == draft_number}
    out = []
    for student, per in drafts.items():
        if student not in revised:
            continue
        for criterion, comments in per.items():
            for i, c in enumerate(comments):
                if (student, criterion, i) in sent:
                    out.append({"student": student, "criterion": criterion, "item": i,
                                "draft_number": draft_number,
                                "uptake": revision_uptake(c["quote"], revised[student])})
    return out


# --- local review page -----------------------------------------------------

PAGE_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feedback Commons review</title>
<style>
body{font-family:system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.5}
.card{border:1px solid #bbb;border-radius:8px;padding:1rem;margin:1rem 0}
.flag{color:#a00;font-weight:bold}
blockquote{margin:0 0 .75rem;padding-left:.75rem;border-left:4px solid #888}
textarea{width:100%;min-height:5rem;font:inherit}
button{font:inherit;margin:.5rem .5rem 0 0;padding:.3rem .9rem}
</style></head><body>
<h1>Feedback Commons review</h1>
"""

PAGE_TAIL = "</body></html>\n"


def _count(drafts):
    return sum(len(cs) for per in drafts.values() for cs in per.values())


def render_review(items, total, token):
    """HTML for the review page: the next pending comment, or a done message."""
    e = html.escape
    if not items:
        body = ("<p>All %d comments are reviewed. Your decisions are in the log file. "
                "You can close this tab and stop the server with Ctrl+C.</p>" % total)
        return PAGE_HEAD + body + PAGE_TAIL
    student, criterion, i, c = items[0]
    flag = ("" if c.get("grounded") else
            '<p class="flag">This quote was NOT found in the student\'s text. '
            'Check it before accepting.</p>')
    hidden = "".join('<input type="hidden" name="%s" value="%s">' % (k, e(str(v)))
                     for k, v in (("token", token), ("student", student),
                                  ("criterion", criterion), ("item", i)))
    body = (
        "<p>%d of %d comments left.</p>" % (len(items), total)
        + '<div class="card"><h2>%s &middot; %s</h2>' % (e(student), e(criterion))
        + "<blockquote>%s</blockquote>%s" % (e(c.get("quote", "")), flag)
        + "<p><b>Feed up:</b> %s</p>" % e(c.get("feed_up", ""))
        + "<p><b>Feed back:</b> %s</p>" % e(c.get("feed_back", ""))
        + '<form method="post" action="/review">' + hidden
        + '<label for="text"><b>Feed forward</b> (what the student will see; edit it if you like)</label>'
        + '<textarea id="text" name="text">%s</textarea>' % e(c.get("feed_forward", ""))
        + '<button name="action" value="accept">Accept as drafted</button>'
        + '<button name="action" value="edit">Save my edit</button>'
        + '<button name="action" value="reject">Reject</button>'
        + "</form></div>"
    )
    return PAGE_HEAD + body + PAGE_TAIL


def decide(drafts, form, token):
    """Turn a submitted review form into review-event fields. Raises ValueError."""
    if not secrets.compare_digest(form.get("token", "").encode("utf-8"), token.encode("utf-8")):
        raise ValueError("this page is out of date; reload it")
    student, criterion = form.get("student", ""), form.get("criterion", "")
    try:
        item = int(form.get("item", ""))
        if item < 0:
            raise IndexError(item)
        c = drafts[student][criterion][item]
    except (KeyError, IndexError, ValueError, TypeError):
        raise ValueError("unknown comment")
    action, text = form.get("action", ""), form.get("text", "").strip()
    if action == "edit" and not text:
        raise ValueError("an edit needs some text")
    d = review(c, lambda _: (action, text or None))
    return dict(student=student, criterion=criterion, item=item, quote=c["quote"],
                grounded=c.get("grounded", False), **d)


def make_handler(drafts, log_path, draft_number=1, token=None):
    """Request handler for the local review page. Only answers requests addressed to this computer."""
    token = token or secrets.token_urlsafe(16)
    total = _count(drafts)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="text/html; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _local(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self._local():
                return self._send(403, "forbidden", "text/plain; charset=utf-8")
            if self.path != "/":
                return self._send(404, "not found", "text/plain; charset=utf-8")
            items = pending(drafts, _events_if_any(log_path), draft_number)
            self._send(200, render_review(items, total, token))

        def do_POST(self):
            if not self._local():
                return self._send(403, "forbidden", "text/plain; charset=utf-8")
            if self.path != "/review":
                return self._send(404, "not found", "text/plain; charset=utf-8")
            try:
                n = int(self.headers.get("Content-Length") or 0)
                form = dict(urllib.parse.parse_qsl(self.rfile.read(n).decode("utf-8"),
                                                   keep_blank_values=True))
                fields = decide(drafts, form, token)
            except ValueError as e:
                return self._send(400, str(e), "text/plain; charset=utf-8")
            key = (fields["student"], fields["criterion"], fields["item"])
            if key not in reviewed_keys(_events_if_any(log_path), draft_number):
                log_event(log_path, "review", draft_number=draft_number, **fields)
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    Handler.token = token
    return Handler


# --- de-identification and export ------------------------------------------

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w-])\+?\d[\d ().-]{7,}\d(?![\w-])")
LONG_ID = re.compile(r"\b\d{5,}\b")


def _phone(m):
    return "[PHONE]" if sum(ch.isdigit() for ch in m.group(0)) >= 9 else m.group(0)


def deidentify(text, roster=()):
    """Remove emails, roster names, phone numbers and long ID numbers from text."""
    text = EMAIL.sub("[EMAIL]", text)
    names = sorted({n.strip() for n in roster if n.strip()}, key=len, reverse=True)
    for name in names:
        text = re.sub(r"\b%s\b" % re.escape(name), "[STUDENT]", text, flags=re.I)
    for name in names:
        for part in name.split():
            if len(part) >= 2:
                text = re.sub(r"\b%s\b" % re.escape(part), "[STUDENT]", text, flags=re.I)
    text = PHONE.sub(_phone, text)
    return LONG_ID.sub("[ID]", text)


def pseudonym(student, salt):
    return "s-" + hashlib.sha256((salt + "\0" + student).encode("utf-8")).hexdigest()[:10]


KEEP = {"schema", "ts", "kind", "criterion", "action", "grounded", "draft_number",
        "uptake", "seconds"}


def export_records(events, roster, consented, salt):
    """De-identified records for consented students only. Use a fresh secret salt per export."""
    consented = set(consented)
    out = []
    for e in events:
        student = e.get("student")
        if student not in consented:
            continue
        rec = {"student": pseudonym(student, salt)}
        for k, v in e.items():
            if k == "student":
                continue
            rec[k] = v if (k in KEEP or not isinstance(v, str)) else deidentify(v, roster)
        out.append(rec)
    return out


# --- command line ----------------------------------------------------------

def _read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _read_essays(folder):
    """{student: text} for every .txt file in a folder; the file name is the student."""
    essays = {}
    for name in sorted(os.listdir(folder)):
        if name.endswith(".txt"):
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                essays[name[:-4]] = f.read()
    return essays


def _read_drafts(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_draft(args):
    rubric = load_rubric(args.rubric)
    results = {}
    for student, text in _read_essays(args.essays).items():
        per = {}
        for c in rubric["criteria"]:
            raw = call_ollama(build_messages(c, text, args.grade), args.model, args.host)
            try:
                per[c["id"]] = ground(parse_comments(raw), text)
            except ValueError as e:
                per[c["id"]] = []
                print("%s / %s: model reply unusable (%s)" % (student, c["id"], e), file=sys.stderr)
        results[student] = per
        print("drafted %s" % student, file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def _ask(comment):
    flag = "" if comment.get("grounded") else "  [quote NOT found in the text]"
    print('\n"%s"%s\n  up:      %s\n  back:    %s\n  forward: %s' % (
        comment["quote"], flag, comment["feed_up"], comment["feed_back"], comment["feed_forward"]))
    while True:
        a = input("[a]ccept, [e]dit, [r]eject? ").strip().lower()[:1]
        if a == "a":
            return "accept", None
        if a == "r":
            return "reject", None
        if a == "e":
            return "edit", input("your comment: ").strip()


def cmd_review(args):
    drafts = _read_drafts(args.drafts)
    for student, criterion, i, c in pending(drafts, _events_if_any(args.log), args.draft_number):
        print("\n=== %s / %s ===" % (student, criterion))
        d = review(c, _ask)
        log_event(args.log, "review", student=student, criterion=criterion, item=i,
                  quote=c["quote"], grounded=c.get("grounded", False),
                  draft_number=args.draft_number, **d)


def cmd_serve(args):
    drafts = _read_drafts(args.drafts)
    server = HTTPServer(("127.0.0.1", args.port), make_handler(drafts, args.log, args.draft_number))
    print("Review at http://127.0.0.1:%d/ (only this computer can open it). Ctrl+C stops it."
          % server.server_address[1], file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def cmd_uptake(args):
    drafts = _read_drafts(args.drafts)
    found = uptake_events(drafts, read_events(args.log), _read_essays(args.revised), args.draft_number)
    for u in found:
        log_event(args.log, "uptake", **u)
    revised = sum(1 for u in found if u["uptake"] == "revised")
    print("%d of %d sent comments led to a change in the quoted passage" % (revised, len(found)),
          file=sys.stderr)


def cmd_eval(args):
    rubric = load_rubric(args.rubric)
    essays = _read_essays(args.essays)
    reports = []
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        r = evaluate(rubric, essays, lambda m, model=model: call_ollama(m, model, args.host), args.grade)
        reports.append(dict({"model": model}, **r))
        print("%s: usable %s, grounded %s, %s s/request" % (
            model, r["usable_rate"], r["grounded_rate"], r["seconds_per_request"]), file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"schema": SCHEMA, "version": __version__, "rubric": rubric.get("title", ""),
                   "reports": reports}, f, indent=2, ensure_ascii=False)


def cmd_export(args):
    roster = _read_lines(args.roster)
    consented = _read_lines(args.consented)
    salt = os.urandom(16).hex()
    recs = export_records(read_events(args.log), roster, consented, salt)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("exported %d records; review them by hand before sharing" % len(recs), file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(prog="feedback-commons", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="draft feedback for a folder of .txt essays")
    d.add_argument("rubric")
    d.add_argument("essays")
    d.add_argument("--out", default="drafts.json")
    d.add_argument("--grade", default="")
    d.add_argument("--model", default=DEFAULT_MODEL)
    d.add_argument("--host", default=DEFAULT_HOST)
    d.set_defaults(func=cmd_draft)
    r = sub.add_parser("review", help="accept, edit or reject each drafted comment in the terminal")
    r.add_argument("drafts")
    r.add_argument("--log", default="events.jsonl")
    r.add_argument("--draft-number", type=int, default=1)
    r.set_defaults(func=cmd_review)
    s = sub.add_parser("serve", help="review drafted comments on a local web page")
    s.add_argument("drafts")
    s.add_argument("--log", default="events.jsonl")
    s.add_argument("--draft-number", type=int, default=1)
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(func=cmd_serve)
    u = sub.add_parser("uptake", help="log whether revised essays changed the passages you commented on")
    u.add_argument("drafts")
    u.add_argument("revised", help="folder of revised .txt essays, same file names")
    u.add_argument("--log", default="events.jsonl")
    u.add_argument("--draft-number", type=int, default=1, help="the round the comments were given in")
    u.set_defaults(func=cmd_uptake)
    v = sub.add_parser("eval", help="check how reliably local models draft grounded feedback")
    v.add_argument("rubric")
    v.add_argument("essays")
    v.add_argument("--models", default=DEFAULT_MODEL, help="comma-separated Ollama models")
    v.add_argument("--grade", default="")
    v.add_argument("--host", default=DEFAULT_HOST)
    v.add_argument("--out", default="eval.json")
    v.set_defaults(func=cmd_eval)
    e = sub.add_parser("export", help="de-identified export for consented students")
    e.add_argument("log")
    e.add_argument("--roster", required=True, help="file with one student name per line")
    e.add_argument("--consented", required=True, help="file with names of students whose families consented")
    e.add_argument("--out", default="dataset.jsonl")
    e.set_defaults(func=cmd_export)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
