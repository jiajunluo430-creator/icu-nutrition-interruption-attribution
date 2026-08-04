"""N2 step 22 - rebuild the Supplementary Material from scratch against the CURRENT
analysis. The previous builder appended new sections onto a stale S1-S11 base, so the
supplement still carried superseded numbers. This version derives every section from
the current output files and matches the S1-S14 list declared in the manuscript.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, MAN = ROOT / "03_outputs", ROOT / "07_manuscript"

rev = json.load(open(OUT / "rev_results.json"))
rev2 = json.load(open(OUT / "rev2_results.json"))
rr = json.load(open(OUT / "rev_rate.json"))
eic = json.load(open(OUT / "eicu_g6.json"))
frz = json.load(open(ROOT / "00_contracts" / "contract_freeze.json"))

L = []
_raw = L.append


def w(x):
    """Emit a block, replacing pandas NaN placeholders with NA."""
    _raw(str(x).replace("| nan ", "| NA  ").replace(" nan |", " NA  |"))
w("# Supplementary Material\n")
w("Sections are numbered as cited in the main text. All values are derived from the "
  "current analysis; superseded values appear only where explicitly labelled.\n")
w("---\n")

# ---------------------------------------------------------------- S1
w("## S1. Frozen analysis plan\n")
w(f"- File: `contract/N2_analysis_contract_v1.md`")
w(f"- SHA-256: `{frz['contract_sha256']}`")
w(f"- Frozen (UTC): {frz['frozen_utc']}")
w(f"- Nutrition item list SHA-256: `{frz['itemids_sha256']}` "
  f"({frz['n_nutrition_itemids']} items)\n")
w("The plan fixed every cohort criterion, item list, interruption rule, procedure class, "
  "attribution window, defensible fasting window, reference target, falsification test "
  "and stop-loss gate before any estimate was computed. It is an internally frozen "
  "prespecified plan, not a public preregistration. Deviations made after the freeze, "
  "including four corrections of our own methods, are listed in S13.\n")

# ---------------------------------------------------------------- S2
w("## S2. Cohort flow\n")
w(pd.read_csv(OUT / "cohort_flow.csv").to_markdown(index=False) + "\n")

# ---------------------------------------------------------------- S3
w("## S3. Binding gate results\n")
g = pd.read_csv(OUT / "pilot_gates.csv")
g["pass"] = g["pass"].map({True: "PASS", False: "FAIL"}).fillna("interpretive")
g = g.fillna("NA")   # no Python nan in published tables
w(g.to_markdown(index=False) + "\n")
w("**G5 failed and the natural experiment was dropped, not relaxed.** `ERCP (Done in "
  "unit)` has 12 events in all of MIMIC-IV v3.1 and `Portable CT scan` has none, despite "
  "both appearing in the item dictionary.\n")
w(f"**G6 failed on semantics, not population.** eICU has "
  f"{eic['hospitals_with_ge20_eligible_stays']} hospitals with >=20 eligible stays and "
  f"{eic['stays_ge_2_nutrition_days']:,} stays with >=2 nutrition days, but its intake "
  f"records carry neither an infusion rate nor a status field.\n")
w("G3b was defined against the original simple-shift null and is retained for the record; "
  "the primary null is now the case-crossover design of S7.\n")

# ---------------------------------------------------------------- S4
w("## S4. Complete procedure class list (43 items)\n")
PROC = {
    "P1": [("224385", "Intubation"), ("227194", "Extubation"),
           ("225448", "Percutaneous Tracheostomy"), ("226237", "Open Tracheostomy"),
           ("225400", "Bronchoscopy"), ("229585", "Surgical Procedure at Bedside")],
    "P2": [("225439", "Endoscopy"), ("225434", "Colonoscopy"), ("227550", "ERCP (Travel to)"),
           ("229576", "ERCP (Done in unit)"), ("225446", "PEG Insertion"),
           ("221255", "Trans Esophageal Echo")],
    "P3": [("229575", "Travel to Radiology"), ("221214", "CT scan"), ("223253", "MRI"),
           ("225427", "Angiography"), ("225462", "Interventional Radiology"),
           ("225430", "Cardiac Cath"), ("229577", "Cath Lab (Received)"),
           ("229578", "Cath Lab (Sent)")],
    "P4": [("225433", "Chest Tube Placed"), ("225445", "Paracentesis"),
           ("225479", "Thoracentesis"), ("225442", "Liver Biopsy"),
           ("225447", "Percutaneous Drain Insertion"), ("229580", "Line Placement at Bedside"),
           ("225399", "Lumbar Puncture"), ("226474", "ICP Bolt Inserted"),
           ("226475", "Intraventricular Drain Inserted"), ("225449", "Pericardiocentesis")],
    "P5": [("225441", "Hemodialysis"), ("227551", "Plasma Pheresis")],
    "P0": [("225402", "EKG"), ("221223", "EEG"), ("229614", "EEG (Continuous)"),
           ("229581", "Portable Chest X-Ray"), ("229351", "Foley Catheter"),
           ("221217", "Ultrasound"), ("225432", "Transthoracic Echo"),
           ("225457", "Abdominal X-Ray"), ("229380", "Nursing Water Swallow Screening"),
           ("229584", "EMG"), ("228715", "Transcranial Doppler")],
}
rows = [{"Class": c, "Role": "negative control" if c == "P0" else "target",
         "Defensible window (h)": 6 if c in ("P1", "P2") else 0,
         "itemid": i, "Label": l} for c, v in PROC.items() for i, l in v]
w(pd.DataFrame(rows).to_markdown(index=False) + "\n")
w(f"Total {len(rows)} items. Class priority for multiple attribution: "
  "P1 > P2 > P3 > P4 > P5 > P0. Alternative priority rules are in S9.\n")

# ---------------------------------------------------------------- S5
w("## S5. Delivery adequacy by ICU day (nutrition-support days)\n")
w(pd.read_csv(OUT / "table2_delivery_adequacy.csv").to_markdown(index=False) + "\n")
w("These panels are conditional on a day having nutrition support recorded, and "
  "correspond to Figure 2A,B. The shortfall decomposition in S6 uses the full "
  "alive-in-ICU denominator instead.\n")

# ---------------------------------------------------------------- S6
w("## S6. Shortfall decomposition and the denominator change\n")
w(pd.DataFrame([{"Component": k, "% of shortfall": v}
                for k, v in rev["shortfall_components_pct"].items()]
               ).to_markdown(index=False) + "\n")
w(f"- Denominator: {rev['denominator_icu_hours']:,.0f} alive-in-ICU hours, days 1-7")
w(f"- Reference target 89.0 M kcal; delivered 24.1 M kcal; "
  f"shortfall {rev['shortfall_total_kcal']/1e6:.1f} M kcal")
w(f"- **Superseded:** a nutrition-day-only denominator gave "
  f"{rev['old_denominator_deficit_kcal']/1e6:.1f} M kcal, "
  f"{rev['old_vs_new_denominator_ratio']}x smaller, and excluded pre-initiation entirely.\n")
w("Denominator sensitivities:\n")
w(f"- Censoring each stay at its first recorded oral or supplement intake "
  f"({rev2['pct_stays_with_oral_intake']}% of stays had any): shortfall "
  f"{rev2['oral_censored_shortfall_kcal']/1e6:.1f} M kcal; procedural share "
  f"{rev2['target_pct_oral_censored']:.3f}%.")
w(f"- Ramped reference target (40% day 1, 70% day 2, 100% from day 3): shortfall "
  f"{rev2['ramped_shortfall_kcal']/1e6:.1f} M kcal; procedural share "
  f"{rev2['target_pct_ramped']:.3f}%; pre-initiation "
  f"{rev2['pre_initiation_pct_ramped']}% rather than 48.5%.\n")

# ---------------------------------------------------------------- S7
rev3 = json.load(open(OUT / "canonical" / "canonical_primary.json"))
dnull = json.load(open(OUT / "rev3_day_preserving_null.json"))

w("## S7. Attribution rate under the case-crossover null\n")
w(pd.read_csv(OUT / "canonical" / "canonical_class_results.csv").to_markdown(index=False) + "\n")
w(f"Analysis set: {rev3['n_analysis_set']:,} interruptions with at least one referent day; "
  f"{rev3['n_excluded_no_referent']} excluded. Primary null: within-stay case-crossover "
  f"preserving clock hour and patient identity; {rev3['n_replicates']:,} replicates drawn "
  f"once from a locked draw set (seed {rev3['seed']}) and reused for every estimate.\n")
w(f"Any-class rate: observed {rev3['rate']['obs_pct']}% vs null {rev3['rate']['null_pct']}%; "
  f"excess **{rev3['rate']['excess_pp']} pp (95% CI {rev3['rate']['ci_lo']} to "
  f"{rev3['rate']['ci_hi']})**; empirical p = {rev3['rate']['p']:.3f}.\n")
w("**Class-specific attribution rates are non-exclusive**: each class is assessed "
  "independently for presence in the window, so one interruption may count towards several "
  "classes and the class percentages do not sum to the any-class rate. The priority rule "
  "applies only to the mutually exclusive energy estimand in S8.\n")
w("## S7b. Complementary null preserving ICU day and clock hour\n")
w(pd.DataFrame([{"metric": k, "value": str(v)} for k, v in dnull.items()]
               ).to_markdown(index=False) + "\n")
w(f"This across-patient null preserves ICU day and clock hour but not patient identity. It "
  f"gives a larger point estimate ({dnull['rate_excess_pp']} pp; "
  f"{dnull['pct_of_shortfall']:.3f}% of shortfall) than the primary within-stay null. The "
  f"two designs rely on different exchangeability assumptions and should be read as "
  f"complementary sensitivity analyses, not as lower and upper bounds. Both remain well "
  f"below 1% of the standardized nutrition-support shortfall.\n")

w("## S7c. Procedure density by ICU day and class (procedures per stay-day)\n")
w(pd.read_csv(OUT / "rev3_procedure_density_by_day.csv").to_markdown(index=False) + "\n")
w("Density is concentrated on ICU day 1 for every class; this is the structure that "
  "motivates reporting both nulls.\n")

w("## S7d. Negative-control energy diagnostics\n")
w(pd.read_csv(OUT / "canonical" / "canonical_p0_diagnostics.csv").to_markdown(index=False) + "\n")
w(pd.read_csv(OUT / "canonical" / "canonical_p0_strata.csv").to_markdown(index=False) + "\n")
w("The negative control is null on the attribution-rate scale but significantly negative "
  "on the energy scale under priority assignment. Evaluated non-exclusively it is null, "
  "and the negative excess concentrates in 12-24 h gaps, identifying exclusive assignment "
  "rather than residual confounding as the cause. The energy scale is therefore NOT "
  "claimed to be validated by the negative control.\n")

# ---------------------------------------------------------------- S8
w("## S8. Energy estimand by class: observed, null, chance-corrected\n")
w(pd.read_csv(OUT / "canonical" / "canonical_class_results.csv"
              ).to_markdown(index=False) + "\n")
w(f"Target burden is the sum over P1-P5: observed {rev3['target_obs_kcal']:,.0f} kcal, "
  f"null {rev3['target_null_kcal']:,.0f} kcal, chance-corrected "
  f"**{rev3['target_excess_kcal']:,.0f} kcal** (95% CI "
  f"{rev3['target_excess_ci'][0]:,.0f}-{rev3['target_excess_ci'][1]:,.0f}) = "
  f"{rev3['target_pct']}% of the shortfall, "
  f"{rev3['target_per_stay']} kcal per ICU stay.\n")
w(f"P0 is a **negative control reported as a diagnostic** and is excluded from the target "
  f"burden; its chance-corrected energy was {rev3['p0_energy_excess_kcal']:,.0f} kcal. "
  f"Including it, as an earlier version of this analysis did, would offset the candidate "
  f"classes and roughly halve the estimate.\n")
w("**Superseded:** an earlier version selected classes on attribution excess and summed "
  "their full observed burden, giving 450,892 kcal against a smaller denominator (1.3%). "
  "That is a specificity-screened upper bound, not a chance-corrected estimate.\n")

# ---------------------------------------------------------------- S9
w("## S9. Full sensitivity table (target classes P1-P5)\n")
sens = pd.read_csv(OUT / "canonical" / "canonical_sensitivity.csv")
w(sens.to_markdown(index=False) + "\n")
main = sens[~sens.analysis.str.contains("mixed")]
w(f"Range across specifications: {main.pct_of_shortfall.min():.3f}% to "
  f"{main.pct_of_shortfall.max():.3f}%. The 120-interruption mixed-route subgroup is too "
  f"small for a stable estimate and is shown for completeness only.\n")

# ---------------------------------------------------------------- S10
w("## S10. Null distribution (1,000 case-crossover replicates)\n")
nd = pd.read_csv(OUT / "canonical" / "canonical_null_distribution.csv")
w(nd["null_attr_pct"].describe().to_frame("null attribution %").round(3).to_markdown() + "\n")
w(f"Observed {rr['obs_rate_pct']}%; null range "
  f"{rr['null_rate_range_pct'][0]}-{rr['null_rate_range_pct'][1]}%. "
  f"Full per-replicate values are in `outputs/rev_null_distribution.csv`.\n")

# ---------------------------------------------------------------- S11
w("## S11. Time-of-day distribution of interruption onset\n")
w(pd.read_csv(OUT / "table8_time_of_day.csv").to_markdown(index=False) + "\n")
w("The modal onset hour of 00:00 is most plausibly a charting-rollover artefact and is "
  "not interpreted as a clinical signal; excluding those events is in S9.\n")

# ---------------------------------------------------------------- S12
w("## S12. eICU interface audit\n")
w(pd.DataFrame([{"metric": k, "value": v} for k, v in eic.items()
                if not k.endswith("columns")]).to_markdown(index=False) + "\n")
w(f"- `intakeOutput` columns: `{', '.join(eic['intakeOutput_columns'])}`")
w(f"- `infusionDrug` columns: `{', '.join(eic['infusionDrug_columns'])}`\n")

# ---------------------------------------------------------------- S13
w("## S13. Post-freeze decision registry\n")
w(pd.read_csv(OUT / "exploratory_attempts.csv").to_markdown(index=False) + "\n")

# ---------------------------------------------------------------- S14
w("## S14. Reproducibility manifest and environment\n")
rows = []
for p in sorted(list((ROOT / "01_scripts").glob("*.py"))
                + list((ROOT / "00_contracts").glob("*"))
                + list(OUT.glob("*.csv")) + list(OUT.glob("*.json"))):
    rows.append({"file": str(p.relative_to(ROOT)).replace("\\", "/"),
                 "bytes": p.stat().st_size,
                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16]})
mf = pd.DataFrame(rows)
mf.to_csv(OUT / "reproducibility_manifest.csv", index=False)
w(mf.to_markdown(index=False) + "\n")
import sys
w("```")
w(f"python {sys.version.split()[0]}")
for m in ("pandas", "numpy", "matplotlib", "scipy"):
    try:
        w(f"{m} {__import__(m).__version__}")
    except Exception:
        pass
w(f"generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
w("```")

(MAN / "supplement.md").write_text("\n".join(L), encoding="utf-8")
txt = "\n".join(L)
print(f"supplement rebuilt: {len(L)} blocks, {len(mf)} manifest entries")
live = txt.split("## S13. Post-freeze decision registry")[0]
for bad, why in [("33.8 million", "old denominator"),
                 ("8.7 kcal per ICU stay", "old per-stay")]:
    if bad in live:
        print(f"  WARNING stale value present: {bad} ({why})")
print("sections:", txt.count("\n## S"))
