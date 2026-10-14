"""Quote fidelity: do small local models quote English learners' essays faithfully?

Feedback Commons asks the model to quote the student's exact words in every
comment, and flags a comment when the quote is not in the essay. This study
runs that same pipeline on real essays by English language learners (the
ELLIPSE corpus, grades 8-12) and sorts every quote into:

  exact        found as Feedback Commons checks it (case, spacing, curly quotes ignored)
  punctuation  the same words in the same order, only punctuation differs
  altered      a close match with some of the student's words changed, for
               example a misspelling silently corrected
  not_in_text  nothing in the essay is that close (invented or paraphrased)
  too_short    under 3 characters, which Feedback Commons never accepts

Essays are drawn from two bands of the human Conventions score (spelling,
punctuation, capitalization), so the study can show whether weaker spellers'
essays get less faithful quotes, and so more flagged comments.

Standard library only; pyspellchecker is used to count corrections if it is
installed. By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import csv
import datetime
import difflib
import itertools
import json
import os
import random
import re
import sys
import time
import urllib.request

try:
    import feedback_commons as fc
except ImportError:  # run from research/ in the repo: the tool sits one folder up
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import feedback_commons as fc

ELLIPSE_URL = ("https://raw.githubusercontent.com/scrosseye/ELLIPSE-Corpus/main/"
               "ELLIPSE_Final_github_train.csv")
KINDS = ("exact", "punctuation", "altered", "not_in_text", "too_short")
WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")
ALTERED_MIN = 0.7  # word-level similarity: 2 changed words in a 10-word quote is 0.8


# --- classifying one quote -------------------------------------------------

def bare_words(s):
    """Lower-case words of s, with punctuation dropped and apostrophes inside words kept."""
    return WORD.findall(fc._norm(s))


def _contains(words, part):
    n = len(part)
    return n > 0 and any(words[i:i + n] == part for i in range(len(words) - n + 1))


def best_window(quote_words, text_words):
    """(similarity, start, end) of the run of essay words most like the quote."""
    best = (0.0, 0, 0)
    n = len(quote_words)
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(quote_words)
    for size in range(max(1, n - 2), n + 3):
        for i in range(max(1, len(text_words) - size + 1)):
            sm.set_seq1(text_words[i:i + size])
            if sm.real_quick_ratio() <= best[0] or sm.quick_ratio() <= best[0]:
                continue
            r = sm.ratio()
            if r > best[0]:
                best = (r, i, i + size)
    return best


def word_changes(student, quote):
    """(student words, quote words) for each place the quote swapped words for others."""
    pairs = []
    sm = difflib.SequenceMatcher(None, student, quote, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "replace":
            continue
        if i2 - i1 == j2 - j1:
            pairs.extend(zip(student[i1:i2], quote[j1:j2]))
        else:
            pairs.append((" ".join(student[i1:i2]), " ".join(quote[j1:j2])))
    return pairs


def is_correction(student, quote, known):
    """True when the quote replaced words the spell checker doesn't know with words it does."""
    s, q = student.split(), quote.split()
    return bool(s) and bool(q) and not all(known(w) for w in s) and all(known(w) for w in q)


def classify_quote(quote, text, known=None):
    """How faithfully one comment's quote reproduces the student's text (see the module doc)."""
    qw = bare_words(quote)
    out = {"kind": "not_in_text", "similarity": 0.0, "words": len(qw), "changes": [],
           "corrections": None}
    if len(fc._norm(quote).strip(" .\"'")) < 3:
        return dict(out, kind="too_short")
    if fc.quote_found(quote, text):
        return dict(out, kind="exact", similarity=1.0)
    tw = bare_words(text)
    if not qw:
        return out
    if _contains(tw, qw):
        return dict(out, kind="punctuation", similarity=1.0)
    ratio, i, j = best_window(qw, tw)
    out["similarity"] = round(ratio, 3)
    if ratio < ALTERED_MIN:
        return out
    changes = word_changes(tw[i:j], qw)
    out.update(kind="altered", changes=changes)
    if known is not None:
        out["corrections"] = sum(1 for s, q in changes if is_correction(s, q, known))
    return out


def spell_checker():
    """known(word) from pyspellchecker's English list, or None if it isn't installed."""
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return None
    sc = SpellChecker()
    return lambda w: bool(sc.known([w]))


# --- essays ----------------------------------------------------------------

