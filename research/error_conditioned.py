"""Exploratory: are quotes less faithful where there are misspellings to fix?

Declared on 2026-10-14, before any output of the quote-fidelity study had
been seen (README.md, "Exploratory analysis declared before results"). It is
not part of the preregistered analysis and is reported as exploratory.

For every quote the study could place in the essay (exact, punctuation or
altered), this finds the student's own passage behind the quote and checks
whether that passage has a word the spell checker does not know. Then, for
each model and language:

  - the verbatim rate (exact or punctuation-only) of quotes taken from a
    passage with a misspelling, and of quotes from a passage without one,
    with a 95% essay-bootstrap interval for the difference;
  - the same rates within each Conventions band, so a band gap can be read
    as "more misspellings to fix" or as "the same kind of passage treated
    differently";
  - the share of misspelled words that the quote kept as the student wrote them.

Quotes that could not be placed (not_in_text, too_short) are only counted.
It reads the study's requests.jsonl and the same ELLIPSE essays, and writes
aggregate numbers only, never essay text. Needs pyspellchecker.
By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import collections
import datetime
import json
import os
import random
import sys

import quote_fidelity as qf

PLACED = ("exact", "punctuation", "altered")
VERBATIM = ("exact", "punctuation")


def misspelled(words, known):
    """The words known() rejects. Words with digits never count, and don't counts as known if don does."""
    out = []
    for w in words:
        if any(ch.isdigit() for ch in w) or known(w):
            continue
        if "'" in w and known(w.split("'")[0]):
            continue
        out.append(w)
    return out


def place_quote(quote, text_words):
    """The student's own words behind a quote, matched as the study matches it, or None."""
    qw = qf.bare_words(quote)
    if not qw:
        return None
    ratio, i, j = qf.best_window(qw, text_words)
    return text_words[i:j] if ratio >= qf.ALTERED_MIN else None


def quote_rows(records, texts, known):
    """One row per quote: its essay, band, model and language, and for placed quotes
    whether it is verbatim, how many misspelled words its passage has and how many it kept."""
    words = {k: qf.bare_words(v) for k, v in texts.items()}
    rows = []
    for r in records:
        tw = words.get(r["essay"])
        for c in r["comments"]:
            row = {"essay": r["essay"], "band": r["band"], "model": r["model"],
                   "language": r["language"], "kind": c["kind"], "placed": False}
            source = place_quote(c["quote"], tw) if c["kind"] in PLACED and tw else None
            if source:
                wrong = misspelled(source, known)
                left = collections.Counter(qf.bare_words(c["quote"]))
                kept = 0
                for w in wrong:
                    if left[w] > 0:
                        left[w] -= 1
                        kept += 1
                row.update(placed=True, verbatim=c["kind"] in VERBATIM, misspelled=len(wrong),
                           kept=kept)
            rows.append(row)
    return rows


def _rate(rows):
    n, v = len(rows), sum(1 for r in rows if r["verbatim"])
    return {"quotes": n, "verbatim": v, "verbatim_rate": round(v / n, 3) if n else None}


def _contrast(items):
    a, b = sum(x[1] for x in items), sum(x[3] for x in items)
    if not a or not b:
        return None
    return sum(x[0] for x in items) / a - sum(x[2] for x in items) / b


def bootstrap_contrast(per_essay, n=2000, seed=7):
    """Verbatim rate from misspelled passages minus clean passages, pooled, with a 95% interval.

    per_essay is a list of (verbatim misspelled, quotes misspelled, verbatim
    clean, quotes clean) per essay; essays are resampled whole.
    """
    point = _contrast(per_essay)
    if point is None:
        return None
    rng = random.Random(seed)
    diffs = sorted(d for d in (_contrast([rng.choice(per_essay) for _ in per_essay])
                               for _ in range(n)) if d is not None)
    if not diffs:
        return None
    return {"misspelled_minus_clean": round(point, 3),
            "ci95": [round(diffs[int(0.025 * len(diffs))], 3),
                     round(diffs[max(0, int(0.975 * len(diffs)) - 1)], 3)],
            "resamples": len(diffs)}


def misspelling_rates(texts, bands, known):
    """Mean share of each essay's words that the spell checker does not know, per band."""
    by_band = collections.defaultdict(list)
    for essay, band in bands.items():
        words = qf.bare_words(texts.get(essay, ""))
        if words:
            by_band[band].append(len(misspelled(words, known)) / len(words))
    return [{"band": b, "essays": len(v), "misspelled_word_rate": round(sum(v) / len(v), 4)}
            for b, v in sorted(by_band.items())]


