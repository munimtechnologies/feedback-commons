"""quote-fidelity-v6: the preregistered paired analysis (research/PREREG-v6.md).

v6 runs each of v5's four model x language cells twice on the same 120 essays,
once with the unchanged prompt (condition c) and once with one added
quote-exactly sentence (condition q): eight cells, made by v6_run.py, whose
requests.jsonl lines each carry their condition. This reads them and writes
the one primary test and the declared secondary analyses:

  analysis set   essays with a usable reply for every criterion in all eight
                 cells (v3_run.analysis_set, with each cell keyed by model,
                 language and condition), so c and q cover the same essays
  matched quote  as in v5 (v5_analyze.matched_rows): a quote labelled exact,
                 punctuation or altered whose student passage
                 error_conditioned.place_quote finds; not_in_text, too_short
                 and unplaceable quotes are excluded and counted
  primary        exact-quote rate (the exact label only) of matched quotes under
                 q minus under c, pooled over the four model x language cells,
                 with a 95% percentile interval from 10,000 resamples of whole
                 essays, each essay carrying its quotes under both conditions
                 (seed "v6-boot-20261024"); read only with at least 300 matched
                 quotes in each condition
  secondary      the same gap per Conventions band and per model x language
                 cell; every quote's label by condition, unmatched ones
                 included; quotes per usable reply by condition; misspelled
                 words kept as written by condition (v5_analyze.descriptive)

Aggregate numbers only, never essay text or quotes. Needs pyspellchecker
(SPELLCHECKER_VERSION). By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import collections
import json
import os
import sys

import error_conditioned as ec
import quote_fidelity as qf
import v3_run as v3r
import v5_analyze as v5a

STUDY, SAMPLE = "quote-fidelity-v6", "quote-fidelity-v5"
CONDITIONS = ("c", "q")
FLOOR = 300  # matched quotes in each condition needed before the primary test is read
RESAMPLES, BOOT_SEED = 10000, "v6-boot-20261024"
SPELLCHECKER_VERSION = v5a.SPELLCHECKER_VERSION
KINDS = (("exact", "Exact"), ("punctuation", "Same words"), ("altered", "Changed words"),
         ("not_in_text", "Not found"), ("too_short", "Too short"))


def check_records(records):
    """ValueError unless every record names a condition and every model x language cell has both."""
    bad = sum(1 for r in records if r.get("condition") not in CONDITIONS)
    if bad:
        raise ValueError("%d records have no condition c or q (were they made by v6_run.py?)" % bad)
    have = collections.defaultdict(set)
    for r in records:
        have[(r["model"], r["language"])].add(r["condition"])
    lone = sorted("%s, %s" % k for k, v in have.items() if v != set(CONDITIONS))
    if lone:
        raise ValueError("cells without both conditions: %s" % "; ".join(lone))


def keyed(records):
    """The records with the condition folded into the language, so v3_run's per-cell rules see eight cells."""
    return [dict(r, language="%s/%s" % (r["language"], r["condition"])) for r in records]


def per_essay(rows_q, rows_c, essays):
    """(exact q, quotes q, exact c, quotes c) for each essay, in order; zeros where it has no matched quote."""
    per = {e: [0, 0, 0, 0] for e in essays}
    for k, rows in ((0, rows_q), (2, rows_c)):
        for r in rows:
            v = per[r["essay"]]
            v[k] += 1 if r["exact"] else 0
            v[k + 1] += 1
    return [tuple(per[e]) for e in essays]


def contrast(rows_q, rows_c, essays, n=RESAMPLES, seed=BOOT_SEED):
    """Exact-quote rates under q and c, and q minus c with a paired whole-essay bootstrap interval."""
    items = per_essay(rows_q, rows_c, essays)
    ex_q, nq, ex_c, nc = (sum(x[k] for x in items) for k in range(4))
    g = ec.bootstrap_contrast(items, n, seed)
    return {"essays": len(items),
            "q_quotes": nq, "q_exact": ex_q, "q_exact_rate": round(ex_q / nq, 3) if nq else None,
            "c_quotes": nc, "c_exact": ex_c, "c_exact_rate": round(ex_c / nc, 3) if nc else None,
            "gap": None if g is None else {"q_minus_c": g["misspelled_minus_clean"], "ci95": g["ci95"],
                                           "resamples": g["resamples"]}}


