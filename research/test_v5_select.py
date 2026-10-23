"""Offline tests for the v5 essay selection. No model or network needed."""

import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quote_fidelity as qf  # noqa: E402
import v3_select as v3s  # noqa: E402
import v4_select as v4s  # noqa: E402
import v5_select as v5  # noqa: E402


def row(i, conventions, words=200):
    return {"text_id_kaggle": "E%03d" % i, "full_text": " ".join(["word%d" % i] * words),
            "Conventions": str(conventions), "grade": "9"}


ROWS = ([row(i, 2.0) for i in range(40)] + [row(100 + i, 4.5) for i in range(30)]
        + [row(200, 3.0), row(201, 2.0, words=100), row(202, 4.0, words=600)])
# Big enough for the real per-band numbers: 200 per band, less v2's 15, v3's 48 and v4's 60, leaves 77.
BIG = [row(i, 2.0) for i in range(200)] + [row(1000 + i, 4.5) for i in range(200)]


def ids(essays):
    return [e["id"] for e in essays]


class SelectTests(unittest.TestCase):
    def test_v2_v3_v4_are_regenerated_and_excluded(self):
        v2, v3, v4, chosen, eligible = v5.select_v5(ROWS, 8, "s5", 8, "s4", 6, 5, 4, 1)
        self.assertEqual(ids(v2), ids(qf.select_essays(ROWS, 4, 1)))
        self.assertEqual(ids(v3), ids(v3s.select_v3(ROWS, 6, 5, 4, 1)[1]))
        self.assertEqual(ids(v4), ids(v4s.select_v4(ROWS, 8, "s4", 6, 5, 4, 1)[2]))
        self.assertFalse(set(ids(v2) + ids(v3) + ids(v4)) & set(ids(chosen)))
        self.assertEqual(eligible, {"before_exclusion": {"low": 40, "high": 30},
                                    "after_exclusion": {"low": 22, "high": 12}})
        self.assertEqual([e["band"] for e in chosen], ["low", "high"] * 8)

    def test_short_band_takes_all(self):
        chosen = v5.select_v5(ROWS, 25, "s5", 8, "s4", 6, 5, 4, 1)[3]
        self.assertEqual(v3s.bands(chosen), {"low": 22, "high": 12})

    def test_reproducible_and_order_free(self):
        a = v5.select_v5(ROWS, 8, "s5", 8, "s4", 6, 5, 4, 1)[3]
        b = v5.select_v5(ROWS, 8, "s5", 8, "s4", 6, 5, 4, 1)[3]
        c = v5.select_v5(list(reversed(ROWS)), 8, "s5", 8, "s4", 6, 5, 4, 1)[3]
        self.assertEqual(ids(a), ids(b))
        self.assertEqual(ids(a), ids(c))

    def test_missing_or_duplicate_ids_fail(self):
        with self.assertRaises(ValueError):
            v5.select_v5(ROWS + [dict(row(300, 2.0), text_id_kaggle="")])
        with self.assertRaises(ValueError):
            v5.select_v5(ROWS + [row(5, 2.0)])


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.csv = os.path.join(self.d, "train.csv")
        with open(self.csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["text_id_kaggle", "full_text", "Conventions", "grade"])
            w.writeheader()
            w.writerows(BIG)
        self.old = v3s.V2_DONE
        v3s.V2_DONE = tuple(ids(qf.select_essays(BIG, v3s.V2_PER_BAND, v3s.V2_SEED)))
        v2, v3, _ = v3s.select_v3(BIG)
        self.v3_committed = {"data_sha256": v3s.sha256(self.csv), "v2_excluded": ids(v2),
                             "essays": [{"id": e["id"], "band": e["band"]} for e in v3]}
        self.v3_path = os.path.join(self.d, "v3-essays.json")
        with open(self.v3_path, "w", encoding="utf-8") as f:
            json.dump(self.v3_committed, f)
        self.v4_path = os.path.join(self.d, "v4", "essays.json")
        v4s.main(["--data-dir", self.d, "--v3-essays", self.v3_path, "--out", self.v4_path])
        with open(self.v4_path, encoding="utf-8") as f:
            self.v4_committed = json.load(f)
        self.out = os.path.join(self.d, "v5", "essays.json")

    def tearDown(self):
        v3s.V2_DONE = self.old
        self.tmp.cleanup()

    def run_main(self, v3_committed, v4_committed):
        vp = os.path.join(self.d, "v3c.json")
        wp = os.path.join(self.d, "v4c.json")
        with open(vp, "w", encoding="utf-8") as f:
            json.dump(v3_committed, f)
        with open(wp, "w", encoding="utf-8") as f:
            json.dump(v4_committed, f)
        v5.main(["--data-dir", self.d, "--v3-essays", vp, "--v4-essays", wp, "--out", self.out])

    def test_writes_ids_and_bands_only(self):
        self.run_main(self.v3_committed, self.v4_committed)
        with open(self.out, encoding="utf-8") as f:
            out = json.load(f)
        self.assertEqual(out["study"], "quote-fidelity-v5")
        self.assertEqual(set(out["essays"][0]), {"id", "band"})
        self.assertEqual(out["selected"], {"low": 60, "high": 60})
        self.assertEqual(out["short_bands"], [])
        self.assertEqual((len(out["v2_excluded"]), len(out["v3_excluded"]), len(out["v4_excluded"])),
                         (30, 96, 120))
        self.assertEqual(out["eligible_before_exclusion"], {"low": 200, "high": 200})
        self.assertEqual(out["eligible_after_exclusion"], {"low": 77, "high": 77})
        self.assertFalse(set(out["v2_excluded"] + out["v3_excluded"] + out["v4_excluded"])
                         & set(ids(out["essays"])))
        self.assertEqual(out["seed"], "v5-select-20261023")
        self.assertNotIn("word0", json.dumps(out))  # no essay text

    def test_v3_mismatch_stops_the_command(self):
        wrong = dict(self.v3_committed, essays=list(reversed(self.v3_committed["essays"])))
        with self.assertRaises(SystemExit):
            self.run_main(wrong, self.v4_committed)
        self.assertFalse(os.path.exists(self.out))

    def test_v4_mismatch_stops_the_command(self):
        wrong = dict(self.v4_committed, essays=list(reversed(self.v4_committed["essays"])))
        with self.assertRaises(SystemExit):
            self.run_main(self.v3_committed, wrong)
        self.assertFalse(os.path.exists(self.out))

    def test_other_data_file_stops_the_command(self):
        with self.assertRaises(SystemExit):
            self.run_main(dict(self.v3_committed, data_sha256="0" * 64), self.v4_committed)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
