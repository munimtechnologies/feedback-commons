"""Offline tests for the edit-type classifier. No model, network or spell checker needed."""

import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit_types as et  # noqa: E402
import quote_fidelity as qf  # noqa: E402

TEXT_L = "Some people say we cant think without imagenation in our lives at school."
TEXT_H = "Yesterday she went to store with her mom and her little brother."
KNOWN = {"some", "people", "say", "we", "cant", "can't", "think", "without", "imagination", "in",
         "our", "lives", "at", "school", "you", "your", "the", "they", "their", "there",
         "homework", "need", "more", "time", "to", "finish", "experience", "experiences"}


def known(w):
    return w in KNOWN


def types(found):
    return [(e["type"], e["edge"]) for e in found]


class PairTests(unittest.TestCase):
    def test_same_stem(self):
        self.assertTrue(et.same_stem("experience", "experiences"))
        self.assertTrue(et.same_stem("you", "your"))
        self.assertTrue(et.same_stem("studied", "studies"))
        self.assertFalse(et.same_stem("the", "then"))
        self.assertFalse(et.same_stem("chilhood", "childhood"))

    def test_pair_type(self):
        self.assertEqual(et.pair_type("dont", "don't"), "apostrophe")
        self.assertEqual(et.pair_type("imagenation", "imagination", known), "spelling")
        self.assertEqual(et.pair_type("you", "your", known), "inflection")
        self.assertEqual(et.pair_type("their", "there", known), "real_word")
        self.assertEqual(et.pair_type("the", "they", known), "real_word")
        self.assertEqual(et.pair_type("teh", "the"), "other")


class EditTests(unittest.TestCase):
    def test_join_at_the_start_is_not_an_inserted_word(self):
        found = et.edits("Without water plants die because water is life.",
                         "so with out water plants die because water is life.", known)
        self.assertEqual(types(found), [("join", True)])
        self.assertEqual((found[0]["student"], found[0]["quote"]), (["with", "out"], ["without"]))

    def test_apostrophe_at_the_start_and_spelling_inside(self):
        found = et.edits("can't think without imagination in our lives", TEXT_L, known)
        self.assertEqual(types(found), [("apostrophe", True), ("spelling", False)])
        self.assertEqual(found[1]["student"], ["imagenation"])

    def test_inserted_and_dropped_words(self):
        found = et.edits("she went to the store with her mom and her brother", TEXT_H, known)
        self.assertEqual(types(found), [("inserted", False), ("dropped", False)])
        self.assertEqual([(e["words"], e["function_words"]) for e in found], [(1, 1), (1, 0)])

    def test_inflections(self):
        found = et.edits("should based on your experiences do you agree",
                         "Do you agree? It should based on you experience do you agree with it.",
                         known)
        self.assertEqual(types(found), [("inflection", False), ("inflection", False)])

    def test_split(self):
        found = et.edits("there are a lot of people who like to read books",
                         "There are alot of people who like to read books at night.")
        self.assertEqual(types(found), [("split", False)])
        self.assertEqual(found[0]["words"], 2)

    def test_end_of_quote(self):
        self.assertEqual(types(et.edits("Plants need water to live well",
                                        "Plants need water to live and grow tall.", known)),
                         [("inserted", True)])
        found = et.edits("need more time to finish our homework",
                         "We all need more time to finish our homwork tonight.", known)
        self.assertEqual(types(found), [("spelling", True)])
        self.assertEqual(found[0]["student"], ["homwork"])

    def test_cannot_place(self):
        self.assertIsNone(et.edits("Technology helps us learn faster than ever before", TEXT_H))
        self.assertIsNone(et.edits("...", TEXT_H))


def record(essay, band, *comments):
    return {"essay": essay, "band": band, "model": "m", "language": "English",
            "comments": [{"kind": k, "quote": q} for k, q in comments]}


RECORDS = [record("L1", "low", ("altered", "can't think without imagination in our lives"),
                  ("exact", "we cant think")),
           record("H1", "high", ("altered", "she went to the store with her mom and her brother"),
                  ("not_in_text", "a sentence nobody wrote"))]


class SummaryTests(unittest.TestCase):
    def setUp(self):
        rows = et.quote_edits(RECORDS, {"L1": TEXT_L, "H1": TEXT_H}, known)
        self.s = et.summarize(rows, RECORDS)

    def kind(self, band, t):
        return [x for x in self.s["types"] if (x["band"], x["type"]) == (band, t)][0]

    def test_counts(self):
        self.assertEqual((self.s["quotes"], self.s["altered"], self.s["placed"]), (4, 2, 2))
        self.assertEqual(self.s["bands"][-1], {"band": "all", "altered": 2, "placed": 2,
                                               "no_edits": 0, "edits": 4})
        self.assertEqual(self.kind("all", "apostrophe")["at_edge"], 1)
        self.assertEqual(self.kind("all", "inserted")["function_words"], 1)
        self.assertEqual(self.kind("low", "inserted")["edits"], 0)
        self.assertEqual(self.kind("high", "dropped")["words"], 1)

    def test_lengths(self):
        self.assertEqual([(x["band"], x["kind"], x["mean_words"]) for x in self.s["lengths"]],
                         [("high", "altered", 11.0), ("high", "not_in_text", 4.0),
                          ("low", "altered", 7.0), ("low", "exact", 3.0)])

    def test_no_student_words_in_output(self):
        text = json.dumps(self.s)
        for w in ("imagenation", "imagination", "little", "cant", "L1"):
            self.assertNotIn(w, text)

    def test_markdown(self):
        md = et.render_markdown(self.s)
        self.assertIn("| all | 2 | 2 | 0 | 4 |", md)
        self.assertIn("| all | apostrophe | 1 | 1 | 1 | 1 | - |", md)
        self.assertIn("| all | inserted | 1 | 1 | 1 | 0 | 1 |", md)
        self.assertIn("- low, altered: 1 quotes, mean 7.0 words", md)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_end_to_end_with_recheck(self):
        data = os.path.join(self.dir, "data")
        os.makedirs(data)
        low, high = " ".join([TEXT_L] * 12), " ".join([TEXT_H] * 13)
        with open(os.path.join(data, "ellipse.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["text_id_kaggle", "full_text", "Conventions", "grade"])
            w.writerow(["L1", low, "2.0", "9"])
            w.writerow(["H1", high, "4.5", "9"])
        q_low = "can't think without imagination in our lives"
        recs = [{"essay": "L1", "band": "low", "model": "m", "language": "English",
                 "comments": [{"kind": "altered", "quote": q_low,
                               "similarity": qf.classify_quote(q_low, low)["similarity"]}]},
                {"essay": "H1", "band": "high", "model": "m", "language": "English",
                 "comments": [{"kind": "altered", "similarity": 0.5,
                               "quote": "she went to the store with her mom and her brother"}]}]
        requests = os.path.join(self.dir, "requests.jsonl")
        with open(requests, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        out = os.path.join(self.dir, "out")
        et.main(["--requests", requests, "--data-dir", data, "--out-dir", out, "--per-band", "1"],
                known=known)
        with open(os.path.join(out, "edit_types.json"), encoding="utf-8") as f:
            s = json.load(f)
        self.assertEqual((s["altered"], s["placed"]), (2, 2))
        self.assertEqual((s["similarity_rechecked"], s["similarity_mismatches"]), (2, 1))
        self.assertTrue(os.path.exists(os.path.join(out, "edit_types.md")))


if __name__ == "__main__":
    unittest.main()
