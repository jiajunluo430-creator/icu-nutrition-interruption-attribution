"""N2 step 31 - eICU background co-occurrence rate (external validation).

Governed by 00_contracts/N2_external_validation_contract_v1.md
SHA-256 ca02b0d6ef8fdec3b65e549cb7c8d6ead9b4d41cf0f14e93a8c1e2f49af44923, frozen before
this script was run.

Estimates the attribution rate that arises when NO interruption has occurred: reference
windows are placed independently of any nutrition event, so every window that catches a
procedure catches it by background co-occurrence alone.
"""
import csv
import gzip
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
ZIP = Path(r"D:\respiratory_icu_qdp\eicu-collaborative-research-database-2.0.zip")
PREFIX = "eicu-collaborative-research-database-2.0/"
Z = zipfile.ZipFile(ZIP)

SEED, K = 20260805, 5
ATTR_MIN = 60                 # +/-1 h attribution window, as in the parent contract
MAX_MIN = 7 * 1440            # days 1-7
MIN_LOS_MIN, RESTART_GAP = 2880, 240
rng = np.random.default_rng(SEED)


def stream(table):
    with Z.open(PREFIX + table + ".csv.gz") as fh:
        raw = io.BytesIO(fh.read())
    with gzip.GzipFile(fileobj=raw) as gz:
        r = csv.reader(io.TextIOWrapper(gz, encoding="utf-8", errors="replace"))
        hdr = next(r)
        for row in r:
            if len(row) == len(hdr):
                yield dict(zip(hdr, row))


def as_int(v):
    v = (v or "").strip()
    return int(v) if v.lstrip("-").isdigit() else None


# ------------------------------------------------- 1. MIMIC window distribution
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start"])
DRAWS = np.load(OUT / "locked_referent_draws.npy")
KEEP = np.array([DRAWS[:, i].any() for i in range(DRAWS.shape[1])])
GAP_H = itr["gap_h"].values[KEEP]
ONSET_HR = itr["gap_start"].dt.hour.values[KEEP]
print(f"[1/6] MIMIC window distribution: n={len(GAP_H):,}, "
      f"median gap {np.median(GAP_H):.1f} h, IQR {np.percentile(GAP_H,25):.1f}-"
      f"{np.percentile(GAP_H,75):.1f}")

# ------------------------------------------------- 2. eICU cohort
print("[2/6] eICU cohort ...")
los_of, hosp_of, admitmin_of = {}, {}, {}
for p in stream("patient"):
    age = p["age"].strip()
    age_n = 90 if age == "> 89" else (int(age) if age.isdigit() else None)
    los = as_int(p["unitdischargeoffset"])
    if age_n is None or age_n < 18 or los is None or los < MIN_LOS_MIN:
        continue
    if p["unitvisitnumber"].strip() != "1":
        continue
    t = p["unitadmittime24"].strip()
    if not re.match(r"^\d{2}:\d{2}", t):
        continue
    sid = p["patientunitstayid"]
    los_of[sid] = min(los, MAX_MIN)
    hosp_of[sid] = p["hospitalid"]
    admitmin_of[sid] = int(t[:2]) * 60 + int(t[3:5])   # clock time of unit admission
print(f"      {len(los_of):,} stays with a usable admit clock time")

# ------------------------------------------------- 3. harmonized events
print("[3/6] harmonized events (airway + sedation starts) ...")
ev = defaultdict(set)
for r in stream("respiratoryCare"):
    sid = r["patientunitstayid"]
    if sid in los_of:
        for k in ("ventstartoffset", "ventendoffset"):
            v = as_int(r[k])
            if v is not None and 0 < v <= los_of[sid]:
                ev[sid].add(v)
SED = re.compile(r"propofol|diprivan|midazolam|versed|dexmedetomidine|precedex|"
                 r"fentanyl|lorazepam|ativan|ketamine|cisatracurium|rocuronium|"
                 r"vecuronium|nimbex", re.I)
