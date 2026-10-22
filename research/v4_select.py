"""v4 essay selection: the preregistered essays for the quote-fidelity-v4 study.

v4 (research/PREREG-v4.md) asks, on new essays, whether a quote is
reproduced exactly less often when the student's passage behind it holds a
misspelling. This module fixes its sample before any v4 feedback is generated:

  1. regenerate v2's and v3's selections with v3_select.select_v3 and check
     them against the committed v3/essays.json (v2's 30 excluded essays and
     v3's 96 essays, in order) and against the 22 essays v2 finished;
  2. drop all of those essays (126);
  3. from what is left, draw 60 per band with select_essays and the declared
     seed "v4-select-20261022" (same bands, word limits and alternating
     low/high order as v2 and v3).

The command writes essays.json in v3's format: essay IDs and bands in
processing order, the excluded IDs, the eligible pool sizes and the SHA-256
of the ELLIPSE file it read. It never writes essay text. The cells rebuild
the essays, text included, with v3_run.py run --essays v4/essays.json.

Standard library only. By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import datetime
import json
import os
import sys

import quote_fidelity as qf
import v3_select as v3s

V4_PER_BAND, V4_SEED = 60, "v4-select-20261022"


def select_v4(rows, per_band=V4_PER_BAND, seed=V4_SEED, v3_per_band=v3s.V3_PER_BAND,
              v3_seed=v3s.V3_SEED, v2_per_band=v3s.V2_PER_BAND, v2_seed=v3s.V2_SEED):
    """(v2's essays, v3's essays, v4's essays, eligible counts per band before and after dropping v2's and v3's)."""
    v2, v3, _ = v3s.select_v3(rows, v3_per_band, v3_seed, v2_per_band, v2_seed)
    excluded = {e["id"] for e in v2 + v3} | set(v3s.V2_DONE)
    rest = [r for r in rows if r["text_id_kaggle"] not in excluded]
    eligible = {"before_exclusion": v3s.bands(qf.select_essays(rows, v3s.ALL, seed)),
                "after_exclusion": v3s.bands(qf.select_essays(rest, v3s.ALL, seed))}
    return v2, v3, qf.select_essays(rest, per_band, seed), eligible


def check_earlier(v2, v3, committed):
    """What differs between the regenerated v2 and v3 selections and the committed v3/essays.json, or None."""
    v2_ids, v3_ids = [e["id"] for e in v2], [e["id"] for e in v3]
    if v2_ids[:len(v3s.V2_DONE)] != list(v3s.V2_DONE):
        return "v2's selection did not regenerate: its first %d essays differ from the ones v2 finished" \
               % len(v3s.V2_DONE)
    if v2_ids != committed.get("v2_excluded"):
        return "v2's selection differs from v2_excluded in v3/essays.json"
    if v3_ids != [e["id"] for e in committed.get("essays", [])]:
        return "v3's selection did not regenerate: it differs from the essays in v3/essays.json"
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data-dir", required=True)
    p.add_argument("--v3-essays", default="v3/essays.json", help="the committed v3/essays.json")
    p.add_argument("--out", required=True, help="where to write essays.json")
    args = p.parse_args(argv)

    path = qf.find_csv(args.data_dir)
    rows = qf.load_rows(path)
    digest = v3s.sha256(path)
    with open(args.v3_essays, encoding="utf-8") as f:
        committed = json.load(f)
    if committed.get("data_sha256") != digest:
        sys.exit("the ELLIPSE file's SHA-256 is %s, not %s as v3/essays.json records"
                 % (digest, committed.get("data_sha256")))
    v2, v3, v4, eligible = select_v4(rows)
    problem = check_earlier(v2, v3, committed)
    if problem:
        sys.exit(problem)
    excluded = {e["id"] for e in v2 + v3} | set(v3s.V2_DONE)
    v4_ids = [e["id"] for e in v4]
    if excluded & set(v4_ids):
        sys.exit("a v4 essay is one v2 or v3 used")
    if [e["id"] for e in select_v4(list(reversed(rows)))[2]] != v4_ids:
        sys.exit("v4's selection depends on the order of the rows")
    out = {"study": "quote-fidelity-v4",
           "rule": "ELLIPSE training essays of 150-450 words; low band Conventions <= 2.5, high "
                   "band >= 4.0; all %d essays v2 selected and all %d essays v3 selected excluded "
                   "(both regenerated and checked against v3/essays.json); %d per band drawn with "
                   "select_essays and seed %r, alternating low/high."
                   % (len(v2), len(v3), V4_PER_BAND, V4_SEED),
           "seed": V4_SEED,
           "data": qf.ELLIPSE_URL, "data_sha256": digest, "data_rows": len(rows),
           "data_license": "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus); IDs and bands only",
           "v2_excluded": [e["id"] for e in v2], "v3_excluded": [e["id"] for e in v3],
           "earlier_regenerated": True,
           "eligible_before_exclusion": eligible["before_exclusion"],
           "eligible_after_exclusion": eligible["after_exclusion"], "selected": v3s.bands(v4),
           "short_bands": sorted(b for b in ("low", "high")
                                 if eligible["after_exclusion"].get(b, 0) < V4_PER_BAND),
           "essays": [{"id": e["id"], "band": e["band"]} for e in v4],
           "made": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    rebuilt = v3s.essays_from_selection(rows, out)
    print(json.dumps({"data_rows": len(rows), "excluded": len(excluded),
                      "eligible_before_exclusion": out["eligible_before_exclusion"],
                      "eligible_after_exclusion": out["eligible_after_exclusion"],
                      "selected": out["selected"], "short_bands": out["short_bands"],
                      "rebuilt": len(rebuilt)}), file=sys.stderr)


if __name__ == "__main__":
    main()
