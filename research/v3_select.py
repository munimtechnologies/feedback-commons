"""v3 essay selection: the preregistered essays for the quote-fidelity-v3 study.

v3 asks v2's question again with about four times the essays and none of
v2's. This module fixes the sample before any v3 feedback is generated:

  1. regenerate v2's own selection (select_essays, 15 per band, seed 2026)
     and check it against the 22 essays v2 actually finished, in order;
  2. drop all 30 of v2's essays, finished or not;
  3. from what is left, draw 48 per band with select_essays and seed 2027
     (same bands, word limits and alternating order as v2).

The command writes essays.json: essay IDs and bands in processing order,
the eligible pool sizes, and the SHA-256 of the ELLIPSE file it read. It
never writes essay text. essays_from_selection() rebuilds the essays, text
included, from that file and the same CSV at run time.

Standard library only. By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import sys

import quote_fidelity as qf

V2_PER_BAND, V2_SEED = 15, 2026
V3_PER_BAND, V3_SEED = 48, 2027
ALL = 10 ** 9  # a per_band larger than any band: select_essays then returns every eligible essay
# The essays quote-fidelity-v2 finished before its time budget ran out, in processing order
# (from its requests.jsonl, job of 2026-10-14).
V2_DONE = ("2ACDFF7FCAAA", "D2421A895FFA", "7B557B2F27CE", "F610B3CBF3DF", "BB5B58E098AB",
           "C2DCF6EED519", "C01AC1CDDD65", "70E490A83717", "E2E3D86A8CF8", "02B36EBD5C66",
           "2379CD1725FE", "29BB45AA907C", "550D53DE2832", "374CF6E834A5", "D9FB5E411A4F",
           "85D3E5A1D64E", "DE8162CAC353", "33DEFCDAD05F", "CD506B5747F7", "C6DDD966C9FC",
           "9EB7D09C785B", "09ADB0629CD0")


def check_ids(rows):
    """Every row needs its own text_id_kaggle: filtering rows would otherwise shift select_essays' fallback IDs."""
    ids = [r.get("text_id_kaggle") for r in rows]
    if not all(ids):
        raise ValueError("%d rows have no text_id_kaggle" % sum(1 for i in ids if not i))
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dupes:
        raise ValueError("%d duplicate text_id_kaggle values, e.g. %s" % (len(dupes), dupes[0]))


def bands(essays):
    return dict(collections.Counter(e["band"] for e in essays))


def select_v3(rows, per_band=V3_PER_BAND, seed=V3_SEED, v2_per_band=V2_PER_BAND, v2_seed=V2_SEED):
    """(v2's essays, v3's essays, eligible counts per band after dropping v2's)."""
    check_ids(rows)
    v2 = qf.select_essays(rows, v2_per_band, v2_seed)
    excluded = {e["id"] for e in v2}
    rest = [r for r in rows if r["text_id_kaggle"] not in excluded]
    return v2, qf.select_essays(rest, per_band, seed), bands(qf.select_essays(rest, ALL, seed))


def essays_from_selection(rows, selection):
    """The selected essays, text included, in the selection's order, built exactly as select_essays builds them."""
    check_ids(rows)
    wanted = [(e["id"], e["band"]) for e in selection["essays"]]
    found = {e["id"]: e for e in qf.select_essays([r for r in rows if r["text_id_kaggle"] in
                                                   dict(wanted)], ALL, 0)}
    missing = [i for i, _ in wanted if i not in found]
    if missing:
        raise ValueError("%d selected essays are not eligible in this file, e.g. %s" % (len(missing),
                                                                                       missing[0]))
    moved = [i for i, b in wanted if found[i]["band"] != b]
    if moved:
        raise ValueError("%d selected essays changed band, e.g. %s" % (len(moved), moved[0]))
    return [found[i] for i, _ in wanted]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out", required=True, help="where to write essays.json")
    args = p.parse_args(argv)

    path = qf.find_csv(args.data_dir)
    rows = qf.load_rows(path)
    v2, v3, eligible = select_v3(rows)
    v2_ids = [e["id"] for e in v2]
    if v2_ids[:len(V2_DONE)] != list(V2_DONE):
        sys.exit("v2's selection did not regenerate: its first %d essays differ from the ones v2 "
                 "finished" % len(V2_DONE))
    out = {"study": "quote-fidelity-v3",
           "rule": "ELLIPSE training essays of 150-450 words; low band Conventions <= 2.5, high "
                   "band >= 4.0; all %d essays v2 selected (select_essays, %d per band, seed %d) "
                   "excluded; %d per band drawn with select_essays and seed %d, alternating "
                   "low/high." % (len(v2), V2_PER_BAND, V2_SEED, V3_PER_BAND, V3_SEED),
           "data": qf.ELLIPSE_URL, "data_sha256": sha256(path), "data_rows": len(rows),
           "data_license": "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus); IDs and bands only",
           "v2_excluded": v2_ids, "v2_regenerated": True,
           "eligible_after_exclusion": eligible, "selected": bands(v3),
           "short_bands": sorted(b for b in ("low", "high") if eligible.get(b, 0) < V3_PER_BAND),
           "essays": [{"id": e["id"], "band": e["band"]} for e in v3],
           "made": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    rebuilt = essays_from_selection(rows, out)
    print(json.dumps({"data_rows": len(rows), "eligible_after_exclusion": eligible,
                      "selected": out["selected"], "short_bands": out["short_bands"],
                      "rebuilt": len(rebuilt)}), file=sys.stderr)


if __name__ == "__main__":
    main()
