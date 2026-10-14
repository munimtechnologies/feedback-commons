"""Offline tests for the quote-fidelity study. No model or network needed."""

import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quote_fidelity as qf  # noqa: E402

ESSAY = "I beleive that students should have more time to finish there homework at home."
KNOWN = {"i", "believe", "that", "students", "should", "have", "more", "time", "to", "finish",
         "their", "there", "homework", "at", "home", "a", "lot", "dont", "don't"} - {"dont"}


def known(w):
    return w in KNOWN


class ClassifyTests(unittest.TestCase):
    def test_exact_ignores_case_and_spacing(self):
        r = qf.classify_quote("i  beleive that Students", ESSAY)
        self.assertEqual(r["kind"], "exact")

    def test_punctuation_only(self):
        r = qf.classify_quote("people should work hard", "Firstly, people should, work hard.")
        self.assertEqual(r["kind"], "punctuation")

    def test_altered_counts_spelling_fixes(self):
        r = qf.classify_quote("I believe that students should have more time to finish their homework",
                              ESSAY, known)
        self.assertEqual(r["kind"], "altered")
        self.assertEqual(r["changes"], [("beleive", "believe"), ("there", "their")])
        self.assertEqual(r["corrections"], 1)  # there -> their swaps two real words
        self.assertGreaterEqual(r["similarity"], qf.ALTERED_MIN)

    def test_altered_without_spell_checker(self):
        r = qf.classify_quote("I believe that students should have more time", ESSAY)
        self.assertEqual(r["kind"], "altered")
        self.assertIsNone(r["corrections"])

    def test_split_word_is_one_change(self):
        r = qf.classify_quote("they help alot of people every day", "They help a lot of people every day.",
                              known)
        self.assertEqual(r["kind"], "altered")
        self.assertEqual(r["changes"], [("a lot", "alot")])
        self.assertEqual(r["corrections"], 0)

    def test_not_in_text(self):
        r = qf.classify_quote("Technology helps us learn faster than ever before", ESSAY, known)
        self.assertEqual(r["kind"], "not_in_text")
        self.assertLess(r["similarity"], qf.ALTERED_MIN)

    def test_too_short(self):
        self.assertEqual(qf.classify_quote("it", ESSAY)["kind"], "too_short")


def row(i, conventions, words=200):
    return {"text_id_kaggle": "E%03d" % i, "full_text": " ".join(["word"] * words),
            "Conventions": str(conventions), "grade": "9"}


class SelectTests(unittest.TestCase):
    ROWS = ([row(i, 2.0) for i in range(5)] + [row(10 + i, 4.5) for i in range(5)]
            + [row(20, 3.0), row(21, 2.0, words=100), row(22, 4.0, words=600), row(23, "")])

    def test_bands_alternate_and_filters_apply(self):
        got = qf.select_essays(self.ROWS, per_band=2)
        self.assertEqual([e["band"] for e in got], ["low", "high", "low", "high"])
        ids = {e["id"] for e in got}
        self.assertFalse(ids & {"E020", "E021", "E022", "E023"})

    def test_deterministic(self):
        a = [e["id"] for e in qf.select_essays(self.ROWS, 3, seed=1)]
        b = [e["id"] for e in qf.select_essays(list(reversed(self.ROWS)), 3, seed=1)]
        self.assertEqual(a, b)

    def test_short_band(self):
        got = qf.select_essays(self.ROWS, per_band=9)
        self.assertEqual(len(got), 10)


CRITERIA = [{"id": "conventions", "name": "Conventions", "description": "Spelling."}]
ESSAYS = [{"id": "L1", "band": "low", "conventions": 2.0, "grade": "9", "text": ESSAY},
          {"id": "H1", "band": "high", "conventions": 4.5, "grade": "9",
           "text": "I believe that students should have more time to finish their homework at home."}]


def reply(*quotes):
    return json.dumps({"comments": [{"quote": q, "feed_up": "u", "feed_back": "b", "feed_forward": "f"}
                                    for q in quotes]})


class Clock:
    def __init__(self, step):
        self.t, self.step = 0.0, step

    def __call__(self):
        self.t += self.step
        return self.t


class StudyTests(unittest.TestCase):
    def ask(self, messages, model):
        self.calls.append(model)
        return reply("I believe that students should have more time to finish their homework",
                     "a sentence nobody wrote anywhere at all")

    def setUp(self):
        self.calls = []

    def test_records_and_summary(self):
        out = io.StringIO()
        recs = qf.run_study(ESSAYS, CRITERIA, ["m1", "m2"], ["", "Spanish"], self.ask, out, 3600,
                            clock=Clock(1), known=known)
        self.assertEqual(len(recs), 8)
        self.assertEqual(len(out.getvalue().splitlines()), 8)
        self.assertEqual(self.calls, ["m1", "m1", "m2", "m2"] * 2)
        low = [r for r in recs if r["band"] == "low"][0]
        self.assertEqual([c["kind"] for c in low["comments"]], ["altered", "not_in_text"])
        high = [r for r in recs if r["band"] == "high"][0]
        self.assertEqual([c["kind"] for c in high["comments"]], ["exact", "not_in_text"])
        s = qf.summarize(recs)
        self.assertEqual(s["overall"]["comments"], 16)
        self.assertEqual(s["overall"]["exact"], 4)
        self.assertEqual(s["overall"]["altered_with_correction"], 4)
        gap = [g for g in s["gaps"] if g["model"] == "m1" and g["language"] == "English"][0]
        self.assertEqual(gap["exact_rate_gap"]["low_minus_high"], -0.5)
        md = qf.render_markdown(s, {"feedback_commons": "x", "finished": "now", "essays_done": 2,
                                    "low_max": 2.5, "high_min": 4.0})
        self.assertIn("| m1 | Spanish | low | all | 2 | 0% |", md)

    def test_budget_stops_between_essays(self):
        recs = qf.run_study(ESSAYS, CRITERIA, ["m1"], [""], self.ask, None, 1.5, clock=Clock(1))
        self.assertEqual([r["essay"] for r in recs], ["L1"])

    def test_bad_replies_and_errors_are_recorded(self):
        def ask(messages, model):
            if model == "broken":
                raise OSError("connection refused")
            return "not json"
        recs = qf.run_study(ESSAYS[:1], CRITERIA, ["broken", "chatty"], [""], ask, None, 3600)
        self.assertEqual([r["usable"] for r in recs], [False, False])
        self.assertIn("OSError", recs[0]["error"])
        self.assertIn("not JSON", recs[1]["error"])
        self.assertEqual(qf.tally(recs)["unusable"], 2)


class BootstrapTests(unittest.TestCase):
    def test_interval_brackets_the_gap(self):
        low = [(1, 4), (2, 4), (0, 4), (1, 4)]
        high = [(3, 4), (4, 4), (3, 4), (4, 4)]
        g = qf.bootstrap_diff(low, high, n=500)
        self.assertEqual(g["low_minus_high"], -0.625)
        self.assertLessEqual(g["ci95"][0], -0.625)
        self.assertGreaterEqual(g["ci95"][1], -0.625)
        self.assertEqual(g["resamples"], 500)

    def test_no_quotes(self):
        self.assertIsNone(qf.bootstrap_diff([(0, 0)], [(1, 2)]))


if __name__ == "__main__":
    unittest.main()