def verdict(c, floor=FLOOR):
    """The preregistered reading rule, after the power floor."""
    if c["q_quotes"] < floor or c["c_quotes"] < floor:
        return "underpowered (fewer than %d matched quotes in a condition): the sign is not interpreted" % floor
    if c["gap"] is None:
        return "no interval (a condition is missing from the resamples)"
    lo, hi = c["gap"]["ci95"]
    if lo > 0:
        return "H1 supported: the quote-exactly instruction raises the exact-quote rate"
    if hi < 0:
        return "the instruction hurts: quotes are reproduced exactly less often with it"
    return "no clear effect"


def composition(records):
    """Every quote's label, unmatched ones included, as counts and shares."""
    kinds = collections.Counter(c["kind"] for r in records for c in r["comments"])
    total = sum(kinds.values())
    return {"quotes": total,
            "kinds": [{"kind": k, "label": label, "quotes": kinds[k],
                       "share": round(kinds[k] / total, 3) if total else None} for k, label in KINDS]}


def quoting(records, matched):
    """How much the model quotes: quotes and matched quotes per usable reply."""
    replies = sum(1 for r in records if r["usable"])
    quotes = sum(len(r["comments"]) for r in records)
    return {"usable_replies": replies, "quotes": quotes, "matched_quotes": matched,
            "quotes_per_reply": round(quotes / replies, 3) if replies else None,
            "matched_per_reply": round(matched / replies, 3) if replies else None,
            "replies_with_no_quote": sum(1 for r in records if r["usable"] and not r["comments"])}


def analyze(records, selection, texts, known, criteria, n=RESAMPLES, seed=BOOT_SEED):
    unknown = sorted({r["essay"] for r in records} - {e["id"] for e in selection["essays"]})
    if unknown:
        raise ValueError("%d essays in the requests are not in essays.json, e.g. %s" % (len(unknown),
                                                                                       unknown[0]))
    check_records(records)
    keep, dropped = v3r.analysis_set(keyed(records), selection, criteria)
    ids = set(keep)
    band = {e["id"]: e["band"] for e in selection["essays"]}
    recs, rows, excluded = {}, {}, {}
    for cond in CONDITIONS:
        recs[cond] = [r for r in records if r["essay"] in ids and r["condition"] == cond]
        rows[cond], excluded[cond] = v5a.matched_rows(recs[cond], texts, known)
    cells = sorted({(r["model"], r["language"]) for r in records})
    primary = contrast(rows["q"], rows["c"], keep, n, seed)
    primary["verdict"] = verdict(primary)

    def only(cond, test):
        return [r for r in rows[cond] if test(r)]

    return {"cells": [{"model": m, "language": l} for m, l in cells],
            "analysis_set": {"essays": len(keep), "low": sum(1 for i in keep if band[i] == "low"),
                             "high": sum(1 for i in keep if band[i] == "high"), "dropped": dropped},
            "failures": v3r.failures(keyed(records)),
            "quotes": {cond: {"all": len(rows[cond]) + sum(excluded[cond].values()),
                              "matched": len(rows[cond]), "excluded": excluded[cond]} for cond in CONDITIONS},
            "primary": primary,
            "secondary_bands": [dict({"band": b}, **contrast(only("q", lambda r: r["band"] == b),
                                                             only("c", lambda r: r["band"] == b),
                                                             [i for i in keep if band[i] == b], n, seed))
                                for b in ("low", "high")],
            "secondary_cells": [dict({"model": m, "language": l},
                                     **contrast(only("q", lambda r: (r["model"], r["language"]) == (m, l)),
                                                only("c", lambda r: (r["model"], r["language"]) == (m, l)),
                                                keep, n, seed))
                                for m, l in cells],
            "secondary_composition": {cond: composition(recs[cond]) for cond in CONDITIONS},
            "secondary_quoting": {cond: quoting(recs[cond], len(rows[cond])) for cond in CONDITIONS},
            "secondary_misspelled": {cond: v5a.descriptive(rows[cond]) for cond in CONDITIONS}}


def _gap(gap):
    return "not enough data" if gap is None else "%+.3f [%+.3f, %+.3f]" % (
        gap["q_minus_c"], gap["ci95"][0], gap["ci95"][1])


def _line(label, c):
    return "- %s: with the instruction %d of %d exact (%s), without %d of %d (%s); gap %s" % (
        label, c["q_exact"], c["q_quotes"], qf._pct(c["q_exact_rate"]),
        c["c_exact"], c["c_quotes"], qf._pct(c["c_exact_rate"]), _gap(c["gap"]))


