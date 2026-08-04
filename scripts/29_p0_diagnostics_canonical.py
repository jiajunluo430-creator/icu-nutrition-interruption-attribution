"""N2 step 29 - regenerate the P0 diagnostics from the SAME locked draws.

The previous diagnostic table used a 200-replicate subsample and therefore reported
-55,269 kcal where the canonical class table reports -54,612. Recomputed here over all
locked replicates so there is one P0 value.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
CAN = OUT / "canonical"
ALL = ["P1", "P2", "P3", "P4", "P5", "P0"]
DEF6 = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W, DAY, SEED = 3600, 86400, 20260807
SWALLOW = {229380}

DRAWS = np.load(OUT / "locked_referent_draws.npy")
N_CC, N = DRAWS.shape
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
krate = itr["kcal_rate_pre"].fillna(0).values
gaph = itr["gap_h"].values
KEEP = np.array([DRAWS[:, i].any() for i in range(N)])
PRI = {c: i for i, c in enumerate(ALL)}

pmap, pcls, pitem = {}, {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values
    pitem[k] = o["itemid"].values


def p0_energy(shift_row, exclude=frozenset(), nonexclusive=False):
    e = np.zeros(N)
    for i in range(N):
        if not KEEP[i]:
            continue
        sh = int(shift_row[i]) * DAY
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        j0 = np.searchsorted(arr, g0[i] + sh - ATTR_W)
        j1 = np.searchsorted(arr, g1[i] + sh + ATTR_W, "right")
        if j1 <= j0:
            continue
        cs, its = pcls[stays[i]][j0:j1], pitem[stays[i]][j0:j1]
        if exclude:
            m = ~np.isin(its, list(exclude))
            cs = cs[m]
            if len(cs) == 0:
                continue
        hit = ("P0" in cs) if nonexclusive else (min(cs, key=lambda c: PRI[c]) == "P0")
        if hit:
            e[i] = max(0.0, gaph[i] - DEF6["P0"]) * krate[i]
    return e


uniq = np.unique(stays[KEEP])
idx = {s: np.where((stays == s) & KEEP)[0] for s in uniq}
rng = np.random.default_rng(SEED + 99)
PICKS = [np.concatenate([idx[s] for s in rng.choice(uniq, size=len(uniq), replace=True)])
         for _ in range(400)]

rows = []
for name, kw in [("P0 priority-assigned (as in the primary analysis)", {}),
                 ("P0 non-exclusive (any P0 in window)", {"nonexclusive": True}),
                 ("P0 excluding swallow screening", {"exclude": SWALLOW})]:
    o = p0_energy(np.zeros(N, dtype=np.int64), **kw)
    nl = np.zeros(N)
    for b in range(N_CC):
        nl += p0_energy(DRAWS[b], **kw)
    nl /= N_CC
    d = o - nl
    bs = np.array([d[ii].sum() for ii in PICKS])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    rows.append({"variant": name, "obs_kcal": round(o[KEEP].sum()),
                 "null_kcal": round(nl[KEEP].sum()), "excess_kcal": round(d[KEEP].sum()),
                 "ci": f"{lo:,.0f} to {hi:,.0f}", "null_excluded": not (lo < 0 < hi)})
    print(f"  {name:46s} {d[KEEP].sum():+9,.0f}  ({lo:,.0f} to {hi:,.0f})")
    if name.startswith("P0 priority"):
        strat = []
        for nm, m in [("gap 2-6 h", (gaph < 6) & KEEP),
                      ("gap 6-12 h", (gaph >= 6) & (gaph < 12) & KEEP),
                      ("gap 12-24 h", (gaph >= 12) & KEEP)]:
            strat.append({"stratum": nm, "n": int(m.sum()),
                          "P0_excess_kcal": round(d[m].sum())})
        pd.DataFrame(strat).to_csv(CAN / "canonical_p0_strata.csv", index=False)
        print("   strata:", {r["stratum"]: r["P0_excess_kcal"] for r in strat})

pd.DataFrame(rows).to_csv(CAN / "canonical_p0_diagnostics.csv", index=False)

cls = pd.read_csv(CAN / "canonical_class_results.csv").set_index("class")
canon_p0 = float(cls.loc["P0", "energy_excess_kcal"])
assert abs(rows[0]["excess_kcal"] - canon_p0) < 2, (rows[0]["excess_kcal"], canon_p0)
print(f"\nASSERT OK: diagnostic P0 == canonical class-table P0 ({canon_p0:,.0f})")