by_drug = defaultdict(list)
for r in stream("infusionDrug"):
    sid = r["patientunitstayid"]
    if sid in los_of and SED.search(r["drugname"]):
        v = as_int(r["infusionoffset"])
        if v is not None and 0 <= v <= los_of[sid]:
            by_drug[(sid, r["drugname"])].append(v)
for (sid, _d), offs in by_drug.items():
    offs.sort()
    prev = None
    for o in offs:
        if prev is None or o - prev > RESTART_GAP:
            ev[sid].add(o)
        prev = o
EV = {s: np.array(sorted(v), dtype=np.int64) for s, v in ev.items()}
print(f"      {sum(len(v) for v in EV.values()):,} distinct events in {len(EV):,} stays")

# ------------------------------------------------- 4. reference windows
print(f"[4/6] placing K={K} reference windows per stay (seed {SEED}) ...")
sids = sorted(los_of)
w_sid, w_hit = [], []
for sid in sids:
    L, am = los_of[sid], admitmin_of[sid]
    arr = EV.get(sid)
    ndays = max(1, L // 1440)
    for _ in range(K):
        i = rng.integers(len(GAP_H))
        dur = float(GAP_H[i]) * 60.0
        hr = int(ONSET_HR[rng.integers(len(ONSET_HR))])
        target = hr * 60 + rng.integers(60)
        day = rng.integers(ndays)
        t0 = day * 1440 + ((target - am) % 1440)
        t1 = t0 + dur
        if t1 > L:                       # window must fit inside the observed stay
            continue
        w_sid.append(sid)
        if arr is None or len(arr) == 0:
            w_hit.append(0)
        else:
            lo = np.searchsorted(arr, t0 - ATTR_MIN)
            hi = np.searchsorted(arr, t1 + ATTR_MIN, "right")
            w_hit.append(1 if hi > lo else 0)
w_sid = np.array(w_sid)
w_hit = np.array(w_hit, dtype=np.int8)
np.save(OUT / "eicu_reference_windows.npy", w_hit)
rate = 100 * w_hit.mean()
print(f"      {len(w_hit):,} usable windows; background rate {rate:.1f}%")

# cluster bootstrap over stays
uniq = np.unique(w_sid)
idx = {s: np.where(w_sid == s)[0] for s in uniq}
bs = []
for _ in range(1000):
    pick = np.concatenate([idx[s] for s in rng.choice(uniq, len(uniq), replace=True)])
    bs.append(100 * w_hit[pick].mean())
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"      95% CI {lo:.1f}-{hi:.1f}")

