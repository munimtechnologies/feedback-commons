"""v5 essay selection: the preregistered essays for the quote-fidelity-v5 study.

v5 (research/PREREG-v5.md) repeats v4's confirmatory passage-level test on a
fresh, non-overlapping essay sample with a larger compute budget. This module
fixes that sample before any v5 feedback is generated:

  1. regenerate v2's, v3's and v4's selections with v4_select.select_v4 (which
     itself regenerates v2 and v3) and check them against the committed
     v3/essays.json (v2's excluded essays and v3's essays) and v4/essays.json
     (v4's essays);
  2. drop all of those essays, plus the 22 essays v2 finished;
  3. from what is left, draw 60 per band with select_essays and the declared
     seed "v5-select-20261023" (same bands, word limits and alternating
     low/high order as v2, v3 and v4).

The command writes essays.json in v4's format: essay IDs and bands in
processing order, the excluded IDs for each earlier study, the eligible pool
sizes and the SHA-256 of the ELLIPSE file it read. It never writes essay
text. The cells rebuild the essays, text included, with
v3_run.py run --essays v5/essays.json.

Standard library only. By MV2 of Munim, Inc. Apache-2.0.
"""

import argparse
import datetime
import json
import os
import sys

import quote_fidelity as qf
import v3_select as v3s
import v4_select as v4s

V5_PER_BAND, V5_SEED = 60, "v5-select-20261023"


def select_v5(rows, per_band=V5_PER_BAND, seed=V5_SEED,
              v4_per_band=v4s.V4_PER_BAND, v4_seed=v4s.V4_SEED,
              v3_per_band=v3s.V3_PER_BAND, v3_seed=v3s.V3_SEED,
              v2_per_band=v3s.V2_PER_BAND, v2_seed=v3s.V2_SEED):
    """(v2's, v3's, v4's and v5's essays, and eligible counts per band before and after dropping v2+v3+v4)."""
    v2, v3, v4, _ = v4s.select_v4(rows, v4_per_band, v4_seed, v3_per_band, v3_seed, v2_per_band, v2_seed)
    excluded = {e["id"] for e in v2 + v3 + v4} | set(v3s.V2_DONE)
    rest = [r for r in rows if r["text_id_kaggle"] not in excluded]
    eligible = {"before_exclusion": v3s.bands(qf.select_essays(rows, v3s.ALL, seed)),
                "after_exclusion": v3s.bands(qf.select_essays(rest, v3s.ALL, seed))}
    return v2, v3, v4, qf.select_essays(rest, per_band, seed), eligible


def check_earlier(v2, v3, v4, v3_committed, v4_committed):
    """What differs between the regenerated v2/v3/v4 selections and the committed essays.json files, or None."""
    problem = v4s.check_earlier(v2, v3, v3_committed)
    if problem:
        return problem
    if [e["id"] for e in v4] != [e["id"] for e in v4_committed.get("essays", [])]:
        return "v4's selection did not regenerate: it differs from the essays in v4/essays.json"
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data-dir", required=True)
    p.add_argument("--v3-essays", default="v3/essays.json", help="the committed v3/essays.json")
    p.add_argument("--v4-essays", default="v4/essays.json", help="the committed v4/essays.json")
    p.add_argument("--out", required=True, help="where to write essays.json")
    args = p.parse_args(argv)

    path = qf.find_csv(args.data_dir)
    rows = qf.load_rows(path)
    digest = v3s.sha256(path)
    with open(args.v3_essays, encoding="utf-8") as f:
        v3_committed = json.load(f)
    with open(args.v4_essays, encoding="utf-8") as f:
        v4_committed = json.load(f)
    for name, committed in (("v3", v3_committed), ("v4", v4_committed)):
        if committed.get("data_sha256") != digest:
            sys.exit("the ELLIPSE file's SHA-256 is %s, not %s as %s/essays.json records"
                     % (digest, committed.get("data_sha256"), name))
    v2, v3, v4, v5, eligible = select_v5(rows)
    problem = check_earlier(v2, v3, v4, v3_committed, v4_committed)
    if problem:
        sys.exit(problem)
    excluded = {e["id"] for e in v2 + v3 + v4} | set(v3s.V2_DONE)
    v5_ids = [e["id"] for e in v5]
    if excluded & set(v5_ids):
        sys.exit("a v5 essay is one v2, v3 or v4 used")
    if [e["id"] for e in select_v5(list(reversed(rows)))[3]] != v5_ids:
        sys.exit("v5's selection depends on the order of the rows")
    out = {"study": "quote-fidelity-v5",
           "rule": "ELLIPSE training essays of 150-450 words; low band Conventions <= 2.5, high "
                   "band >= 4.0; all %d essays v2 selected, all %d essays v3 selected and all %d "
                   "essays v4 selected excluded (all regenerated and checked against v3/essays.json "
                   "and v4/essays.json); %d per band drawn with select_essays and seed %r, "
                   "alternating low/high."
                   % (len(v2), len(v3), len(v4), V5_PER_BAND, V5_SEED),
           "seed": V5_SEED,
           "data": qf.ELLIPSE_URL, "data_sha256": digest, "data_rows": len(rows),
           "data_license": "CC BY-NC-SA 4.0 (Crossley et al., ELLIPSE corpus); IDs and bands only",
           "v2_excluded": [e["id"] for e in v2], "v3_excluded": [e["id"] for e in v3],
           "v4_excluded": [e["id"] for e in v4],
           "earlier_regenerated": True,
           "eligible_before_exclusion": eligible["before_exclusion"],
           "eligible_after_exclusion": eligible["after_exclusion"], "selected": v3s.bands(v5),
           "short_bands": sorted(b for b in ("low", "high")
                                 if eligible["after_exclusion"].get(b, 0) < V5_PER_BAND),
           "essays": [{"id": e["id"], "band": e["band"]} for e in v5],
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
