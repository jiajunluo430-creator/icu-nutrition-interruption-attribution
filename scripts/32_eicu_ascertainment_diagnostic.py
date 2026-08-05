"""N2 step 32 - is the between-hospital spread in background rate real, or documentation?

The contract prespecified that the between-hospital spread confounds true procedure
density with documentation practice. This script measures how much of it is the latter,
by correlating each hospital's background rate against the fraction of its stays that
record ANY harmonized event at all.
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
Z = zipfile.ZipFile(r"D:\respiratory_icu_qdp\eicu-collaborative-research-database-2.0.zip")
P = "eicu-collaborative-research-database-2.0/"


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


los, hosp = {}, {}
for p in stream("patient"):
    a = p["age"].strip()
    an = 90 if a == "> 89" else (int(a) if a.isdigit() else None)
    L = ai(p["unitdischargeoffset"])
    if an is None or an < 18 or L is None or L < 2880 or p["unitvisitnumber"].strip() != "1":
        continue
    los[p["patientunitstayid"]] = L
    hosp[p["patientunitstayid"]] = p["hospitalid"]

has_ev = set()
for r in stream("respiratoryCare"):
    s = r["patientunitstayid"]
    if s in los and any(ai(r[k]) for k in ("ventstartoffset", "ventendoffset")):
        has_ev.add(s)
SED = re.compile(r"propofol|diprivan|midazolam|versed|dexmedetomidine|precedex|fentanyl|"
                 r"lorazepam|ativan|ketamine|cisatracurium|rocuronium|vecuronium|nimbex", re.I)
for r in stream("infusionDrug"):
    s = r["patientunitstayid"]
    if s in los and SED.search(r["drugname"]):
        has_ev.add(s)

tot, cov = defaultdict(int), defaultdict(int)
for s, h in hosp.items():
    tot[h] += 1
    cov[h] += (s in has_ev)
asc = pd.DataFrame([{"hospitalid": str(h), "stays": tot[h],
                     "pct_stays_with_any_event": round(100 * cov[h] / tot[h], 1)}
                    for h in tot if tot[h] >= 20])

bg = pd.read_csv(OUT / "eicu_background_by_hospital.csv")
bg["hospitalid"] = bg["hospitalid"].astype(str)
m = bg.merge(asc[["hospitalid", "pct_stays_with_any_event"]], on="hospitalid")
r = float(np.corrcoef(m["pct_stays_with_any_event"], m["background_rate_pct"])[0, 1])

print(f"hospitals matched: {len(m)}")
print(f"ascertainment: median {m['pct_stays_with_any_event'].median():.1f}%, "
      f"range {m['pct_stays_with_any_event'].min():.1f}-{m['pct_stays_with_any_event'].max():.1f}%")
print(f"\nPearson r (ascertainment vs background rate) = {r:.3f}")
print(f"R^2 = {r**2:.3f}  -> {100*r**2:.0f}% of between-hospital variance tracks documentation\n")

med = m["pct_stays_with_any_event"].median()
hi = m[m["pct_stays_with_any_event"] >= med]
v = hi["background_rate_pct"].values
print(f"restricted to the {len(hi)} better-documenting hospitals (>= median ascertainment):")
print(f"   median {np.median(v):.1f}%, IQR {np.percentile(v,25):.1f}-{np.percentile(v,75):.1f}, "
      f"10th-90th {np.percentile(v,10):.1f}-{np.percentile(v,90):.1f}")

m.to_csv(OUT / "eicu_hospital_ascertainment.csv", index=False)
json.dump({
    "hospitals": len(m),
    "ascertainment_median_pct": float(med),
    "ascertainment_min_pct": float(m["pct_stays_with_any_event"].min()),
    "ascertainment_max_pct": float(m["pct_stays_with_any_event"].max()),
    "pearson_r": round(r, 3),
    "r_squared": round(r ** 2, 3),
    "restricted_n_hospitals": int(len(hi)),
    "restricted_median_pct": round(float(np.median(v)), 1),
    "restricted_iqr": [round(float(np.percentile(v, 25)), 1),
                       round(float(np.percentile(v, 75)), 1)],
    "restricted_p10_p90": [round(float(np.percentile(v, 10)), 1),
                           round(float(np.percentile(v, 90)), 1)],
}, open(OUT / "eicu_ascertainment_diagnostic.json", "w"), indent=2)
print("\nwrote eicu_ascertainment_diagnostic.json")
