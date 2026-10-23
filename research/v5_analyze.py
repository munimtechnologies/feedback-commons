"""quote-fidelity-v5: the preregistered passage-level analysis (research/PREREG-v5.md).

v5 repeats v4's confirmatory test on a fresh, non-overlapping sample with a
larger compute budget; the analysis is byte-for-byte v4's logic, only the
study name and bootstrap seed differ. The four cells are generated exactly as
v3's and v4's, by v3_run.py run with --essays v5/essays.json. This reads their
requests.jsonl files and writes the one primary test and the declared
secondary analyses:

  analysis set   essays with a usable reply for every criterion in all four
                 cells (v3_run.analysis_set); dropped essays are counted per
                 band and reason
  matched quote  a quote the tool labels exact, punctuation or altered whose
                 student passage error_conditioned.place_quote finds, with the
                 best_window alignment quote_fidelity uses to label altered
                 quotes; not_in_text, too_short and unplaceable quotes are
                 excluded and counted
  misspelled     the matched passage has at least one word pyspellchecker's
                 English dictionary does not know, counted with
                 error_conditioned.misspelled as v3's exploratory analysis
                 counted it (words with digits never count; "don't" is known
                 when "don" is)
  primary        exact-quote rate (the exact label only) of misspelled-passage
                 quotes minus clean-passage quotes, pooled over the four cells,
                 with a 95% percentile interval from 10,000 resamples of whole
                 essays (seed "v5-boot-20261023"); read only with at least 150
                 quotes of each kind

How the preregistration is read, fixed here before any v5 data exists:
  - "Tokens are the checker's own word tokens": the words checked are the
    tool's word tokens (quote_fidelity.bare_words), the units best_window
    aligns, each looked up with pyspellchecker's known(). pyspellchecker
    splits text into runs of word characters with inner apostrophes too.
  - The bootstrap resamples every essay in the analysis set, including any
    with no matched quote.
  - Known limit: best_window can leave a corrected word out of the passage
    when it sits at the quote's edge, so some altered quotes over a
    misspelling count as clean. That works against H1, not for it.

Aggregate numbers only, never essay text or quotes. Needs pyspellchecker
(SPELLCHECKER_VERSION). By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import collections
import datetime
import json
import os
import sys

import error_conditioned as ec
import quote_fidelity as qf
import v3_run as v3r

STUDY = "quote-fidelity-v5"
FLOOR = 150  # quotes of each passage kind needed before the primary test is read
RESAMPLES, BOOT_SEED = 10000, "v5-boot-20261023"
SPELLCHECKER_VERSION = "0.9.1"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def checker_version():
    try:
        from importlib import metadata
        return metadata.version("pyspellchecker")
    except Exception:
        return None


def matched_rows(records, texts, known):
    """(error_conditioned.quote_rows' rows for the matched quotes, each with exact; excluded quotes per reason)."""
    rows, excluded = [], collections.Counter()
    for r in ec.quote_rows(records, texts, known):
        if r["placed"]:
            rows.append(dict(r, exact=r["kind"] == "exact"))
        else:
            excluded["unplaced" if r["kind"] in ec.PLACED else r["kind"]] += 1
    return rows, {k: excluded[k] for k in ("not_in_text", "too_short", "unplaced")}


def per_essay(rows, essays):
    """(exact misspelled, misspelled, exact clean, clean) for each essay, in order; zeros if it has no matched quote."""
    per = {e: [0, 0, 0, 0] for e in essays}
    for r in rows:
        v = per[r["essay"]]
        k = 0 if r["misspelled"] else 2
        v[k] += 1 if r["exact"] else 0
        v[k + 1] += 1
    return [tuple(per[e]) for e in essays]


def contrast(rows, essays, n=RESAMPLES, seed=BOOT_SEED):
    """Exact-quote rates of misspelled- and clean-passage quotes, and their difference with an essay-bootstrap interval."""
    items = per_essay(rows, essays)
    ex_m, mis, ex_c, clean = (sum(x[k] for x in items) for k in range(4))
    return {"essays": len(items),
            "misspelled_quotes": mis, "misspelled_exact": ex_m,
            "misspelled_exact_rate": round(ex_m / mis, 3) if mis else None,
            "clean_quotes": clean, "clean_exact": ex_c,
            "clean_exact_rate": round(ex_c / clean, 3) if clean else None,
            "gap": ec.bootstrap_contrast(items, n, seed)}


def verdict(c, floor=FLOOR):
    """The preregistered decision rule, after the analysis floor."""
    if c["misspelled_quotes"] < floor or c["clean_quotes"] < floor:
        return "underpowered (fewer than %d quotes of a passage kind): the sign is not interpreted" % floor
    if c["gap"] is None:
        return "no interval (a passage kind is missing from the resamples)"
    lo, hi = c["gap"]["ci95"]
    if hi < 0:
        return "H1 supported: misspelled-passage quotes are reproduced exactly less often"
    if lo > 0:
        return "opposite of H1: misspelled-passage quotes are reproduced exactly more often"
    return "no clear difference"


def descriptive(rows):
    """Share of matched passages flagged misspelled, and misspelled words kept as written or not, by band."""
    out = []
    for band in ("low", "high", "all"):
        sel = [r for r in rows if band in ("all", r["band"])]
        flagged = sum(1 for r in sel if r["misspelled"])
        wrong, kept = sum(r["misspelled"] for r in sel), sum(r["kept"] for r in sel)
        out.append({"band": band, "matched_quotes": len(sel), "misspelled_passages": flagged,
                    "misspelled_share": round(flagged / len(sel), 3) if sel else None,
                    "misspelled_words": wrong, "kept": kept, "not_kept": wrong - kept,
                    "kept_rate": round(kept / wrong, 3) if wrong else None})
    return out


def analyze(records, selection, texts, known, criteria, n=RESAMPLES, seed=BOOT_SEED):
    unknown = sorted({r["essay"] for r in records} - {e["id"] for e in selection["essays"]})
    if unknown:
        raise ValueError("%d essays in the requests are not in essays.json, e.g. %s" % (len(unknown),
                                                                                       unknown[0]))
    keep, dropped = v3r.analysis_set(records, selection, criteria)
    ids = set(keep)
    band = {e["id"]: e["band"] for e in selection["essays"]}
    rows, excluded = matched_rows([r for r in records if r["essay"] in ids], texts, known)
    cells = sorted({(r["model"], r["language"]) for r in records})
    primary = contrast(rows, keep, n, seed)
    primary["verdict"] = verdict(primary)
    return {"cells": [{"model": m, "language": l} for m, l in cells],
            "analysis_set": {"essays": len(keep), "low": sum(1 for i in keep if band[i] == "low"),
                             "high": sum(1 for i in keep if band[i] == "high"), "dropped": dropped},
            "failures": v3r.failures(records),
            "quotes": {"all": len(rows) + sum(excluded.values()), "matched": len(rows),
                       "excluded": excluded},
            "primary": primary,
            "secondary_bands": [dict({"band": b}, **contrast([r for r in rows if r["band"] == b],
                                                             [i for i in keep if band[i] == b], n, seed))
                                for b in ("low", "high")],
            "secondary_cells": [dict({"model": m, "language": l},
                                     **contrast([r for r in rows if (r["model"], r["language"]) == (m, l)],
                                                keep, n, seed))
                                for m, l in cells],
            "secondary_descriptive": descriptive(rows)}


def _gap(gap):
    return "not enough data" if gap is None else "%+.3f [%+.3f, %+.3f]" % (
        gap["misspelled_minus_clean"], gap["ci95"][0], gap["ci95"][1])


def _line(label, c):
    return "- %s: misspelled %d of %d exact (%s), clean %d of %d (%s); gap %s" % (
        label, c["misspelled_exact"], c["misspelled_quotes"], qf._pct(c["misspelled_exact_rate"]),
        c["clean_exact"], c["clean_quotes"], qf._pct(c["clean_exact_rate"]), _gap(c["gap"]))


def render_analysis(s):
    p, a, q = s["primary"], s["analysis_set"], s["quotes"]
    out = ["# quote-fidelity-v5: preregistered analysis", "",
           "%d cells. Analysis set: %d essays (%d low, %d high) completed in every cell. Dropped: "
           "low %d not reached, %d with an unusable reply; high %d not reached, %d with an unusable "
           "reply." % (len(s["cells"]), a["essays"], a["low"], a["high"],
                       a["dropped"]["low"]["not_reached"], a["dropped"]["low"]["unusable"],
                       a["dropped"]["high"]["not_reached"], a["dropped"]["high"]["unusable"]), "",
           "%d quotes, %d with a matched passage. Excluded: %d not in text, %d too short, %d labelled "
           "in the text but not placeable." % (q["all"], q["matched"], q["excluded"]["not_in_text"],
                                               q["excluded"]["too_short"], q["excluded"]["unplaced"]), "",
           "## Primary: exact-quote rate, misspelled minus clean passages, all cells pooled", "",
           _line("All cells", p),
           "- Floor: at least %d quotes of each kind." % FLOOR,
           "- Verdict: %s" % p["verdict"], "",
           "## Secondary 1: within each Conventions band", ""]
    out += [_line("%s band" % c["band"], c) for c in s["secondary_bands"]]
    out += ["", "## Secondary 2: each cell", ""]
    out += [_line("%s, %s" % (c["model"], c["language"]), c) for c in s["secondary_cells"]]
    out += ["", "## Secondary 3: misspelled passages and misspelled words kept", "",
            "| Band | Matched quotes | Misspelled passages | Share | Misspelled words | Kept as written | Not kept |",
            "|---|---|---|---|---|---|---|"]
    out += ["| %s | %d | %d | %s | %d | %d | %d |" % (d["band"], d["matched_quotes"], d["misspelled_passages"],
                                                     qf._pct(d["misspelled_share"]), d["misspelled_words"],
                                                     d["kept"], d["not_kept"])
            for d in s["secondary_descriptive"]]
    out += ["", "## Failures per cell", ""]
    out += ["- %s, %s: %d requests, %d failed, %d unusable replies, %d with no quote" % (
        f["model"], f["language"], f["requests"], f["request_failed"], f["unusable_reply"], f["no_quote"])
        for f in s["failures"]]
    return "\n".join(out) + "\n"


def cmd_analyze(args, known=None):
    version = checker_version()
    if known is None:
        known = qf.spell_checker()
        if known is None:
            sys.exit("pyspellchecker is needed: pip install pyspellchecker==%s" % SPELLCHECKER_VERSION)
        if version != SPELLCHECKER_VERSION:
            sys.exit("pyspellchecker %s is installed; the analysis is pinned to %s"
                     % (version, SPELLCHECKER_VERSION))
    selection = v3r.read_selection(args.essays)
    if selection.get("study") != STUDY:
        sys.exit("%s is not the %s selection" % (args.essays, STUDY))
    try:
        texts = {e["id"]: e["text"] for e in v3r.load_essays(args.data_dir, selection)}
    except ValueError as err:
        sys.exit(str(err))
    records = []
    for path in args.requests:
        with open(path, encoding="utf-8") as f:
            records += [json.loads(line) for line in f if line.strip()]
    try:
        summary = analyze(records, selection, texts, known, v3r._split(args.criteria))
    except ValueError as err:
        sys.exit(str(err))
    summary["meta"] = {"study": STUDY, "requests": len(records), "files": len(args.requests),
                       "floor": FLOOR, "resamples": RESAMPLES, "bootstrap_seed": BOOT_SEED,
                       "spellchecker": version, "spellchecker_pinned": SPELLCHECKER_VERSION,
                       "data_sha256": selection["data_sha256"], "data_license": v3r.LICENSE,
                       "finished": _now()}
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "analysis.md"), "w", encoding="utf-8") as f:
        f.write(render_analysis(summary))
    print(json.dumps({"analysis_set": summary["analysis_set"], "verdict": summary["primary"]["verdict"],
                      "gap": summary["primary"]["gap"]}), file=sys.stderr)


def main(argv=None, known=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--essays", required=True, help="v5/essays.json")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--criteria", default=v3r.CRITERIA)
    p.add_argument("requests", nargs="+", help="each cell's requests.jsonl")
    cmd_analyze(p.parse_args(argv), known)


if __name__ == "__main__":
    main()
