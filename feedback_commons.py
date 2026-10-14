"""Feedback Commons: local-first, teacher-approved writing feedback.

Drafts rubric-aligned feedback on student writing with a small open model
running on the school's own computer (Ollama), so student work never leaves
the device. Every comment must quote the student's text; comments whose quote
cannot be found are flagged. Comments can be written in each student's own
language, with an English gloss for the teacher. Rubrics can come from a
spreadsheet saved as CSV. The teacher accepts, edits or rejects each comment,
in the terminal or on a local web page, and those decisions are logged
locally. A class summary shows which criteria most students need help with.
With consent, the log can be exported as a de-identified dataset. An MCP tool
server lets other AI tools use the drafting, quote checks and class summary.

Standard library only. By MV2 of Munim, Inc.
"""

import argparse
import csv
import datetime
import hashlib
import html
import io
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

__version__ = "0.5.0"

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

# A language name such as Spanish, Tiếng Việt or Português (Brasil); nothing that reads as an instruction.
LANGUAGE = re.compile(r"\w[\w ()'-]{0,39}")
ENGLISH = ("english", "en")


# --- rubric and prompt -----------------------------------------------------

def load_rubric(path):
    """Read a rubric: JSON {"title": ..., "criteria": [{"id", "name", "description"}]}, or a spreadsheet saved as CSV."""
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            rubric = rubric_from_csv(f.read(), os.path.splitext(os.path.basename(path))[0])
    else:
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


RUBRIC_NAME_COLUMNS = ("criterion", "criteria", "name", "category", "trait", "skill")


