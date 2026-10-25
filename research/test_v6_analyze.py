"""Tests for v6_analyze.py on made-up essays and replies (no ELLIPSE text, no model). Apache-2.0."""

import json
import unittest

import quote_fidelity as qf
import v6_analyze as v6a

TEXTS = {
    "e1": "I think school should start later becuase students are tired in the morning. "
          "We went home after the game and ate dinner together.",
    "e2": "Reading every day helps students learn new words. My sister reads before bed and she loves mystery books.",
    "e3": "Sports teach teamwork and patience. Our coach always says that practice makes progress.",
}
SELECTION = {"study": "quote-fidelity-v5", "data_sha256": "ab" * 32,
             "essays": [{"id": "e1", "band": "low"}, {"id": "e2", "band": "high"}, {"id": "e3", "band": "low"}]}
EXACT = {"e1": "students are tired in the morning", "e2": "My sister reads before bed",
         "e3": "practice makes progress"}
ALTERED = {"e1": "students are really tired in the morning", "e2": "My sister reads before her bed",
           "e3": "practice always makes progress"}
EXTRA_EXACT = "start later becuase students"   # holds the one misspelled word
NOT_FOUND, TOO_SHORT = "flying cars are great fun", "ok"
CELLS = [("m", "English"), ("m", "Spanish")]
CRITERIA = ["evidence", "conventions"]
known = lambda w: w != "becuase"  # noqa: E731


def rec(essay, model, language, condition, criterion, quotes, usable=True):
    return {"essay": essay, "band": next(e["band"] for e in SELECTION["essays"] if e["id"] == essay),
            "conventions": 3.0, "model": model, "language": language, "criterion": criterion,
            "condition": condition, "usable": usable,
            "comments": [dict(qf.classify_quote(q, TEXTS[essay], known), quote=q) for q in quotes] if usable else []}


def records(q_quotes=EXACT, c_quotes=ALTERED, extras=True):
    out = []
    for e in TEXTS:
        for m, l in CELLS:
            for crit in CRITERIA:
                q = [q_quotes[e]]
                if extras and (e, l, crit) == ("e1", "English", "evidence"):
                    q.append(EXTRA_EXACT)
                if extras and (e, l, crit) == ("e2", "English", "conventions"):
                    q += [NOT_FOUND, TOO_SHORT]
                out.append(rec(e, m, l, "q", crit, q))
                out.append(rec(e, m, l, "c", crit, [c_quotes[e]]))
    return out


def run(recs, **kw):
    return v6a.analyze(recs, SELECTION, TEXTS, known, CRITERIA, n=kw.get("n", 200), seed="test")


class FixtureTest(unittest.TestCase):
    def test_the_made_up_quotes_get_the_labels_the_tests_assume(self):
        for e in TEXTS:
            self.assertEqual(qf.classify_quote(EXACT[e], TEXTS[e], known)["kind"], "exact")
            self.assertEqual(qf.classify_quote(ALTERED[e], TEXTS[e], known)["kind"], "altered")
        self.assertEqual(qf.classify_quote(EXTRA_EXACT, TEXTS["e1"], known)["kind"], "exact")
        self.assertEqual(qf.classify_quote(NOT_FOUND, TEXTS["e2"], known)["kind"], "not_in_text")
        self.assertEqual(qf.classify_quote(TOO_SHORT, TEXTS["e2"], known)["kind"], "too_short")


