"""Edit types: what a model changed when it quoted a student's words.

The quote-fidelity study calls a quote "altered" when it closely matches a
passage of the essay with some words changed, and it lists only the words
swapped one for another. That misses words the model added or left out. It
also mistakes edits at either end of a quote for added words: when a student
wrote "with out" and the quote begins "Without", the closest passage stops
just after "with out", so "without" looks like a word the student never wrote.

This module names every edit mechanically. It aligns the quote with the
student's passage plus two words on each side, treats student words beyond
either end of the quote as context, and sorts what is left into:

  spelling     one word for one: the spell checker does not know the student's
               word and knows the quote's (a misspelling fixed)
  apostrophe   the same letters with an apostrophe added or removed (cant, can't)
  join         two or more student words written as one (with out, without)
  split        one student word written as two or more (alot, a lot)
  inflection   one word for another with the same stem: one is the other plus
               a common ending (experience, experiences; you, your), or they
               share at least four letters and differ by at most four after them
  real_word    one word for another, both known to the spell checker
  inserted     quote words the student did not write
  dropped      student words inside the passage that the quote left out
  other        anything else

At either end of the quote, a student word next to the passage counts as the
quote's word when it spells the same letters (joins, splits, apostrophes) or
is a close character match (similarity at least 0.6); otherwise the quote's
word counts as inserted. Without a spell checker, spelling and real_word never
fire and those edits count as other. Inserted and dropped edits also count how
many of their words are function words (articles, pronouns, prepositions,
auxiliaries, conjunctions), and every edit says whether it sits at either end
of the quote.

The command reads the study's requests.jsonl (or any file of the same form)
and the same ELLIPSE essays, and writes aggregate counts only, never essay
text or the words changed. Standard library only; pyspellchecker if installed.
By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import collections
import datetime
import difflib
import json
import os
import sys

import quote_fidelity as qf

TYPES = ("spelling", "apostrophe", "join", "split", "inflection", "real_word", "inserted",
         "dropped", "other")
ENDINGS = ("s", "es", "d", "ed", "ing", "r", "er", "ly", "'s")
FUNCTION_WORDS = frozenset("""
a an the this that these those my your his her its our their i you he she it we they me him us
them to of in on at by for with from into about as than and or but so if because when while is
are was were be been being am do does did have has had will would can could should may might
must shall not no""".split())
MARGIN = 2  # student words looked at beyond each end of the matched passage
CLOSE = 0.6  # character similarity for a student word at an end of the quote to count as its source


def _squash(words):
    return "".join(words).replace("'", "")


def same_stem(a, b):
    """True when one word is the other plus a common ending, or they share four letters and differ by at most four after them."""
    p = len(os.path.commonprefix([a, b]))
    if p < 3:
        return False
    rest = (a[p:], b[p:])
    if p == min(len(a), len(b)):
        return max(rest, key=len) in ENDINGS
    return p >= 4 and max(len(r) for r in rest) <= 4


def pair_type(student, quote, known=None):
    """The type of a one-for-one word swap (see the module doc)."""
    if student.replace("'", "") == quote.replace("'", ""):
        return "apostrophe"
    if known is not None and not known(student) and known(quote):
        return "spelling"
    if same_stem(student, quote):
        return "inflection"
    if known is not None and known(student) and known(quote):
        return "real_word"
    return "other"


def _edge_student(s, q, lead, inside):
    """The student words behind an edit at an end of the quote.

    s runs past the end of the matched passage (before it when lead is True,
    after it otherwise); inside is how many of its words lie within the passage.
    """
    target = _squash(q)
    for k in range(1, len(s) + 1):
        run = s[len(s) - k:] if lead else s[:k]
        if _squash(run) == target:
            return run
    m = len(q)
    run = s[len(s) - m:] if lead else s[:m]
    if len(run) == m and all(difflib.SequenceMatcher(None, a, b).ratio() >= CLOSE
                             for a, b in zip(run, q)):
        return run
    return s[len(s) - inside:] if lead else s[:inside]


def _name(s, q, edge, known):
    def edit(kind, words, student=s, quote=q):
        e = {"type": kind, "words": words, "edge": edge, "student": student, "quote": quote}
        if kind in ("inserted", "dropped"):
            e["function_words"] = sum(1 for w in quote or student if w in FUNCTION_WORDS)
        return e
    if not s:
        return [edit("inserted", len(q))]
    if not q:
        return [edit("dropped", len(s))]
    if len(s) == len(q):
        return [edit(pair_type(a, b, known), 1, [a], [b]) for a, b in zip(s, q)]
    if _squash(s) == _squash(q):
        return [edit("join" if len(s) > len(q) else "split", len(q))]
    return [edit("other", max(len(s), len(q)))]


def edits(quote, text, known=None, margin=MARGIN):
    """Every edit between a quote and the passage it was taken from, or None if it can't be placed.

    Each edit is a dict with its type, its number of words, whether it is at
    an end of the quote, and the student's and the quote's words (kept for
    tests and inspection; the command never writes them).
    """
    qw, tw = qf.bare_words(quote), qf.bare_words(text)
    if not qw:
        return None
    ratio, i, j = qf.best_window(qw, tw)
    if ratio < qf.ALTERED_MIN:
        return None
    lo, hi = max(0, i - margin), min(len(tw), j + margin)
    student = tw[lo:hi]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, student, qw,
                                                      autojunk=False).get_opcodes():
        s, q = student[i1:i2], qw[j1:j2]
        start, end = j1 == 0, j2 == len(qw)
        if op == "equal" or (op == "delete" and (start or end)):
            continue
        if op == "replace" and start:
            s = _edge_student(s, q, True, max(0, i2 - max(i1, i - lo)))
        elif op == "replace" and end:
            s = _edge_student(s, q, False, max(0, min(i2, j - lo) - i1))
        out.extend(_name(s, q, start or end, known))
    return out


# --- the study's altered quotes ----------------------------------------------

def quote_edits(records, texts, known=None):
    """One row per altered quote: band, model, language, length and its edits, without any words."""
    rows = []
    for r in records:
        text = texts.get(r["essay"])
        for c in r["comments"]:
            if c["kind"] != "altered":
                continue
            found = edits(c["quote"], text, known) if text else None
            row = {"essay": r["essay"], "band": r["band"], "model": r["model"],
                   "language": r["language"], "words": len(qf.bare_words(c["quote"])),
                   "placed": found is not None,
                   "edits": [{k: e[k] for k in ("type", "words", "edge", "function_words") if k in e}
                             for e in found or []]}
            if text and "similarity" in c:
                row["recorded"] = c["similarity"]
                row["rechecked"] = qf.classify_quote(c["quote"], text)["similarity"]
            rows.append(row)
    return rows


def summarize(rows, records):
    out = {"quotes": sum(len(r["comments"]) for r in records), "altered": len(rows),
           "placed": sum(1 for r in rows if r["placed"]),
           "similarity_rechecked": sum(1 for r in rows if "recorded" in r),
           "similarity_mismatches": sum(1 for r in rows
                                        if "recorded" in r and r["recorded"] != r["rechecked"]),
           "bands": [], "types": [], "lengths": []}
    for band in ("low", "high", "all"):
        sel = [r for r in rows if r["placed"] and band in ("all", r["band"])]
        out["bands"].append({"band": band, "altered": sum(1 for r in rows if band in ("all", r["band"])),
                             "placed": len(sel), "no_edits": sum(1 for r in sel if not r["edits"]),
                             "edits": sum(len(r["edits"]) for r in sel)})
        for t in TYPES:
            es = [e for r in sel for e in r["edits"] if e["type"] == t]
            row = {"band": band, "type": t, "edits": len(es),
                   "quotes": sum(1 for r in sel if any(e["type"] == t for e in r["edits"])),
                   "words": sum(e["words"] for e in es), "at_edge": sum(1 for e in es if e["edge"])}
            if t in ("inserted", "dropped"):
                row["function_words"] = sum(e["function_words"] for e in es)
            out["types"].append(row)
    lengths = collections.defaultdict(list)
    for r in records:
        for c in r["comments"]:
            lengths[(r["band"], c["kind"])].append(len(qf.bare_words(c["quote"])))
    out["lengths"] = [{"band": b, "kind": k, "quotes": len(v), "mean_words": round(sum(v) / len(v), 1)}
                      for (b, k), v in sorted(lengths.items())]
    return out


def render_markdown(summary):
    out = ["# Edit types in altered quotes", "",
           "%d quotes, %d altered, %d of those placed in the essay. Recorded similarity rechecked "
           "for %d, mismatches: %d." % (summary["quotes"], summary["altered"], summary["placed"],
                                        summary["similarity_rechecked"],
                                        summary["similarity_mismatches"]), "",
           "| Band | Altered | Placed | With no edit found | Edits |", "|---|---|---|---|---|"]
    for b in summary["bands"]:
        out.append("| %s | %d | %d | %d | %d |" % (b["band"], b["altered"], b["placed"],
                                                   b["no_edits"], b["edits"]))
    out += ["", "| Band | Edit type | Edits | Quotes with one | Words | At an end of the quote "
            "| Function words |", "|---|---|---|---|---|---|---|"]
    for t in summary["types"]:
        if t["edits"]:
            out.append("| %s | %s | %d | %d | %d | %d | %s |" % (
                t["band"], t["type"], t["edits"], t["quotes"], t["words"], t["at_edge"],
                t.get("function_words", "-")))
    out += ["", "## Quote length in words, by band and kind", ""]
    for x in summary["lengths"]:
        out.append("- %s, %s: %d quotes, mean %.1f words" % (x["band"], x["kind"], x["quotes"],
                                                             x["mean_words"]))
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
    with open(args.requests, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    essays = qf.select_essays(qf.load_rows(qf.find_csv(args.data_dir)), args.per_band, args.seed)
    texts = {e["id"]: e["text"] for e in essays}
    missing = sorted({r["essay"] for r in records} - set(texts))
    if missing:
        sys.exit("%d essays in the requests are not in the selection, e.g. %s" % (len(missing),
                                                                                 missing[0]))
    summary = summarize(quote_edits(records, texts, known), records)
    summary["meta"] = {"requests": len(records), "per_band": args.per_band, "seed": args.seed,
                       "spell_checker": known is not None, "margin": MARGIN, "close": CLOSE,
                       "data_license": "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus)",
                       "finished": datetime.datetime.now(datetime.timezone.utc).strftime(
                           "%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "edit_types.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "edit_types.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(summary))
    print(json.dumps({k: summary[k] for k in ("quotes", "altered", "placed",
                                              "similarity_mismatches")}), file=sys.stderr)


if __name__ == "__main__":
    main()
