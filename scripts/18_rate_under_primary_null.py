"""N2 step 18 - attribution RATE under the same primary null as the energy estimand.

Reviewer point 2: the effect size and the significance test must not rest on two
different null models. Everything is now referred to the within-stay case-crossover
null (whole-ICU-day relocation, clock hour preserved).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260805)
ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
CLASSES = ["P1", "P2", "P3", "P4", "P5", "P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
ATTR_W, DAY, N_CC, N_BOOT = 3600, 86400, 1000, 1000

itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
t0 = itr["intime"].values.astype("datetime64[s]").astype(np.int64)
t1 = itr["win_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
N = len(g0)

pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values

valid_k = []
for i in range(N):
    ks = [k for k in range(-6, 7) if k != 0
          and g0[i] + k * DAY >= t0[i] and g1[i] + k * DAY <= t1[i]]
    valid_k.append(np.array(ks) if ks else np.array([0]))


def hits(a, b):
    """any-class hit and per-class hit indicators."""
    anyh = np.zeros(N, dtype=bool)
    per = {c: np.zeros(N, dtype=bool) for c in CLASSES}
    for i in range(N):
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        j0 = np.searchsorted(arr, a[i] - ATTR_W)
        j1 = np.searchsorted(arr, b[i] + ATTR_W, "right")
        if j1 <= j0:
            continue
        anyh[i] = True
        for c in set(pcls[stays[i]][j0:j1]):
            per[c][i] = True
    return anyh, per


obs_any, obs_per = hits(g0, g1)
print(f"observed any-class attribution: {obs_any.mean():.3%}", flush=True)

null_any = np.zeros(N)
null_per = {c: np.zeros(N) for c in CLASSES}
null_any_rate = np.empty(N_CC)
for b in range(N_CC):
    k = np.array([v[rng.integers(len(v))] for v in valid_k]) * DAY
    a_, p_ = hits(g0 + k, g1 + k)
    null_any += a_
    null_any_rate[b] = a_.mean()
    for c in CLASSES:
        null_per[c] += p_[c]
    if (b + 1) % 250 == 0:
        print(f"  replicate {b+1}/{N_CC}", flush=True)
null_any /= N_CC
for c in CLASSES:
    null_per[c] /= N_CC

obs_rate, null_rate = obs_any.mean(), null_any.mean()
print(f"case-crossover null attribution: {null_rate:.3%}")
print(f"excess: {100*(obs_rate-null_rate):.2f} pp")

# permutation p-value from 1000 replicates
p_emp = (np.sum(null_any_rate >= obs_rate) + 1) / (N_CC + 1)
print(f"empirical p (1000 replicates): {p_emp:.4f}")

uniq = np.unique(stays)
idx = {s: np.where(stays == s)[0] for s in uniq}


def boot(o, n):
    d = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx[s] for s in pick])
        d[b] = o[ii].mean() - n[ii].mean()
    return np.percentile(d, [2.5, 97.5])


rows = []
lo, hi = boot(obs_any.astype(float), null_any)
rows.append({"class": "ANY", "label": "Any prespecified class",
             "observed_pct": round(100 * obs_rate, 1),
             "null_pct": round(100 * null_rate, 1),
             "excess_pp": round(100 * (obs_rate - null_rate), 1),
             "excess_ci": f"{100*lo:.1f} to {100*hi:.1f}",
             "significant": not (lo < 0 < hi)})
for c in CLASSES:
    o, n = obs_per[c].astype(float), null_per[c]
    lo, hi = boot(o, n)
    rows.append({"class": c, "label": LABEL[c],
                 "observed_pct": round(100 * o.mean(), 1),
                 "null_pct": round(100 * n.mean(), 1),
                 "excess_pp": round(100 * (o.mean() - n.mean()), 1),
                 "excess_ci": f"{100*lo:.1f} to {100*hi:.1f}",
                 "significant": not (lo < 0 < hi)})
df = pd.DataFrame(rows)
print(df.to_string(index=False))
df.to_csv(OUT / "rev_table_rate_ci.csv", index=False)

json.dump({"obs_rate_pct": round(100 * obs_rate, 1),
           "null_rate_pct": round(100 * null_rate, 1),
           "excess_pp": round(100 * (obs_rate - null_rate), 1),
           "excess_ci_pp": [round(100 * lo, 1), round(100 * hi, 1)],
           "empirical_p": float(p_emp),
           "n_replicates": N_CC,
           "null_rate_range_pct": [round(100 * null_any_rate.min(), 1),
                                   round(100 * null_any_rate.max(), 1)]},
          open(OUT / "rev_rate.json", "w"), indent=2)
pd.DataFrame({"replicate": range(1, N_CC + 1),
              "null_attr_pct": 100 * null_any_rate}).to_csv(
    OUT / "rev_null_distribution.csv", index=False)
print("DONE")
