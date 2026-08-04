"""N2 step 04 - main analysis under the frozen contract.

G5 failed (see 03_outputs/exploratory_attempts.csv): the natural experiment is dropped.
Primary content is therefore:
  (A) nutrition delivery adequacy,
  (B) interruption burden,
  (C) chance-corrected procedure attribution (contract section 9 placebo test),
  (D) negative-control specificity,
  (E) excess fasting hours among genuinely attributable interruptions.
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"

KCAL_PER_KG, PROT_PER_KG = 25.0, 1.3
ATTR_WIN_H = 1.0
CLASS_PRIORITY = ["P1", "P2", "P3", "P4", "P5", "P0"]
CLASS_LABEL = {
    "P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
    "P4": "Bedside invasive", "P5": "Renal replacement",
    "P0": "Negative control (bedside diagnostics)",
}
DEFENSIBLE_H = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}

seg = pd.read_csv(OUT / "segments_final.csv", parse_dates=["starttime", "endtime", "intime", "win_end"])
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "outtime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime", "endtime"])
res = {}

# ===================================================== A. cohort description
print("[A] cohort", flush=True)
wt = seg.groupby("stay_id")["weight_kg"].first()
coh = coh.merge(wt.rename("weight_kg"), on="stay_id", how="left")
coh["obs_h"] = (coh["win_end"] - coh["intime"]).dt.total_seconds() / 3600.0

t1 = {
    "N (first ICU stays)": len(coh),
    "Age, median (IQR)": f"{coh.anchor_age.median():.0f} ({coh.anchor_age.quantile(.25):.0f}-{coh.anchor_age.quantile(.75):.0f})",
    "Female, n (%)": f"{(coh.gender=='F').sum():,} ({100*(coh.gender=='F').mean():.1f})",
    "Weight kg, median (IQR)": f"{coh.weight_kg.median():.1f} ({coh.weight_kg.quantile(.25):.1f}-{coh.weight_kg.quantile(.75):.1f})",
    "ICU LOS h, median (IQR)": f"{coh.los_h.median():.1f} ({coh.los_h.quantile(.25):.1f}-{coh.los_h.quantile(.75):.1f})",
    "Observation window h, median (IQR)": f"{coh.obs_h.median():.1f} ({coh.obs_h.quantile(.25):.1f}-{coh.obs_h.quantile(.75):.1f})",
    "In-hospital death, n (%)": f"{coh.hospital_expire_flag.sum():,.0f} ({100*coh.hospital_expire_flag.mean():.1f})",
}
for k, v in t1.items():
    print(f"  {k}: {v}")
pd.Series(t1).to_frame("value").to_csv(OUT / "table1_cohort.csv")

# ===================================================== B. delivery adequacy
print("\n[B] delivery adequacy by ICU day", flush=True)
seg["dur_h"] = (seg["endtime"] - seg["starttime"]).dt.total_seconds() / 3600.0
seg["kcal_delivered"] = seg["dur_h"] * seg["kcal_rate"]
seg["prot_delivered"] = seg["dur_h"] * seg["prot_rate"]

day = (seg.groupby(["stay_id", "icu_day"])
       .agg(kcal=("kcal_delivered", "sum"), prot=("prot_delivered", "sum"),
            fed_h=("dur_h", "sum"), weight_kg=("weight_kg", "first"))
       .reset_index())
day = day[(day["icu_day"] >= 1) & (day["icu_day"] <= 7)]
day["kcal_target"] = day["weight_kg"] * KCAL_PER_KG
day["prot_target"] = day["weight_kg"] * PROT_PER_KG
day["kcal_pct"] = 100 * day["kcal"] / day["kcal_target"]
day["prot_pct"] = 100 * day["prot"] / day["prot_target"]
day["kcal_per_kg"] = day["kcal"] / day["weight_kg"]

adq = (day.groupby("icu_day")
       .agg(n_stay_days=("stay_id", "size"),
            kcal_per_kg_median=("kcal_per_kg", "median"),
            kcal_pct_median=("kcal_pct", "median"),
            kcal_pct_q1=("kcal_pct", lambda s: s.quantile(.25)),
            kcal_pct_q3=("kcal_pct", lambda s: s.quantile(.75)),
            prot_pct_median=("prot_pct", "median"),
            fed_h_median=("fed_h", "median"),
            pct_days_ge80=("kcal_pct", lambda s: 100 * (s >= 80).mean()),
            pct_days_ge100=("kcal_pct", lambda s: 100 * (s >= 100).mean()))
       .round(1).reset_index())
print(adq.to_string(index=False))
adq.to_csv(OUT / "table2_delivery_adequacy.csv", index=False)
day.to_csv(OUT / "stay_days.csv", index=False)
res["overall_kcal_pct_median"] = float(day["kcal_pct"].median())
res["overall_prot_pct_median"] = float(day["prot_pct"].median())
res["pct_stay_days_ge80_target"] = float(100 * (day["kcal_pct"] >= 80).mean())

# ===================================================== C. interruption burden
print("\n[C] interruption burden", flush=True)
per_stay = itr.groupby("stay_id").agg(n=("gap_h", "size"), hours=("gap_h", "sum"),
                                      kcal=("kcal_lost", "sum")).reset_index()
tot_fed_h = seg.groupby("stay_id")["dur_h"].sum().rename("fed_h")
per_stay = per_stay.merge(tot_fed_h, on="stay_id", how="left")
burden = {
    "stays with >=1 qualifying interruption, n (%)":
        f"{len(per_stay):,} ({100*len(per_stay)/len(coh):.1f})",
    "qualifying interruptions, total": f"{len(itr):,}",
    "interruptions per affected stay, median (IQR)":
        f"{per_stay.n.median():.0f} ({per_stay.n.quantile(.25):.0f}-{per_stay.n.quantile(.75):.0f})",
    "interruption hours per affected stay, median (IQR)":
        f"{per_stay.hours.median():.1f} ({per_stay.hours.quantile(.25):.1f}-{per_stay.hours.quantile(.75):.1f})",
    "single interruption duration h, median (IQR)":
        f"{itr.gap_h.median():.1f} ({itr.gap_h.quantile(.25):.1f}-{itr.gap_h.quantile(.75):.1f})",
    "energy lost per interruption kcal, median (IQR)":
        f"{itr.kcal_lost.median():.0f} ({itr.kcal_lost.quantile(.25):.0f}-{itr.kcal_lost.quantile(.75):.0f})",
    "interruption h per 100 feeding h, median":
        f"{(100*per_stay.hours/per_stay.fed_h).median():.1f}",
}
for k, v in burden.items():
    print(f"  {k}: {v}")
pd.Series(burden).to_frame("value").to_csv(OUT / "table3_interruption_burden.csv")

# ============================== D. chance-corrected attribution (contract sec 9)
print("\n[D] chance-corrected attribution by class", flush=True)
by_stay = {k: v[["starttime", "proc_class"]].values
           for k, v in prc.groupby("stay_id", sort=False)}
win = timedelta(hours=ATTR_WIN_H)


def class_hits(shift_h):
    """Unconditional per-class hit indicator for every interruption."""
    hits = {c: np.zeros(len(itr), dtype=bool) for c in CLASS_PRIORITY}
    sh = timedelta(hours=shift_h)
    for i, (sid, g0, g1) in enumerate(zip(itr["stay_id"], itr["gap_start"], itr["gap_end"])):
        arr = by_stay.get(sid)
        if arr is None:
            continue
        lo, hi = g0 - win, g1 + win
        for t, c in arr:
            if lo <= t + sh <= hi:
                hits[c][i] = True
    return hits


obs = class_hits(0.0)
SHIFTS = [48.0, 24.0, 72.0, -48.0]
pbo_runs = {s: class_hits(s) for s in SHIFTS}

rows = []
for c in CLASS_PRIORITY:
    o = obs[c].mean()
    p_primary = pbo_runs[48.0][c].mean()
    p_all = [pbo_runs[s][c].mean() for s in SHIFTS]
    excess = o - p_primary
    rows.append({
        "class": c, "label": CLASS_LABEL[c],
        "n_procedure_events": int((prc["proc_class"] == c).sum()),
        "observed_pct": round(100 * o, 1),
        "placebo48_pct": round(100 * p_primary, 1),
        "placebo_mean_pct": round(100 * float(np.mean(p_all)), 1),
        "placebo_range_pct": f"{100*min(p_all):.1f}-{100*max(p_all):.1f}",
        "excess_pp": round(100 * excess, 1),
        "specificity_ratio": round(excess / o, 3) if o > 0 else np.nan,
    })
attr = pd.DataFrame(rows)
print(attr.to_string(index=False))
attr.to_csv(OUT / "table4_attribution_specificity.csv", index=False)

any_obs = np.any([obs[c] for c in CLASS_PRIORITY], axis=0).mean()
any_pbo = np.any([pbo_runs[48.0][c] for c in CLASS_PRIORITY], axis=0).mean()
res["any_class_observed_pct"] = round(100 * float(any_obs), 1)
res["any_class_placebo48_pct"] = round(100 * float(any_pbo), 1)
res["chance_corrected_attributable_pct"] = round(100 * float(any_obs - any_pbo), 1)
res["fraction_of_apparent_attribution_that_is_chance"] = round(
    float(any_pbo / any_obs), 3)
print(f"\n  any-class observed: {100*any_obs:.1f}%")
print(f"  any-class placebo(+48h): {100*any_pbo:.1f}%")
print(f"  chance-corrected attributable: {100*(any_obs-any_pbo):.1f} pp")
print(f"  share of apparent attribution that is chance: {100*any_pbo/any_obs:.1f}%")

# ===================================================== E. excess fasting hours
print("\n[E] excess fasting hours among attributed interruptions", flush=True)
att = itr[itr["proc_class"].notna()].copy()
ex = (att.groupby("proc_class")
      .agg(n=("gap_h", "size"), gap_median=("gap_h", "median"),
           excess_median=("excess_h", "median"), excess_total=("excess_h", "sum"),
           kcal_lost_median=("kcal_lost", "median"),
           excess_kcal_total=("excess_kcal", "sum"))
      .round(1).reset_index())
ex["label"] = ex["proc_class"].map(CLASS_LABEL)
ex["defensible_h"] = ex["proc_class"].map(DEFENSIBLE_H)
print(ex.to_string(index=False))
ex.to_csv(OUT / "table5_excess_fasting.csv", index=False)

# ===================================================== F. sensitivity
print("\n[F] sensitivity", flush=True)
sens = []
for tgt in (20.0, 25.0, 30.0):
    v = 100 * day["kcal"] / (day["weight_kg"] * tgt)
    sens.append({"analysis": f"energy target {tgt:.0f} kcal/kg",
                 "metric": "median % of target", "value": round(float(v.median()), 1)})
for w in (0.5, 1.0, 2.0):
    win = timedelta(hours=w)
    hit = np.zeros(len(itr), dtype=bool)
    for i, (sid, g0, g1) in enumerate(zip(itr["stay_id"], itr["gap_start"], itr["gap_end"])):
        arr = by_stay.get(sid)
        if arr is None:
            continue
        lo, hi = g0 - win, g1 + win
        hit[i] = any(lo <= t <= hi for t, _ in arr)
    hitp = np.zeros(len(itr), dtype=bool)
    sh = timedelta(hours=48)
    for i, (sid, g0, g1) in enumerate(zip(itr["stay_id"], itr["gap_start"], itr["gap_end"])):
        arr = by_stay.get(sid)
        if arr is None:
            continue
        lo, hi = g0 - win, g1 + win
        hitp[i] = any(lo <= t + sh <= hi for t, _ in arr)
    sens.append({"analysis": f"attribution window +/-{w}h",
                 "metric": "chance-corrected attributable pp",
                 "value": round(100 * float(hit.mean() - hitp.mean()), 1)})
sdf = pd.DataFrame(sens)
print(sdf.to_string(index=False))
sdf.to_csv(OUT / "table6_sensitivity.csv", index=False)

json.dump(res, open(OUT / "main_results.json", "w"), indent=2)
print("\nDONE")
print(json.dumps(res, indent=2))