class AnalyzeTest(unittest.TestCase):
    def test_primary_counts_and_direction(self):
        s = run(records())
        p = s["primary"]
        self.assertEqual(s["analysis_set"]["essays"], 3)
        self.assertEqual((p["q_exact"], p["q_quotes"], p["c_exact"], p["c_quotes"]), (13, 13, 0, 12))
        self.assertEqual(p["gap"]["q_minus_c"], 1.0)
        self.assertEqual(p["gap"]["ci95"], [1.0, 1.0])
        self.assertTrue(p["verdict"].startswith("underpowered"))  # 13 quotes is far below the floor of 300
        self.assertTrue(v6a.verdict(p, floor=1).startswith("H1 supported"))

    def test_hurts_and_no_effect(self):
        hurt = run(records(q_quotes=ALTERED, c_quotes=EXACT, extras=False))["primary"]
        self.assertEqual(hurt["gap"]["q_minus_c"], -1.0)
        self.assertTrue(v6a.verdict(hurt, floor=1).startswith("the instruction hurts"))
        mixed = dict(EXACT, e2=ALTERED["e2"])
        same = run(records(q_quotes=mixed, c_quotes=mixed, extras=False))["primary"]
        self.assertEqual(same["gap"]["q_minus_c"], 0.0)
        self.assertEqual(v6a.verdict(same, floor=1), "no clear effect")

    def test_an_unusable_reply_in_one_run_drops_the_essay_from_both_conditions(self):
        recs = records()
        for r in recs:
            if (r["essay"], r["language"], r["condition"], r["criterion"]) == ("e3", "Spanish", "q", "conventions"):
                r["usable"], r["comments"] = False, []
        s = run(recs)
        self.assertEqual(s["analysis_set"]["essays"], 2)
        self.assertEqual(s["analysis_set"]["dropped"]["low"], {"not_reached": 0, "unusable": 1})
        p = s["primary"]
        self.assertEqual((p["q_quotes"], p["c_quotes"]), (9, 8))  # e3's quotes are gone from c too
        self.assertEqual(len(s["failures"]), 4)
        bad = [f for f in s["failures"] if f["unusable_reply"]]
        self.assertEqual([(f["language"], f["unusable_reply"]) for f in bad], [("Spanish/q", 1)])

    def test_secondaries(self):
        s = run(records())
        bands = {b["band"]: b for b in s["secondary_bands"]}
        self.assertEqual((bands["low"]["essays"], bands["low"]["q_quotes"], bands["low"]["c_quotes"]), (2, 9, 8))
        self.assertEqual((bands["high"]["essays"], bands["high"]["q_quotes"]), (1, 4))
        cells = {c["language"]: c for c in s["secondary_cells"]}
        self.assertEqual((cells["English"]["q_quotes"], cells["Spanish"]["q_quotes"]), (7, 6))
        comp = {k["kind"]: k["quotes"] for k in s["secondary_composition"]["q"]["kinds"]}
        self.assertEqual(comp, {"exact": 13, "punctuation": 0, "altered": 0, "not_in_text": 1, "too_short": 1})
        self.assertEqual(s["secondary_composition"]["c"]["kinds"][2]["quotes"], 12)
        self.assertEqual(s["quotes"]["q"], {"all": 15, "matched": 13,
                                            "excluded": {"not_in_text": 1, "too_short": 1, "unplaced": 0}})
        g = s["secondary_quoting"]["q"]
        self.assertEqual((g["usable_replies"], g["quotes"], g["quotes_per_reply"], g["matched_per_reply"]),
                         (12, 15, 1.25, 1.083))
        mis = {d["band"]: d for d in s["secondary_misspelled"]["q"]}
        self.assertEqual((mis["all"]["misspelled_words"], mis["all"]["kept"]), (1, 1))
        self.assertEqual(s["secondary_misspelled"]["c"][2]["misspelled_words"], 0)

    def test_outputs_hold_no_essay_text_or_quote(self):
        s = run(records())
        out = json.dumps(s, ensure_ascii=False) + v6a.render_analysis(s)
        for text in list(EXACT.values()) + list(ALTERED.values()) + [EXTRA_EXACT, NOT_FOUND]:
            self.assertNotIn(text, out)
        self.assertNotIn("becuase", out)
        self.assertIn("Verdict: underpowered", v6a.render_analysis(s))

    def test_records_must_be_v6s(self):
        recs = records()
        recs[0] = dict(recs[0])
        del recs[0]["condition"]
        with self.assertRaises(ValueError):
            run(recs)
        with self.assertRaises(ValueError):
            run([r for r in records() if not (r["language"] == "Spanish" and r["condition"] == "q")])
        with self.assertRaises(ValueError):
            run(records() + [dict(rec("e1", "m", "English", "q", "evidence", [EXACT["e1"]]), essay="zz")])

    def test_the_bootstrap_is_repeatable(self):
        mixed = dict(EXACT, e2=ALTERED["e2"])
        a = run(records(q_quotes=mixed))["primary"]["gap"]
        b = run(records(q_quotes=mixed))["primary"]["gap"]
        self.assertEqual(a, b)
        self.assertEqual(a["resamples"], 200)


if __name__ == "__main__":
    unittest.main()
