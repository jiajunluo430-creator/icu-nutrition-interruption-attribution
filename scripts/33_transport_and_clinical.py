"""N2 step 33 - temporal transport, patient-level burden, and post-procedure recovery.

Everything here is computed from the SAME canonical assignment arrays written by
script 27 (obs_assigned_primary.npy, null_assigned_primary.npy), so no result can drift
from the canonical primary. Nothing re-seeds an RNG.

Three analyses:
  A. Temporal transport across the four MIMIC-IV anchor-year eras (non-overlapping
     patients, different practice eras) - a within-database independent-cohort check.
  B. Patient-level distribution of the chance-corrected burden - is the 16.7 kcal/stay
     mean hiding a concentrated minority?
  C. Time from procedure to resumption of feeding, by class - which processes are
     actually slow to restart.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
CANON = OUT / "canonical"

TARGET = ["P1", "P2", "P3", "P4", "P5"]
ALL = TARGET + ["P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
DEF6 = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
C2I = {c: i for i, c in enumerate(ALL)}
NONE = -1
ATTR_W = 3600

OBS = np.load(CANON / "obs_assigned_primary.npy")
NULLC = np.load(CANON / "null_assigned_primary.npy")
N_CC, N = NULLC.shape
DRAWS = np.load(OUT / "locked_referent_draws.npy")
KEEP = np.array([DRAWS[:, i].any() for i in range(N)])

itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime"])
part = pd.read_csv(OUT / "rev_time_partition.csv")
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
CANJ = json.load(open(CANON / "canonical_primary.json"))

gaph = itr["gap_h"].values
krate = itr["kcal_rate_pre"].fillna(0).values
stays = itr["stay_id"].values


def energy_of(assigned):
    e = np.zeros(N)
    for c in TARGET:
        m = assigned == C2I[c]
        e[m] = np.maximum(0.0, gaph[m] - DEF6[c]) * krate[m]
    return e


obs_e = energy_of(OBS)
null_e = np.zeros(N)
for b in range(N_CC):
    null_e += energy_of(NULLC[b])
null_e /= N_CC
exc_e = obs_e - null_e

# sanity: must reproduce the canonical primary exactly
assert abs(exc_e[KEEP].sum() - CANJ["target_excess_kcal"]) < 2, \
    (exc_e[KEEP].sum(), CANJ["target_excess_kcal"])
print(f"ASSERT OK: reproduces canonical primary ({exc_e[KEEP].sum():,.0f} kcal)\n")

obs_hit = (OBS != NONE)
null_hit = np.zeros(N)
for b in range(N_CC):
    null_hit += (NULLC[b] != NONE)
null_hit /= N_CC

era_of = coh.set_index("stay_id")["anchor_year_group"]
unit_of = coh.set_index("stay_id")["first_careunit"]
itr_era = pd.Series(stays).map(era_of).values
part_era = part["stay_id"].map(era_of)

# ------------------------------------------------------- A. temporal transport
print("[A] temporal transport across anchor-year eras")
rows = []
for era in sorted(pd.unique(era_of.dropna())):
    m = KEEP & (itr_era == era)
    if m.sum() < 50:
        continue
    era_stays = coh.loc[coh["anchor_year_group"] == era, "stay_id"]
    tot = float(part.loc[part_era == era, "deficit_total"].sum())
    rows.append({
        "era": era, "stays": int(len(era_stays)), "interruptions": int(m.sum()),
        "rate_observed_pct": round(100 * obs_hit[m].mean(), 1),
        "rate_background_pct": round(100 * null_hit[m].mean(), 1),
        "rate_excess_pp": round(100 * (obs_hit[m].mean() - null_hit[m].mean()), 1),
        "energy_excess_kcal": round(exc_e[m].sum()),
        "shortfall_kcal": round(tot),
        "pct_of_shortfall": round(100 * exc_e[m].sum() / tot, 3),
        "kcal_per_stay": round(exc_e[m].sum() / len(era_stays), 1),
    })
era_df = pd.DataFrame(rows)
era_df.to_csv(CANON / "canonical_temporal_transport.csv", index=False)
print(era_df.to_string(index=False))
sp = era_df["pct_of_shortfall"]
print(f"\n  across eras: {sp.min():.3f}% to {sp.max():.3f}% "
      f"(canonical pooled {CANJ['target_pct']}%)")
print(f"  excess pp  : {era_df['rate_excess_pp'].min()} to {era_df['rate_excess_pp'].max()} "
      f"(pooled {CANJ['rate']['excess_pp']})")

# ------------------------------------------------- B. patient-level burden
print("\n[B] patient-level distribution of chance-corrected burden")
per_stay = pd.Series(exc_e[KEEP]).groupby(pd.Series(stays[KEEP])).sum()
allst = pd.Series(0.0, index=coh["stay_id"])
allst.loc[per_stay.index] = per_stay.values
v = allst.values
v_sorted = np.sort(v)[::-1]
top10_sum = float(v_sorted[:max(1, len(v) // 10)].sum())
# A chance-corrected per-stay value can be negative (the stay's observed assignment
# carries less energy than its own null average). The net cohort total is therefore much
# smaller than the positive tail, and "top decile share of the net total" exceeds 100%
# and is meaningless. Concentration is reported against the GROSS POSITIVE burden, with
# the net stated alongside so the two are never confused.
pos, neg = v[v > 0], v[v < 0]
gross_pos = float(pos.sum())
burden = {
    "n_stays": int(len(v)),
    "net_total_kcal": round(float(v.sum())),
    "gross_positive_kcal": round(gross_pos),
    "gross_negative_kcal": round(float(neg.sum())),
    "mean_kcal": round(float(v.mean()), 1),
    "median_kcal": round(float(np.median(v)), 1),
    "iqr": [round(float(np.percentile(v, 25)), 1), round(float(np.percentile(v, 75)), 1)],
    "p90_kcal": round(float(np.percentile(v, 90)), 1),
    "p95_kcal": round(float(np.percentile(v, 95)), 1),
    "p99_kcal": round(float(np.percentile(v, 99)), 1),
    "max_kcal": round(float(v.max()), 1),
    "pct_stays_exactly_zero": round(100 * float((v == 0).mean()), 1),
    "pct_stays_negative": round(100 * float((v < 0).mean()), 1),
    "pct_stays_positive": round(100 * float((v > 0).mean()), 1),
    "pct_stays_over_100": round(100 * float((v > 100).mean()), 1),
    "pct_stays_over_250": round(100 * float((v > 250).mean()), 1),
    "pct_stays_over_500": round(100 * float((v > 500).mean()), 1),
    "top10pct_kcal": round(top10_sum),
    "top10pct_share_of_gross_positive": round(100 * top10_sum / gross_pos, 1),
    "top10pct_over_net_total": round(top10_sum / float(v.sum()), 1),
}
for k, x in burden.items():
    print(f"   {k:<32} {x}")

unit_rows = []
for u, g in allst.groupby(allst.index.map(unit_of)):
    if len(g) >= 100:
        unit_rows.append({"care_unit": u, "stays": int(len(g)),
                          "mean_kcal_per_stay": round(float(g.mean()), 1),
                          "p90_kcal": round(float(np.percentile(g.values, 90)), 1),
                          "pct_over_250": round(100 * float((g.values > 250).mean()), 1)})
unit_df = pd.DataFrame(unit_rows).sort_values("mean_kcal_per_stay", ascending=False)
unit_df.to_csv(CANON / "canonical_burden_by_unit.csv", index=False)
print("\n  by care unit:")
print(unit_df.to_string(index=False))

# ------------------------------------------- C. post-procedure recovery delay
print("\n[C] time from procedure to resumption of feeding")
pmap, pcls = {}, {}
for k, g in prc.groupby("stay_id", sort=False):
    o = g.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values
g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)

rec = {c: [] for c in ALL}
for i in range(N):
    if not KEEP[i] or OBS[i] == NONE:
        continue
    c = ALL[OBS[i]]
    arr = pmap.get(stays[i])
    if arr is None:
        continue
    j0 = np.searchsorted(arr, g0[i] - ATTR_W)
    j1 = np.searchsorted(arr, g1[i] + ATTR_W, "right")
    cs, ts = pcls[stays[i]][j0:j1], arr[j0:j1]
    sel = ts[cs == c]
    if len(sel):
        rec[c].append((g1[i] - sel[0]) / 3600.0)   # first matching procedure -> resumption

rrows = []
for c in ALL:
    a = np.array([x for x in rec[c] if x > 0])
    if len(a) < 30:
        continue
    rrows.append({
        "class": c, "label": LABEL[c], "n": int(len(a)),
        "median_h_to_resumption": round(float(np.median(a)), 1),
        "iqr": f"{np.percentile(a,25):.1f}-{np.percentile(a,75):.1f}",
        "pct_resumed_within_2h": round(100 * float((a <= 2).mean()), 1),
        "pct_resumed_within_4h": round(100 * float((a <= 4).mean()), 1),
        "pct_resumed_within_6h": round(100 * float((a <= 6).mean()), 1),
        "pct_beyond_defensible": round(100 * float((a > DEF6[c]).mean()), 1)
        if DEF6[c] > 0 else "",
    })
rec_df = pd.DataFrame(rrows)
rec_df.to_csv(CANON / "canonical_recovery_delay.csv", index=False)
print(rec_df.to_string(index=False))

json.dump({"temporal_transport": rows, "burden_distribution": burden,
           "recovery_delay": rrows},
          open(CANON / "canonical_transport_clinical.json", "w"), indent=2)
print("\nwrote canonical_temporal_transport.csv, canonical_burden_by_unit.csv, "
      "canonical_recovery_delay.csv")
