"""Offline tests for the v3 essay selection. No model or network needed."""

import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quote_fidelity as qf  # noqa: E402
import v3_select as v3  # noqa: E402


def row(i, conventions, words=200):
    return {"text_id_kaggle": "E%03d" % i, "full_text": " ".join(["word%d" % i] * words),
            "Conventions": str(conventions), "grade": "9"}


ROWS = ([row(i, 2.0) for i in range(40)] + [row(100 + i, 4.5) for i in range(30)]
        + [row(200, 3.0), row(201, 2.0, words=100), row(202, 4.0, words=600)])


class SelectTests(unittest.TestCase):
    def test_v2_is_regenerated_and_excluded(self):
        v2, chosen, eligible = v3.select_v3(ROWS, per_band=10, seed=5, v2_per_band=4, v2_seed=1)
        self.assertEqual([e["id"] for e in v2], [e["id"] for e in qf.select_essays(ROWS, 4, 1)])
        self.assertFalse({e["id"] for e in v2} & {e["id"] for e in chosen})
        self.assertEqual(eligible, {"low": 36, "high": 26})
        self.assertEqual([e["band"] for e in chosen], ["low", "high"] * 10)

    def test_short_band_takes_all(self):
        _, chosen, eligible = v3.select_v3(ROWS, per_band=30, seed=5, v2_per_band=4, v2_seed=1)
        self.assertEqual(v3.bands(chosen), {"low": 30, "high": 26})
        self.assertEqual(eligible["high"], 26)

    def test_order_of_rows_does_not_matter(self):
        a = v3.select_v3(ROWS, 10, 5, 4, 1)[1]
        b = v3.select_v3(list(reversed(ROWS)), 10, 5, 4, 1)[1]
        self.assertEqual([e["id"] for e in a], [e["id"] for e in b])

    def test_missing_or_duplicate_ids_fail(self):
        with self.assertRaises(ValueError):
            v3.select_v3(ROWS + [dict(row(300, 2.0), text_id_kaggle="")])
        with self.assertRaises(ValueError):
            v3.select_v3(ROWS + [row(5, 2.0)])


class RebuildTests(unittest.TestCase):
    def test_rebuilds_text_in_selection_order(self):
        chosen = v3.select_v3(ROWS, 6, 5, 4, 1)[1]
        sel = {"essays": [{"id": e["id"], "band": e["band"]} for e in chosen]}
        got = v3.essays_from_selection(list(reversed(ROWS)), sel)
        self.assertEqual(got, chosen)
        self.assertTrue(got[0]["text"].startswith("word"))

    def test_ineligible_or_moved_essay_fails(self):
        with self.assertRaises(ValueError):
            v3.essays_from_selection(ROWS, {"essays": [{"id": "E200", "band": "low"}]})
        with self.assertRaises(ValueError):
            v3.essays_from_selection(ROWS, {"essays": [{"id": "E001", "band": "high"}]})


class CommandTests(unittest.TestCase):
    def test_v2_mismatch_stops_the_command(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "train.csv"), "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["text_id_kaggle", "full_text", "Conventions", "grade"])
                w.writeheader()
                w.writerows(ROWS)
            with self.assertRaises(SystemExit):
                v3.main(["--data-dir", d, "--out", os.path.join(d, "essays.json")])
            self.assertFalse(os.path.exists(os.path.join(d, "essays.json")))

    def test_writes_ids_and_bands_only(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "train.csv"), "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["text_id_kaggle", "full_text", "Conventions", "grade"])
                w.writeheader()
                w.writerows(ROWS)
            old = v3.V2_DONE
            v3.V2_DONE = tuple(e["id"] for e in qf.select_essays(ROWS, v3.V2_PER_BAND, v3.V2_SEED))
            try:
                v3.main(["--data-dir", d, "--out", os.path.join(d, "essays.json")])
            finally:
                v3.V2_DONE = old
            with open(os.path.join(d, "essays.json"), encoding="utf-8") as f:
                out = json.load(f)
            self.assertEqual(set(out["essays"][0]), {"id", "band"})
            self.assertEqual(out["short_bands"], ["high", "low"])
            self.assertEqual(len(out["v2_excluded"]), 30)
            self.assertNotIn("word0", json.dumps(out))  # no essay text


if __name__ == "__main__":
    unittest.main()
