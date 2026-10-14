import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer

import feedback_commons as fc

RUBRIC = {"title": "Argument", "criteria": [
    {"id": "claim", "name": "Clear claim", "description": "States a position the essay defends."},
    {"id": "evidence", "name": "Evidence", "description": "Supports the claim with specific evidence."},
]}

ESSAY = ("School should start later. Teenagers   need more sleep, and tired students "
         "can't focus. In conclusion, it is good.")

DRAFTS = {
    "Ana Ruiz": {"claim": [
        {"quote": "it is good", "feed_up": "u", "feed_back": "b", "feed_forward": "Say why.", "grounded": True},
        {"quote": "made up <b>", "feed_up": "u", "feed_back": "b", "feed_forward": "Add a reason.", "grounded": False},
    ]},
    "Ben Ode": {"evidence": [
        {"quote": "tired students", "feed_up": "u", "feed_back": "b", "feed_forward": "Cite a study.", "grounded": True},
    ]},
}

# Ignores proxy settings so the tests always reach the local server.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def review_event(student, criterion, item, action, draft_number=1):
    return {"schema": fc.SCHEMA, "kind": "review", "student": student, "criterion": criterion,
            "item": item, "action": action, "draft_number": draft_number}


def uptake_event(student, criterion, item, uptake, draft_number=1):
    return {"schema": fc.SCHEMA, "kind": "uptake", "student": student, "criterion": criterion,
            "item": item, "uptake": uptake, "draft_number": draft_number}


class RubricTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(fc.validate_rubric(RUBRIC))

    def test_missing_criteria(self):
        with self.assertRaises(ValueError):
            fc.validate_rubric({"title": "x", "criteria": []})

    def test_duplicate_id(self):
        bad = {"criteria": [{"id": "a", "name": "A"}, {"id": "a", "name": "B"}]}
        with self.assertRaises(ValueError):
            fc.validate_rubric(bad)

    def test_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(RUBRIC, f)
            self.assertEqual(fc.load_rubric(p)["title"], "Argument")


class PromptTests(unittest.TestCase):
    def test_messages(self):
        m = fc.build_messages(RUBRIC["criteria"][1], ESSAY, grade="8", max_comments=3)
        self.assertEqual([x["role"] for x in m], ["system", "user"])
        self.assertIn("Never invent quotes", m[0]["content"])
        self.assertIn("Criterion: Evidence", m[1]["content"])
        self.assertIn("Grade level: 8", m[1]["content"])
        self.assertIn("at most 3 comments", m[1]["content"])
        self.assertIn("School should start later.", m[1]["content"])


class ParseTests(unittest.TestCase):
    def test_dict(self):
        raw = json.dumps({"comments": [{"quote": "it is good", "feed_up": "u",
                                        "feed_back": "b", "feed_forward": "f"}]})
        c = fc.parse_comments(raw)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["quote"], "it is good")

    def test_fenced_list(self):
        raw = '```json\n[{"quote": "School should start later", "feed_forward": "Add a reason."}]\n```'
        c = fc.parse_comments(raw)
        self.assertEqual(c[0]["feed_forward"], "Add a reason.")
        self.assertEqual(c[0]["feed_up"], "")

    def test_drops_incomplete(self):
        raw = json.dumps({"comments": [{"quote": "", "feed_forward": "x"},
                                       {"quote": "q q q", "feed_forward": ""},
                                       "not a dict",
                                       {"quote": "tired students", "feed_forward": "Cite a study."}]})
        c = fc.parse_comments(raw)
        self.assertEqual([x["quote"] for x in c], ["tired students"])

    def test_not_json(self):
        with self.assertRaises(ValueError):
            fc.parse_comments("Sure! Here is my feedback.")

    def test_no_list(self):
        with self.assertRaises(ValueError):
            fc.parse_comments('{"feedback": "good"}')


