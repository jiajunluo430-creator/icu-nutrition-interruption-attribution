"""N2 step 03 - eICU gate G6.

Question: can eICU represent (a) per-hospital nutrition delivery for >=30 hospitals
with >=20 eligible stays each, and (b) interruption semantics equivalent to MIMIC's
Paused/Stopped status codes?

Prespecified fallback (contract G6): if failed, eICU is demoted to an
interface-audit appendix and the manuscript becomes MIMIC-only.

Reuses the ND03 eICU interface whitelist (read-only).
"""
import csv
import gzip
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

ZIP = Path(r"D:\respiratory_icu_qdp\eicu-collaborative-research-database-2.0.zip")
PREFIX = "eicu-collaborative-research-database-2.0/"
WL = Path(r"D:\GI_CHARLS_NHANES\ND03_refeeding_phosphate_qdp\config\eicu_interface_whitelist.csv")
OUT = Path(r"D:\N2_icu_nutrition_delivery_gap\03_outputs")
OUT.mkdir(exist_ok=True)

csv.field_size_limit(10_000_000)
MIN_LOS_MIN = 48 * 60
OBS_MIN = 7 * 24 * 60


def stream(zf, name):
    with zf.open(PREFIX + name) as raw:
        with gzip.open(raw, "rt", encoding="utf-8", errors="replace", newline="") as t:
            yield from csv.DictReader(t)


# ---------------------------------------------------------- whitelist
strict_io = set()
strict_inf = set()
for r in csv.DictReader(open(WL, encoding="utf-8-sig")):
    if "nutrition" not in r.get("role", ""):
        continue
    if r["tier"] == "strict_administration_like":
        # ND03 stored the key as "<cellpath> | <celllabel> | <cellvaluenumeric>",
        # i.e. one row per value-instance. Strip the trailing value to recover the
        # interface identity.
        key = r["label"].strip().rsplit(" | ", 1)[0]
        (strict_io if r["source_table"] == "intakeOutput" else strict_inf).add(key)
print(f"strict intakeOutput labels: {len(strict_io):,}")
print(f"strict infusionDrug labels: {len(strict_inf):,}")

zf = zipfile.ZipFile(ZIP)

# ---------------------------------------------------------- patients
print("\n[1] patient.csv.gz", flush=True)
pat = {}
for r in stream(zf, "patient.csv.gz"):
    try:
        los = int(r["unitdischargeoffset"])
    except (ValueError, TypeError):
        continue
    pat[r["patientunitstayid"]] = {
        "hospitalid": r["hospitalid"],
        "los_min": los,
        "age": r.get("age", ""),
        "unittype": r.get("unittype", ""),
    }
print(f"  unit stays: {len(pat):,}")
elig_los = {k for k, v in pat.items() if v["los_min"] >= MIN_LOS_MIN}
print(f"  LOS >= 48 h: {len(elig_los):,}")

# ---------------------------------------------------------- intakeOutput
print("\n[2] intakeOutput.csv.gz -> nutrition volume records", flush=True)
n = kept = 0
stay_days = defaultdict(set)
stay_vol = defaultdict(float)
stay_events = defaultdict(int)
for r in stream(zf, "intakeOutput.csv.gz"):
    n += 1
    if n % 5_000_000 == 0:
        print(f"    scanned {n:,} ...", flush=True)
    # ND03 whitelist key is "<cellpath> | <celllabel>", not the bare celllabel
    lbl = f"{(r.get('cellpath') or '').strip()} | {(r.get('celllabel') or '').strip()}"
    if lbl not in strict_io:
        continue
    sid = r["patientunitstayid"]
    if sid not in elig_los:
        continue
    try:
        off = int(r["intakeoutputoffset"])
        val = float(r["cellvaluenumeric"])
    except (ValueError, TypeError):
        continue
    if off < 0 or off > OBS_MIN or val <= 0:
        continue
    kept += 1
    stay_days[sid].add(off // 1440)
    stay_vol[sid] += val
    stay_events[sid] += 1
print(f"  scanned {n:,}; nutrition volume rows kept {kept:,}")
print(f"  stays with >=1 nutrition record: {len(stay_days):,}")

# ---------------------------------------------------------- eligibility
elig = {s for s, d in stay_days.items() if len(d) >= 2}
print(f"  stays with >=2 nutrition days: {len(elig):,}")

by_hosp = defaultdict(int)
for s in elig:
    by_hosp[pat[s]["hospitalid"]] += 1
hosp_ok = {h: c for h, c in by_hosp.items() if c >= 20}
print(f"  hospitals with >=20 eligible stays: {len(hosp_ok)}")

# ---------------------------------------------------------- interruption semantics
# Does intakeOutput carry any rate or status field at all?
print("\n[3] interruption-semantics probe", flush=True)
cols_io = None
for r in stream(zf, "intakeOutput.csv.gz"):
    cols_io = list(r.keys())
    break
cols_inf = None
for r in stream(zf, "infusionDrug.csv.gz"):
    cols_inf = list(r.keys())
    break
print(f"  intakeOutput columns: {cols_io}")
print(f"  infusionDrug columns: {cols_inf}")
has_rate_io = any("rate" in c.lower() for c in (cols_io or []))
has_status_io = any(k in c.lower() for c in (cols_io or [])
                    for k in ("status", "stop", "pause"))
print(f"  intakeOutput has rate field: {has_rate_io}")
print(f"  intakeOutput has status/stop/pause field: {has_status_io}")

zf.close()

# ---------------------------------------------------------- verdict
g6a = len(hosp_ok) >= 30
g6b = has_rate_io and has_status_io
result = {
    "eicu_unit_stays": len(pat),
    "los_ge_48h": len(elig_los),
    "nutrition_volume_rows": kept,
    "stays_with_nutrition": len(stay_days),
    "stays_ge_2_nutrition_days": len(elig),
    "hospitals_with_ge20_eligible_stays": len(hosp_ok),
    "intakeOutput_columns": cols_io,
    "infusionDrug_columns": cols_inf,
    "intakeOutput_has_rate": has_rate_io,
    "intakeOutput_has_status": has_status_io,
    "G6a_hospital_coverage_pass": bool(g6a),
    "G6b_interruption_semantics_pass": bool(g6b),
    "G6_overall_pass": bool(g6a and g6b),
}
json.dump(result, open(OUT / "eicu_g6.json", "w"), indent=2)

with open(OUT / "eicu_hospital_counts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["hospitalid", "eligible_stays"])
    for h, c in sorted(by_hosp.items(), key=lambda kv: -kv[1]):
        w.writerow([h, c])

print("\n=== G6 VERDICT ===")
print(json.dumps(result, indent=2))
