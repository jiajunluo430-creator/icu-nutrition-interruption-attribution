"""N2 step 17 - revision sensitivities (reviewer points 4, 5, 6)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260804)
ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"

CLASSES = ["P1", "P2", "P3", "P4", "P5", "P0"]
DEFENSIBLE = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W, DAY, N_CC = 3600, 86400, 200

seg = pd.read_csv(OUT / "segments_final.csv", parse_dates=["starttime", "endtime"])
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
rev = json.load(open(OUT / "rev_results.json"))
TOT = rev["shortfall_total_kcal"]
out = {}

# route of each interruption: route of the segment ending at gap start
seg["route"] = seg["route"].fillna("unknown")
route_by_stay = seg.groupby("stay_id")["route"].agg(
    lambda s: "EN" if set(s.dropna()) <= {"EN", "unknown"} else
              ("PN" if set(s.dropna()) <= {"PN", "unknown"} else "mixed"))
itr = itr.merge(route_by_stay.rename("stay_route"), on="stay_id", how="left")
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")
print("[R4] route composition of stays")
print(route_by_stay.value_counts().to_string())
out["stay_route_counts"] = route_by_stay.value_counts().to_dict()
out["interruption_route_counts"] = itr["stay_route"].value_counts().to_dict()

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
t0 = itr["intime"].values.astype("datetime64[s]").astype(np.int64)
t1 = itr["win_end"].values.astype("datetime64[s]").astype(np.int64)
stays, krate = itr["stay_id"].values, itr["kcal_rate_pre"].fillna(0).values
hour = itr["gap_start"].dt.hour.values
route = itr["stay_route"].values

pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values

valid_k = []
for i in range(len(g0)):
    ks = [k for k in range(-6, 7) if k != 0
          and g0[i] + k * DAY >= t0[i] and g1[i] + k * DAY <= t1[i]]
    valid_k.append(np.array(ks) if ks else np.array([0]))


def excess(a, b, defensible, order=CLASSES, mask=None):
    pri = {c: i for i, c in enumerate(order)}
    tot = 0.0
    for i in range(len(a)):
        if mask is not None and not mask[i]:
            continue
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        j0 = np.searchsorted(arr, a[i] - ATTR_W)
        j1 = np.searchsorted(arr, b[i] + ATTR_W, "right")
        if j1 <= j0:
            continue
        best = min(pcls[stays[i]][j0:j1], key=lambda c: pri[c])
        if best == "P0":
            continue      # negative control is a diagnostic, not part of the target burden
        tot += max(0.0, (b[i] - a[i]) / 3600.0 - defensible[best]) * krate[i]
    return tot


def corrected(defensible=DEFENSIBLE, order=CLASSES, mask=None, reps=N_CC):
    o = excess(g0, g1, defensible, order, mask)
    n = []
    for _ in range(reps):
        k = np.array([v[rng.integers(len(v))] for v in valid_k]) * DAY
        n.append(excess(g0 + k, g1 + k, defensible, order, mask))
    return o, float(np.mean(n)), o - float(np.mean(n))


rows = []


def add(name, o, n, e, note=""):
    rows.append({"analysis": name, "observed_kcal": round(o), "null_kcal": round(n),
                 "chance_corrected_kcal": round(e),
                 "pct_of_shortfall": round(100 * e / TOT, 3),
                 "kcal_per_stay": round(e / len(coh), 1), "note": note})
    print(f"  {name:44s} excess {e:>9,.0f}  ({100*e/TOT:5.3f}%)")


print("\n[base]")
add("Primary (all routes, 6 h defensible)", *corrected())

print("\n[R4] EN-only / route stratification")
for r in ("EN", "mixed"):
    m = route == r
    if m.sum() >= 100:
        add(f"Route = {r} only (n={int(m.sum())} interruptions)", *corrected(mask=m))

print("\n[R6] defensible fasting window on the ENERGY scale")
for w in (0.0, 2.0, 4.0, 6.0, 8.0):
    d = {"P1": w, "P2": w, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
    add(f"Defensible window for P1/P2 = {w:.0f} h", *corrected(defensible=d))

print("\n[R6] midnight charting-artefact exclusion")
m = (hour != 0)
add(f"Excluding onsets at 00:00 (n={int(m.sum())})", *corrected(mask=m))
m2 = ~np.isin(hour, [23, 0, 1])
add(f"Excluding onsets 23:00-01:00 (n={int(m2.sum())})", *corrected(mask=m2))

print("\n[R6] alternative class-priority rules")
for nm, order in [("transport-first (P3>P1>P2>P4>P5>P0)", ["P3", "P1", "P2", "P4", "P5", "P0"]),
                  ("negative-control-first (P0 wins ties)", ["P0", "P1", "P2", "P3", "P4", "P5"])]:
    add(f"Priority: {nm}", *corrected(order=order))

print("\n[R5] reference target sensitivity (share of shortfall)")
base_o, base_n, base_e = corrected()
for kk in (20.0, 25.0, 30.0):
    part = pd.read_csv(OUT / "rev_time_partition.csv")
    tgt = part["wkg"] * kk / 24.0
    tot_k = ((tgt * part["obs_h"]) - part["kcal_del"]).clip(lower=0).sum()
    rows.append({"analysis": f"Reference target {kk:.0f} kcal/kg/day",
                 "observed_kcal": round(base_o), "null_kcal": round(base_n),
                 "chance_corrected_kcal": round(base_e),
                 "pct_of_shortfall": round(100 * base_e / tot_k, 3),
                 "kcal_per_stay": round(base_e / len(coh), 1),
                 "note": f"total shortfall {tot_k/1e6:.1f} M kcal"})
    print(f"  target {kk:.0f} kcal/kg -> shortfall {tot_k/1e6:5.1f} M kcal, "
          f"procedural share {100*base_e/tot_k:.3f}%")

df = pd.DataFrame(rows)
df.to_csv(OUT / "rev2_sensitivity.csv", index=False)
out["sensitivity_rows"] = len(df)
out["range_pct_of_shortfall"] = [float(df["pct_of_shortfall"].min()),
                                 float(df["pct_of_shortfall"].max())]
json.dump(out, open(OUT / "rev_sensitivity.json", "w"), indent=2)
print(f"\nchance-corrected share across ALL sensitivities: "
      f"{df['pct_of_shortfall'].min():.3f}% to {df['pct_of_shortfall'].max():.3f}%")
print("DONE")