class GroundingTests(unittest.TestCase):
    def test_spacing_and_case(self):
        self.assertTrue(fc.quote_found("teenagers need more sleep", ESSAY))

    def test_curly_quotes(self):
        self.assertTrue(fc.quote_found("“tired students can’t focus.”", ESSAY))

    def test_invented(self):
        self.assertFalse(fc.quote_found("studies show sleep improves grades", ESSAY))

    def test_too_short(self):
        self.assertFalse(fc.quote_found("is", ESSAY))
        self.assertFalse(fc.quote_found("", ESSAY))

    def test_ground(self):
        g = fc.ground([{"quote": "it is good"}, {"quote": "made up"}], ESSAY)
        self.assertEqual([x["grounded"] for x in g], [True, False])

    def test_uptake(self):
        revised = ESSAY.replace("it is good", "later start times help students learn")
        self.assertEqual(fc.revision_uptake("it is good", revised), "revised")
        self.assertEqual(fc.revision_uptake("tired students", revised), "unchanged")


class EvalTests(unittest.TestCase):
    def reply(self, *quotes):
        return json.dumps({"comments": [{"quote": q, "feed_forward": "Do this."} for q in quotes]})

    def test_counts(self):
        replies = iter([
            self.reply("it is good", "studies show sleep helps"),  # a / claim
            "Sure! Here is my feedback.",                           # a / evidence
            self.reply("tired students"),                           # b / claim
            self.reply(),                                           # b / evidence
        ])
        ticks = iter([0, 2, 2, 3, 3, 4, 4, 8])
        seen = []

        def ask(messages):
            seen.append(messages)
            return next(replies)

        r = fc.evaluate(RUBRIC, {"b": ESSAY, "a": ESSAY}, ask, grade="8", clock=lambda: next(ticks))
        self.assertEqual(r, {"essays": 2, "requests": 4, "unusable_replies": 1, "usable_rate": 0.75,
                             "comments": 3, "grounded_comments": 2, "grounded_rate": 0.667,
                             "seconds_per_request": 2.0})
        self.assertIn("Grade level: 8", seen[0][1]["content"])

    def test_empty(self):
        r = fc.evaluate(RUBRIC, {}, lambda m: self.fail("no call expected"))
        self.assertEqual(r["requests"], 0)
        self.assertIsNone(r["usable_rate"])
        self.assertIsNone(r["grounded_rate"])
        self.assertIsNone(r["seconds_per_request"])


class ReviewTests(unittest.TestCase):
    C = {"quote": "it is good", "feed_up": "u", "feed_back": "b", "feed_forward": "Say why."}

    def test_accept(self):
        d = fc.review(self.C, lambda c: ("accept", None))
        self.assertEqual(d, {"action": "accept", "draft": "Say why.", "final": "Say why."})

    def test_edit(self):
        d = fc.review(self.C, lambda c: ("edit", "Restate your claim."))
        self.assertEqual(d["final"], "Restate your claim.")

    def test_reject(self):
        self.assertEqual(fc.review(self.C, lambda c: ("reject", None))["final"], "")

    def test_unknown(self):
        with self.assertRaises(ValueError):
            fc.review(self.C, lambda c: ("skip", None))

    def test_log_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "events.jsonl")
            fc.log_event(p, "review", student="Ana", action="accept")
            fc.log_event(p, "review", student="Ben", action="reject")
            ev = fc.read_events(p)
            self.assertEqual(len(ev), 2)
            self.assertEqual(ev[0]["schema"], fc.SCHEMA)
            self.assertEqual(ev[1]["student"], "Ben")
            self.assertTrue(ev[0]["ts"].endswith("Z"))


class PendingTests(unittest.TestCase):
    def keys(self, items):
        return [(s, c, i) for s, c, i, _ in items]

    def test_all_pending(self):
        self.assertEqual(self.keys(fc.pending(DRAFTS, [])),
                         [("Ana Ruiz", "claim", 0), ("Ana Ruiz", "claim", 1), ("Ben Ode", "evidence", 0)])

    def test_skips_decided_in_same_round(self):
        events = [review_event("Ana Ruiz", "claim", 0, "accept"),
                  {"kind": "review", "student": "Ben Ode", "criterion": "evidence", "action": "accept"}]
        self.assertEqual(self.keys(fc.pending(DRAFTS, events)),
                         [("Ana Ruiz", "claim", 1), ("Ben Ode", "evidence", 0)])
        self.assertEqual(len(fc.pending(DRAFTS, events, draft_number=2)), 3)


