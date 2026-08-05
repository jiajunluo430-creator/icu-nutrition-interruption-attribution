"""N2 step 34 - append registry entries E28-E32 for the external-validation round."""
import csv
from pathlib import Path

P = Path(r"D:\N2_icu_nutrition_delivery_gap\03_outputs\exploratory_attempts.csv")
rows = list(csv.DictReader(open(P, encoding="utf-8")))
flds = list(rows[0].keys())
have = {r["attempt"] for r in rows}

NEW = [
    dict(attempt="E28", date="2026-08-05", domain="external validation",
         change="eICU background co-occurrence rate added as external validation "
                "(contract ca02b0d6, frozen before any rate was computed)",
         reason="Frontiers desk-rejected the submission for lack of independent "
                "validation. The background rate is a property of procedure density, "
                "not of nutrition records, so eICU can support it despite failing "
                "nutrition gate G6.",
         result="eICU 6.7% (95% CI 6.5-6.8) over 63,703 stays in 182 hospitals vs "
                "MIMIC P1 background 8.1%; 7.7% among the 92 better-documenting "
                "hospitals. Gates F1-F4 all PASS.",
         disposition="ADOPTED as external validation. No energy estimand attempted in "
                     "eICU, because G6 proved the required fields absent.",
         contract_compliant="yes"),
    dict(attempt="E29", date="2026-08-05", domain="external validation",
         change="Between-hospital spread reported only alongside an ascertainment "
                "diagnostic",
         reason="The raw spread (10th-90th 0.0-14.9%) could be pure documentation "
                "heterogeneity rather than a difference in procedure density.",
         result="Ascertainment explains 35% of between-hospital variance (r=0.593). "
                "Restricted to the 92 better-documenting hospitals the rate still "
                "spans 0.8-22.9% (10th-90th).",
         disposition="ADOPTED. Reported as spread in the MEASURED background rate, "
                     "explicitly not as variation in care.",
         contract_compliant="yes"),
    dict(attempt="E30", date="2026-08-05", domain="clinical interpretation",
         change="Per-stay burden concentration reported against the gross positive "
                "burden rather than the net total",
         reason="A chance-corrected per-stay value can be negative, so the net total "
                "(114,660 kcal) is far below the positive tail (304,074 kcal). The "
                "top-decile share of the net total computes to 248% and is meaningless.",
         result="67.5% of stays exactly zero, 18.0% negative, 14.5% positive. Top "
                "decile 284,249 kcal = 93.5% of the gross positive burden. 10.8% of "
                "stays >100 kcal, 6.3% >250 kcal, 2.7% >500 kcal, max 2,195 kcal.",
         disposition="ADOPTED. Net and gross are reported together so the two cannot "
                     "be confused.",
         contract_compliant="correction of error"),
    dict(attempt="E31", date="2026-08-05", domain="clinical interpretation",
         change="Time from procedure to resumption of feeding added, including for the "
                "negative-control class",
         reason="Reviewers would ask which processes are actually slow to restart, not "
                "merely that the total burden is small.",
         result="Airway/sedation median 4.0 h (31.7% beyond the 6 h defensible window); "
                "off-unit transport 2.4 h. The negative control is SLOWER (4.4 h) than "
                "airway, indicating restart delay is a property of feeding workflow "
                "rather than of the procedure.",
         disposition="ADOPTED. The negative-control comparison is the primary "
                     "interpretive anchor for this analysis.",
         contract_compliant="yes"),
    dict(attempt="E32", date="2026-08-05", domain="transportability",
         change="Temporal transport across the five MIMIC-IV anchor-year eras",
         reason="Non-overlapping patients and distinct practice eras give a "
                "within-database independent-cohort check at no additional data cost.",
         result="Excess 7.7-11.7 pp across eras (pooled 9.9); share of shortfall "
                "0.090-0.207% (pooled 0.177%). The 2020-2022 era is lowest at 0.090% "
                "on 697 stays.",
         disposition="ADOPTED. Direction consistent in every era.",
         contract_compliant="yes"),
]

added = 0
for r in NEW:
    if r["attempt"] in have:
        continue
    rows.append({k: r.get(k, "") for k in flds})
    added += 1

with open(P, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=flds)
    w.writeheader()
    w.writerows(rows)

ids = [r["attempt"] for r in rows]
print(f"added {added}; registry now {len(rows)} entries {ids[0]}..{ids[-1]}")
assert ids == [f"E{i:02d}" for i in range(1, len(ids) + 1)], "registry ids not sequential"
print("ASSERT OK: registry ids sequential with no gaps")
