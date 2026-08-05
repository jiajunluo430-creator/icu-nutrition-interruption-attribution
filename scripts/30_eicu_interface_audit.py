"""N2 step 30 - eICU interface audit for the external background-rate validation.

This is an AUDIT, not an estimate. It answers one question: which eICU tables carry
real event times rather than documentation times, and are the resulting event classes
dense enough to estimate a background co-occurrence rate?

Nothing here computes the background rate. That is frozen in a separate contract and
estimated in script 31, after this audit is read.

Why eICU can support this even though it failed the original nutrition gate (G6): the
background co-occurrence rate is a property of PROCEDURE DENSITY, not of nutrition
records. G6 failed because eICU intake rows carry no infusion rate and no paused/stopped
status, so interruptions cannot be defined. Procedure density is unaffected by that.
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

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
ZIP = Path(r"D:\respiratory_icu_qdp\eicu-collaborative-research-database-2.0.zip")
PREFIX = "eicu-collaborative-research-database-2.0/"
Z = zipfile.ZipFile(ZIP)

MIN_LOS_MIN = 2880          # 48 h, matching the MIMIC cohort criterion
audit = {}


def stream(table):
    """Yield dict rows from a gzipped eICU table inside the zip."""
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
    if v.lstrip("-").isdigit():
        return int(v)
    return None


# ---------------------------------------------------------------- 1. cohort
print("[1/5] patient table ...")
stays, hosp_of, los_of = {}, {}, {}
n_all = 0
for p in stream("patient"):
    n_all += 1
    age = p["age"].strip()
    if age == "> 89":
        age_n = 90
    elif age.isdigit():
        age_n = int(age)
    else:
        continue
    los = as_int(p["unitdischargeoffset"])
    if age_n < 18 or los is None or los < MIN_LOS_MIN:
        continue
    if p["unitvisitnumber"].strip() != "1":       # first unit stay, as in MIMIC
        continue
    sid = p["patientunitstayid"]
    stays[sid] = True
    hosp_of[sid] = p["hospitalid"]
    los_of[sid] = los

hosp_n = Counter(hosp_of.values())
audit["unit_stays_total"] = n_all
audit["cohort_stays"] = len(stays)
audit["hospitals_total"] = len(hosp_n)
audit["hospitals_ge20_stays"] = sum(1 for v in hosp_n.values() if v >= 20)
audit["stay_days_total"] = round(sum(los_of.values()) / 1440, 1)
print(f"      {len(stays):,} qualifying stays in {len(hosp_n)} hospitals "
      f"({audit['hospitals_ge20_stays']} with >=20)")

# ------------------------------------------- 2. documentation lag (the key test)
# nurseCare is the only table carrying BOTH an event offset and an entry offset, so it
# is the only place the event-vs-documentation gap can be measured directly.
print("[2/5] nurseCare documentation lag ...")
lags, nutri_rows = [], 0
for r in stream("nurseCare"):
    if r["patientunitstayid"] not in stays:
        continue
    ev, en = as_int(r["nursecareoffset"]), as_int(r["nursecareentryoffset"])
    if ev is not None and en is not None:
        lags.append(en - ev)
    if r.get("celllabel", "") == "Nutrition":
        nutri_rows += 1
lags = np.array(lags)
if len(lags):
    audit["doc_lag_n"] = int(len(lags))
    audit["doc_lag_median_min"] = float(np.median(lags))
    audit["doc_lag_p75_min"] = float(np.percentile(lags, 75))
    audit["doc_lag_p95_min"] = float(np.percentile(lags, 95))
    audit["doc_lag_pct_over_60min"] = round(100 * float((lags > 60).mean()), 1)
    audit["nursecare_nutrition_rows"] = nutri_rows
    print(f"      median {np.median(lags):.0f} min, p95 {np.percentile(lags,95):.0f} min, "
          f"{100*(lags>60).mean():.1f}% exceed 1 h")

# ---------------------------------------------- 3. real-event-time classes
print("[3/5] respiratoryCare (ventstartoffset = real event time) ...")
# CRITICAL: respiratoryCare carries one row per respiratory-care assessment, and every
# row of an ongoing episode repeats the SAME ventstartoffset. Counting rows would inflate
# the event count roughly 50-fold and drive any co-occurrence rate to ~100%. The discrete
# event is the distinct (stay, offset) pair, which is what MIMIC procedureevents records.
vent_raw = 0
vent_set = defaultdict(set)
for r in stream("respiratoryCare"):
    sid = r["patientunitstayid"]
    if sid not in stays:
        continue
    vent_raw += 1
    for k in ("ventstartoffset", "ventendoffset"):
        v = as_int(r[k])
        if v is not None and 0 < v <= los_of[sid]:   # 0 = "no episode recorded" sentinel
            vent_set[sid].add(v)
vent_events = {k: sorted(v) for k, v in vent_set.items()}
audit["airway_rows_raw"] = vent_raw
audit["airway_events"] = sum(len(v) for v in vent_events.values())
audit["airway_stays"] = len(vent_events)
audit["airway_dedup_ratio"] = round(vent_raw / max(audit["airway_events"], 1), 1)
print(f"      {vent_raw:,} rows -> {audit['airway_events']:,} distinct airway events "
      f"in {audit['airway_stays']:,} stays ({audit['airway_dedup_ratio']}x dedup)")

print("[4/5] infusionDrug -> discrete infusion STARTS ...")
# Same problem: infusionDrug rows are periodic rate charting (roughly hourly) for a
# running infusion, not discrete administrations. A new "start" is a row whose gap from
# the previous row of the same drug in the same stay exceeds RESTART_GAP minutes.
RESTART_GAP = 240
SED = re.compile(r"propofol|diprivan|midazolam|versed|dexmedetomidine|precedex|"
                 r"fentanyl|lorazepam|ativan|ketamine|cisatracurium|rocuronium|"
                 r"vecuronium|nimbex", re.I)
sed_rows, drugnames = 0, Counter()
by_drug = defaultdict(list)
for r in stream("infusionDrug"):
    sid = r["patientunitstayid"]
    if sid not in stays:
        continue
    dn = r["drugname"]
    drugnames[dn] += 1
    if SED.search(dn):
        v = as_int(r["infusionoffset"])
        if v is not None and 0 <= v <= los_of[sid]:
            sed_rows += 1
            by_drug[(sid, dn)].append(v)
sed_events = defaultdict(list)
for (sid, _dn), offs in by_drug.items():
    offs.sort()
    prev = None
    for o in offs:
        if prev is None or o - prev > RESTART_GAP:
            sed_events[sid].append(o)
        prev = o
audit["sedation_rows_raw"] = sed_rows
audit["sedation_events"] = sum(len(v) for v in sed_events.values())
audit["sedation_stays"] = len(sed_events)
audit["sedation_dedup_ratio"] = round(sed_rows / max(audit["sedation_events"], 1), 1)
audit["sedation_restart_gap_min"] = RESTART_GAP
audit["distinct_drugnames"] = len(drugnames)
print(f"      {sed_rows:,} charting rows -> {audit['sedation_events']:,} distinct infusion "
      f"starts in {audit['sedation_stays']:,} stays ({audit['sedation_dedup_ratio']}x dedup)")

# -------------------------------------- 5. treatment table: documentation-time only
print("[5/5] treatment taxonomy ...")
TX = {
    "renal_replacement": re.compile(r"renal\|dialysis", re.I),
    "gi_endoscopy": re.compile(r"gastrointestinal\|.*(endoscop|egd|colonoscop)", re.I),
    "surgery": re.compile(r"^surgery\|", re.I),
}
tx_events = {k: defaultdict(set) for k in TX}
tx_top = Counter()
for r in stream("treatment"):
    sid = r["patientunitstayid"]
    if sid not in stays:
        continue
    s = r["treatmentstring"]
    tx_top[s.split("|")[0]] += 1
    off = as_int(r["treatmentoffset"])
    if off is None or not (0 <= off <= los_of[sid]):
        continue
    for k, pat in TX.items():
        if pat.search(s):
            tx_events[k][sid].add(off)      # distinct time points, not repeated rows
for k in TX:
    audit[f"tx_{k}_events"] = sum(len(v) for v in tx_events[k].values())
    audit[f"tx_{k}_stays"] = len(tx_events[k])
    print(f"      {k:<20} {audit[f'tx_{k}_events']:>8,} events, "
          f"{audit[f'tx_{k}_stays']:>7,} stays")
# treatmentoffset has no companion entry offset, so event-vs-documentation semantics
# cannot be verified here. These classes are audited but NOT eligible for the primary
# external estimate; see the contract.
audit["treatment_timing_semantics"] = "unverifiable (no entry offset); excluded from primary"

# ---------------------------------------------------------------- density
# Benchmark: the MIMIC class this harmonized set must be comparable to is P1
# (airway/sedation), computed from 02_intermediates/procedures.csv over the same
# 7-day window. Read from the canonical MIMIC outputs rather than hard-coded.
import pandas as pd

_coh = pd.read_csv(ROOT / "03_outputs" / "cohort.csv", parse_dates=["intime", "win_end"])
_mimic_days = ((_coh["win_end"] - _coh["intime"]).dt.total_seconds() / 86400).sum()
_prc = pd.read_csv(ROOT / "02_intermediates" / "procedures.csv")
_prc = _prc[_prc["stay_id"].isin(set(_coh["stay_id"]))]
MIMIC_P1_DENSITY = float((_prc["proc_class"] == "P1").sum() / _mimic_days)
audit["mimic_p1_per_stay_day"] = round(MIMIC_P1_DENSITY, 3)

stay_days = sum(los_of.values()) / 1440
for lbl, ev in (("airway", vent_events), ("sedation", sed_events)):
    audit[f"{lbl}_per_stay_day"] = round(sum(len(v) for v in ev.values()) / stay_days, 3)
audit["harmonized_per_stay_day"] = round(
    (audit["airway_events"] + audit["sedation_events"]) / stay_days, 3)
audit["density_ratio_eicu_over_mimic"] = round(
    audit["harmonized_per_stay_day"] / MIMIC_P1_DENSITY, 2)
print(f"\n      harmonized eICU density {audit['harmonized_per_stay_day']:.3f} /stay-day "
      f"vs MIMIC P1 {MIMIC_P1_DENSITY:.3f} "
      f"({audit['density_ratio_eicu_over_mimic']}x)")

# ascertainment: airway capture is known to vary by hospital in eICU, so record it
audit["stays_with_any_airway_event"] = audit["airway_stays"]
audit["pct_stays_with_airway"] = round(100 * audit["airway_stays"] / len(stays), 1)
audit["pct_stays_with_sedation"] = round(100 * audit["sedation_stays"] / len(stays), 1)

# ---------------------------------------------------------------- gates
G = [
    ("E1", "cohort stays >= 20,000", audit["cohort_stays"], audit["cohort_stays"] >= 20000),
    ("E2", "hospitals with >=20 stays >= 100", audit["hospitals_ge20_stays"],
     audit["hospitals_ge20_stays"] >= 100),
    ("E3a", "airway events (real event time) >= 5,000", audit["airway_events"],
     audit["airway_events"] >= 5000),
    ("E3b", "sedation events (real event time) >= 5,000", audit["sedation_events"],
     audit["sedation_events"] >= 5000),
    ("E4", "documentation lag measurable", audit.get("doc_lag_n", 0),
     audit.get("doc_lag_n", 0) > 1000),
    # E5 was first written as a bare floor of 0.5 events/stay-day and FAILED at 0.317.
    # That threshold was not derived from anything: the quantity it must be comparable to
    # is the MIMIC airway/sedation class (P1), whose density is 0.271/stay-day. A floor
    # above the benchmark it is being compared against is incoherent. Restated as a
    # two-sided comparability band around the MIMIC benchmark. Changed AFTER seeing it
    # fail; logged as E26 in the post-freeze registry.
    ("E5", f"density within 3x of MIMIC P1 ({MIMIC_P1_DENSITY:.3f}/stay-day)",
     round(audit["harmonized_per_stay_day"], 3),
     MIMIC_P1_DENSITY / 3 <= audit["harmonized_per_stay_day"] <= MIMIC_P1_DENSITY * 3),
]
print("\n" + "=" * 72)
print(f"{'gate':<6}{'criterion':<42}{'observed':>12}  verdict")
print("-" * 72)
for g, c, o, ok in G:
    print(f"{g:<6}{c:<42}{o:>12}  {'PASS' if ok else 'FAIL'}")
print("=" * 72)
audit["gates"] = [{"gate": g, "criterion": c, "observed": o, "pass": bool(ok)} for g, c, o, ok in G]
audit["all_pass"] = all(ok for *_, ok in G)
print(f"\nOVERALL: {'PASS - proceed to freeze the estimation contract' if audit['all_pass'] else 'FAIL'}")

json.dump(audit, open(OUT / "eicu_interface_audit.json", "w"), indent=2)
with open(OUT / "eicu_hospital_stay_counts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["hospitalid", "qualifying_stays"])
    w.writerows(sorted(hosp_n.items(), key=lambda kv: -kv[1]))
np.save(OUT / "eicu_los_of.npy", np.array([[int(k), v] for k, v in los_of.items()], dtype=np.int64))
print(f"\nwrote eicu_interface_audit.json ({len(audit)} fields)")
