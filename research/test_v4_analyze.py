"""Offline tests for the v4 passage-level analysis. Synthetic essays and replies only; no model or network."""

import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3_select as v3s  # noqa: E402
import v4_analyze as v4a  # noqa: E402

CELLS = [("m:1", "English"), ("m:1", "Spanish"), ("m:2", "English"), ("m:2", "Spanish")]
# "bezzt" is the one word the stub spell checker does not know.
TEXT = "gamma delta bezzt epsilon zeta eta theta iota kappa lambda"
MIS_EXACT = {"kind": "exact", "quote": "delta bezzt epsilon"}
MIS_ALTERED = {"kind": "altered", "quote": "gamma delta best epsilon zeta"}  # aligned to words 0-4
CLEAN_EXACT = {"kind": "exact", "quote": "eta theta iota"}
CLEAN_ALTERED = {"kind": "altered", "quote": "eta theta iota kappa lamda"}  # aligned to words 5-8
NOT_IN_TEXT = {"kind": "not_in_text", "quote": "nothing like it at all"}
TOO_SHORT = {"kind": "too_short", "quote": "ok"}


def known(word):
    return "zz" not in word


def rec(essay, band, cell, comments, criterion="x", usable=True):
    return {"essay": essay, "band": band, "model": cell[0], "language": cell[1], "criterion": criterion,
            "usable": usable, "comments": comments if usable else []}


SELECTION = {"study": "quote-fidelity-v4", "essays": [{"id": "A", "band": "low"}, {"id": "B", "band": "high"}]}
TEXTS = {"A": TEXT, "B": TEXT}
RECORDS = ([rec("A", "low", c, [MIS_EXACT, MIS_ALTERED, CLEAN_EXACT, NOT_IN_TEXT]) for c in CELLS]
           + [rec("B", "high", c, [CLEAN_EXACT, CLEAN_ALTERED, TOO_SHORT]) for c in CELLS])


def q(essay, misspelled, exact, band="low"):
    return {"essay": essay, "band": band, "misspelled": misspelled, "exact": exact, "kept": 0}


def fake(mis, clean, ci):
    return {"misspelled_quotes": mis, "clean_quotes": clean,
            "gap": {"misspelled_minus_clean": 0.0, "ci95": ci, "resamples": 10}}


class DecisionTests(unittest.TestCase):
    def test_three_branches(self):
        self.assertTrue(v4a.verdict(fake(150, 150, [-0.2, -0.01])).startswith("H1 supported"))
        self.assertEqual(v4a.verdict(fake(150, 150, [-0.1, 0.1])), "no clear difference")
        self.assertTrue(v4a.verdict(fake(150, 150, [0.01, 0.2])).startswith("opposite of H1"))

    def test_floor_comes_first(self):
        self.assertTrue(v4a.verdict(fake(149, 500, [-0.2, -0.1])).startswith("underpowered"))
        self.assertTrue(v4a.verdict(fake(500, 149, [-0.2, -0.1])).startswith("underpowered"))
        self.assertTrue(v4a.verdict(fake(5, 5, [-0.2, -0.1]), floor=5).startswith("H1 supported"))


class EstimandTests(unittest.TestCase):
    ROWS = [q("A", 1, True), q("A", 2, False), q("A", 0, True), q("B", 0, False), q("B", 0, True)]

    def test_per_essay_counts_and_empty_essays(self):
        self.assertEqual(v4a.per_essay(self.ROWS, ["A", "B", "C"]),
                         [(1, 2, 1, 1), (0, 0, 1, 2), (0, 0, 0, 0)])

    def test_pooled_point_estimate(self):
        c = v4a.contrast(self.ROWS, ["A", "B", "C"], n=200)
        self.assertEqual((c["misspelled_quotes"], c["misspelled_exact"]), (2, 1))
        self.assertEqual((c["clean_quotes"], c["clean_exact"]), (3, 2))
        self.assertEqual((c["misspelled_exact_rate"], c["clean_exact_rate"]), (0.5, 0.667))
        self.assertEqual(c["gap"]["misspelled_minus_clean"], -0.167)
        self.assertTrue(0 < c["gap"]["resamples"] <= 200)

    def test_bootstrap_is_deterministic(self):
        a = v4a.contrast(self.ROWS, ["A", "B", "C"], n=300)["gap"]
        b = v4a.contrast(self.ROWS, ["A", "B", "C"], n=300)["gap"]
        self.assertEqual(a, b)

    def test_no_misspelled_quotes_gives_no_gap(self):
        c = v4a.contrast([q("B", 0, True)], ["B"], n=50)
        self.assertIsNone(c["gap"])
        self.assertIsNone(c["misspelled_exact_rate"])


