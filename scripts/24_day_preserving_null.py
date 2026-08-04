"""N2 step 24 - secondary null preserving BOTH ICU day and clock hour.

The within-stay case-crossover preserves clock hour and patient identity but not day of
stay. This complementary null preserves ICU day and clock hour exactly, at the cost of
borrowing another patient's procedure timeline: for each interruption on ICU day d at
clock hour h, a donor stay is drawn whose observation window covers day d, and the
window is evaluated against the donor's procedures at the same ICU day and same clock
hour. Agreement between the two nulls is the reassurance the reviewer asked for.

Also reports procedure density by ICU day for each class, which is the structure that
motivated the concern.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
SEED, N_REP = 20260808, 500
TARGET = ["P1", "P2", "P3", "P4", "P5"]
ALL = TARGET + ["P0"]
DEFENSIBLE = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W, DAY = 3600, 86400

itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
part = pd.read_csv(OUT / "rev_time_partition.csv")
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")
TOT = float(part["deficit_total"].sum())

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
t0 = itr["intime"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
krate = itr["kcal_rate_pre"].fillna(0).values
gaph = itr["gap_h"].values
dur = g1 - g0
off = g0 - t0                       # offset from ICU admission
icu_day = (off // DAY).astype(int)
N = len(g0)

S0 = {r.stay_id: int(pd.Timestamp(r.intime).timestamp()) for r in coh.itertuples()}
S1 = {r.stay_id: int(pd.Timestamp(r.win_end).timestamp()) for r in coh.itertuples()}
pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values
PRI = {c: i for i, c in enumerate(ALL)}

# ---------------------------------------------- procedure density by ICU day
print("[density] procedures per stay-day by ICU day and class", flush=True)
p2 = prc.copy()                       # procedures_in_window already carries intime
p2["intime"] = pd.to_datetime(p2["intime"])
p2["icu_day"] = ((p2["starttime"] - p2["intime"]).dt.total_seconds() // DAY).astype(int) + 1
p2 = p2[(p2["icu_day"] >= 1) & (p2["icu_day"] <= 7)]
atrisk = {}
for r in coh.itertuples():
    h = (pd.Timestamp(r.win_end) - pd.Timestamp(r.intime)).total_seconds() / DAY
    for d in range(1, 8):
        if h > d - 1:
            atrisk[d] = atrisk.get(d, 0) + 1
dens = (p2.groupby(["icu_day", "proc_class"]).size().unstack(fill_value=0))
dens = dens.div(pd.Series(atrisk), axis=0).round(3)
dens.to_csv(OUT / "rev3_procedure_density_by_day.csv")
print(dens.to_string())

# ---------------------------------------------- donor pools by ICU day
pool = {d: np.array([s for s in coh["stay_id"].values
                     if S1[s] - S0[s] >= (d + 1) * DAY])
        for d in range(0, 7)}
usable = np.array([len(pool.get(icu_day[i], [])) >= 20 for i in range(N)])
print(f"\ninterruptions with a donor pool >=20: {usable.sum():,} of {N:,} "
      f"({100*usable.mean():.1f}%)")


def evaluate(donor, start, i):
    arr = pmap.get(donor)
    if arr is None:
        return None
    a, b = start, start + dur[i]
    j0 = np.searchsorted(arr, a - ATTR_W)
    j1 = np.searchsorted(arr, b + ATTR_W, "right")
    if j1 <= j0:
        return None
    return min(pcls[donor][j0:j1], key=lambda c: PRI[c])


rng = np.random.default_rng(SEED)
null_e = np.zeros(N)
null_hit = np.zeros(N)
rate_rep = np.empty(N_REP)
for b in range(N_REP):
    hits = 0
    for i in range(N):
        if not usable[i]:
            continue
        p = pool[icu_day[i]]
        donor = p[rng.integers(len(p))]
        if donor == stays[i]:
            continue
        # same ICU day AND same clock hour/minute as the index window
        start = S0[donor] + off[i]
        if start + dur[i] > S1[donor]:
            continue
        c = evaluate(donor, start, i)
        if c is None:
            continue
        hits += 1
        null_hit[i] += 1
        if c in TARGET:
            null_e[i] += max(0.0, gaph[i] - DEFENSIBLE[c]) * krate[i]
    rate_rep[b] = hits / max(usable.sum(), 1)
    if (b + 1) % 125 == 0:
        print(f"  replicate {b+1}/{N_REP}", flush=True)
null_e /= N_REP
null_hit /= N_REP

# observed, restricted to the same usable set
obs_e = np.zeros(N)
obs_hit = np.zeros(N, dtype=bool)
for i in range(N):
    if not usable[i]:
        continue
    arr = pmap.get(stays[i])
    if arr is None:
        continue
    j0 = np.searchsorted(arr, g0[i] - ATTR_W)
    j1 = np.searchsorted(arr, g1[i] + ATTR_W, "right")
    if j1 <= j0:
        continue
    obs_hit[i] = True
    c = min(pcls[stays[i]][j0:j1], key=lambda x: PRI[x])
    if c in TARGET:
        obs_e[i] = max(0.0, gaph[i] - DEFENSIBLE[c]) * krate[i]

U = usable
E = (obs_e - null_e)[U].sum()
uniq = np.unique(stays[U])
idx = {s: np.where((stays == s) & U)[0] for s in uniq}
br = np.random.default_rng(SEED + 1)
bs = np.empty(600)
for b in range(600):
    pick = br.choice(uniq, size=len(uniq), replace=True)
    ii = np.concatenate([idx[s] for s in pick])
    bs[b] = (obs_e - null_e)[ii].sum()
lo, hi = np.percentile(bs, [2.5, 97.5])

out = {
    "null_type": "across-patient, ICU day and clock hour both preserved",
    "n_replicates": N_REP, "seed": SEED,
    "n_usable": int(U.sum()),
    "rate_observed_pct": round(100 * obs_hit[U].mean(), 1),
    "rate_null_pct": round(100 * null_hit[U].mean(), 1),
    "rate_excess_pp": round(100 * (obs_hit[U].mean() - null_hit[U].mean()), 1),
    "energy_excess_kcal": float(E),
    "energy_excess_ci": [float(lo), float(hi)],
    "pct_of_shortfall": round(100 * E / TOT, 3),
    "pct_ci": [round(100 * lo / TOT, 3), round(100 * hi / TOT, 3)],
}
json.dump(out, open(OUT / "rev3_day_preserving_null.json", "w"), indent=2)
print("\n=== DAY- AND CLOCK-PRESERVING NULL ===")
print(json.dumps(out, indent=2))
