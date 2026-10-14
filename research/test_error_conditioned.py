"""Offline tests for the exploratory misspelling analysis. No model, network or spell checker needed."""

import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import error_conditioned as ec  # noqa: E402
import quote_fidelity as qf  # noqa: E402

ESSAY = "I beleive that students should have more time to finish there homework at home."
CLEAN = "I believe that students should have more time to finish their homework at home."
KNOWN = {"i", "believe", "that", "students", "should", "have", "more", "time", "to", "finish",
         "their", "there", "homework", "at", "home", "don"}


def known(w):
    return w in KNOWN


class WordTests(unittest.TestCase):
    def test_misspelled(self):
        got = ec.misspelled(["don't", "dont", "1990", "beleive", "home"], known)
        self.assertEqual(got, ["dont", "beleive"])

    def test_place_exact_and_altered(self):
        tw = qf.bare_words(ESSAY)
        self.assertEqual(ec.place_quote("I beleive that students", tw),
                         ["i", "beleive", "that", "students"])
        self.assertEqual(ec.place_quote("I believe that students should have more time", tw),
                         tw[:8])
        self.assertIsNone(ec.place_quote("Technology helps us learn faster than ever before", tw))
        self.assertIsNone(ec.place_quote("...", tw))


def record(essay, band, *comments, model="m", language="English"):
    return {"essay": essay, "band": band, "model": model, "language": language,
            "comments": [{"kind": k, "quote": q} for k, q in comments]}


class RowTests(unittest.TestCase):
    def test_quote_rows(self):
        recs = [record("L1", "low",
                       ("exact", "I beleive that students"),
                       ("altered", "I believe that students should have more time"),
                       ("exact", "finish there homework"),
                       ("not_in_text", "a sentence nobody wrote"))]
        rows = ec.quote_rows(recs, {"L1": ESSAY}, known)
        self.assertEqual([r["placed"] for r in rows], [True, True, True, False])
        self.assertEqual([(r["verbatim"], r["misspelled"], r["kept"]) for r in rows[:3]],
                         [(True, 1, 1), (False, 1, 0), (True, 0, 0)])
        self.assertNotIn("verbatim", rows[3])

    def test_unknown_essay_is_unplaced(self):
        rows = ec.quote_rows([record("X", "low", ("exact", "I beleive that"))], {}, known)
        self.assertFalse(rows[0]["placed"])


def placed(essay, band, verbatim, misspelled, kept):
    return {"essay": essay, "band": band, "model": "m", "language": "English",
            "kind": "exact" if verbatim else "altered", "placed": True, "verbatim": verbatim,
            "misspelled": misspelled, "kept": kept}


ROWS = [placed("L1", "low", False, 1, 0), placed("L1", "low", True, 1, 1),
        placed("L1", "low", True, 0, 0), placed("H1", "high", True, 0, 0),
        placed("H1", "high", False, 1, 0),
        {"essay": "H1", "band": "high", "model": "m", "language": "English",
         "kind": "not_in_text", "placed": False}]


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.s = ec.summarize(ROWS, {"L1": ESSAY, "H1": CLEAN}, known)

    def cell(self, band, passage):
        return [c for c in self.s["cells"] if (c["band"], c["passage"]) == (band, passage)][0]

    def test_cells(self):
        self.assertEqual((self.s["quotes"], self.s["placed"]), (6, 5))
        self.assertEqual(self.cell("all", "misspelled")["verbatim_rate"], 0.333)
        self.assertEqual(self.cell("all", "clean")["verbatim_rate"], 1.0)
        self.assertEqual(self.cell("low", "misspelled")["quotes"], 2)
        self.assertEqual(self.cell("high", "clean")["verbatim"], 1)

    def test_contrast_and_kept(self):
        gap = self.s["contrasts"][0]["verbatim_gap"]
        self.assertEqual(gap["misspelled_minus_clean"], -0.667)
        self.assertLessEqual(gap["ci95"][0], -0.667)
        self.assertGreaterEqual(gap["ci95"][1], -0.667)
        kept = [k for k in self.s["kept"] if k["band"] == "all"][0]
        self.assertEqual((kept["kept"], kept["misspelled_words"], kept["kept_rate"]), (1, 3, 0.333))

    def test_misspelling_rates(self):
        self.assertEqual(self.s["essays"], [
            {"band": "high", "essays": 1, "misspelled_word_rate": 0.0},
            {"band": "low", "essays": 1, "misspelled_word_rate": 0.0714}])

    def test_markdown(self):
        md = ec.render_markdown(self.s)
        self.assertIn("| m | English | all | misspelled | 3 | 33% |", md)
        self.assertIn("- m, English: -0.667 [", md)
        self.assertIn("- low band: 1 essays, 7.1%", md)

    def test_no_misspelled_passages(self):
        self.assertIsNone(ec.bootstrap_contrast([(0, 0, 2, 3), (0, 0, 1, 1)]))


class MainTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_end_to_end(self):
        data = os.path.join(self.dir, "data")
        os.makedirs(data)
        with open(os.path.join(data, "ellipse.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["text_id_kaggle", "full_text", "Conventions", "grade"])
            w.writerow(["L1", " ".join([ESSAY] * 11), "2.0", "9"])
            w.writerow(["H1", " ".join([CLEAN] * 11), "4.5", "9"])
        requests = os.path.join(self.dir, "requests.jsonl")
        with open(requests, "w", encoding="utf-8") as f:
            f.write(json.dumps(record("L1", "low", ("exact", "I beleive that students"))) + "\n")
            f.write(json.dumps(record("H1", "high", ("exact", "I believe that students"))) + "\n")
        out = os.path.join(self.dir, "out")
        ec.main(["--requests", requests, "--data-dir", data, "--out-dir", out, "--per-band", "1"],
                known=known)
        with open(os.path.join(out, "error_conditioned.json"), encoding="utf-8") as f:
            s = json.load(f)
        self.assertEqual((s["quotes"], s["placed"], s["meta"]["requests"]), (2, 2, 2))
        self.assertTrue(os.path.exists(os.path.join(out, "error_conditioned.md")))

    def test_essay_not_in_selection(self):
        data = os.path.join(self.dir, "data")
        os.makedirs(data)
        with open(os.path.join(data, "ellipse.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["text_id_kaggle", "full_text", "Conventions", "grade"])
            w.writerow(["L1", " ".join([ESSAY] * 11), "2.0", "9"])
        requests = os.path.join(self.dir, "requests.jsonl")
        with open(requests, "w", encoding="utf-8") as f:
            f.write(json.dumps(record("Z9", "low", ("exact", "I beleive"))) + "\n")
        with self.assertRaises(SystemExit):
            ec.main(["--requests", requests, "--data-dir", data, "--out-dir", self.dir], known=known)


if __name__ == "__main__":
    unittest.main()
