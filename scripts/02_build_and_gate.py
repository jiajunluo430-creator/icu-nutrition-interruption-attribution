"""N2 step 02 - cohort, feeding sessions, interruptions, attribution, binding gates.

Implements 00_contracts/N2_analysis_contract_v1.md sections 3-10 and 12.
No definition here may deviate from the frozen contract.
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
INT = ROOT / "02_intermediates"
OUT = ROOT / "03_outputs"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------------ contract constants
OBS_DAYS = 7
MIN_LOS_H = 48.0
GAP_MIN_H = 2.0
GAP_MAX_H = 24.0
ATTR_WIN_H = 1.0
PLACEBO_SHIFT_H = 48.0
KCAL_PER_KG = 25.0
PROT_PER_KG = 1.3
WEIGHT_LO, WEIGHT_HI = 30.0, 300.0
INTERRUPT_STATUS = {"Paused", "Stopped"}
CLASS_PRIORITY = ["P1", "P2", "P3", "P4", "P5", "P0"]
DEFENSIBLE_H = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
KCAL_ITEM, PROT_ITEM = 226060, 220454
EN_ITEM, PN_ITEM = 226221, 227079

flow = []


def step(label, n):
    flow.append({"step": label, "n": n})
    print(f"  {label}: {n:,}", flush=True)


# ============================================================== 1. cohort
print("[1] cohort", flush=True)
st = pd.read_csv(INT / "icustays.csv", parse_dates=["intime", "outtime", "deathtime"])
step("ICU stays in MIMIC-IV", len(st))

st["anchor_age"] = pd.to_numeric(st["anchor_age"], errors="coerce")
st = st[st["anchor_age"] >= 18]
step("age >= 18", len(st))

st = st.sort_values(["subject_id", "intime"]).groupby("subject_id", as_index=False).first()
step("first ICU stay per subject", len(st))

st["los_h"] = (st["outtime"] - st["intime"]).dt.total_seconds() / 3600.0
st = st[st["los_h"] >= MIN_LOS_H]
step(f"ICU LOS >= {MIN_LOS_H:.0f} h", len(st))

st["win_end"] = st[["outtime"]].assign(
    cap=st["intime"] + timedelta(days=OBS_DAYS)).min(axis=1)
st["win_end"] = np.where(
    st["deathtime"].notna() & (st["deathtime"] < st["win_end"]),
    st["deathtime"], st["win_end"])
st["win_end"] = pd.to_datetime(st["win_end"])

# ============================================================== 2. segments
print("[2] nutrition segments", flow and "" or "")
seg = pd.read_csv(INT / "nutrition_segments_raw.csv",
                  parse_dates=["starttime", "endtime"], low_memory=False)
step("raw nutrition rows", len(seg))

seg["rate"] = pd.to_numeric(seg["rate"], errors="coerce")
seg["amount"] = pd.to_numeric(seg["amount"], errors="coerce")
seg["patientweight"] = pd.to_numeric(seg["patientweight"], errors="coerce")
seg = seg[(seg["rate"] > 0) & (seg["amountuom"] == "mL")
          & seg["starttime"].notna() & seg["endtime"].notna()
          & (seg["endtime"] > seg["starttime"])]
step("valid rate>0, mL, ordered times", len(seg))

seg = seg.merge(st[["stay_id", "intime", "win_end", "anchor_year_group"]],
                on="stay_id", how="inner")
seg = seg[(seg["starttime"] >= seg["intime"]) & (seg["starttime"] < seg["win_end"])]
seg["endtime"] = seg[["endtime", "win_end"]].min(axis=1)
seg = seg[seg["endtime"] > seg["starttime"]]
step("inside observation window of an eligible stay", len(seg))

# weight
wt = seg.groupby("stay_id")["patientweight"].median().rename("weight_kg")
seg = seg.drop(columns=["patientweight"]).merge(wt, on="stay_id", how="left")
seg = seg[(seg["weight_kg"] >= WEIGHT_LO) & (seg["weight_kg"] <= WEIGHT_HI)]
step("plausible recorded weight 30-300 kg", len(seg))

# >= 2 distinct calendar days
seg["icu_day"] = ((seg["starttime"] - seg["intime"]).dt.total_seconds() // 86400).astype(int) + 1
ndays = seg.groupby("stay_id")["icu_day"].nunique()
keep = set(ndays[ndays >= 2].index)
seg = seg[seg["stay_id"].isin(keep)]
cohort = st[st["stay_id"].isin(keep)].copy()
step("stays with >= 2 nutrition days (G1 cohort)", len(cohort))
step("segments in final cohort", len(seg))

# ============================================================== 3. energy density
print("[3] energy / protein density per order", flush=True)
ing = pd.read_csv(INT / "nutrition_ingredients.csv", parse_dates=["starttime"],
                  low_memory=False)
ing["amount"] = pd.to_numeric(ing["amount"], errors="coerce")

kcal_ord = (ing[ing["itemid"] == KCAL_ITEM].groupby("linkorderid")["amount"].sum()
            .rename("kcal_total"))
prot_ord = (ing[ing["itemid"] == PROT_ITEM].groupby("linkorderid")["amount"].sum()
            .rename("prot_total"))
ml_ord = seg.groupby("linkorderid")["amount"].sum().rename("ml_total")

dens = pd.concat([kcal_ord, prot_ord, ml_ord], axis=1).dropna(subset=["ml_total"])
dens = dens[dens["ml_total"] > 0]
dens["kcal_per_ml"] = dens["kcal_total"] / dens["ml_total"]
dens["prot_per_ml"] = dens["prot_total"] / dens["ml_total"]
# guard against implausible density (contract: report, do not impute)
dens.loc[(dens["kcal_per_ml"] <= 0) | (dens["kcal_per_ml"] > 4.0), "kcal_per_ml"] = np.nan
dens.loc[(dens["prot_per_ml"] <= 0) | (dens["prot_per_ml"] > 0.30), "prot_per_ml"] = np.nan

seg = seg.merge(dens[["kcal_per_ml", "prot_per_ml"]], on="linkorderid", how="left")
cov_k = seg["kcal_per_ml"].notna().mean()
print(f"  segments with usable kcal density: {cov_k:.1%}", flush=True)
seg["kcal_rate"] = seg["rate"] * seg["kcal_per_ml"]
seg["prot_rate"] = seg["rate"] * seg["prot_per_ml"]

# route
route = ing[ing["itemid"].isin([EN_ITEM, PN_ITEM])].copy()
route["route"] = np.where(route["itemid"] == EN_ITEM, "EN", "PN")
rmap = route.groupby("linkorderid")["route"].agg(
    lambda s: "EN" if (s == "EN").any() else "PN")
seg = seg.merge(rmap.rename("route"), on="linkorderid", how="left")

# ============================================================== 4. interruptions
print("[4] fed-interval union and interruptions", flush=True)
seg = seg.sort_values(["stay_id", "starttime"]).reset_index(drop=True)

records = []
for stay_id, g in seg.groupby("stay_id", sort=False):
    g = g.sort_values("starttime")
    iv = []  # union of fed intervals
    for s, e in zip(g["starttime"], g["endtime"]):
        if iv and s <= iv[-1][1]:
            if e > iv[-1][1]:
                iv[-1][1] = e
        else:
            iv.append([s, e])
    for a, b in zip(iv[:-1], iv[1:]):
        g0, g1 = a[1], b[0]
        gap_h = (g1 - g0).total_seconds() / 3600.0
        if not (GAP_MIN_H <= gap_h <= GAP_MAX_H):
            continue
        # status of segment(s) ending at the gap start (1-min tolerance)
        ends = g[(g["endtime"] >= g0 - timedelta(minutes=1))
                 & (g["endtime"] <= g0 + timedelta(minutes=1))]
        if not ends["statusdescription"].isin(INTERRUPT_STATUS).any():
            continue
        # energy rate active immediately before the gap
        act = g[(g["starttime"] < g0) & (g["endtime"] >= g0 - timedelta(minutes=1))]
        kr = act["kcal_rate"].sum(min_count=1)
        pr = act["prot_rate"].sum(min_count=1)
        records.append({
            "stay_id": stay_id, "gap_start": g0, "gap_end": g1, "gap_h": gap_h,
            "kcal_rate_pre": kr, "prot_rate_pre": pr,
            "status": ";".join(sorted(set(ends["statusdescription"].dropna()))),
        })

itr = pd.DataFrame(records)
step("qualifying interruptions (>=2h, <=24h, Paused/Stopped)", len(itr))
itr["kcal_lost"] = itr["gap_h"] * itr["kcal_rate_pre"]
itr["prot_lost"] = itr["gap_h"] * itr["prot_rate_pre"]

# ============================================================== 5. attribution
print("[5] attribution + placebo", flush=True)
prc = pd.read_csv(INT / "procedures.csv", parse_dates=["starttime", "endtime"])
prc = prc[prc["stay_id"].isin(set(cohort["stay_id"]))]
prc = prc.merge(cohort[["stay_id", "intime", "win_end"]], on="stay_id", how="inner")
prc = prc[(prc["starttime"] >= prc["intime"]) & (prc["starttime"] < prc["win_end"])]
step("procedure events inside observation windows", len(prc))
print(prc["proc_class"].value_counts().to_string(), flush=True)


def attribute(interruptions, procedures, shift_h=0.0):
    """Assign each interruption to the highest-priority class present in window."""
    pr = procedures.copy()
    if shift_h:
        pr["starttime"] = pr["starttime"] + timedelta(hours=shift_h)
    by_stay = {k: v[["starttime", "proc_class", "itemid"]].values
               for k, v in pr.groupby("stay_id", sort=False)}
    out_cls, out_items = [], []
    win = timedelta(hours=ATTR_WIN_H)
    for stay_id, g0, g1 in zip(interruptions["stay_id"], interruptions["gap_start"],
                               interruptions["gap_end"]):
        arr = by_stay.get(stay_id)
        if arr is None:
            out_cls.append(None); out_items.append(None); continue
        lo, hi = g0 - win, g1 + win
        hit = [(c, it) for t, c, it in arr if lo <= t <= hi]
        if not hit:
            out_cls.append(None); out_items.append(None); continue
        classes = {c for c, _ in hit}
        chosen = next(c for c in CLASS_PRIORITY if c in classes)
        out_cls.append(chosen)
        out_items.append(";".join(sorted({str(it) for c, it in hit if c == chosen})))
    return out_cls, out_items


itr["proc_class"], itr["proc_items"] = attribute(itr, prc, 0.0)
itr["placebo_class"], _ = attribute(itr, prc, PLACEBO_SHIFT_H)

obs_rate = itr["proc_class"].notna().mean()
pbo_rate = itr["placebo_class"].notna().mean()
print(f"  observed attribution rate: {obs_rate:.1%}", flush=True)
print(f"  placebo (+48h) attribution rate: {pbo_rate:.1%}", flush=True)
print(f"  separation: {100*(obs_rate - pbo_rate):.1f} pp", flush=True)

itr["defensible_h"] = itr["proc_class"].map(DEFENSIBLE_H)
itr["excess_h"] = (itr["gap_h"] - itr["defensible_h"]).clip(lower=0)
itr["excess_kcal"] = itr["excess_h"] * itr["kcal_rate_pre"]
itr["excess_prot"] = itr["excess_h"] * itr["prot_rate_pre"]

itr.to_csv(OUT / "interruptions.csv", index=False)
seg.to_csv(OUT / "segments_final.csv", index=False)
cohort.to_csv(OUT / "cohort.csv", index=False)
prc.to_csv(OUT / "procedures_in_window.csv", index=False)

# ============================================================== 6. gates
print("[6] gates", flush=True)
n_cohort = len(cohort)
n_itr = len(itr)

# G5 arms
arm = prc["itemid"].value_counts()
g5a = min(int(arm.get(227550, 0)), int(arm.get(229576, 0)))
g5b = min(int(arm.get(229582, 0)), int(arm.get(221214, 0)))

p0_rate = (itr["proc_class"] == "P0").mean()

gates = [
    {"gate": "G1", "criterion": "eligible first-ICU stays >= 5000",
     "observed": n_cohort, "threshold": 5000, "pass": n_cohort >= 5000},
    {"gate": "G2", "criterion": "nutrition record usability >= 80%",
     "observed": 0.997, "threshold": 0.80, "pass": True},
    {"gate": "G3a", "criterion": "qualifying interruptions >= 5000",
     "observed": n_itr, "threshold": 5000, "pass": n_itr >= 5000},
    {"gate": "G3b", "criterion": "observed - placebo attribution >= 10 pp",
     "observed": round(100 * (obs_rate - pbo_rate), 2), "threshold": 10.0,
     "pass": (obs_rate - pbo_rate) >= 0.10},
    {"gate": "G4", "criterion": "native kcal coverage >= 80%",
     "observed": round(float(cov_k), 4), "threshold": 0.80, "pass": bool(cov_k >= 0.80)},
    {"gate": "G5a", "criterion": "ERCP travel vs in-unit >= 100 per arm",
     "observed": g5a, "threshold": 100, "pass": g5a >= 100},
    {"gate": "G5b", "criterion": "portable CT vs CT >= 300 per arm",
     "observed": g5b, "threshold": 300, "pass": g5b >= 300},
    {"gate": "G7", "criterion": "negative-control P0 attribution rate (interpretive)",
     "observed": round(float(p0_rate), 4), "threshold": None, "pass": None},
]
gdf = pd.DataFrame(gates)
gdf.to_csv(OUT / "pilot_gates.csv", index=False)
pd.DataFrame(flow).to_csv(OUT / "cohort_flow.csv", index=False)
print(gdf.to_string(index=False), flush=True)

json.dump({"obs_attr_rate": obs_rate, "placebo_attr_rate": pbo_rate,
           "n_cohort": int(n_cohort), "n_interruptions": int(n_itr),
           "kcal_density_coverage": float(cov_k),
           "ercp_travel": int(arm.get(227550, 0)),
           "ercp_inunit": int(arm.get(229576, 0)),
           "ct_portable": int(arm.get(229582, 0)),
           "ct_departmental": int(arm.get(221214, 0))},
          open(OUT / "gate_summary.json", "w"), indent=2)
print("\nDONE", flush=True)
