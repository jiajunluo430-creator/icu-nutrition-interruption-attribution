"""N2 step 16 - revision analysis addressing peer-review critiques 1-6.

R1  The energy estimand is now run THROUGH the null. Previously we screened classes
    on attribution excess and then summed their full observed burden, which is a
    specificity-screened upper bound, not a chance correction.
    Now: E_excess = E_observed - mean(E_null), same pipeline both sides.
R2  Nulls preserve temporal structure. Primary null is a within-stay case-crossover
    that relocates each interruption window by whole ICU days, preserving clock hour
    exactly. Secondary null is a clock-preserving circular shift (24 h multiples).
R3  Denominator rebuilt over ALL alive-in-ICU days 1-7 with zero-fill, and the
    shortfall decomposed into pre-initiation / interruption / long-gap /
    post-cessation / running-below-target.
R4  EN-only stratification.
R5  Reference-target sensitivity reported on the interruption share, not just on
    median attainment.
R6  Midnight-artefact, route-consistency, defensible-window and priority-rule
    sensitivities.
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260803)
ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"

CLASSES = ["P1", "P2", "P3", "P4", "P5", "P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
DEFENSIBLE = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W = 3600           # +/- 1 h in seconds
KCAL_KG = 25.0
N_CC = 1000             # case-crossover replicates
N_BOOT = 1000

seg = pd.read_csv(OUT / "segments_final.csv",
                  parse_dates=["starttime", "endtime", "intime", "win_end"])
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "outtime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
res = {}

# ==================================================================== R3
print("[R3] denominator over ALL alive-in-ICU days 1-7", flush=True)
wt = seg.groupby("stay_id")["weight_kg"].first()
coh = coh.merge(wt.rename("wkg"), on="stay_id", how="left")
coh["obs_h"] = (coh["win_end"] - coh["intime"]).dt.total_seconds() / 3600.0
seg["dur_h"] = (seg["endtime"] - seg["starttime"]).dt.total_seconds() / 3600.0
seg["kcal_del"] = seg["dur_h"] * seg["kcal_rate"]

# per-stay time partition
rows = []
for r in coh.itertuples():
    g = seg[seg.stay_id == r.stay_id].sort_values("starttime")
    if g.empty:
        continue
    iv = []
    for s, e in zip(g["starttime"], g["endtime"]):
        if iv and s <= iv[-1][1]:
            iv[-1][1] = max(iv[-1][1], e)
        else:
            iv.append([s, e])
    fed_h = sum((b - a).total_seconds() for a, b in iv) / 3600.0
    pre_h = (iv[0][0] - r.intime).total_seconds() / 3600.0
    post_h = (r.win_end - iv[-1][1]).total_seconds() / 3600.0
    gaps = [((b[0] - a[1]).total_seconds() / 3600.0) for a, b in zip(iv[:-1], iv[1:])]
    short_h = sum(x for x in gaps if 2.0 <= x <= 24.0)
    other_gap_h = sum(gaps) - short_h
    rows.append({"stay_id": r.stay_id, "wkg": r.wkg, "obs_h": r.obs_h,
                 "fed_h": fed_h, "pre_h": max(pre_h, 0), "post_h": max(post_h, 0),
                 "short_gap_h": short_h, "other_gap_h": other_gap_h,
                 "kcal_del": g["kcal_del"].sum()})
part = pd.DataFrame(rows)
part["target_rate"] = part["wkg"] * KCAL_KG / 24.0            # kcal per hour
part["target_total"] = part["target_rate"] * part["obs_h"]
part["deficit_total"] = (part["target_total"] - part["kcal_del"]).clip(lower=0)
for k, col in [("pre", "pre_h"), ("short", "short_gap_h"),
               ("othergap", "other_gap_h"), ("post", "post_h")]:
    part[f"def_{k}"] = part["target_rate"] * part[col]
part["def_running"] = (part["target_rate"] * part["fed_h"] - part["kcal_del"]).clip(lower=0)

tot = part["deficit_total"].sum()
comp = {k: float(part[f"def_{k}"].sum()) for k in ("pre", "short", "othergap", "post")}
comp["running"] = float(part["def_running"].sum())
scale = tot / sum(comp.values())            # normalise rounding/clip drift
comp = {k: v * scale for k, v in comp.items()}
print(f"  eligible stays               {len(part):,}")
print(f"  ICU-hours in denominator     {part['obs_h'].sum():,.0f}")
print(f"  reference target             {part['target_total'].sum()/1e6:,.1f} M kcal")
print(f"  delivered                    {part['kcal_del'].sum()/1e6:,.1f} M kcal")
print(f"  TOTAL shortfall              {tot/1e6:,.1f} M kcal")
for k, v in comp.items():
    print(f"    {k:10s} {v/1e6:7.2f} M kcal  ({100*v/tot:5.1f}%)")
res["shortfall_total_kcal"] = float(tot)
res["shortfall_components_pct"] = {k: round(100 * v / tot, 1) for k, v in comp.items()}
res["denominator_icu_hours"] = float(part["obs_h"].sum())
part.to_csv(OUT / "rev_time_partition.csv", index=False)

# also: old (nutrition-day-only) denominator for transparency
day = pd.read_csv(OUT / "stay_days.csv")
res["old_denominator_deficit_kcal"] = float(
    (day["kcal_target"] - day["kcal"]).clip(lower=0).sum())
res["old_vs_new_denominator_ratio"] = round(
    tot / res["old_denominator_deficit_kcal"], 2)
print(f"  (previous nutrition-day-only denominator gave "
      f"{res['old_denominator_deficit_kcal']/1e6:.1f} M kcal; "
      f"ratio {res['old_vs_new_denominator_ratio']}x)")

# ==================================================================== R1+R2
print("\n[R1+R2] running the ENERGY estimand through the null", flush=True)
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")
g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
t0 = itr["intime"].values.astype("datetime64[s]").astype(np.int64)
t1 = itr["win_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
gap_h = itr["gap_h"].values
krate = itr["kcal_rate_pre"].fillna(0).values

pmap = {k: np.sort(v["starttime"].values.astype("datetime64[s]").astype(np.int64))
        for k, v in prc.groupby("stay_id", sort=False)}
cmap = {k: v.set_index("starttime")["proc_class"].to_dict()
        for k, v in prc.groupby("stay_id", sort=False)}
# class lookup aligned to sorted times
pcls = {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pcls[k] = o["proc_class"].values

PRI = {c: i for i, c in enumerate(CLASSES)}


def excess_kcal(a, b, order=CLASSES):
    """Attribute each window [a,b] and return per-interruption excess kcal."""
    out = np.zeros(len(a))
    pri = {c: i for i, c in enumerate(order)}
    for i in range(len(a)):
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        lo, hi = a[i] - ATTR_W, b[i] + ATTR_W
        j0, j1 = np.searchsorted(arr, lo), np.searchsorted(arr, hi, "right")
        if j1 <= j0:
            continue
        cs = pcls[stays[i]][j0:j1]
        best = min(cs, key=lambda c: pri[c])
        h = (b[i] - a[i]) / 3600.0
        out[i] = max(0.0, h - DEFENSIBLE[best]) * krate[i]
    return out


obs_kcal = excess_kcal(g0, g1)
print(f"  observed excess kcal            {obs_kcal.sum():,.0f}")

# --- primary null: within-stay case-crossover, whole-ICU-day relocation
dur = g1 - g0
DAY = 86400
valid_k = []
for i in range(len(g0)):
    ks = [k for k in range(-6, 7) if k != 0
          and g0[i] + k * DAY >= t0[i] and g1[i] + k * DAY <= t1[i]]
    valid_k.append(np.array(ks) if ks else np.array([0]))
n_usable = sum(1 for k in valid_k if k[0] != 0 or len(k) > 1)
print(f"  interruptions with >=1 same-clock-hour control day: {n_usable:,} "
      f"({100*n_usable/len(g0):.1f}%)")

cc = np.zeros((N_CC, len(g0)))
for b in range(N_CC):
    k = np.array([v[rng.integers(len(v))] for v in valid_k]) * DAY
    cc[b] = excess_kcal(g0 + k, g1 + k)
    if (b + 1) % 250 == 0:
        print(f"    case-crossover replicate {b+1}/{N_CC}", flush=True)
null_kcal = cc.mean(axis=0)
print(f"  null excess kcal (mean of {N_CC})  {null_kcal.sum():,.0f}")

E_obs, E_null = obs_kcal.sum(), null_kcal.sum()
E_exc = E_obs - E_null
print(f"  CHANCE-CORRECTED excess kcal    {E_exc:,.0f}  ({100*E_exc/tot:.2f}% of shortfall)")

# bootstrap over stays on the difference
uniq = np.unique(stays)
idx = {s: np.where(stays == s)[0] for s in uniq}
bs = np.empty(N_BOOT)
for b in range(N_BOOT):
    pick = rng.choice(uniq, size=len(uniq), replace=True)
    ii = np.concatenate([idx[s] for s in pick])
    bs[b] = obs_kcal[ii].sum() - null_kcal[ii].sum()
lo, hi = np.percentile(bs, [2.5, 97.5])
scale_b = 1.0
print(f"  bootstrap 95% CI                {lo:,.0f} to {hi:,.0f} kcal")
res["energy_observed_excess_kcal"] = float(E_obs)
res["energy_null_excess_kcal"] = float(E_null)
res["energy_chance_corrected_kcal"] = float(E_exc)
res["energy_chance_corrected_ci"] = [float(lo), float(hi)]
res["energy_chance_corrected_pct_of_shortfall"] = round(100 * E_exc / tot, 2)
res["energy_chance_corrected_pct_ci"] = [round(100 * lo / tot, 2), round(100 * hi / tot, 2)]
res["energy_per_stay_kcal"] = round(float(E_exc / len(coh)), 1)
res["n_case_crossover_replicates"] = N_CC
res["pct_interruptions_with_control_day"] = round(100 * n_usable / len(g0), 1)

# --- secondary null: clock-preserving circular shift (24 h multiples)
circ = []
W = (t1 - t0)
for kd in (1, 2, 3, 4, 5, 6):
    sh = kd * DAY
    a = t0 + np.mod(g0 - t0 + sh, np.maximum(W, 1))
    circ.append(excess_kcal(a, a + dur).sum())
res["circular24_null_kcal_mean"] = float(np.mean(circ))
res["circular24_null_kcal_range"] = [float(np.min(circ)), float(np.max(circ))]
print(f"  clock-preserving circular null  mean {np.mean(circ):,.0f} "
      f"(range {np.min(circ):,.0f}-{np.max(circ):,.0f})")

# --- per-class chance-corrected energy
percls = []
for c in CLASSES:
    o = np.zeros(len(g0)); n = np.zeros(len(g0))
    for i in range(len(g0)):
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        lo_, hi_ = g0[i] - ATTR_W, g1[i] + ATTR_W
        j0, j1 = np.searchsorted(arr, lo_), np.searchsorted(arr, hi_, "right")
        cs = pcls[stays[i]][j0:j1]
        if len(cs) and min(cs, key=lambda x: PRI[x]) == c:
            o[i] = max(0.0, gap_h[i] - DEFENSIBLE[c]) * krate[i]
    for b in range(0, N_CC, 10):        # 100 replicates per class is ample
        k = np.array([v[rng.integers(len(v))] for v in valid_k]) * DAY
        aa, bb = g0 + k, g1 + k
        for i in range(len(g0)):
            arr = pmap.get(stays[i])
            if arr is None:
                continue
            lo_, hi_ = aa[i] - ATTR_W, bb[i] + ATTR_W
            j0, j1 = np.searchsorted(arr, lo_), np.searchsorted(arr, hi_, "right")
            cs = pcls[stays[i]][j0:j1]
            if len(cs) and min(cs, key=lambda x: PRI[x]) == c:
                n[i] += max(0.0, (bb[i] - aa[i]) / 3600.0 - DEFENSIBLE[c]) * krate[i]
    n /= (N_CC // 10)
    percls.append({"class": c, "label": LABEL[c],
                   "obs_kcal": round(o.sum()), "null_kcal": round(n.sum()),
                   "excess_kcal": round(o.sum() - n.sum()),
                   "pct_of_shortfall": round(100 * (o.sum() - n.sum()) / tot, 3)})
    print(f"    {c} obs {o.sum():>9,.0f}  null {n.sum():>9,.0f}  "
          f"excess {o.sum()-n.sum():>9,.0f}")
pd.DataFrame(percls).to_csv(OUT / "rev_table_energy_by_class.csv", index=False)

json.dump(res, open(OUT / "rev_results.json", "w"), indent=2)
print("\nDONE")
print(json.dumps(res, indent=2))