class DecideTests(unittest.TestCase):
    def form(self, **kw):
        f = {"token": "t0k", "student": "Ana Ruiz", "criterion": "claim", "item": "0",
             "action": "accept", "text": "Say why."}
        f.update(kw)
        return f

    def test_accept(self):
        d = fc.decide(DRAFTS, self.form(), "t0k")
        self.assertEqual(d, {"student": "Ana Ruiz", "criterion": "claim", "item": 0,
                             "quote": "it is good", "grounded": True,
                             "action": "accept", "draft": "Say why.", "final": "Say why."})

    def test_edit(self):
        d = fc.decide(DRAFTS, self.form(action="edit", text="  Give one reason.  "), "t0k")
        self.assertEqual((d["action"], d["final"]), ("edit", "Give one reason."))

    def test_rejects_bad_input(self):
        for bad in (self.form(token="nope"), self.form(token="ünï"), self.form(item="5"),
                    self.form(item="-1"), self.form(item="x"), self.form(student="Zoe"),
                    self.form(action="edit", text="  "), self.form(action="skip")):
            with self.assertRaises(ValueError):
                fc.decide(DRAFTS, bad, "t0k")


class RenderTests(unittest.TestCase):
    def test_escapes_and_flags(self):
        items = fc.pending(DRAFTS, [review_event("Ana Ruiz", "claim", 0, "accept")])
        page = fc.render_review(items, 3, "t0k")
        self.assertIn("2 of 3 comments left", page)
        self.assertIn("made up &lt;b&gt;", page)
        self.assertNotIn("made up <b>", page)
        self.assertIn("NOT found", page)
        self.assertIn('name="token" value="t0k"', page)
        self.assertIn('name="item" value="1"', page)

    def test_done(self):
        self.assertIn("All 3 comments are reviewed", fc.render_review([], 3, "t0k"))


class UptakeTests(unittest.TestCase):
    EVENTS = [review_event("Ana Ruiz", "claim", 0, "accept"),
              review_event("Ana Ruiz", "claim", 1, "reject"),
              review_event("Ben Ode", "evidence", 0, "edit")]

    def test_sent_comments_only(self):
        revised = {"Ana Ruiz": ESSAY.replace("it is good", "later starts help"), "Ben Ode": ESSAY}
        u = fc.uptake_events(DRAFTS, self.EVENTS, revised)
        self.assertEqual([(x["student"], x["item"], x["uptake"]) for x in u],
                         [("Ana Ruiz", 0, "revised"), ("Ben Ode", 0, "unchanged")])

    def test_missing_revision_skipped(self):
        u = fc.uptake_events(DRAFTS, self.EVENTS, {"Ben Ode": ESSAY})
        self.assertEqual([x["student"] for x in u], ["Ben Ode"])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            drafts = os.path.join(d, "drafts.json")
            with open(drafts, "w", encoding="utf-8") as f:
                json.dump(DRAFTS, f)
            log = os.path.join(d, "events.jsonl")
            with open(log, "w", encoding="utf-8") as f:
                for e in self.EVENTS:
                    f.write(json.dumps(e) + "\n")
            revised = os.path.join(d, "revised")
            os.mkdir(revised)
            with open(os.path.join(revised, "Ana Ruiz.txt"), "w", encoding="utf-8") as f:
                f.write("A new draft entirely.")
            fc.main(["uptake", drafts, revised, "--log", log])
            up = [e for e in fc.read_events(log) if e["kind"] == "uptake"]
            self.assertEqual(len(up), 1)
            self.assertEqual((up[0]["student"], up[0]["uptake"]), ("Ana Ruiz", "revised"))


