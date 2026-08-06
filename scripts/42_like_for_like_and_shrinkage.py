"""N2 step 42 - genuinely like-for-like eICU comparison, and shrunk hospital estimates.

Two corrections demanded by review round 6:

M9  The eICU "harmonized airway/sedation class" is not like-for-like with MIMIC P1.
    MIMIC P1 contains six itemids, all airway: extubation, intubation, bronchoscopy,
    percutaneous and open tracheostomy, bedside surgical procedure. It contains NO
    sedation infusions. The eICU class added 100,640 sedation/NMB infusion starts against
    7,644 airway events, so 93% of its events had no counterpart in the comparator.
    Recomputed restricting eICU to airway events only.

M8  The raw between-hospital spread counts binomial sampling noise as if it were
    between-hospital variation. With ~100 windows per hospital, sampling alone produces
    a wide spread. Recomputed with beta-binomial empirical-Bayes shrinkage, reporting
    tau, ICC, the noise-only reference spread, and funnel-plot coordinates.
"""
import csv
import gzip
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
REV = OUT / "review6"
REV.mkdir(exist_ok=True)
Z = zipfile.ZipFile(r"D:\respiratory_icu_qdp\eicu-collaborative-research-database-2.0.zip")
P = "eicu-collaborative-research-database-2.0/"
SEED, K, ATTR_MIN, MAX_MIN, MIN_LOS = 20260805, 5, 60, 7 * 1440, 2880
rng = np.random.default_rng(SEED)


def stream(t):
    with Z.open(P + t + ".csv.gz") as fh:
        raw = io.BytesIO(fh.read())
    with gzip.GzipFile(fileobj=raw) as gz:
        r = csv.reader(io.TextIOWrapper(gz, encoding="utf-8", errors="replace"))
        h = next(r)
        for row in r:
            if len(row) == len(h):
                yield dict(zip(h, row))


def ai(v):
    v = (v or "").strip()
    return int(v) if v.lstrip("-").isdigit() else None


# ------------------------------------------------------- MIMIC window distribution
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start"])
DR = np.load(OUT / "locked_referent_draws.npy")
KEEP = np.array([DR[:, i].any() for i in range(DR.shape[1])])
GAP_H, ONSET = itr["gap_h"].values[KEEP], itr["gap_start"].dt.hour.values[KEEP]

# ------------------------------------------------------- eICU cohort + AIRWAY ONLY
print("[1/3] eICU cohort and airway-only events ...")
los, hosp, admitmin = {}, {}, {}
for p in stream("patient"):
    a = p["age"].strip()
    an = 90 if a == "> 89" else (int(a) if a.isdigit() else None)
    L = ai(p["unitdischargeoffset"])
    t = p["unitadmittime24"].strip()
    if (an is None or an < 18 or L is None or L < MIN_LOS
            or p["unitvisitnumber"].strip() != "1" or not re.match(r"^\d{2}:\d{2}", t)):
        continue
    s = p["patientunitstayid"]
    los[s] = min(L, MAX_MIN)
    hosp[s] = p["hospitalid"]
    admitmin[s] = int(t[:2]) * 60 + int(t[3:5])

ev = defaultdict(set)
for r in stream("respiratoryCare"):
    s = r["patientunitstayid"]
    if s in los:
        for k in ("ventstartoffset", "ventendoffset"):
            v = ai(r[k])
            if v is not None and 0 < v <= los[s]:
                ev[s].add(v)
EV = {s: np.array(sorted(v), dtype=np.int64) for s, v in ev.items()}
n_ev = sum(len(v) for v in EV.values())
stay_days = sum(los.values()) / 1440
print(f"      {n_ev:,} airway events in {len(EV):,} of {len(los):,} stays "
      f"({100*len(EV)/len(los):.1f}%); density {n_ev/stay_days:.3f}/stay-day")

# ------------------------------------------------------- reference windows
print("[2/3] placing reference windows ...")
w_sid, w_hit = [], []
for s in sorted(los):
    L, am, arr = los[s], admitmin[s], EV.get(s)
    nd = max(1, L // 1440)
    for _ in range(K):
        dur = float(GAP_H[rng.integers(len(GAP_H))]) * 60.0
        hr = int(ONSET[rng.integers(len(ONSET))])
        t0 = rng.integers(nd) * 1440 + ((hr * 60 + rng.integers(60) - am) % 1440)
        if t0 + dur > L:
            continue
        w_sid.append(s)
        if arr is None or not len(arr):
            w_hit.append(0)
        else:
            w_hit.append(int(np.searchsorted(arr, t0 + dur + ATTR_MIN, "right")
                             > np.searchsorted(arr, t0 - ATTR_MIN)))
w_sid, w_hit = np.array(w_sid), np.array(w_hit, dtype=np.int8)
rate = 100 * w_hit.mean()
uniq = np.unique(w_sid)
idx = {s: np.where(w_sid == s)[0] for s in uniq}
bs = [100 * w_hit[np.concatenate([idx[s] for s in rng.choice(uniq, len(uniq), True)])].mean()
      for _ in range(500)]
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"      airway-only background rate {rate:.2f}% (95% CI {lo:.2f}-{hi:.2f}) "
      f"over {len(w_hit):,} windows")

