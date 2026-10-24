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
"""quote_batch: check every quote in a JSONL file of AI feedback against the student's text.

Part of Feedback Commons, by MV2 of Munim, Inc. Made with AI agents working in his name.

verbatim_quote_check checks one quote. This runs it over a whole file, so a school or a
developer can audit a feedback tool on many essays at once. Each input line is a JSON object
with the student's text in "source" and the quotes in exactly one of:

    "quote"     -- one quoted span
    "quotes"    -- a list of quoted spans
    "feedback"  -- the whole feedback text; every passage in "double", curly, guillemet or
                   low-high quotation marks is checked (the same marks as quote-check.html;
                   single quotes are skipped because they double as apostrophes)

An optional "id" names the record (default: its line number). It prints a summary and can
write one result row per quote. Quote text is left out of those rows unless --with-text is
given, so results can be shared without the students' writing. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

# Make the sibling module importable no matter the working directory the runner uses.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verbatim_quote_check import (  # noqa: E402
    ALTERED,
    EXACT,
    NOT_FOUND,
    PUNCT_WHITESPACE,
    check,
    clean_quote,
)

CATEGORIES = (EXACT, PUNCT_WHITESPACE, ALTERED, NOT_FOUND)

# Quoted passages in feedback text, as in quote-check.html: "...", “...”, «...», „...“/”.
_QUOTED_RE = re.compile(r'“([^”]*)”|"([^"]*)"|«([^»]*)»|„([^“”]*)[“”]')


class InputError(ValueError):
    """A line of the input file that is not a usable record."""


def extract_quotes(feedback: str) -> list[str]:
    """Passages the feedback puts in double, curly, guillemet or low-high quotation marks."""
    out = []
    for m in _QUOTED_RE.finditer(feedback):
        span = next(g for g in m.groups() if g is not None)
        if clean_quote(span) != "":
            out.append(span)
    return out


def quotes_of(record: dict) -> list[str]:
    """The quotes one record asks to check."""
    given = [k for k in ("quote", "quotes", "feedback") if k in record]
    if len(given) != 1:
        raise InputError('needs exactly one of "quote", "quotes" or "feedback"')
    key, value = given[0], record[given[0]]
    if key == "quotes":
        if not isinstance(value, list) or not all(isinstance(q, str) for q in value):
            raise InputError('"quotes" must be a list of strings')
        return value
    if not isinstance(value, str):
        raise InputError('"%s" must be a string' % key)
    return [value] if key == "quote" else extract_quotes(value)


def check_record(record: dict, threshold: float = 0.6) -> list[dict]:
    """One result row per quote of the record."""
    rows = []
    for i, quote in enumerate(quotes_of(record), 1):
        r = check(record["source"], quote, altered_threshold=threshold)
        rows.append({"id": record.get("id"), "index": i, "category": r.category,
                     "similarity": r.similarity, "quote": quote})
    return rows


def summarize(rows: list[dict], records: int, without_quotes: int) -> dict:
    """Counts over all checked quotes."""
    counts = Counter(r["category"] for r in rows)
    faithful = counts[EXACT] + counts[PUNCT_WHITESPACE]
    summary = {"records": records, "records_without_quotes": without_quotes, "quotes": len(rows)}
    summary.update((c, counts[c]) for c in CATEGORIES)
    summary["faithful"] = faithful
    summary["faithful_rate"] = round(faithful / len(rows), 4) if rows else None
    return summary


def run(lines, threshold: float = 0.6) -> tuple[list[dict], dict]:
    """Check every record in JSONL lines; returns (rows, summary).

    Blank lines are skipped. Raises InputError naming the first line that is not a record.
    """
    rows, records, without_quotes = [], 0, 0
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if not isinstance(record, dict) or not isinstance(record.get("source"), str):
                raise InputError('needs a "source" string')
            found = check_record(dict(record, id=record.get("id", n)), threshold)
        except ValueError as err:  # bad JSON or an InputError
            raise InputError("line %d: %s" % (n, err)) from None
        records += 1
        without_quotes += 0 if found else 1
        rows += found
    return rows, summarize(rows, records, without_quotes)


def format_summary(s: dict) -> str:
    head = "%d records (%d without quotes), %d quotes" % (
        s["records"], s["records_without_quotes"], s["quotes"])
    if not s["quotes"]:
        return head + "."
    return head + ": %d keep the student's words (%.1f%%; %d %s, %d %s), %d %s, %d %s." % (
        s["faithful"], 100 * s["faithful_rate"], s[EXACT], EXACT, s[PUNCT_WHITESPACE],
        PUNCT_WHITESPACE, s[ALTERED], ALTERED, s[NOT_FOUND], NOT_FOUND)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check every quote in a JSONL file against each record's source text.",
    )
    parser.add_argument(
        "input",
        help='JSONL file, one {"source": ..., "quote" | "quotes" | "feedback": ...} per line '
             '("-" reads standard input)',
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="min word similarity for 'altered' rather than 'not_found' (default 0.6)",
    )
    parser.add_argument("--out", help="write one JSON row per quote to this file")
    parser.add_argument(
        "--with-text",
        action="store_true",
        help="keep each quote's text in the --out rows (left out by default)",
    )
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    try:
        if args.input == "-":
            rows, summary = run(sys.stdin, args.threshold)
        else:
            # utf-8-sig: files saved by Windows editors often start with a byte-order mark.
            with open(args.input, "r", encoding="utf-8-sig") as fh:
                rows, summary = run(fh, args.threshold)
    except (InputError, OSError) as err:
        print("quote_batch: %s" % err, file=sys.stderr)
        return 3

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for row in rows:
                if not args.with_text:
                    row = {k: v for k, v in row.items() if k != "quote"}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(summary) if args.json else format_summary(summary))

    # Exit code as in verbatim_quote_check, for the worst quote: 0 all faithful, 1 some altered,
    # 2 some not found, 3 unreadable input -- usable as a CI gate.
    if summary[NOT_FOUND]:
        return 2
    return 1 if summary[ALTERED] else 0


if __name__ == "__main__":
    sys.exit(main())
