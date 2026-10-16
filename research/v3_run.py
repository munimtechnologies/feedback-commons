"""quote-fidelity-v3: run one model x language cell, then the preregistered analysis.

v3 is the powered replication preregistered in README.md ("Preregistration:
quote-fidelity-v3"). Its essays are fixed in v3/essays.json by v3_select.py.

  run      rebuilds those essays from the ELLIPSE file (it stops if the file's
           SHA-256 is not the one essays.json records), asks one model in one
           language for feedback on every essay and criterion through Ollama,
           with temperature 0.2 and request seed 1, and writes requests.jsonl,
           summary.json and summary.md as quote_fidelity.py does, plus the
           model's digest and the Ollama version. The v3 jobs run it with
           Feedback Commons 0.5.0, the version v2 used, so the prompt is v2's.
  analyze  reads the four cells' requests.jsonl files and writes the
           preregistered analysis: the analysis set (essays completed in all
           four cells), the one primary test (low-minus-high exact-quote rate
           pooled over the cells, whole essays resampled) and the four
           secondary outcomes. Aggregate numbers only, never essay text or
           quotes.

An essay is completed in a cell when every one of its requests in that cell
returned usable JSON; a usable reply with no quoted comment still counts.
Standard library only; analyze needs pyspellchecker. By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import collections
import datetime
import json
import os
import sys
import urllib.request

import edit_types as et
import error_conditioned as ec
import quote_fidelity as qf
import v3_select as v3s

fc = qf.fc
TEMPERATURE, REQUEST_SEED, TIMEOUT = 0.2, 1, 300
CRITERIA = "evidence,conventions"
MIN_PER_BAND = 30  # fewer analysed essays in either band: the primary test is descriptive only
LICENSE = "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus)"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _split(s):
    return [x.strip() for x in s.split(",") if x.strip()]


# --- one cell ----------------------------------------------------------------

class RequestFailed(Exception):
    """An HTTP or server error or a timeout, counted apart from replies that are not usable JSON."""


def seeded_ask(host=None, seed=REQUEST_SEED, timeout=TIMEOUT):
    """ask(messages, model): fc.call_ollama's request with the preregistered request seed added."""
    url = (host or fc.DEFAULT_HOST).rstrip("/") + "/api/chat"

    def ask(messages, model):
        body = json.dumps({"model": model, "messages": messages, "stream": False, "format": "json",
                           "options": {"temperature": TEMPERATURE, "seed": seed}}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))["message"]["content"]
        except Exception as err:
            raise RequestFailed("%s: %s" % (type(err).__name__, err)) from err
    return ask


def server_info(host, model):
    """The Ollama version and the model's digest as the server reports them; errors are recorded, not raised."""
    base, got, info = (host or fc.DEFAULT_HOST).rstrip("/"), {}, {"model": model}
    for key in ("version", "tags"):
        try:
            with urllib.request.urlopen("%s/api/%s" % (base, key), timeout=30) as resp:
                got[key] = json.loads(resp.read().decode("utf-8"))
        except Exception as err:
            info[key + "_error"] = ("%s: %s" % (type(err).__name__, err))[:300]
    info["ollama_version"] = got.get("version", {}).get("version")
    found = [m for m in got.get("tags", {}).get("models", []) if model in (m.get("name"), m.get("model"))]
    info["digest"] = found[0].get("digest") if found else None
    return info