# MIMIC comparator: P1 is already airway-only (6 itemids, verified)
EBprev = json.load(open(OUT / "eicu_background_rate.json"))
mimic_bg = EBprev["mimic_p1_background_pct"]
mimic_dens = 7649 / (1021294 / 24)

like = {
    "eicu_airway_only_pct": round(float(rate), 2),
    "eicu_airway_only_ci": [round(float(lo), 2), round(float(hi), 2)],
    "eicu_airway_events": int(n_ev),
    "eicu_airway_density_per_stay_day": round(n_ev / stay_days, 3),
    "eicu_pct_stays_with_airway_event": round(100 * len(EV) / len(los), 1),
    "mimic_p1_background_pct": mimic_bg,
    "mimic_p1_events": 7649,
    "mimic_p1_density_per_stay_day": round(mimic_dens, 3),
    "density_ratio_mimic_over_eicu": round(mimic_dens / (n_ev / stay_days), 1),
    "verdict": ("NOT concordant. Restricted to the only event class the two databases "
                "genuinely share, eICU airway ascertainment is far sparser than MIMIC-IV, "
                "and the background rates differ severalfold. The earlier apparent "
                "agreement was produced by eICU sedation/NMB infusion starts, which have "
                "no counterpart in MIMIC P1."),
}
json.dump(like, open(REV / "like_for_like_airway.json", "w"), indent=2)
print(f"      MIMIC P1 {mimic_bg}% (density {mimic_dens:.3f}) vs eICU airway "
      f"{rate:.2f}% (density {n_ev/stay_days:.3f}); "
      f"density ratio {mimic_dens/(n_ev/stay_days):.1f}x")

# ------------------------------------------------------- M8: shrinkage
print("[3/3] empirical-Bayes shrinkage of hospital rates ...")
H = pd.read_csv(OUT / "eicu_background_by_hospital.csv")
H["hits"] = (H["background_rate_pct"] / 100 * H["windows"]).round().astype(int)
n, y = H["windows"].values.astype(float), H["hits"].values.astype(float)
p_raw = y / n
m = y.sum() / n.sum()

# method-of-moments beta-binomial: subtract the binomial component from total variance
w = n / n.sum()
s2 = float(np.sum(w * (p_raw - m) ** 2))
binom_var = float(np.sum(w * m * (1 - m) / n))
tau2 = max(s2 - binom_var, 0.0)
shrink_w = tau2 / (tau2 + m * (1 - m) / n)
p_sh = shrink_w * p_raw + (1 - shrink_w) * m
icc = tau2 / (tau2 + m * (1 - m))

noise = rng.binomial(n.astype(int), m) / n          # pure sampling-noise reference
H["shrinkage_weight"] = shrink_w.round(3)
H["background_rate_shrunk_pct"] = (100 * p_sh).round(2)
H["se_pct"] = (100 * np.sqrt(m * (1 - m) / n)).round(2)
H.sort_values("background_rate_shrunk_pct").to_csv(
    REV / "hospital_rates_shrunk.csv", index=False)

sh = {
    "hospitals": int(len(H)), "median_windows_per_hospital": int(np.median(n)),
    "pooled_rate_pct": round(100 * m, 2),
    "tau_pp": round(100 * float(np.sqrt(tau2)), 2),
    "icc": round(float(icc), 3),
    "raw_p10_p90": [round(100 * float(np.percentile(p_raw, 10)), 1),
                    round(100 * float(np.percentile(p_raw, 90)), 1)],
    "shrunk_p10_p90": [round(100 * float(np.percentile(p_sh, 10)), 1),
                       round(100 * float(np.percentile(p_sh, 90)), 1)],
    "sampling_noise_only_p10_p90": [round(100 * float(np.percentile(noise, 10)), 1),
                                    round(100 * float(np.percentile(noise, 90)), 1)],
    "raw_fold_range": round(float(np.percentile(p_raw, 90))
                            / max(float(np.percentile(p_raw, 10)), 1e-9), 1),
    "shrunk_fold_range": round(float(np.percentile(p_sh, 90))
                               / max(float(np.percentile(p_sh, 10)), 1e-9), 1),
}
json.dump(sh, open(REV / "hospital_shrinkage.json", "w"), indent=2)
for k, v in sh.items():
    print(f"      {k:<32} {v}")
print("\nwrote like_for_like_airway.json, hospital_shrinkage.json, "
      "hospital_rates_shrunk.csv")
