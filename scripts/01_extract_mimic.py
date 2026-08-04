"""N2 step 01 - single-pass extraction of MIMIC-IV intermediates.

Reads only. Writes compact CSVs to 02_intermediates.
Governed by 00_contracts/N2_analysis_contract_v1.md (frozen).
"""
import csv
import gzip
import json
import sys
from pathlib import Path

MIMIC = Path(r"D:\respiratory_icu_qdp\MIMIC-IV\mimic-iv-3.1")
ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "02_intermediates"
OUT.mkdir(exist_ok=True)

csv.field_size_limit(10_000_000)


def reader(rel):
    f = gzip.open(MIMIC / rel, "rt", encoding="utf-8", errors="replace", newline="")
    return f, csv.DictReader(f)


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- frozen sets
NUTR = {
    r["itemid"]
    for r in csv.DictReader(
        open(ROOT / "00_contracts" / "nutrition_itemids_frozen.csv", encoding="utf-8")
    )
}
log(f"frozen nutrition itemids: {len(NUTR)}")

# Contract section 7. Class -> itemids. Locked.
PROC_CLASS = {
    "P1": ["224385", "227194", "225448", "226237", "225400", "229585"],
    "P2": ["225439", "225434", "227550", "229576", "225446", "221255"],
    "P3": ["229575", "221214", "223253", "225427", "225462", "225430", "229577", "229578"],
    "P4": ["225433", "225445", "225479", "225442", "225447", "229580", "225399",
           "226474", "226475", "225449"],
    "P5": ["225441", "227551"],
    "P0": ["225402", "221223", "229614", "229581", "229351", "221217", "225432",
           "225457", "229380", "229584", "228715"],
}
PROC_ITEM2CLASS = {i: c for c, ids in PROC_CLASS.items() for i in ids}
log(f"frozen procedure itemids: {len(PROC_ITEM2CLASS)} across {len(PROC_CLASS)} classes")

KCAL_ITEM, PROT_ITEM = "226060", "220454"
EN_ITEM, PN_ITEM, PO_ITEM, SUP_ITEM = "226221", "227079", "226506", "227080"
INGR_KEEP = {KCAL_ITEM, PROT_ITEM, EN_ITEM, PN_ITEM, PO_ITEM, SUP_ITEM}

# ---------------------------------------------------------------- 1. icustays
log("\n[1/5] icustays + patients + admissions")
f, rd = reader("icu/icustays.csv.gz")
stays = [dict(r) for r in rd]
f.close()
log(f"  icustays rows: {len(stays):,}")

f, rd = reader("hosp/patients.csv.gz")
pat = {r["subject_id"]: r for r in rd}
f.close()

f, rd = reader("hosp/admissions.csv.gz")
adm = {r["hadm_id"]: r for r in rd}
f.close()

with open(OUT / "icustays.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["subject_id", "hadm_id", "stay_id", "first_careunit", "intime",
                "outtime", "los", "anchor_age", "anchor_year_group", "gender",
                "dod", "hospital_expire_flag", "admittime", "deathtime"])
    for s in stays:
        p = pat.get(s["subject_id"], {})
        a = adm.get(s["hadm_id"], {})
        w.writerow([s["subject_id"], s["hadm_id"], s["stay_id"], s["first_careunit"],
                    s["intime"], s["outtime"], s["los"],
                    p.get("anchor_age", ""), p.get("anchor_year_group", ""),
                    p.get("gender", ""), p.get("dod", ""),
                    a.get("hospital_expire_flag", ""), a.get("admittime", ""),
                    a.get("deathtime", "")])
log(f"  wrote icustays.csv")

# ------------------------------------------------------------- 2. inputevents
log("\n[2/5] inputevents -> nutrition segments")
cols = ["subject_id", "hadm_id", "stay_id", "starttime", "endtime", "itemid",
        "amount", "amountuom", "rate", "rateuom", "orderid", "linkorderid",
        "ordercategorydescription", "patientweight", "statusdescription",
        "originalrate", "totalamount"]
n = kept = 0
link_ids = set()
f, rd = reader("icu/inputevents.csv.gz")
with open(OUT / "nutrition_segments_raw.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.DictWriter(fo, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rd:
        n += 1
        if r["itemid"] in NUTR:
            kept += 1
            link_ids.add(r["linkorderid"])
            w.writerow(r)
        if n % 2_000_000 == 0:
            log(f"    scanned {n:,} ...")
f.close()
log(f"  scanned {n:,}; nutrition rows kept {kept:,}; linkorderids {len(link_ids):,}")

# -------------------------------------------------------- 3. ingredientevents
log("\n[3/5] ingredientevents -> kcal / protein / route for nutrition orders")
n = kept = 0
f, rd = reader("icu/ingredientevents.csv.gz")
with open(OUT / "nutrition_ingredients.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["stay_id", "linkorderid", "itemid", "starttime", "endtime",
                "amount", "amountuom", "rate", "rateuom", "statusdescription"])
    for r in rd:
        n += 1
        if r["itemid"] in INGR_KEEP and r["linkorderid"] in link_ids:
            kept += 1
            w.writerow([r["stay_id"], r["linkorderid"], r["itemid"], r["starttime"],
                        r["endtime"], r["amount"], r["amountuom"], r["rate"],
                        r["rateuom"], r["statusdescription"]])
        if n % 3_000_000 == 0:
            log(f"    scanned {n:,} ...")
f.close()
log(f"  scanned {n:,}; ingredient rows kept {kept:,}")

# --------------------------------------------------------- 4. procedureevents
log("\n[4/5] procedureevents -> frozen classes")
n = kept = 0
f, rd = reader("icu/procedureevents.csv.gz")
with open(OUT / "procedures.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["subject_id", "hadm_id", "stay_id", "starttime", "endtime",
                "itemid", "proc_class", "statusdescription"])
    for r in rd:
        n += 1
        c = PROC_ITEM2CLASS.get(r["itemid"])
        if c:
            kept += 1
            w.writerow([r["subject_id"], r["hadm_id"], r["stay_id"], r["starttime"],
                        r["endtime"], r["itemid"], c, r["statusdescription"]])
f.close()
log(f"  scanned {n:,}; procedure rows kept {kept:,}")

# ------------------------------------------------- 5. covariates for sensitivity
log("\n[5/5] vasopressor + invasive ventilation flags (sensitivity covariates)")
VASO = {"221906", "221289", "221662", "221749", "222315", "221986", "221653"}
VENT = {"225792"}
n = 0
f, rd = reader("icu/inputevents.csv.gz")
vaso_stays = set()
for r in rd:
    n += 1
    if r["itemid"] in VASO:
        vaso_stays.add(r["stay_id"])
f.close()
f, rd = reader("icu/procedureevents.csv.gz")
vent_rows = []
for r in rd:
    if r["itemid"] in VENT:
        vent_rows.append((r["stay_id"], r["starttime"], r["endtime"]))
f.close()
with open(OUT / "covariates.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["stay_id", "any_vasopressor"])
    for s in sorted(vaso_stays):
        w.writerow([s, 1])
with open(OUT / "vent_intervals.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["stay_id", "starttime", "endtime"])
    w.writerows(vent_rows)
log(f"  vasopressor stays: {len(vaso_stays):,}; invasive-vent intervals: {len(vent_rows):,}")

json.dump(
    {"nutrition_rows": kept, "n_linkorderids": len(link_ids),
     "proc_classes": {k: len(v) for k, v in PROC_CLASS.items()}},
    open(OUT / "extract_manifest.json", "w"), indent=2)
log("\nDONE")