class SummaryTests(unittest.TestCase):
    EVENTS = UptakeTests.EVENTS + [
        uptake_event("Ana Ruiz", "claim", 0, "revised"),
        uptake_event("Ben Ode", "evidence", 0, "unchanged"),
        review_event("Ana Ruiz", "claim", 1, "accept", draft_number=2),  # another round: ignored
    ]

    def test_counts(self):
        rows = fc.class_summary(DRAFTS, self.EVENTS, RUBRIC["criteria"])
        self.assertEqual([r["name"] for r in rows], ["Clear claim", "Evidence"])
        claim, evidence = rows
        self.assertEqual(claim, {"criterion": "claim", "name": "Clear claim", "drafted": 2,
                                 "ungrounded": 1, "accepted": 1, "edited": 0, "rejected": 1,
                                 "not_reviewed": 0, "revised": 1, "unchanged": 0,
                                 "students_sent": ["Ana Ruiz"], "share_sent": 0.5,
                                 "suggestion": "whole-class mini-lesson"})
        self.assertEqual((evidence["edited"], evidence["unchanged"], evidence["students_sent"]),
                         (1, 1, ["Ben Ode"]))

    def test_small_group_and_unreviewed(self):
        drafts = dict(DRAFTS)
        drafts["Cy Lee"] = {"claim": [], "evidence": []}
        rows = fc.class_summary(drafts, UptakeTests.EVENTS[:1], RUBRIC["criteria"])
        self.assertEqual((rows[0]["share_sent"], rows[0]["suggestion"]), (0.333, "small group"))
        self.assertEqual(rows[0]["not_reviewed"], 1)
        self.assertEqual((rows[1]["not_reviewed"], rows[1]["suggestion"]), (1, "no comments sent"))

    def test_without_rubric(self):
        rows = fc.class_summary(DRAFTS, [])
        self.assertEqual([(r["criterion"], r["name"]) for r in rows],
                         [("claim", "claim"), ("evidence", "evidence")])

    def test_render(self):
        rows = fc.class_summary(DRAFTS, self.EVENTS, [{"id": "claim", "name": "Claim | thesis"}])
        text = fc.render_summary(rows, 2)
        self.assertIn("# Class summary, draft 1", text)
        self.assertIn("| Claim \\| thesis | 1 of 2 | 1 | 1 | 0 | 1 | 1 / 0 | whole-class mini-lesson |", text)
        self.assertIn("Sent a comment: Ana Ruiz", text)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            drafts = os.path.join(d, "drafts.json")
            with open(drafts, "w", encoding="utf-8") as f:
                json.dump(DRAFTS, f)
            rubric = os.path.join(d, "rubric.json")
            with open(rubric, "w", encoding="utf-8") as f:
                json.dump(RUBRIC, f)
            log = os.path.join(d, "events.jsonl")
            with open(log, "w", encoding="utf-8") as f:
                for e in self.EVENTS:
                    f.write(json.dumps(e) + "\n")
            out = os.path.join(d, "summary.md")
            fc.main(["summary", drafts, "--log", log, "--rubric", rubric, "--out", out])
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("| Evidence | 1 of 2 | 1 | 0 | 0 | 0 | 0 / 1 | whole-class mini-lesson |", text)


class ServeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.log = os.path.join(self.dir.name, "events.jsonl")
        self.server = HTTPServer(("127.0.0.1", 0), fc.make_handler(DRAFTS, self.log, token="t0k"))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.dir.cleanup()

    def get(self, path="/", headers=None):
        with OPENER.open(urllib.request.Request(self.url + path, headers=headers or {}), timeout=10) as r:
            return r.read().decode("utf-8")

    def post(self, **form):
        data = urllib.parse.urlencode(form).encode("utf-8")
        with OPENER.open(urllib.request.Request(self.url + "/review", data=data), timeout=10) as r:
            return r.read().decode("utf-8")

    def status(self, fn):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            fn()
        cm.exception.close()
        return cm.exception.code

    def test_review_flow(self):
        self.assertIn("3 of 3 comments left", self.get())
        form = {"token": "t0k", "student": "Ana Ruiz", "criterion": "claim", "item": "0",
                "action": "edit", "text": "Give one reason."}
        self.assertIn("2 of 3 comments left", self.post(**form))
        self.post(**form)  # a double click is logged once
        ev = fc.read_events(self.log)
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["item"], ev[0]["final"], ev[0]["draft_number"]), (0, "Give one reason.", 1))

    def test_refusals(self):
        self.assertEqual(self.status(lambda: self.post(token="bad", student="Ana Ruiz",
                                                       criterion="claim", item="0", action="accept")), 400)
        self.assertEqual(self.status(lambda: self.get(headers={"Host": "evil.example"})), 403)
        self.assertEqual(self.status(lambda: self.get("/other")), 404)
        self.assertFalse(os.path.exists(self.log))


