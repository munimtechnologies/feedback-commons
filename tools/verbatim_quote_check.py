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
"""verbatim_quote_check: does an AI feedback quote reproduce the student's words?

Part of Feedback Commons, by MV2 of Munim, Inc. Made with AI agents working in his name.

When a writing-feedback tool quotes a student's own sentence back to them, it should
copy it faithfully -- otherwise the student cannot see and fix what they actually wrote.
This is a tiny, dependency-free checker. Given the student's source text and a quote a
tool claims to take from it, it reports how faithfully the quote reproduces the source:

    exact                    -- the quote is a verbatim substring of the source
    punctuation_or_whitespace-- the words match in order; only punctuation, spacing or
                                case differ (so the tool quietly tidied punctuation/case)
    altered                  -- the quote's words best-match a span of the source but
                                with word-level changes (a word added, dropped or swapped)
    not_found                -- the quote cannot be located in the source

It is deliberately small and uses only the Python standard library so it runs anywhere
and is easy to read, teach and audit. See TUTORIAL.md for the ideas behind each choice.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass

EXACT = "exact"
PUNCT_WHITESPACE = "punctuation_or_whitespace"
ALTERED = "altered"
NOT_FOUND = "not_found"

# Quotation marks a tool may wrap around the quoted span; stripped before matching.
_QUOTE_CHARS = "\"'“”‘’«»`"

# A "word" is a run of letters or digits (no underscore). Case is folded on comparison.
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class Result:
    """The outcome of one check."""

    category: str  # one of EXACT, PUNCT_WHITESPACE, ALTERED, NOT_FOUND
    similarity: float  # word-level similarity of the best-matching span, 0.0..1.0

    @property
    def faithful_words(self) -> bool:
        """True when the words match exactly, in order (EXACT or PUNCT_WHITESPACE)."""
        return self.category in (EXACT, PUNCT_WHITESPACE)


def clean_quote(quote: str) -> str:
    """Strip surrounding whitespace and quotation marks from a quoted span."""
    return quote.strip().strip(_QUOTE_CHARS).strip()


def words(text: str) -> list[str]:
    """Lowercased word tokens (letters/digits only). Unicode is normalised to NFC."""
    text = unicodedata.normalize("NFC", text)
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def _contiguous_word_match(src_words: list[str], q_words: list[str]) -> bool:
    """True if q_words appears as a contiguous run inside src_words."""
    n, m = len(src_words), len(q_words)
    if m == 0 or m > n:
        return False
    first = q_words[0]
    for i in range(n - m + 1):
        if src_words[i] == first and src_words[i : i + m] == q_words:
            return True
    return False


def _best_ratio(src_words: list[str], q_words: list[str], slack: int = 2) -> float:
    """Highest difflib word-ratio between q_words and any window of src_words.

    Windows a little shorter and longer than the quote are tried too, so a single
    inserted or dropped word is still recognised as a near match rather than a miss.
    """
    m = len(q_words)
    n = len(src_words)
    if m == 0 or n == 0:
        return 0.0
    sizes = {w for w in range(max(1, m - slack), m + slack + 1)}
    matcher = difflib.SequenceMatcher(autojunk=False)
    matcher.set_seq2(q_words)
    best = 0.0
    for w in sorted(sizes):
        last_start = max(0, n - w)
        for i in range(0, last_start + 1):
            window = src_words[i : i + w]
            if not window:
                continue
            matcher.set_seq1(window)
            r = matcher.ratio()
            if r > best:
                best = r
                if best >= 1.0:
                    return 1.0
    return best


def check(source: str, quote: str, altered_threshold: float = 0.6) -> Result:
    """Classify how faithfully `quote` reproduces a span of `source`.

    altered_threshold: minimum word-level similarity for ALTERED rather than NOT_FOUND.
    """
    cleaned = clean_quote(quote)
    if cleaned == "":
        return Result(NOT_FOUND, 0.0)
    if cleaned in source:
        return Result(EXACT, 1.0)
    src_words = words(source)
    q_words = words(cleaned)
    if not q_words:
        return Result(NOT_FOUND, 0.0)
    if _contiguous_word_match(src_words, q_words):
        return Result(PUNCT_WHITESPACE, 1.0)
    ratio = _best_ratio(src_words, q_words)
    if ratio >= altered_threshold:
        return Result(ALTERED, ratio)
    return Result(NOT_FOUND, ratio)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether a quote reproduces a span of the source text.",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--source", help="the source text (e.g. the student's essay)")
    src.add_argument("--source-file", help="path to a file holding the source text")
    qt = parser.add_mutually_exclusive_group(required=True)
    qt.add_argument("--quote", help="the quoted span to check")
    qt.add_argument("--quote-file", help="path to a file holding the quote")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="min word similarity for 'altered' rather than 'not_found' (default 0.6)",
    )
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)

    source = args.source if args.source is not None else _read(args.source_file)
    quote = args.quote if args.quote is not None else _read(args.quote_file)

    result = check(source, quote, altered_threshold=args.threshold)

    if args.json:
        import json

        print(json.dumps(asdict(result)))
    else:
        print(f"{result.category}\t{result.similarity:.3f}")

    # Exit code: 0 words faithful, 1 altered, 2 not found -- usable as a CI gate.
    return {EXACT: 0, PUNCT_WHITESPACE: 0, ALTERED: 1, NOT_FOUND: 2}[result.category]


if __name__ == "__main__":
    sys.exit(main())