def read_selection(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_essays(data_dir, selection):
    """The selected essays, text included; ValueError if the ELLIPSE file is not the one they were drawn from."""
    path = qf.find_csv(data_dir)
    got = v3s.sha256(path)
    if got != selection["data_sha256"]:
        raise ValueError("the ELLIPSE file's SHA-256 is %s, not %s as essays.json records"
                         % (got, selection["data_sha256"]))
    return v3s.essays_from_selection(qf.load_rows(path), selection)


def failures(records):
    """Per cell: failed requests, replies that were not usable JSON, and usable replies with no quote."""
    out = []
    for model, language in sorted({(r["model"], r["language"]) for r in records}):
        mine = [r for r in records if (r["model"], r["language"]) == (model, language)]
        failed = sum(1 for r in mine if not r["usable"]
                     and str(r.get("error", "")).startswith(RequestFailed.__name__ + ":"))
        out.append({"model": model, "language": language, "requests": len(mine),
                    "request_failed": failed,
                    "unusable_reply": sum(1 for r in mine if not r["usable"]) - failed,
                    "no_quote": sum(1 for r in mine if r["usable"] and not r["comments"])})
    return out


def cmd_run(args):
    selection = read_selection(args.essays)
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)
    try:
        essays = load_essays(args.data_dir, selection)
    except ValueError as err:
        sys.exit(str(err))
    wanted = _split(args.criteria)
    criteria = [c for c in fc.load_rubric(args.rubric)["criteria"] if c["id"] in wanted]
    if len(criteria) != len(wanted):
        sys.exit("the rubric lacks a criterion of %s" % ", ".join(wanted))
    language = "" if args.language.strip().lower() in fc.ENGLISH else fc.check_language(args.language)
    known = qf.spell_checker()
    meta = {"study": selection.get("study"), "feedback_commons": fc.__version__, "model": args.model,
            "language": qf.language_label(language), "criteria": wanted, "temperature": TEMPERATURE,
            "request_seed": REQUEST_SEED, "timeout_seconds": TIMEOUT,
            "ollama_context_length": os.environ.get("OLLAMA_CONTEXT_LENGTH"),
            "server": server_info(args.host, args.model), "essays_selected": len(essays),
            "low_max": 2.5, "high_min": 4.0, "spell_checker": known is not None,
            "data": qf.ELLIPSE_URL, "data_sha256": selection["data_sha256"], "data_license": LICENSE,
            "budget_minutes": args.budget_minutes, "started": _now()}
    print("%d essays, %s, %s" % (len(essays), args.model, meta["language"]), file=sys.stderr)
    with open(os.path.join(args.out_dir, "requests.jsonl"), "w", encoding="utf-8") as out:
        records = qf.run_study(essays, criteria, [args.model], [language], seeded_ask(args.host),
                               out, args.budget_minutes * 60, known=known)
    meta["essays_done"] = len({r["essay"] for r in records})
    meta["finished"] = _now()
    summary = qf.summarize(records)
    summary["failures"] = failures(records)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(dict(meta=meta, **summary), f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(qf.render_markdown(summary, meta))
    print(json.dumps(summary["overall"]), file=sys.stderr)


# --- the preregistered analysis ------------------------------------------------

def analysis_set(records, selection, criteria):
    """(IDs of the essays completed in every cell, in essays.json order; essays dropped, per band and reason)."""
    cells = sorted({(r["model"], r["language"]) for r in records})
    need = [(m, l, c) for m, l in cells for c in criteria]
    done = collections.defaultdict(dict)
    for r in records:
        done[r["essay"]][(r["model"], r["language"], r["criterion"])] = r["usable"]
    keep, dropped = [], {b: {"not_reached": 0, "unusable": 0} for b in ("low", "high")}
    for e in selection["essays"]:
        got = done.get(e["id"], {})
        if not need or not all(k in got for k in need):
            dropped[e["band"]]["not_reached"] += 1
        elif not all(got[k] for k in need):
            dropped[e["band"]]["unusable"] += 1
        else:
            keep.append(e["id"])
    return keep, dropped


def primary(records, selection, keep):
    """The one preregistered test: low-minus-high exact-quote rate over all cells, whole essays resampled."""
    band, ids = {e["id"]: e["band"] for e in selection["essays"]}, set(keep)
    counts = qf.per_essay([r for r in records if r["essay"] in ids])
    by = {b: [counts.get(i, (0, 0)) for i in keep if band[i] == b] for b in ("low", "high")}
    gap = qf.bootstrap_diff(by["low"], by["high"])
    out = {"bootstrap": {"resamples": 2000, "seed": 7}, "exact_rate_gap": gap}
    for b, items in by.items():
        exact, total = sum(x for x, _ in items), sum(t for _, t in items)
        out[b] = {"essays": len(items), "quotes": total, "exact": exact,
                  "exact_rate": round(exact / total, 3) if total else None}
    if min(len(v) for v in by.values()) < MIN_PER_BAND:
        out["verdict"] = "underpowered (fewer than %d essays in a band): descriptive only" % MIN_PER_BAND
    elif gap is None:
        out["verdict"] = "no quotes in a band"
    else:
        out["verdict"] = "clear" if gap["ci95"][1] < 0 else "not clear"
    return out


def length_tertiles(records):
    """Exact-quote rate by band within quote-length tertiles; cut points from all the quotes given."""
    words = sorted(len(qf.bare_words(c["quote"])) for r in records for c in r["comments"])
    if not words:
        return {"cut_points_words": None, "rows": []}
    n = len(words)
    cuts = [words[-(-n // 3) - 1], words[-(-2 * n // 3) - 1]]  # last word count of the first and second thirds
    quotes, exact = collections.Counter(), collections.Counter()
    for r in records:
        for c in r["comments"]:
            w = len(qf.bare_words(c["quote"]))
            k = (r["band"], "short" if w <= cuts[0] else "middle" if w <= cuts[1] else "long")
            quotes[k] += 1
            exact[k] += c["kind"] == "exact"
    return {"cut_points_words": cuts, "rows": [
        {"band": b, "length": t, "quotes": quotes[(b, t)], "exact": exact[(b, t)],
         "exact_rate": round(exact[(b, t)] / quotes[(b, t)], 3) if quotes[(b, t)] else None}
        for b in ("low", "high") for t in ("short", "middle", "long")]}


def misspellings(records, texts, known):
    """error_conditioned.py's summary, plus the kept-rate of misspelled words by band over all cells."""
    rows = ec.quote_rows(records, texts, known)
    out = ec.summarize(rows, texts, known)
    out["kept_pooled"] = []
    for band in ("low", "high", "all"):
        sel = [r for r in rows if r["placed"] and band in ("all", r["band"])]
        wrong, kept = sum(r["misspelled"] for r in sel), sum(r["kept"] for r in sel)
        out["kept_pooled"].append({"band": band, "misspelled_words": wrong, "kept": kept,
                                   "kept_rate": round(kept / wrong, 3) if wrong else None})
    return out


def analyze(records, selection, texts, known, criteria):
    unknown = sorted({r["essay"] for r in records} - {e["id"] for e in selection["essays"]})
    if unknown:
        raise ValueError("%d essays in the requests are not in essays.json, e.g. %s" % (len(unknown),
                                                                                       unknown[0]))
    keep, dropped = analysis_set(records, selection, criteria)
    ids = set(keep)
    sel = [r for r in records if r["essay"] in ids]
    band = {e["id"]: e["band"] for e in selection["essays"]}
    cells = qf.summarize(sel)
    return {"cells": [{"model": m, "language": l} for m, l in
                      sorted({(r["model"], r["language"]) for r in records})],
            "analysis_set": {"essays": len(keep), "low": sum(1 for i in keep if band[i] == "low"),
                             "high": sum(1 for i in keep if band[i] == "high"), "dropped": dropped},
            "failures": failures(records),
            "primary": primary(sel, selection, keep),
            "secondary_cells": {"rows": cells["rows"], "gaps": cells["gaps"]},
            "secondary_edit_types": et.summarize(et.quote_edits(sel, texts, known), sel),
            "secondary_length": length_tertiles(sel),
            "secondary_misspellings": misspellings(sel, texts, known)}


def _gap(gap):
    return "not enough data" if gap is None else "%+.3f [%+.3f, %+.3f]" % (
        gap["low_minus_high"], gap["ci95"][0], gap["ci95"][1])


def render_analysis(s):
    p, a = s["primary"], s["analysis_set"]
    out = ["# quote-fidelity-v3: preregistered analysis", "",
           "%d cells. Analysis set: %d essays (%d low, %d high) completed in every cell. Dropped: "
           "low %d not reached, %d with an unusable reply; high %d not reached, %d with an unusable "
           "reply." % (len(s["cells"]), a["essays"], a["low"], a["high"],
                       a["dropped"]["low"]["not_reached"], a["dropped"]["low"]["unusable"],
                       a["dropped"]["high"]["not_reached"], a["dropped"]["high"]["unusable"]), "",
           "## Primary: exact-quote rate, low band minus high band, all cells pooled", "",
           "- Low band: %d of %d quotes exact. High band: %d of %d." % (
               p["low"]["exact"], p["low"]["quotes"], p["high"]["exact"], p["high"]["quotes"]),
           "- Gap with 95%% essay-bootstrap interval: %s" % _gap(p["exact_rate_gap"]),
           "- Verdict (clear only if the whole interval is below zero): %s" % p["verdict"], "",
           "## Secondary 1: the same gap in each cell", ""]
    out += ["- %s, %s: %s" % (g["model"], g["language"], _gap(g["exact_rate_gap"]))
            for g in s["secondary_cells"]["gaps"]]
    out += ["", "## Secondary 2: edit types in altered quotes", "", "| Band | Edit type | Edits | Quotes with one |",
            "|---|---|---|---|"]
    out += ["| %s | %s | %d | %d |" % (t["band"], t["type"], t["edits"], t["quotes"])
            for t in s["secondary_edit_types"]["types"] if t["edits"]]
    out += ["", "## Secondary 3: exact-quote rate by quote length (cut points %s words)" %
            s["secondary_length"]["cut_points_words"], "", "| Band | Length | Quotes | Exact |",
            "|---|---|---|---|"]
    out += ["| %s | %s | %d | %s |" % (r["band"], r["length"], r["quotes"], qf._pct(r["exact_rate"]))
            for r in s["secondary_length"]["rows"]]
    out += ["", "## Secondary 4: misspelled words kept as the student wrote them, all cells", ""]
    out += ["- %s band: %d of %d (%s)" % (k["band"], k["kept"], k["misspelled_words"], qf._pct(k["kept_rate"]))
            for k in s["secondary_misspellings"]["kept_pooled"]]
    out += ["", "## Failures per cell", ""]
    out += ["- %s, %s: %d requests, %d failed, %d unusable replies, %d with no quote" % (
        f["model"], f["language"], f["requests"], f["request_failed"], f["unusable_reply"], f["no_quote"])
        for f in s["failures"]]
    return "\n".join(out) + "\n"


def cmd_analyze(args, known=None):
    known = known or qf.spell_checker()
    if known is None:
        sys.exit("pyspellchecker is needed: pip install pyspellchecker")
    selection = read_selection(args.essays)
    try:
        texts = {e["id"]: e["text"] for e in load_essays(args.data_dir, selection)}
    except ValueError as err:
        sys.exit(str(err))
    records = []
    for path in args.requests:
        with open(path, encoding="utf-8") as f:
            records += [json.loads(line) for line in f if line.strip()]
    try:
        summary = analyze(records, selection, texts, known, _split(args.criteria))
    except ValueError as err:
        sys.exit(str(err))
    summary["meta"] = {"study": selection.get("study"), "requests": len(records),
                       "files": len(args.requests), "min_per_band": MIN_PER_BAND,
                       "data_sha256": selection["data_sha256"], "data_license": LICENSE,
                       "finished": _now()}
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "analysis.md"), "w", encoding="utf-8") as f:
        f.write(render_analysis(summary))
    print(json.dumps({"analysis_set": summary["analysis_set"], "verdict": summary["primary"]["verdict"],
                      "gap": summary["primary"]["exact_rate_gap"]}), file=sys.stderr)


def main(argv=None, known=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="one model x language cell")
    r.add_argument("--essays", required=True, help="v3/essays.json")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--model", required=True)
    r.add_argument("--language", required=True, help="English or Spanish")
    r.add_argument("--rubric", default="sample_rubric.json")
    r.add_argument("--criteria", default=CRITERIA)
    r.add_argument("--budget-minutes", type=float, default=290)
    r.add_argument("--host", default=fc.DEFAULT_HOST)
    a = sub.add_parser("analyze", help="the preregistered analysis of the four cells")
    a.add_argument("--essays", required=True, help="v3/essays.json")
    a.add_argument("--data-dir", required=True)
    a.add_argument("--out-dir", required=True)
    a.add_argument("--criteria", default=CRITERIA)
    a.add_argument("requests", nargs="+", help="each cell's requests.jsonl")
    args = p.parse_args(argv)
    if args.command == "run":
        cmd_run(args)
    else:
        cmd_analyze(args, known)


if __name__ == "__main__":
    main()