def _csv_cell(row, i):
    return " ".join(row[i].split()) if i is not None and i < len(row) else ""


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def rubric_from_csv(text, title=""):
    """Rubric from a spreadsheet saved as CSV, one row per criterion.

    The name column is headed criterion, name, category, trait or skill (else
    it is the first column). Columns headed id and description are optional.
    Every other headed column is a performance level, such as "4 - Exceeds",
    and its cells are added to the criterion's description.
    """
    rows = [r for r in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("the CSV file is empty")
    head = [_csv_cell(rows[0], i) for i in range(len(rows[0]))]
    low = [h.lower() for h in head]
    name_col = next((i for i, h in enumerate(low) if h in RUBRIC_NAME_COLUMNS), 0)
    id_col = low.index("id") if "id" in low else None
    desc_col = low.index("description") if "description" in low else None
    levels = [i for i, h in enumerate(head) if h and i not in (name_col, id_col, desc_col)]
    criteria, seen = [], set()
    for row in rows[1:]:
        name = _csv_cell(row, name_col)
        if not name:
            continue
        parts = [_csv_cell(row, desc_col)] if _csv_cell(row, desc_col) else []
        level_text = ["%s: %s" % (head[i], _csv_cell(row, i).rstrip(".")) for i in levels
                      if _csv_cell(row, i)]
        if level_text:
            parts.append("Levels: " + "; ".join(level_text))
        cid = _csv_cell(row, id_col)
        if not cid:
            base = _slug(name) or "c%d" % (len(criteria) + 1)
            cid, n = base, 2
            while cid in seen:
                cid, n = "%s-%d" % (base, n), n + 1
        seen.add(cid)
        criteria.append({"id": cid, "name": name, "description": " ".join(parts)})
    rubric = {"title": title, "criteria": criteria}
    validate_rubric(rubric)
    return rubric


def check_language(language):
    """'' or a language name such as Spanish; raises ValueError for anything else."""
    language = (language or "").strip()
    if language and not LANGUAGE.fullmatch(language):
        raise ValueError("a language must be a name such as Spanish or Tiếng Việt (40 characters at most)")
    return language


def build_messages(criterion, student_text, grade="", max_comments=2, language=""):
    """Chat messages asking for feedback on one rubric criterion, optionally in the student's language."""
    language = check_language(language)
    lines = ["Criterion: %s" % criterion["name"]]
    if criterion.get("description"):
        lines.append("What it means: %s" % criterion["description"])
    if grade:
        lines.append("Grade level: %s" % grade)
    if language:
        lines.append("Write feed_up, feed_back and feed_forward in %s. Copy each quote exactly "
                     "as the student wrote it." % language)
        if language.lower() not in ENGLISH:
            lines.append('Also give "gloss": feed_forward translated into English, for the teacher.')
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
        gloss = str(item.get("gloss") or "").strip()
        if gloss:
            c["gloss"] = gloss
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


def evaluate(rubric, essays, ask, grade="", clock=time.monotonic, language=""):
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
            raw = ask(build_messages(c, text, grade, language=language))
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


# --- class summary ---------------------------------------------------------

ACTION_COUNT = {"accept": "accepted", "edit": "edited", "reject": "rejected"}


def suggestion(students_sent, total):
    """Rule of thumb for the next lesson; the teacher decides."""
    if not students_sent:
        return "no comments sent"
    return "whole-class mini-lesson" if students_sent * 2 >= total else "small group"


def class_summary(drafts, events, criteria=None, draft_number=1):
    """Per-criterion picture of the class for one draft round, to plan what to teach next.

    criteria is the rubric's criteria list (for order and names); without it
    the criterion ids found in drafts are used. Students count as needing a
    criterion only when the teacher sent them a comment on it, not when the
    model merely drafted one.
    """
    decided, uptake = {}, {}
    for e in events:
        if e.get("draft_number", 1) != draft_number:
            continue
        key = (e.get("student"), e.get("criterion"), e.get("item"))
        if e.get("kind") == "review":
            decided.setdefault(key, e.get("action"))
        elif e.get("kind") == "uptake":
            uptake[key] = e.get("uptake")
    if criteria is None:
        criteria = [{"id": c, "name": c} for c in sorted({c for per in drafts.values() for c in per})]
    rows = []
    for c in criteria:
        row = {"criterion": c["id"], "name": c.get("name") or c["id"], "drafted": 0,
               "ungrounded": 0, "accepted": 0, "edited": 0, "rejected": 0, "not_reviewed": 0,
               "revised": 0, "unchanged": 0, "students_sent": []}
        for student in sorted(drafts):
            sent = False
            for i, comment in enumerate(drafts[student].get(c["id"], [])):
                key = (student, c["id"], i)
                row["drafted"] += 1
                if not comment.get("grounded"):
                    row["ungrounded"] += 1
                action = decided.get(key)
                row[ACTION_COUNT.get(action, "not_reviewed")] += 1
                if action in ("accept", "edit"):
                    sent = True
                    if uptake.get(key) in ("revised", "unchanged"):
                        row[uptake[key]] += 1
            if sent:
                row["students_sent"].append(student)
        row["share_sent"] = _rate(len(row["students_sent"]), len(drafts))
        row["suggestion"] = suggestion(len(row["students_sent"]), len(drafts))
        rows.append(row)
    return rows


def _cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_summary(rows, total, draft_number=1):
    """Markdown class summary. It names students, so keep it on this computer."""
    out = ["# Class summary, draft %d" % draft_number, "",
           "%d students. A student counts for a criterion when you sent them a comment on it "
           "(accepted or edited). Suggestions are a rule of thumb: half the class or more "
           "suggests a whole-class mini-lesson. You decide." % total, "",
           "| Criterion | Students sent a comment | Comments sent | Rejected | Not reviewed "
           "| Quote not found | Revised / unchanged | Suggestion |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %d of %d | %d | %d | %d | %d | %d / %d | %s |" % (
            _cell(r["name"]), len(r["students_sent"]), total, r["accepted"] + r["edited"],
            r["rejected"], r["not_reviewed"], r["ungrounded"], r["revised"], r["unchanged"],
            r["suggestion"]))
    for r in rows:
        if r["students_sent"]:
            out += ["", "## %s" % r["name"], "",
                    "Sent a comment: %s" % ", ".join(r["students_sent"])]
    return "\n".join(out) + "\n"


# --- local review page -----------------------------------------------------

PAGE_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feedback Commons review</title>
<style>
body{font-family:system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.5}
.card{border:1px solid #bbb;border-radius:8px;padding:1rem;margin:1rem 0}
.flag{color:#a00;font-weight:bold}
.gloss{background:#f3f3f3;padding:.5rem .75rem;border-radius:6px}
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
    gloss = ("" if not c.get("gloss") else
             '<p class="gloss"><b>In English, for you:</b> %s<br><small>The model\'s translation '
             'of the feed forward, not checked. Students see only the box below.</small></p>'
             % e(c["gloss"]))
    hidden = "".join('<input type="hidden" name="%s" value="%s">' % (k, e(str(v)))
                     for k, v in (("token", token), ("student", student),
                                  ("criterion", criterion), ("item", i)))
    body = (
        "<p>%d of %d comments left.</p>" % (len(items), total)
        + '<div class="card"><h2>%s &middot; %s</h2>' % (e(student), e(criterion))
        + "<blockquote>%s</blockquote>%s" % (e(c.get("quote", "")), flag)
        + "<p><b>Feed up:</b> %s</p>" % e(c.get("feed_up", ""))
        + "<p><b>Feed back:</b> %s</p>" % e(c.get("feed_back", ""))
        + gloss
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


# --- MCP tool server -------------------------------------------------------

# Modern MCP sends the version in every request's _meta; legacy MCP opens with initialize.
MCP_VERSIONS = ("2026-07-28",)
MCP_LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_SERVER = "io.modelcontextprotocol/serverInfo"
SERVER_INFO = {"name": "feedback-commons", "title": "Feedback Commons", "version": __version__}
MODEL_NAME = re.compile(r"^[\w.:/-]{1,100}$")

MCP_INSTRUCTIONS = (
    "Tools for teacher-approved writing feedback: draft or check comments that must quote "
    "the student's text, see whether a revision changed the quoted passages, and summarize "
    "a class by rubric criterion. No tool approves feedback or sends it to a student; the "
    "teacher decides with 'feedback_commons.py serve' or 'review'. Results can contain "
    "student writing and names, and they go to the app that called the tool."
)

_CRITERION = {"type": "object", "description": "One rubric criterion.",
              "properties": {"id": {"type": "string"}, "name": {"type": "string"},
                             "description": {"type": "string"}},
              "required": ["name"]}
_TEXT = {"type": "string", "description": "The student's writing."}
_GRADE = {"type": "string", "description": "Grade level, for example \"8\"."}
_MAX = {"type": "integer", "minimum": 1, "maximum": 5,
        "description": "The most comments to ask for (default 2)."}
_LANG = {"type": "string", "maxLength": 40,
         "description": "Language for the comments, for example \"Spanish\". Quotes stay as the "
                        "student wrote them, and each comment also gets an English 'gloss' for "
                        "the teacher."}
_READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
              "openWorldHint": False}

MCP_TOOLS = [
    {"name": "build_feedback_prompt", "title": "Build a feedback prompt",
     "description": "Chat messages asking a model for rubric-aligned feedback on one criterion, "
                    "where every comment quotes the student (feed up, feed back, feed forward). "
                    "Send them to your own model, then pass its reply to check_feedback.",
     "inputSchema": {"type": "object", "properties": {
         "criterion": _CRITERION, "student_text": _TEXT, "grade": _GRADE, "max_comments": _MAX,
         "language": _LANG},
         "required": ["criterion", "student_text"]},
     "annotations": _READ_ONLY},
    {"name": "check_feedback", "title": "Check feedback quotes against the text",
     "description": "Reads a model's feedback reply (JSON text) or a list of comments and marks "
                    "each comment grounded only if its quote really appears in the student's "
                    "text. Show ungrounded comments to the teacher flagged, or drop them.",
     "inputSchema": {"type": "object", "properties": {
         "student_text": _TEXT,
         "reply": {"type": "string", "description": "The model's reply, as text."},
         "comments": {"type": "array", "items": {"type": "object"},
                      "description": "Comments with at least 'quote' and 'feed_forward'."}},
         "required": ["student_text"]},
     "annotations": _READ_ONLY},
    {"name": "draft_feedback", "title": "Draft feedback with the local model",
     "description": "Drafts quote-checked feedback on one criterion with the Ollama model on "
                    "this computer, so the essay goes to no other model. The comments are "
                    "drafts for the teacher to accept, edit or reject; nothing reaches a student.",
     "inputSchema": {"type": "object", "properties": {
         "criterion": _CRITERION, "student_text": _TEXT, "grade": _GRADE, "max_comments": _MAX,
         "language": _LANG,
         "model": {"type": "string", "description": "Ollama model name (default: the server's)."}},
         "required": ["criterion", "student_text"]},
     "annotations": dict(_READ_ONLY, idempotentHint=False)},
    {"name": "revision_uptake", "title": "Did the revision change the quoted passages?",
     "description": "For feedback the teacher sent: 'revised' means the quoted passage is no "
                    "longer in the revised text word for word, 'unchanged' means it still is. "
                    "A rough signal, not a grade.",
     "inputSchema": {"type": "object", "properties": {
         "quotes": {"type": "array", "items": {"type": "string"},
                    "description": "Quotes from the comments the teacher sent."},
         "revised_text": {"type": "string", "description": "The student's revised writing."}},
         "required": ["quotes", "revised_text"]},
     "annotations": _READ_ONLY},
    {"name": "class_summary", "title": "Class summary by rubric criterion",
     "description": "From the teacher's review decisions, one row per criterion: students sent "
                    "a comment, rejected or unreviewed drafts, quotes not found, revised or "
                    "unchanged, and a whole-class or small-group suggestion. Only teacher "
                    "decisions count. Give drafts and events inline, or file names inside the "
                    "server's --data-dir.",
     "inputSchema": {"type": "object", "properties": {
         "drafts": {"type": "object",
                    "description": "Content of drafts.json: {student: {criterion_id: [comments]}}."},
         "events": {"type": "array", "items": {"type": "object"},
                    "description": "Events from the review log (events.jsonl)."},
         "drafts_file": {"type": "string", "description": "drafts.json inside --data-dir."},
         "log_file": {"type": "string", "description": "events.jsonl inside --data-dir."},
         "criteria": {"type": "array", "description": "Rubric criteria, for names and order.",
                      "items": {"type": "object", "properties": {
                          "id": {"type": "string"}, "name": {"type": "string"}},
                          "required": ["id"]}},
         "draft_number": {"type": "integer", "minimum": 1},
         "hide_names": {"type": "boolean",
                        "description": "Replace student names with pseudonyms that last "
                                       "while the server runs."}}},
     "annotations": _READ_ONLY},
]


class RpcError(Exception):
    def __init__(self, code, message, data=None):
        Exception.__init__(self, message)
        self.code, self.data = code, data


def _text_arg(args, key):
    v = args.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError("'%s' must be a non-empty string" % key)
    return v


def _criterion_arg(args):
    c = args.get("criterion")
    if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not c["name"].strip():
        raise ValueError("'criterion' needs a 'name', for example {\"name\": \"Evidence\"}")
    return {"name": c["name"], "description": str(c.get("description") or "")}


def _max_arg(args):
    n = args.get("max_comments", 2)
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 5:
        raise ValueError("'max_comments' must be a whole number from 1 to 5")
    return n


def _language_arg(args):
    v = args.get("language") or ""
    if not isinstance(v, str):
        raise ValueError("'language' must be a string such as \"Spanish\"")
    return v


def _checked(comments):
    return {"comments": comments, "grounded": sum(1 for c in comments if c["grounded"]),
            "ungrounded": sum(1 for c in comments if not c["grounded"])}


def _data_file(root, name):
    """A file inside the server's data folder; refuses anything outside it."""
    if not root:
        raise ValueError("start the server with --data-dir to read files")
    if not isinstance(name, str) or not name:
        raise ValueError("file names must be non-empty strings")
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, name))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("%s is outside the data folder" % name)
    return path


def tool_build_feedback_prompt(args, state):
    return {"messages": build_messages(_criterion_arg(args), _text_arg(args, "student_text"),
                                       str(args.get("grade") or ""), _max_arg(args),
                                       _language_arg(args))}


def tool_check_feedback(args, state):
    text = _text_arg(args, "student_text")
    if isinstance(args.get("reply"), str):
        comments = parse_comments(args["reply"])
    elif isinstance(args.get("comments"), list):
        comments = parse_comments(json.dumps({"comments": args["comments"]}))
    else:
        raise ValueError("give 'reply' (the model's text) or 'comments' (a list)")
    return _checked(ground(comments, text))


def tool_draft_feedback(args, state):
    criterion, text = _criterion_arg(args), _text_arg(args, "student_text")
    model = args.get("model") or state["model"]
    if not isinstance(model, str) or not MODEL_NAME.match(model):
        raise ValueError("'model' must be an Ollama model name such as llama3.2:3b")
    messages = build_messages(criterion, text, str(args.get("grade") or ""), _max_arg(args),
                              _language_arg(args))
    try:
        raw = state["ask"](messages, model)
    except OSError as e:
        raise ValueError("could not reach Ollama (%s); is it running?" % e)
    return dict(_checked(ground(parse_comments(raw), text)), model=model)


def tool_revision_uptake(args, state):
    quotes, revised = args.get("quotes"), _text_arg(args, "revised_text")
    if not isinstance(quotes, list) or not all(isinstance(q, str) for q in quotes):
        raise ValueError("'quotes' must be a list of strings")
    results = [{"quote": q, "uptake": revision_uptake(q, revised)} for q in quotes]
    return {"results": results, "revised": sum(1 for r in results if r["uptake"] == "revised")}


def tool_class_summary(args, state):
    if "drafts_file" in args:
        drafts = _read_drafts(_data_file(state.get("data_dir"), args["drafts_file"]))
    else:
        drafts = args.get("drafts")
    if "log_file" in args:
        events = _events_if_any(_data_file(state.get("data_dir"), args["log_file"]))
    else:
        events = args.get("events", [])
    if not isinstance(drafts, dict) or not all(isinstance(per, dict) for per in drafts.values()):
        raise ValueError("give 'drafts' ({student: {criterion_id: [comments]}}) or 'drafts_file'")
    if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
        raise ValueError("'events' must be a list of review-log events")
    criteria = args.get("criteria")
    if criteria is not None and not (isinstance(criteria, list) and
                                     all(isinstance(c, dict) and c.get("id") for c in criteria)):
        raise ValueError("every criterion needs an 'id'")
    draft_number = args.get("draft_number", 1)
    if isinstance(draft_number, bool) or not isinstance(draft_number, int):
        raise ValueError("'draft_number' must be a whole number")
    if args.get("hide_names"):
        names = {s: pseudonym(s, state["salt"]) for s in drafts}
        drafts = {names[s]: per for s, per in drafts.items()}
        events = [dict(e, student=names.get(e.get("student"), e.get("student"))) for e in events]
    rows = class_summary(drafts, events, criteria, draft_number)
    return {"students": len(drafts), "rows": rows,
            "markdown": render_summary(rows, len(drafts), draft_number)}


MCP_HANDLERS = {"build_feedback_prompt": tool_build_feedback_prompt,
                "check_feedback": tool_check_feedback,
                "draft_feedback": tool_draft_feedback,
                "revision_uptake": tool_revision_uptake,
                "class_summary": tool_class_summary}


def _tool_result(data, error=None):
    if error is not None:
        return {"content": [{"type": "text", "text": error}], "isError": True}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
            "structuredContent": data, "isError": False}


def call_tool(params, state):
    """Run one tool. Bad arguments come back as a tool error the model can fix."""
    fn = MCP_HANDLERS.get(params.get("name"))
    if fn is None:
        raise RpcError(-32602, "Unknown tool: %s" % params.get("name"))
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        raise RpcError(-32602, "'arguments' must be an object")
    try:
        return _tool_result(fn(args, state))
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        return _tool_result(None, str(e) or e.__class__.__name__)


def mcp_state(model=DEFAULT_MODEL, host=DEFAULT_HOST, data_dir=None, ask=None):
    """Server settings. ask(messages, model) returns a model reply; by default it calls Ollama."""
    return {"model": model, "data_dir": data_dir, "legacy": None, "salt": os.urandom(16).hex(),
            "ask": ask or (lambda messages, m: call_ollama(messages, m, host))}


def _dispatch(method, params, state):
    """(result, modern) for one request."""
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise RpcError(-32602, "params must be an object")
    meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
    if method == "initialize":
        asked = params.get("protocolVersion")
        state["legacy"] = asked if asked in MCP_LEGACY_VERSIONS else MCP_LEGACY_VERSIONS[0]
        return {"protocolVersion": state["legacy"], "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO, "instructions": MCP_INSTRUCTIONS}, False
    version = meta.get(META_VERSION)
    if version is not None:
        if version not in MCP_VERSIONS:
            raise RpcError(-32022, "Unsupported protocol version",
                           {"supported": list(MCP_VERSIONS), "requested": version})
        if not isinstance(meta.get(META_CAPS), dict):
            raise RpcError(-32602, "_meta needs %s" % META_CAPS)
        modern = True
    elif state.get("legacy") or method == "ping":
        modern = False
    else:
        raise RpcError(-32602, "send %s %s in _meta, or call initialize first"
                       % (META_VERSION, MCP_VERSIONS[0]))
    if method == "server/discover":
        return {"supportedVersions": list(MCP_VERSIONS), "capabilities": {"tools": {}},
                "instructions": MCP_INSTRUCTIONS}, modern
    if method == "ping":
        return {}, modern
    if method == "tools/list":
        return {"tools": MCP_TOOLS}, modern
    if method == "tools/call":
        return call_tool(params, state), modern
    raise RpcError(-32601, "Method not found: %s" % method)


def _rpc_error(rid, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": rid, "error": err}


def handle_mcp(msg, state):
    """Answer one JSON-RPC message from an MCP client; None when no answer is due."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        if isinstance(msg, dict) and ("result" in msg or "error" in msg):
            return None  # a response; this server sends no requests
        return _rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid request")
    if "id" not in msg:
        return None  # notifications such as initialized or cancelled
    rid = msg["id"]
    try:
        result, modern = _dispatch(msg["method"], msg.get("params"), state)
    except RpcError as e:
        return _rpc_error(rid, e.code, str(e), e.data)
    except Exception as e:
        return _rpc_error(rid, -32603, "Internal error: %s" % e)
    if modern:
        result = dict(result, resultType="complete", _meta={META_SERVER: SERVER_INFO})
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve_mcp(inp, out, state):
    """stdio transport over binary streams: one JSON-RPC message per line in and out."""
    for raw in iter(inp.readline, b""):
        line = raw.decode("utf-8", "replace")
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply = _rpc_error(None, -32700, "Parse error")
        else:
            reply = handle_mcp(msg, state)
        if reply is not None:
            out.write((json.dumps(reply) + "\n").encode("utf-8"))
            out.flush()


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


def read_languages(path):
    """{student: language} from a CSV of student,language rows; a header row is fine."""
    languages = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            student, language = _csv_cell(row, 0), _csv_cell(row, 1)
            if not student or not language:
                continue
            if (student.lower(), language.lower()) == ("student", "language"):
                continue
            languages[student] = check_language(language)
    return languages


def cmd_draft(args):
    rubric = load_rubric(args.rubric)
    essays = _read_essays(args.essays)
    languages = read_languages(args.languages) if args.languages else {}
    unknown = sorted(set(languages) - set(essays))
    if unknown:
        print("no essay file for %s; check the names in %s" % (", ".join(unknown), args.languages),
              file=sys.stderr)
    results = {}
    for student, text in essays.items():
        language = languages.get(student, args.language)
        per = {}
        for c in rubric["criteria"]:
            raw = call_ollama(build_messages(c, text, args.grade, language=language),
                              args.model, args.host)
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
    if comment.get("gloss"):
        print("  english: %s  (the model's translation, not checked)" % comment["gloss"])
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


def cmd_summary(args):
    drafts = _read_drafts(args.drafts)
    criteria = load_rubric(args.rubric)["criteria"] if args.rubric else None
    rows = class_summary(drafts, _events_if_any(args.log), criteria, args.draft_number)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_summary(rows, len(drafts), args.draft_number))
    print("wrote %s; it names students, so keep it on this computer" % args.out, file=sys.stderr)


def cmd_eval(args):
    rubric = load_rubric(args.rubric)
    essays = _read_essays(args.essays)
    reports = []
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        r = evaluate(rubric, essays, lambda m, model=model: call_ollama(m, model, args.host), args.grade,
                     language=args.language)
        reports.append(dict({"model": model}, **r))
        print("%s: usable %s, grounded %s, %s s/request" % (
            model, r["usable_rate"], r["grounded_rate"], r["seconds_per_request"]), file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"schema": SCHEMA, "version": __version__, "rubric": rubric.get("title", ""),
                   "language": args.language, "reports": reports}, f, indent=2, ensure_ascii=False)


def cmd_rubric(args):
    rubric = load_rubric(args.source)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rubric, f, indent=2, ensure_ascii=False)
    print("wrote %s with %d criteria; check the names and descriptions before drafting"
          % (args.out, len(rubric["criteria"])), file=sys.stderr)


def cmd_export(args):
    roster = _read_lines(args.roster)
    consented = _read_lines(args.consented)
    salt = os.urandom(16).hex()
    recs = export_records(read_events(args.log), roster, consented, salt)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("exported %d records; review them by hand before sharing" % len(recs), file=sys.stderr)


def cmd_mcp(args):
    state = mcp_state(args.model, args.host, args.data_dir)
    print("Feedback Commons %s MCP server on stdio" % __version__, file=sys.stderr)
    serve_mcp(sys.stdin.buffer, sys.stdout.buffer, state)


def main(argv=None):
    p = argparse.ArgumentParser(prog="feedback-commons", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="draft feedback for a folder of .txt essays")
    d.add_argument("rubric", help="rubric .json, or a spreadsheet saved as .csv")
    d.add_argument("essays")
    d.add_argument("--out", default="drafts.json")
    d.add_argument("--grade", default="")
    d.add_argument("--language", default="", help="write comments in this language, e.g. Spanish")
    d.add_argument("--languages", help="CSV of student,language rows for students who need another language")
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
    m = sub.add_parser("summary", help="class summary: which criteria most students need help with")
    m.add_argument("drafts")
    m.add_argument("--log", default="events.jsonl")
    m.add_argument("--rubric", help="rubric file, for criterion names and order")
    m.add_argument("--draft-number", type=int, default=1)
    m.add_argument("--out", default="summary.md")
    m.set_defaults(func=cmd_summary)
    v = sub.add_parser("eval", help="check how reliably local models draft grounded feedback")
    v.add_argument("rubric")
    v.add_argument("essays")
    v.add_argument("--models", default=DEFAULT_MODEL, help="comma-separated Ollama models")
    v.add_argument("--grade", default="")
    v.add_argument("--language", default="", help="ask for comments in this language")
    v.add_argument("--host", default=DEFAULT_HOST)
    v.add_argument("--out", default="eval.json")
    v.set_defaults(func=cmd_eval)
    b = sub.add_parser("rubric", help="turn a spreadsheet rubric saved as CSV into rubric JSON you can check")
    b.add_argument("source", help="rubric .csv (or .json, to check it)")
    b.add_argument("--out", default="rubric.json")
    b.set_defaults(func=cmd_rubric)
    e = sub.add_parser("export", help="de-identified export for consented students")
    e.add_argument("log")
    e.add_argument("--roster", required=True, help="file with one student name per line")
    e.add_argument("--consented", required=True, help="file with names of students whose families consented")
    e.add_argument("--out", default="dataset.jsonl")
    e.set_defaults(func=cmd_export)
    c = sub.add_parser("mcp", help="MCP tool server on stdio, for AI apps and agents")
    c.add_argument("--data-dir", help="folder whose drafts and logs class_summary may read")
    c.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model for draft_feedback")
    c.add_argument("--host", default=DEFAULT_HOST)
    c.set_defaults(func=cmd_mcp)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
