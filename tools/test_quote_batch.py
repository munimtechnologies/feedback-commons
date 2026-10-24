# Copyright 2026 Munim, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for quote_batch. Standard library only; no network. All texts are made up."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

# Make the module importable no matter the working directory the runner uses.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quote_batch import InputError, extract_quotes, main, run  # noqa: E402
from verbatim_quote_check import ALTERED, EXACT, NOT_FOUND, PUNCT_WHITESPACE  # noqa: E402

# The same made-up example as the quote-check.html smoke test.
SOURCE = "Last year it was the best day of the hole year! We went home."
FEEDBACK = ('You wrote "it was the best day of the whole year", and "We went home." is fine. '
            '"last year it was" needs a comma. "flying cars" is not in it.')


def jsonl(*records):
    return [json.dumps(r, ensure_ascii=False) + "\n" for r in records]


class ExtractTests(unittest.TestCase):
    def test_double_quotes_in_order(self):
        self.assertEqual(extract_quotes(FEEDBACK), [
            "it was the best day of the whole year", "We went home.", "last year it was", "flying cars"])

    def test_curly_guillemet_and_low_high(self):
        text = "A “curly one”, a «guillemet», „low-high“ and „low-high two”."
        self.assertEqual(extract_quotes(text), ["curly one", "guillemet", "low-high", "low-high two"])

    def test_single_quotes_and_empty_quotes_skipped(self):
        self.assertEqual(extract_quotes("Don't say 'hello'. Also \"\" and “ ”."), [])


class RunTests(unittest.TestCase):
    def test_feedback_record_gets_all_four_verdicts(self):
        rows, summary = run(jsonl({"id": "s1", "source": SOURCE, "feedback": FEEDBACK}))
        self.assertEqual([r["category"] for r in rows], [ALTERED, EXACT, PUNCT_WHITESPACE, NOT_FOUND])
        self.assertEqual([r["index"] for r in rows], [1, 2, 3, 4])
        self.assertTrue(all(r["id"] == "s1" for r in rows))
        self.assertEqual(summary, {
            "records": 1, "records_without_quotes": 0, "quotes": 4, EXACT: 1, PUNCT_WHITESPACE: 1,
            ALTERED: 1, NOT_FOUND: 1, "faithful": 2, "faithful_rate": 0.5})

    def test_quote_and_quotes_records(self):
        rows, summary = run(jsonl(
            {"source": SOURCE, "quote": "We went home."},
            {"source": SOURCE, "quotes": ["the hole year", "the whole year"]}))
        self.assertEqual([r["category"] for r in rows], [EXACT, EXACT, ALTERED])
        self.assertEqual(summary["quotes"], 3)
        self.assertEqual(summary["faithful"], 2)

    def test_id_defaults_to_line_number_and_blank_lines_skipped(self):
        lines = ["\n"] + jsonl({"source": SOURCE, "quote": "We went home."})
        rows, summary = run(lines)
        self.assertEqual(rows[0]["id"], 2)
        self.assertEqual(summary["records"], 1)

    def test_feedback_without_quotes_is_counted(self):
        rows, summary = run(jsonl({"source": SOURCE, "feedback": "Nice work, no quotes here."}))
        self.assertEqual(rows, [])
        self.assertEqual(summary["records_without_quotes"], 1)
        self.assertIsNone(summary["faithful_rate"])

    def test_threshold_is_passed_through(self):
        rows, _ = run(jsonl({"source": SOURCE, "quote": "the whole year"}), threshold=0.99)
        self.assertEqual(rows[0]["category"], NOT_FOUND)

    def test_bad_lines_name_the_line(self):
        good = jsonl({"source": SOURCE, "quote": "x"})[0]
        for bad, why in [("{not json\n", "line 2"),
                         (json.dumps({"quote": "x"}) + "\n", '"source"'),
                         (json.dumps({"source": "s", "quote": "x", "feedback": "y"}) + "\n", "exactly one"),
                         (json.dumps({"source": "s", "quotes": "x"}) + "\n", "list of strings"),
                         (json.dumps(["source", "quote"]) + "\n", '"source"')]:
            with self.assertRaises(InputError) as ctx:
                run([good, bad])
            self.assertIn("line 2", str(ctx.exception))
            self.assertIn(why, str(ctx.exception))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.input = os.path.join(self.dir, "in.jsonl")

    def write(self, *records, encoding="utf-8"):
        with open(self.input, "w", encoding=encoding) as fh:
            fh.writelines(jsonl(*records))

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_summary_line_and_worst_exit_code(self):
        self.write({"source": SOURCE, "feedback": FEEDBACK})
        code, out, _ = self._run([self.input])
        self.assertEqual(code, 2)
        self.assertIn("1 records (0 without quotes), 4 quotes: 2 keep the student's words (50.0%", out)

    def test_exit_codes_altered_and_faithful(self):
        self.write({"source": SOURCE, "quote": "the whole year"})
        self.assertEqual(self._run([self.input])[0], 1)
        self.write({"source": SOURCE, "quotes": ["We went home.", "last year it was"]})
        self.assertEqual(self._run([self.input])[0], 0)

    def test_json_summary(self):
        self.write({"source": SOURCE, "feedback": FEEDBACK})
        _, out, _ = self._run([self.input, "--json"])
        self.assertEqual(json.loads(out)["faithful_rate"], 0.5)

    def test_out_rows_leave_text_out_unless_asked(self):
        self.write({"id": "s1", "source": SOURCE, "feedback": FEEDBACK})
        rows_path = os.path.join(self.dir, "rows.jsonl")
        self._run([self.input, "--out", rows_path])
        with open(rows_path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all("quote" not in r for r in rows))
        self.assertEqual(rows[0]["id"], "s1")
        self._run([self.input, "--out", rows_path, "--with-text"])
        with open(rows_path, encoding="utf-8") as fh:
            self.assertEqual(json.loads(fh.readline())["quote"], "it was the best day of the whole year")

    def test_byte_order_mark_is_accepted(self):
        self.write({"source": SOURCE, "quote": "We went home."}, encoding="utf-8-sig")
        self.assertEqual(self._run([self.input])[0], 0)

    def test_unreadable_input_returns_three(self):
        with open(self.input, "w", encoding="utf-8") as fh:
            fh.write("{not json\n")
        code, _, err = self._run([self.input])
        self.assertEqual(code, 3)
        self.assertIn("line 1", err)
        self.assertEqual(self._run([os.path.join(self.dir, "missing.jsonl")])[0], 3)


if __name__ == "__main__":
    unittest.main()
