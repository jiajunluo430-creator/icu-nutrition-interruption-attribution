"""N2 step 26 - per-class attribution-rate CIs from the SAME locked referent draws.

Figure 3B needs real bootstrap intervals on the rate scale. These are computed from
`locked_referent_draws.npy` so that the rate CIs, the energy CIs and the point
estimates all come from one draw set.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
CLASSES = ["P1", "P2", "P3", "P4", "P5", "P0"]
ATTR_W, DAY, N_BOOT = 3600, 86400, 1000

DRAWS = np.load(OUT / "locked_referent_draws.npy")
N_CC, N = DRAWS.shape
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values
keep = DRAWS.any(axis=0) | (DRAWS[0] != 0)
keep = np.array([DRAWS[:, i].any() for i in range(N)])


def hits(shift_row):
    r = {c: np.zeros(N, dtype=bool) for c in CLASSES}
    for i in range(N):
        if not keep[i]:
            continue
        sh = shift_row[i] * DAY
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        j0 = np.searchsorted(arr, g0[i] + sh - ATTR_W)
        j1 = np.searchsorted(arr, g1[i] + sh + ATTR_W, "right")
        for c in set(pcls[stays[i]][j0:j1]):
            r[c][i] = True
    return r


print("observed…", flush=True)
obs = hits(np.zeros(N, dtype=np.int64))
print("null over locked draws…", flush=True)
null = {c: np.zeros(N) for c in CLASSES}
for b in range(N_CC):
    r = hits(DRAWS[b])
    for c in CLASSES:
        null[c] += r[c]
    if (b + 1) % 250 == 0:
        print(f"  {b+1}/{N_CC}", flush=True)
for c in CLASSES:
    null[c] /= N_CC

uniq = np.unique(stays[keep])
idx = {s: np.where((stays == s) & keep)[0] for s in uniq}
rng = np.random.default_rng(20260809)
tbl = pd.read_csv(OUT / "rev3_by_class.csv").set_index("class")
for c in CLASSES:
    d = obs[c].astype(float) - null[c]
    bs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx[s] for s in pick])
        bs[b] = d[ii].mean()
    lo, hi = np.percentile(bs, [2.5, 97.5])
    tbl.loc[c, "rate_excess_lo"] = round(100 * lo, 2)
    tbl.loc[c, "rate_excess_hi"] = round(100 * hi, 2)
    tbl.loc[c, "rate_null_excluded"] = bool(not (lo < 0 < hi))
    print(f"  {c}: {100*d[keep].mean():+.1f} pp (95% CI {100*lo:.1f} to {100*hi:.1f})"
          f"{'  *' if not (lo < 0 < hi) else ''}")
tbl.reset_index().to_csv(OUT / "rev3_by_class.csv", index=False)
print("\nrate CIs written into rev3_by_class.csv")