def summarize(rows, texts, known):
    out = {"quotes": len(rows), "placed": sum(1 for r in rows if r["placed"]),
           "cells": [], "contrasts": [], "kept": []}
    for model, language in sorted({(r["model"], r["language"]) for r in rows}):
        mine = [r for r in rows if r["placed"] and (r["model"], r["language"]) == (model, language)]
        for band in ("low", "high", "all"):
            sel = [r for r in mine if band == "all" or r["band"] == band]
            for passage in ("misspelled", "clean"):
                part = [r for r in sel if (r["misspelled"] > 0) == (passage == "misspelled")]
                out["cells"].append(dict({"model": model, "language": language, "band": band,
                                          "passage": passage}, **_rate(part)))
            wrong, kept = sum(r["misspelled"] for r in sel), sum(r["kept"] for r in sel)
            out["kept"].append({"model": model, "language": language, "band": band,
                                "misspelled_words": wrong, "kept": kept,
                                "kept_rate": round(kept / wrong, 3) if wrong else None})
        per = {}
        for r in mine:
            v = per.setdefault(r["essay"], [0, 0, 0, 0])
            k = 0 if r["misspelled"] else 2
            v[k] += 1 if r["verbatim"] else 0
            v[k + 1] += 1
        out["contrasts"].append({"model": model, "language": language,
                                 "verbatim_gap": bootstrap_contrast([tuple(v) for v in per.values()])})
    out["essays"] = misspelling_rates(texts, {r["essay"]: r["band"] for r in rows}, known)
    return out


def _pct(x):
    return "-" if x is None else "%.0f%%" % (100 * x)


def render_markdown(summary):
    out = ["# Exploratory: quote fidelity where there are misspellings to fix", "",
           "Declared before results (see README.md). %d quotes, %d of them placed in the essay. "
           "A passage counts as misspelled when pyspellchecker does not know at least one of "
           "its words." % (summary["quotes"], summary["placed"]), "",
           "| Model | Language | Band | Passage | Quotes | Verbatim |", "|---|---|---|---|---|---|"]
    for c in summary["cells"]:
        out.append("| %s | %s | %s | %s | %d | %s |" % (c["model"], c["language"], c["band"],
                                                       c["passage"], c["quotes"],
                                                       _pct(c["verbatim_rate"])))
    out += ["", "## Verbatim rate, misspelled minus clean passages (95% essay bootstrap)", ""]
    for g in summary["contrasts"]:
        gap = g["verbatim_gap"]
        out.append("- %s, %s: %s" % (g["model"], g["language"], "not enough data" if gap is None else
                                     "%+.3f [%+.3f, %+.3f]" % (gap["misspelled_minus_clean"],
                                                               gap["ci95"][0], gap["ci95"][1])))
    out += ["", "## Misspelled words the quote kept as the student wrote them", ""]
    for k in summary["kept"]:
        out.append("- %s, %s, %s band: %d of %d (%s)" % (k["model"], k["language"], k["band"],
                                                        k["kept"], k["misspelled_words"],
                                                        _pct(k["kept_rate"])))
    out += ["", "## Words the spell checker does not know, mean share per essay", ""]
    for b in summary["essays"]:
        out.append("- %s band: %d essays, %.1f%%" % (b["band"], b["essays"],
                                                      100 * b["misspelled_word_rate"]))
    return "\n".join(out) + "\n"


def main(argv=None, known=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--requests", required=True, help="the study's requests.jsonl")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--per-band", type=int, default=15)
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args(argv)

    known = known or qf.spell_checker()
    if known is None:
        sys.exit("pyspellchecker is needed: pip install pyspellchecker")
    with open(args.requests, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    essays = qf.select_essays(qf.load_rows(qf.find_csv(args.data_dir)), args.per_band, args.seed)
    texts = {e["id"]: e["text"] for e in essays}
    missing = sorted({r["essay"] for r in records} - set(texts))
    if missing:
        sys.exit("%d essays in the requests are not in the selection, e.g. %s" % (len(missing),
                                                                                 missing[0]))
    summary = summarize(quote_rows(records, texts, known), texts, known)
    summary["meta"] = {"requests": len(records), "per_band": args.per_band, "seed": args.seed,
                       "data_license": "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus)",
                       "finished": datetime.datetime.now(datetime.timezone.utc).strftime(
                           "%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "error_conditioned.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "error_conditioned.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(summary))
    print(json.dumps({k: summary[k] for k in ("quotes", "placed")}), file=sys.stderr)


if __name__ == "__main__":
    main()