class DeidentifyTests(unittest.TestCase):
    def test_all_kinds(self):
        text = ("Maria Lopez wrote this. Maria's email is maria.l@school.org, "
                "phone 555-123-4567, ID 4839201, date 2026-10-13.")
        out = fc.deidentify(text, ["Maria Lopez"])
        self.assertEqual(out, "[STUDENT] wrote this. [STUDENT]'s email is [EMAIL], "
                              "phone [PHONE], ID [ID], date 2026-10-13.")

    def test_case_insensitive_and_word_bounded(self):
        out = fc.deidentify("ben and BEN wrote; Benjamin did not.", ["Ben Ode"])
        self.assertEqual(out, "[STUDENT] and [STUDENT] wrote; Benjamin did not.")

    def test_no_roster(self):
        self.assertEqual(fc.deidentify("Plain text.", []), "Plain text.")

    def test_pseudonym(self):
        a = fc.pseudonym("Ana", "salt1")
        self.assertEqual(a, fc.pseudonym("Ana", "salt1"))
        self.assertNotEqual(a, fc.pseudonym("Ana", "salt2"))
        self.assertNotEqual(a, fc.pseudonym("Ben", "salt1"))
        self.assertTrue(a.startswith("s-") and len(a) == 12)


class ExportTests(unittest.TestCase):
    EVENTS = [
        {"schema": fc.SCHEMA, "ts": "2026-10-13T00:00:00Z", "kind": "review", "student": "Ana Ruiz",
         "criterion": "claim", "action": "edit", "quote": "Ana thinks school is long",
         "draft": "Ana, add a reason.", "final": "Add one reason.", "grounded": True, "draft_number": 1},
        {"schema": fc.SCHEMA, "ts": "2026-10-13T00:00:01Z", "kind": "review", "student": "Ben Ode",
         "criterion": "claim", "action": "accept", "quote": "x", "draft": "y", "final": "y"},
    ]

    def test_only_consented_and_scrubbed(self):
        recs = fc.export_records(self.EVENTS, ["Ana Ruiz", "Ben Ode"], ["Ana Ruiz"], "s")
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["student"], fc.pseudonym("Ana Ruiz", "s"))
        self.assertEqual(r["quote"], "[STUDENT] thinks school is long")
        self.assertEqual(r["draft"], "[STUDENT], add a reason.")
        self.assertEqual(r["action"], "edit")
        self.assertIs(r["grounded"], True)
        self.assertEqual(r["draft_number"], 1)
        self.assertNotIn("Ana", json.dumps(recs))

    def test_cli_export(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "events.jsonl")
            with open(log, "w", encoding="utf-8") as f:
                for e in self.EVENTS:
                    f.write(json.dumps(e) + "\n")
            roster = os.path.join(d, "roster.txt")
            with open(roster, "w", encoding="utf-8") as f:
                f.write("Ana Ruiz\nBen Ode\n")
            consented = os.path.join(d, "consented.txt")
            with open(consented, "w", encoding="utf-8") as f:
                f.write("Ana Ruiz\nBen Ode\n")
            out = os.path.join(d, "dataset.jsonl")
            fc.main(["export", log, "--roster", roster, "--consented", consented, "--out", out])
            recs = fc.read_events(out)
            self.assertEqual(len(recs), 2)
            self.assertNotIn("Ruiz", json.dumps(recs))
            self.assertNotEqual(recs[0]["student"], recs[1]["student"])


if __name__ == "__main__":
    unittest.main()