class AnalysisTests(unittest.TestCase):
    def test_flags_passages_and_pools_cells(self):
        s = v4a.analyze(RECORDS, SELECTION, TEXTS, known, ["x"], n=500)
        self.assertEqual(s["analysis_set"]["essays"], 2)
        self.assertEqual(s["quotes"], {"all": 28, "matched": 20,
                                       "excluded": {"not_in_text": 4, "too_short": 4, "unplaced": 0}})
        p = s["primary"]
        self.assertEqual((p["misspelled_quotes"], p["misspelled_exact"]), (8, 4))
        self.assertEqual((p["clean_quotes"], p["clean_exact"]), (12, 8))
        self.assertEqual(p["gap"]["misspelled_minus_clean"], -0.167)
        self.assertTrue(p["verdict"].startswith("underpowered"))
        self.assertTrue(p["gap"]["ci95"][1] < 0)
        self.assertTrue(v4a.verdict(p, floor=5).startswith("H1 supported"))
        low, high = s["secondary_bands"]
        self.assertEqual((low["band"], low["gap"]["misspelled_minus_clean"]), ("low", -0.5))
        self.assertEqual((high["misspelled_quotes"], high["gap"]), (0, None))
        self.assertEqual([c["gap"]["misspelled_minus_clean"] for c in s["secondary_cells"]], [-0.167] * 4)
        d = {x["band"]: x for x in s["secondary_descriptive"]}
        self.assertEqual((d["all"]["matched_quotes"], d["all"]["misspelled_passages"]), (20, 8))
        self.assertEqual((d["all"]["misspelled_words"], d["all"]["kept"], d["all"]["not_kept"]), (8, 4, 4))
        self.assertEqual(d["high"]["misspelled_passages"], 0)
        raw = json.dumps(s)
        self.assertNotIn("bezzt", raw)  # no essay text or quotes
        self.assertNotIn("gamma", raw)

    def test_unknown_essay_fails(self):
        with self.assertRaises(ValueError):
            v4a.analyze(RECORDS + [rec("Z", "low", CELLS[0], [])], SELECTION, TEXTS, known, ["x"], n=10)


def row(i, conventions, words=200):
    # "zzeta" has no digits: error_conditioned.misspelled never counts a word with digits.
    text = " ".join("zzeta beta gamma delta epsilon".split() * (words // 5))
    return {"text_id_kaggle": "E%03d" % i, "full_text": text, "Conventions": str(conventions), "grade": "9"}


ROWS = [row(i, 2.0) for i in range(40)] + [row(100 + i, 4.5) for i in range(30)] + [row(200, 3.0)]


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = self.tmp.name
        path = os.path.join(d, "train.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["text_id_kaggle", "full_text", "Conventions", "grade"])
            w.writeheader()
            w.writerows(ROWS)
        chosen = v3s.select_v3(ROWS, 4, 5, 4, 1)[1]
        self.selection = {"study": "quote-fidelity-v4", "data_sha256": v3s.sha256(path),
                          "essays": [{"id": e["id"], "band": e["band"]} for e in chosen]}
        self.paths = []
        for i, cell in enumerate(CELLS):
            p = os.path.join(d, "cell%d.jsonl" % i)
            with open(p, "w", encoding="utf-8") as f:
                for e in chosen:
                    comments = [{"kind": "exact", "quote": "zzeta beta gamma"},
                                {"kind": "exact", "quote": "beta gamma delta"}]
                    f.write(json.dumps(rec(e["id"], e["band"], cell, comments)) + "\n")
            self.paths.append(p)

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, selection):
        essays = os.path.join(self.d, "essays.json")
        with open(essays, "w", encoding="utf-8") as f:
            json.dump(selection, f)
        v4a.main(["--essays", essays, "--data-dir", self.d, "--out-dir", os.path.join(self.d, "out"),
                  "--criteria", "x"] + self.paths, known=known)

    def test_four_cells_end_to_end(self):
        self.run_main(self.selection)
        with open(os.path.join(self.d, "out", "analysis.json"), encoding="utf-8") as f:
            raw = f.read()
        s = json.loads(raw)
        self.assertEqual(s["analysis_set"]["essays"], 8)
        p = s["primary"]
        self.assertEqual((p["misspelled_quotes"], p["clean_quotes"]), (32, 32))
        self.assertEqual(p["gap"]["misspelled_minus_clean"], 0.0)
        self.assertTrue(p["verdict"].startswith("underpowered"))
        self.assertEqual(s["meta"]["bootstrap_seed"], "v4-boot-20261022")
        self.assertNotIn("zzeta", raw)  # no essay text or quotes
        self.assertNotIn("beta gamma", raw)
        self.assertTrue(os.path.exists(os.path.join(self.d, "out", "analysis.md")))

    def test_other_study_or_data_stops(self):
        with self.assertRaises(SystemExit):
            self.run_main(dict(self.selection, study="quote-fidelity-v3"))
        with self.assertRaises(SystemExit):
            self.run_main(dict(self.selection, data_sha256="0" * 64))


if __name__ == "__main__":
    unittest.main()
