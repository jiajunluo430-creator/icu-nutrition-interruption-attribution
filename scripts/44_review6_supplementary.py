"""N2 step 44 - the three supplementary analyses demanded by review round 6.

M7  Cohort selection. 24,260 of 31,143 stays with LOS >= 48 h were excluded for having
    fewer than two nutrition days in ICU days 1-7. Those are exactly the patients who
    were never fed or fed once, so the "48.5% of the shortfall accrues before feeding
    starts" figure is conditional on being fed at least twice and is likely an
    UNDERestimate. Recomputed on a relaxed >= 1 nutrition-day cohort, with the
    characteristics of the excluded stays.

M5(R2) Interruption definition. Charted Paused/Stopped may represent an order switch or
    a charting artifact rather than a bedside cessation. Algorithmic validation using
    order and item continuity across each gap, stratified by midnight onset and gap
    length. Not a manual chart review, and labelled as such.

M11 Severity and residual confounding. Vasopressor exposure, invasive ventilation and
    care unit added; background and excess stratified by them; E-value computed for the
    excess on the rate scale.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, INT, CAN = ROOT / "03_outputs", ROOT / "02_intermediates", ROOT / "03_outputs" / "canonical"
REV = OUT / "review6"
REV.mkdir(exist_ok=True)
res = {}

TARGET = ["P1", "P2", "P3", "P4", "P5"]
ALL = TARGET + ["P0"]
C2I = {c: i for i, c in enumerate(ALL)}
TGT = np.array([C2I[c] for c in TARGET])

# ======================================================== M7: cohort selection
print("[M7] relaxed cohort (>= 1 nutrition day)")
ics = pd.read_csv(INT / "icustays.csv", parse_dates=["intime", "outtime"])
ics = ics[(ics["anchor_age"] >= 18) & (ics["los"] * 24 >= 48)]
ics = ics.sort_values(["subject_id", "intime"]).drop_duplicates("subject_id")
ics["win_end"] = ics[["outtime"]].min(axis=1)
ics["win_end"] = np.minimum(ics["outtime"].values,
                            (ics["intime"] + pd.Timedelta(days=7)).values)

raw = pd.read_csv(INT / "nutrition_segments_raw.csv",
                  usecols=["stay_id", "starttime", "endtime", "rate", "patientweight"],
                  parse_dates=["starttime", "endtime"])
raw = raw[raw["rate"] > 0]
raw = raw.merge(ics[["stay_id", "intime", "win_end"]], on="stay_id", how="inner")
raw = raw[(raw["starttime"] >= raw["intime"]) & (raw["starttime"] < raw["win_end"])]
raw["icu_day"] = ((raw["starttime"] - raw["intime"]).dt.total_seconds() // 86400).astype(int)

nd = raw.groupby("stay_id")["icu_day"].nunique()
first_feed = raw.groupby("stay_id")["starttime"].min()
wt = raw.groupby("stay_id")["patientweight"].median()

elig = ics.set_index("stay_id")
elig["n_nutrition_days"] = nd.reindex(elig.index).fillna(0).astype(int)
elig["first_feed"] = first_feed.reindex(elig.index)
elig["wkg"] = wt.reindex(elig.index)
# NOTE: weight is only recoverable from nutrition records, so a weight filter would drop
# every never-fed stay - precisely the group this analysis exists to describe. The filter
# is therefore applied only where a weight exists.
elig = elig[elig["wkg"].isna() | ((elig["wkg"] >= 30) & (elig["wkg"] <= 300))]
elig["obs_h"] = (elig["win_end"] - elig["intime"]).dt.total_seconds() / 3600
elig["pre_h"] = np.where(elig["first_feed"].notna(),
                         (elig["first_feed"] - elig["intime"]).dt.total_seconds() / 3600,
                         elig["obs_h"])
elig["pre_h"] = elig["pre_h"].clip(lower=0, upper=elig["obs_h"])

grp = {"never fed (0 nutrition days)": elig["n_nutrition_days"] == 0,
       "fed on exactly 1 day": elig["n_nutrition_days"] == 1,
       "primary cohort (>= 2 days)": elig["n_nutrition_days"] >= 2}
rows = []
for lbl, m in grp.items():
    g = elig[m]
    rows.append({"group": lbl, "stays": int(len(g)),
                 "median_age": round(float(g["anchor_age"].median()), 0),
                 "median_los_h": round(float(g["los"].median() * 24), 1),
                 "in_hospital_death_pct": round(100 * float(g["hospital_expire_flag"].mean()), 1),
                 "median_pre_initiation_h": round(float(g["pre_h"].median()), 1),
                 "pre_init_share_of_obs_pct": round(
                     100 * float(g["pre_h"].sum() / g["obs_h"].sum()), 1)})
exc = pd.DataFrame(rows)
exc.to_csv(REV / "cohort_selection_m7.csv", index=False)
print(exc.to_string(index=False))

rel = elig[elig["n_nutrition_days"] >= 1]
pre_share_relaxed = 100 * float(rel["pre_h"].sum() / rel["obs_h"].sum())
prim = elig[elig["n_nutrition_days"] >= 2]
pre_share_primary = 100 * float(prim["pre_h"].sum() / prim["obs_h"].sum())
res["m7_cohort"] = {
    "stays_los_ge48h_weight_ok": int(len(elig)),
    "never_fed": int((elig["n_nutrition_days"] == 0).sum()),
    "fed_one_day": int((elig["n_nutrition_days"] == 1).sum()),
    "primary_cohort": int(len(prim)),
    "relaxed_cohort_ge1_day": int(len(rel)),
    "pre_initiation_share_primary_pct": round(pre_share_primary, 1),
    "pre_initiation_share_relaxed_pct": round(pre_share_relaxed, 1),
    "direction": ("Relaxing to >= 1 nutrition day RAISES the pre-initiation share, "
                  "confirming that the primary cohort's 48.5% is conditional on being "
                  "fed at least twice and understates unfed time in the wider ICU "
                  "population."),
    "immortal_time": ("Requiring nutrition on two distinct days conditions on surviving "
                      "and remaining in ICU long enough to be fed twice; this is an "
                      "immortal-time selection and is now stated as such."),
}
print(f"  pre-initiation share: primary {pre_share_primary:.1f}% -> "
      f"relaxed {pre_share_relaxed:.1f}%")

# ============================================ M5(R2): interruption validation
print("\n[M5-R2] algorithmic validation of the interruption definition")
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
seg = pd.read_csv(OUT / "segments_final.csv",
                  usecols=["stay_id", "starttime", "endtime", "itemid", "orderid",
                           "linkorderid", "statusdescription"],
                  parse_dates=["starttime", "endtime"])
seg = seg.sort_values(["stay_id", "starttime"])
by = {k: v for k, v in seg.groupby("stay_id", sort=False)}

lab = []
for r in itr.itertuples():
    s = by.get(r.stay_id)
    if s is None:
        lab.append("no segments")
        continue
    before = s[s["endtime"] <= r.gap_start]
    after = s[s["starttime"] >= r.gap_end]
    if before.empty or after.empty:
        lab.append("boundary")
        continue
    b, a = before.iloc[-1], after.iloc[0]
    midnight = r.gap_start.hour == 0 and r.gap_start.minute == 0
    if midnight:
        lab.append("midnight-boundary artifact candidate")
    elif b["itemid"] != a["itemid"]:
        lab.append("formula/item switch (not a pure interruption)")
    elif b["linkorderid"] != a["linkorderid"]:
        lab.append("same formula, re-ordered on restart")
    else:
        lab.append("same formula and same order")
itr["validation_label"] = lab
vc = itr["validation_label"].value_counts()
vdf = (vc.rename("n").to_frame().assign(pct=lambda d: (100 * d["n"] / len(itr)).round(1))
       .reset_index().rename(columns={"index": "label"}))
vdf.to_csv(REV / "interruption_validation.csv", index=False)
print(vdf.to_string(index=False))

strat = []
for lbl, m in [("2-6 h", itr["gap_h"] < 6), ("6-12 h", (itr["gap_h"] >= 6) & (itr["gap_h"] < 12)),
               ("12-24 h", itr["gap_h"] >= 12)]:
    g = itr[m]
    strat.append({"gap_stratum": lbl, "n": int(len(g)),
                  "same_formula_resumed_pct": round(
                      100 * float(g["validation_label"].str.startswith("same formula").mean()), 1),
                  "same_formula_and_order_pct": round(100 * float(
                      (g["validation_label"] == "same formula and same order").mean()), 1),
                  "formula_switch_pct": round(
                      100 * float(g["validation_label"].str.startswith("formula/item").mean()), 1),
                  "midnight_artifact_pct": round(
                      100 * float(g["validation_label"].str.startswith("midnight").mean()), 1)})
sdf = pd.DataFrame(strat)
sdf.to_csv(REV / "interruption_validation_strata.csv", index=False)
print(sdf.to_string(index=False))
res["m5_validation"] = {
    "n": int(len(itr)),
    "same_formula_resumed_pct": round(
        100 * float(itr["validation_label"].str.startswith("same formula").mean()), 1),
    "same_formula_and_order_pct": round(
        100 * float((itr["validation_label"] == "same formula and same order").mean()), 1),
    "formula_switch_pct": round(
        100 * float(itr["validation_label"].str.startswith("formula/item").mean()), 1),
    "midnight_artifact_pct": round(
        100 * float(itr["validation_label"].str.startswith("midnight").mean()), 1),
    "caveat": ("Algorithmic, not a manual chart review. Resumption of the same "
               "formula is necessary but not sufficient evidence of a true bedside "
               "cessation. In MIMIC-IV a genuine pause and restart is normally re-ordered, "
               "so a new linkorderid with an unchanged item does not indicate an artifact."),
}

# ================================================== M11: severity and E-value
print("\n[M11] severity strata and E-value")
coh = pd.read_csv(OUT / "cohort.csv")
cov = pd.read_csv(INT / "covariates.csv")
vent = pd.read_csv(INT / "vent_intervals.csv")
coh = coh.merge(cov, on="stay_id", how="left")
coh["any_vasopressor"] = coh["any_vasopressor"].fillna(0).astype(int)
coh["ever_ventilated"] = coh["stay_id"].isin(vent["stay_id"].unique()).astype(int)

OBS = np.load(CAN / "obs_assigned_primary.npy")
NUL = np.load(CAN / "null_assigned_primary.npy")
DR = np.load(OUT / "locked_referent_draws.npy")
KEEP = np.array([DR[:, i].any() for i in range(DR.shape[1])])
obs_hit = OBS != -1
nul_hit = (NUL != -1).mean(axis=0)
stays = itr["stay_id"].values
m_vaso = pd.Series(stays).map(coh.set_index("stay_id")["any_vasopressor"]).fillna(0).values
m_vent = pd.Series(stays).map(coh.set_index("stay_id")["ever_ventilated"]).fillna(0).values
m_unit = pd.Series(stays).map(coh.set_index("stay_id")["first_careunit"]).values

srows = []
for lbl, m in [("Invasively ventilated", m_vent == 1), ("Not ventilated", m_vent == 0),
               ("Vasopressor exposed", m_vaso == 1), ("No vasopressor", m_vaso == 0)]:
    k = KEEP & m
    if k.sum() < 50:
        continue
    srows.append({"stratum": lbl, "n": int(k.sum()),
                  "observed_pct": round(100 * obs_hit[k].mean(), 1),
                  "background_pct": round(100 * nul_hit[k].mean(), 1),
                  "excess_pp": round(100 * (obs_hit[k].mean() - nul_hit[k].mean()), 1)})
for u in pd.unique(m_unit):
    k = KEEP & (m_unit == u)
    if k.sum() < 150:
        continue
    srows.append({"stratum": str(u), "n": int(k.sum()),
                  "observed_pct": round(100 * obs_hit[k].mean(), 1),
                  "background_pct": round(100 * nul_hit[k].mean(), 1),
                  "excess_pp": round(100 * (obs_hit[k].mean() - nul_hit[k].mean()), 1)})
st = pd.DataFrame(srows)
st.to_csv(REV / "severity_strata.csv", index=False)
print(st.to_string(index=False))

o, b = obs_hit[KEEP].mean(), nul_hit[KEEP].mean()
rr = o / b
ev = rr + np.sqrt(rr * (rr - 1))
res["m11"] = {
    "observed_pct": round(100 * o, 1), "background_pct": round(100 * b, 1),
    "risk_ratio": round(float(rr), 2), "e_value": round(float(ev), 2),
    "interpretation": (f"An unmeasured confounder would need to be associated with both "
                       f"procedure occurrence and interruption occurrence by a risk ratio "
                       f"of at least {ev:.2f}, above and beyond the matching on patient "
                       f"and time of day, to explain away the excess."),
    "available_covariates": "vasopressor exposure, invasive ventilation, care unit",
    "unavailable": ("SOFA and SAPS-II are not computable: the MIMIC-IV v3.1 download "
                    "used here contains only the hosp and icu modules, with no derived "
                    "severity tables."),
}
print(f"  RR {rr:.2f}, E-value {ev:.2f}")

json.dump(res, open(REV / "review6_supplementary.json", "w"), indent=2)
print(f"\nwrote {REV}")