def find_csv(data_dir, url=ELLIPSE_URL):
    """The ELLIPSE training CSV under data_dir, downloaded there if it isn't yet."""
    for root, _, files in os.walk(data_dir):
        for name in sorted(files):
            if name.lower().endswith(".csv"):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8-sig", errors="replace") as f:
                    head = f.readline()
                if "full_text" in head and "Conventions" in head:
                    return path
    path = os.path.join(data_dir, "ELLIPSE_Final_github_train.csv")
    urllib.request.urlretrieve(url, path)
    return path


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def select_essays(rows, per_band, seed=2026, min_words=150, max_words=450,
                  low_max=2.5, high_min=4.0):
    """per_band essays with Conventions <= low_max and as many with >= high_min, alternating."""
    pool = {"low": [], "high": []}
    for n, r in enumerate(rows):
        text = (r.get("full_text") or "").replace("\r\n", "\n").strip()
        try:
            conventions = float(r.get("Conventions") or "")
        except ValueError:
            continue
        words = len(text.split())
        if not min_words <= words <= max_words:
            continue
        band = "low" if conventions <= low_max else "high" if conventions >= high_min else None
        if band:
            pool[band].append({"id": r.get("text_id_kaggle") or "row%d" % n, "band": band,
                               "conventions": conventions, "grade": (r.get("grade") or "").strip(),
                               "words": words, "text": text})
    rng = random.Random(seed)
    chosen = {}
    for band in ("low", "high"):
        items = sorted(pool[band], key=lambda e: e["id"])
        chosen[band] = rng.sample(items, min(per_band, len(items)))
    return [e for pair in itertools.zip_longest(chosen["low"], chosen["high"]) for e in pair if e]


# --- the study -------------------------------------------------------------

def language_label(language):
    return language or "English"


def run_study(essays, criteria, models, languages, ask, out, budget_seconds,
              clock=time.monotonic, known=None):
    """Ask every model for feedback on every essay, criterion and language until the budget is spent.

    ask(messages, model) returns the model's reply text. Each request becomes
    one record, written to the open file out as a JSON line as soon as it is
    done, so a run that is stopped early keeps what it has. Essays are taken
    whole (every model, language and criterion), so partial runs stay balanced.
    """
    start, records = clock(), []
    for e in essays:
        if clock() - start > budget_seconds:
            break
        for model in models:
            for language in languages:
                for c in criteria:
                    rec = {"essay": e["id"], "band": e["band"], "conventions": e["conventions"],
                           "model": model, "language": language_label(language),
                           "criterion": c["id"], "usable": False, "comments": []}
                    t0 = clock()
                    try:
                        raw = ask(fc.build_messages(c, e["text"], e["grade"], language=language), model)
                    except Exception as err:  # timeouts and HTTP errors: record and go on
                        raw, rec["error"] = None, ("%s: %s" % (type(err).__name__, err))[:300]
                    rec["seconds"] = round(clock() - t0, 2)
                    if raw is not None:
                        try:
                            comments = fc.parse_comments(raw)
                        except ValueError as err:
                            rec["error"] = str(err)[:300]
                        else:
                            rec["usable"] = True
                            rec["comments"] = [dict(classify_quote(x["quote"], e["text"], known),
                                                    quote=x["quote"]) for x in comments]
                    records.append(rec)
                    if out is not None:
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        out.flush()
    return records


def tally(records):
    t = {"requests": len(records), "unusable": sum(1 for r in records if not r["usable"]),
         "comments": 0, "altered_with_correction": 0, "corrections": 0}
    t.update({k: 0 for k in KINDS})
    seconds = [r["seconds"] for r in records if r.get("seconds") is not None]
    for r in records:
        for c in r["comments"]:
            t["comments"] += 1
            t[c["kind"]] += 1
            if c["kind"] == "altered" and c.get("corrections"):
                t["altered_with_correction"] += 1
                t["corrections"] += c["corrections"]
    for k in KINDS:
        t[k + "_rate"] = round(t[k] / t["comments"], 3) if t["comments"] else None
    t["seconds_per_request"] = round(sum(seconds) / len(seconds), 1) if seconds else None
    return t


def per_essay(records):
    """{essay: (exact quotes, all quotes)}."""
    out = {}
    for r in records:
        exact, total = out.get(r["essay"], (0, 0))
        exact += sum(1 for c in r["comments"] if c["kind"] == "exact")
        out[r["essay"]] = (exact, total + len(r["comments"]))
    return out


def _pooled(items):
    total = sum(t for _, t in items)
    return sum(x for x, _ in items) / total if total else None


def bootstrap_diff(low, high, n=2000, seed=7):
    """Low-band minus high-band exact-quote rate, with a 95% interval from resampling essays.

    low and high are lists of (exact, quotes) per essay; resampling whole
    essays respects that one essay's comments are not independent.
    """
    if _pooled(low) is None or _pooled(high) is None:
        return None
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        a = _pooled([rng.choice(low) for _ in low])
        b = _pooled([rng.choice(high) for _ in high])
        if a is not None and b is not None:
            diffs.append(a - b)
    diffs.sort()
    return {"low_minus_high": round(_pooled(low) - _pooled(high), 3),
            "ci95": [round(diffs[int(0.025 * len(diffs))], 3),
                     round(diffs[max(0, int(0.975 * len(diffs)) - 1)], 3)],
            "resamples": len(diffs)}


