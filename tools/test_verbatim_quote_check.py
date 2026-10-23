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
"""Tests for verbatim_quote_check. Standard library only; no network, no data files."""
import contextlib
import io
import os
import sys
import unittest

# Make the module importable no matter the working directory the runner uses.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verbatim_quote_check import (  # noqa: E402
    ALTERED,
    EXACT,
    NOT_FOUND,
    PUNCT_WHITESPACE,
    check,
    clean_quote,
    main,
    words,
)


class HelperTests(unittest.TestCase):
    def test_words_tokenises_and_lowercases(self):
        self.assertEqual(words("Hello, WORLD!"), ["hello", "world"])

    def test_words_keeps_digits_drops_punctuation(self):
        self.assertEqual(words("3 apples, 2 pears."), ["3", "apples", "2", "pears"])

    def test_clean_quote_strips_marks_and_space(self):
        self.assertEqual(clean_quote('  "hello"  '), "hello")
        self.assertEqual(clean_quote("'test'"), "test")
        self.assertEqual(clean_quote("“curly”"), "curly")

    def test_clean_quote_empty(self):
        self.assertEqual(clean_quote('  ""  '), "")


class CheckTests(unittest.TestCase):
    def test_exact_substring(self):
        r = check("The cat sat on the mat.", "cat sat on")
        self.assertEqual(r.category, EXACT)
        self.assertEqual(r.similarity, 1.0)
        self.assertTrue(r.faithful_words)

    def test_exact_with_surrounding_quote_marks(self):
        r = check("She wrote: I am happy today.", '"I am happy"')
        self.assertEqual(r.category, EXACT)

    def test_case_only_difference_is_punctuation_whitespace(self):
        r = check("The cat sat on the mat.", "Cat sat on")
        self.assertEqual(r.category, PUNCT_WHITESPACE)
        self.assertEqual(r.similarity, 1.0)
        self.assertTrue(r.faithful_words)

    def test_punctuation_difference_is_punctuation_whitespace(self):
        r = check("I like apples, oranges and pears.", "apples oranges and pears")
        self.assertEqual(r.category, PUNCT_WHITESPACE)

    def test_altered_word_swapped(self):
        r = check("The quick brown fox jumps", "The quick red fox")
        self.assertEqual(r.category, ALTERED)
        self.assertAlmostEqual(r.similarity, 0.75, places=2)
        self.assertFalse(r.faithful_words)

    def test_altered_word_inserted(self):
        r = check("I really like this essay", "I like this essay")
        self.assertEqual(r.category, ALTERED)
        self.assertGreater(r.similarity, 0.85)

    def test_not_found(self):
        r = check("The quick brown fox", "completely unrelated statement here")
        self.assertEqual(r.category, NOT_FOUND)
        self.assertLess(r.similarity, 0.6)

    def test_empty_quote_is_not_found(self):
        self.assertEqual(check("anything at all", "   ").category, NOT_FOUND)

    def test_quote_marks_only_is_not_found(self):
        self.assertEqual(check("anything at all", '""').category, NOT_FOUND)

    def test_threshold_pushes_altered_to_not_found(self):
        r = check("The quick brown fox", "The quick red fox", altered_threshold=0.9)
        self.assertEqual(r.category, NOT_FOUND)


class CliTests(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_cli_exact_returns_zero(self):
        code, out = self._run(["--source", "The cat sat on", "--quote", "cat sat on"])
        self.assertEqual(code, 0)
        self.assertIn(EXACT, out)

    def test_cli_altered_returns_one(self):
        code, _ = self._run(
            ["--source", "The quick brown fox jumps", "--quote", "The quick red fox"]
        )
        self.assertEqual(code, 1)

    def test_cli_not_found_returns_two(self):
        code, _ = self._run(["--source", "hello world", "--quote", "zzz qqq vvv"])
        self.assertEqual(code, 2)

    def test_cli_json_output(self):
        code, out = self._run(
            ["--source", "The cat sat on", "--quote", "cat sat on", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertIn('"category"', out)
        self.assertIn(EXACT, out)


if __name__ == "__main__":
    unittest.main()