def render_analysis(s):
    p, a = s["primary"], s["analysis_set"]
    out = ["# quote-fidelity-v6: preregistered analysis", "",
           "%d model x language cells, each run without (c) and with (q) the quote-exactly instruction. "
           "Analysis set: %d essays (%d low, %d high) completed in all %d runs. Dropped: low %d not reached, "
           "%d with an unusable reply; high %d not reached, %d with an unusable reply." % (
               len(s["cells"]), a["essays"], a["low"], a["high"], 2 * len(s["cells"]),
               a["dropped"]["low"]["not_reached"], a["dropped"]["low"]["unusable"],
               a["dropped"]["high"]["not_reached"], a["dropped"]["high"]["unusable"]), ""]
    for cond, name in (("c", "Without the instruction (c)"), ("q", "With the instruction (q)")):
        q = s["quotes"][cond]
        out.append("%s: %d quotes, %d with a matched passage. Excluded: %d not in text, %d too short, "
                   "%d labelled in the text but not placeable." % (
                       name, q["all"], q["matched"], q["excluded"]["not_in_text"], q["excluded"]["too_short"],
                       q["excluded"]["unplaced"]))
    out += ["", "## Primary: exact-quote rate, with minus without the instruction, all cells pooled", "",
            _line("All cells", p),
            "- Floor: at least %d matched quotes in each condition." % FLOOR,
            "- Verdict: %s" % p["verdict"], "",
            "## Secondary 1: within each Conventions band", ""]
    out += [_line("%s band" % c["band"], c) for c in s["secondary_bands"]]
    out += ["", "## Secondary 2: each model x language cell", ""]
    out += [_line("%s, %s" % (c["model"], c["language"]), c) for c in s["secondary_cells"]]
    out += ["", "## Secondary 3: every quote's label, by condition", "",
            "| Label | Without: quotes | Without: share | With: quotes | With: share |",
            "|---|---|---|---|---|"]
    comp = s["secondary_composition"]
    for kc, kq in zip(comp["c"]["kinds"], comp["q"]["kinds"]):
        out.append("| %s | %d | %s | %d | %s |" % (kc["label"], kc["quotes"], qf._pct(kc["share"]),
                                                    kq["quotes"], qf._pct(kq["share"])))
    out += ["", "## Secondary 4: how much the models quote", "",
            "| Condition | Usable replies | Quotes | Per reply | Matched per reply | Replies with no quote |",
            "|---|---|---|---|---|---|"]
    for cond, name in (("c", "Without"), ("q", "With")):
        g = s["secondary_quoting"][cond]
        out.append("| %s | %d | %d | %s | %s | %d |" % (
            name, g["usable_replies"], g["quotes"], g["quotes_per_reply"], g["matched_per_reply"],
            g["replies_with_no_quote"]))
    out += ["", "## Secondary 5: misspelled words kept as the student wrote them", "",
            "| Condition | Band | Matched quotes | Misspelled words | Kept as written | Not kept | Kept rate |",
            "|---|---|---|---|---|---|---|"]
    for cond, name in (("c", "Without"), ("q", "With")):
        out += ["| %s | %s | %d | %d | %d | %d | %s |" % (name, d["band"], d["matched_quotes"],
                                                         d["misspelled_words"], d["kept"], d["not_kept"],
                                                         qf._pct(d["kept_rate"]))
                for d in s["secondary_misspelled"][cond]]
    out += ["", "## Failures per run", ""]
    out += ["- %s, %s: %d requests, %d failed, %d unusable replies, %d with no quote" % (
        f["model"], f["language"], f["requests"], f["request_failed"], f["unusable_reply"], f["no_quote"])
        for f in s["failures"]]
    return "\n".join(out) + "\n"


def cmd_analyze(args, known=None):
    version = v5a.checker_version()
    if known is None:
        known = qf.spell_checker()
        if known is None:
            sys.exit("pyspellchecker is needed: pip install pyspellchecker==%s" % SPELLCHECKER_VERSION)
        if version != SPELLCHECKER_VERSION:
            sys.exit("pyspellchecker %s is installed; the analysis is pinned to %s"
                     % (version, SPELLCHECKER_VERSION))
    selection = v3r.read_selection(args.essays)
    if selection.get("study") != SAMPLE:
        sys.exit("%s is not the %s selection v6 reuses" % (args.essays, SAMPLE))
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
    summary["meta"] = {"study": STUDY, "sample": SAMPLE, "requests": len(records), "files": len(args.requests),
                       "floor": FLOOR, "resamples": RESAMPLES, "bootstrap_seed": BOOT_SEED,
                       "spellchecker": version, "spellchecker_pinned": SPELLCHECKER_VERSION,
                       "data_sha256": selection["data_sha256"], "data_license": v3r.LICENSE,
                       "finished": v3r._now()}
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
    p.add_argument("requests", nargs="+", help="each of the eight runs' requests.jsonl")
    cmd_analyze(p.parse_args(argv), known)


if __name__ == "__main__":
    main()