def summarize(records):
    """Rows per (model, language, band) and per criterion, and the low-vs-high gap per model and language."""
    rows, gaps = [], []
    combos = sorted({(r["model"], r["language"]) for r in records})
    for model, language in combos:
        mine = [r for r in records if (r["model"], r["language"]) == (model, language)]
        for band in ("low", "high", "all"):
            sel = [r for r in mine if band == "all" or r["band"] == band]
            rows.append(dict({"model": model, "language": language, "band": band,
                              "criterion": "all", "essays": len({r["essay"] for r in sel})},
                             **tally(sel)))
            for crit in sorted({r["criterion"] for r in sel}):
                part = [r for r in sel if r["criterion"] == crit]
                rows.append(dict({"model": model, "language": language, "band": band,
                                  "criterion": crit, "essays": len({r["essay"] for r in part})},
                                 **tally(part)))
        counts = per_essay(mine)
        bands = {r["essay"]: r["band"] for r in mine}
        low = [v for k, v in counts.items() if bands[k] == "low"]
        high = [v for k, v in counts.items() if bands[k] == "high"]
        gaps.append({"model": model, "language": language, "exact_rate_gap": bootstrap_diff(low, high)})
    return {"rows": rows, "gaps": gaps, "overall": tally(records)}


def _pct(x):
    return "-" if x is None else "%.0f%%" % (100 * x)


def render_markdown(summary, meta):
    out = ["# Quote fidelity of small local models on English learners' essays", "",
           "Feedback Commons %s, %s. %d requests on %d essays (ELLIPSE corpus, CC BY-NC-SA 4.0). "
           "Bands: Conventions score <= %s (low) and >= %s (high)." % (
               meta["feedback_commons"], meta["finished"], summary["overall"]["requests"],
               meta["essays_done"], meta["low_max"], meta["high_min"]), "",
           "| Model | Language | Band | Criterion | Quotes | Exact | Punctuation only | Altered "
           "(of which spelling fixed) | Not in text | Unusable replies | s/request |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["rows"]:
        out.append("| %s | %s | %s | %s | %d | %s | %s | %s (%d) | %s | %d of %d | %s |" % (
            r["model"], r["language"], r["band"], r["criterion"], r["comments"],
            _pct(r["exact_rate"]), _pct(r["punctuation_rate"]), _pct(r["altered_rate"]),
            r["altered_with_correction"], _pct(r["not_in_text_rate"]), r["unusable"],
            r["requests"], r["seconds_per_request"]))
    out += ["", "## Exact-quote rate, low band minus high band (95% essay bootstrap)", ""]
    for g in summary["gaps"]:
        gap = g["exact_rate_gap"]
        out.append("- %s, %s: %s" % (g["model"], g["language"], "not enough data" if gap is None else
                                     "%+.3f [%+.3f, %+.3f]" % (gap["low_minus_high"], gap["ci95"][0],
                                                               gap["ci95"][1])))
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--rubric", default="sample_rubric.json")
    p.add_argument("--criteria", default="evidence,conventions")
    p.add_argument("--models", default="llama3.2:3b,qwen2.5:3b")
    p.add_argument("--languages", default="English,Spanish")
    p.add_argument("--per-band", type=int, default=15)
    p.add_argument("--budget-minutes", type=float, default=240)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--host", default=fc.DEFAULT_HOST)
    args = p.parse_args(argv)

    rubric = fc.load_rubric(args.rubric)
    wanted = [c.strip() for c in args.criteria.split(",") if c.strip()]
    criteria = [c for c in rubric["criteria"] if c["id"] in wanted]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    languages = ["" if l.strip().lower() in fc.ENGLISH else fc.check_language(l)
                 for l in args.languages.split(",") if l.strip()]
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)
    essays = select_essays(load_rows(find_csv(args.data_dir)), args.per_band, args.seed)
    known = spell_checker()
    meta = {"feedback_commons": fc.__version__, "models": models,
            "languages": [language_label(l) for l in languages], "criteria": wanted,
            "per_band": args.per_band, "seed": args.seed, "low_max": 2.5, "high_min": 4.0,
            "essays_selected": len(essays), "spell_checker": known is not None,
            "data": ELLIPSE_URL, "data_license": "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus)",
            "started": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    print("%d essays, %d models, %d languages, %d criteria" % (
        len(essays), len(models), len(languages), len(criteria)), file=sys.stderr)
    with open(os.path.join(args.out_dir, "requests.jsonl"), "w", encoding="utf-8") as out:
        records = run_study(essays, criteria, models, languages,
                            lambda m, model: fc.call_ollama(m, model, args.host), out,
                            args.budget_minutes * 60, known=known)
    meta["essays_done"] = len({r["essay"] for r in records})
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = summarize(records)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(dict(meta=meta, **summary), f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(summary, meta))
    print(json.dumps(summary["overall"]), file=sys.stderr)


if __name__ == "__main__":
    main()