# ------------------------------------------------- 5. MIMIC P1-only comparator
print("[5/6] like-for-like MIMIC P1 background rate ...")
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
prc = prc[prc["proc_class"] == "P1"]
itr2 = itr.merge(coh[["stay_id", "intime"]], on="stay_id", how="left")
g0 = itr2["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = pd.to_datetime(itr2["gap_end"]).values.astype("datetime64[s]").astype(np.int64)
stays_m = itr2["stay_id"].values
pmap = {k: np.sort(v["starttime"].values.astype("datetime64[s]").astype(np.int64))
        for k, v in prc.groupby("stay_id", sort=False)}
SEC, DAY = 3600, 86400


def p1_rate(shift):
    hit = tot = 0
    for i in range(len(g0)):
        if not KEEP[i]:
            continue
        a = pmap.get(stays_m[i])
        tot += 1
        if a is None:
            continue
        sh = int(shift[i]) * DAY
        j0 = np.searchsorted(a, g0[i] + sh - SEC)
        j1 = np.searchsorted(a, g1[i] + sh + SEC, "right")
        if j1 > j0:
            hit += 1
    return 100 * hit / tot


obs_p1 = p1_rate(np.zeros(len(g0), dtype=np.int64))
nulls = [p1_rate(DRAWS[b]) for b in range(0, DRAWS.shape[0], 10)]   # 100 replicates
mimic_bg = float(np.mean(nulls))
print(f"      MIMIC P1 observed {obs_p1:.1f}%, background {mimic_bg:.1f}% "
      f"(excess {obs_p1-mimic_bg:.1f} pp)")

# ------------------------------------------------- 6. between-hospital
print("[6/6] between-hospital spread ...")
hsp = np.array([hosp_of[s] for s in w_sid])
rows = []
for h in np.unique(hsp):
    m = hsp == h
    n_stays = len(np.unique(w_sid[m]))
    if n_stays >= 20:
        rows.append({"hospitalid": h, "stays": n_stays, "windows": int(m.sum()),
                     "background_rate_pct": round(100 * float(w_hit[m].mean()), 2)})
hdf = pd.DataFrame(rows).sort_values("background_rate_pct")
hdf.to_csv(OUT / "eicu_background_by_hospital.csv", index=False)
r = hdf["background_rate_pct"].values
print(f"      {len(hdf)} hospitals: median {np.median(r):.1f}%, "
      f"IQR {np.percentile(r,25):.1f}-{np.percentile(r,75):.1f}, "
      f"10th-90th {np.percentile(r,10):.1f}-{np.percentile(r,90):.1f}")

A = json.load(open(OUT / "eicu_interface_audit.json"))
res = {
    "contract_sha256": "ca02b0d6ef8fdec3b65e549cb7c8d6ead9b4d41cf0f14e93a8c1e2f49af44923",
    "seed": SEED, "windows_per_stay": K,
    "eicu_stays": len(sids), "eicu_windows": int(len(w_hit)),
    "eicu_background_pct": round(rate, 1),
    "eicu_background_ci": [round(lo, 1), round(hi, 1)],
    "mimic_p1_observed_pct": round(obs_p1, 1),
    "mimic_p1_background_pct": round(mimic_bg, 1),
    "mimic_p1_excess_pp": round(obs_p1 - mimic_bg, 1),
    "hospitals": len(hdf),
    "hosp_median_pct": round(float(np.median(r)), 1),
    "hosp_iqr": [round(float(np.percentile(r, 25)), 1), round(float(np.percentile(r, 75)), 1)],
    "hosp_p10_p90": [round(float(np.percentile(r, 10)), 1), round(float(np.percentile(r, 90)), 1)],
    "hosp_p90_over_p10": round(float(np.percentile(r, 90) / max(np.percentile(r, 10), 1e-9)), 2),
    "doc_lag_median_min": A["doc_lag_median_min"],
    "doc_lag_p95_min": A["doc_lag_p95_min"],
    "doc_lag_pct_over_60min": A["doc_lag_pct_over_60min"],
}
G = [("F1", "background rate non-trivial (5-95%)", res["eicu_background_pct"],
      5 <= rate <= 95),
     ("F2", "within 3x of MIMIC P1 background", f"{rate:.1f} vs {mimic_bg:.1f}",
      mimic_bg / 3 <= rate <= mimic_bg * 3),
     ("F3", "hospitals with >=20 stays >= 100", len(hdf), len(hdf) >= 100),
     ("F4", "bootstrap CI half-width < 5 pp", round((hi - lo) / 2, 2), (hi - lo) / 2 < 5)]
print("\n" + "=" * 74)
for g, c, o, ok in G:
    print(f"{g:<5}{c:<42}{str(o):>14}  {'PASS' if ok else 'FAIL'}")
print("=" * 74)
res["gates"] = [{"gate": g, "criterion": c, "observed": str(o), "pass": bool(ok)} for g, c, o, ok in G]
res["all_pass"] = all(ok for *_, ok in G)
json.dump(res, open(OUT / "eicu_background_rate.json", "w"), indent=2)
print(f"\nOVERALL {'PASS' if res['all_pass'] else 'FAIL'}  -> eicu_background_rate.json")
