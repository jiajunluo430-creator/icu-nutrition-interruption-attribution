"""N2 step 07 - assemble supplement and reproducibility manifest."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, MAN = ROOT / "03_outputs", ROOT / "07_manuscript"

CLASS_LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic",
               "P3": "Off-unit transport", "P4": "Bedside invasive",
               "P5": "Renal replacement",
               "P0": "Bedside diagnostics (negative control)"}

adq = pd.read_csv(OUT / "table2_delivery_adequacy.csv")
attr = pd.read_csv(OUT / "table4_attribution_specificity.csv")
ex = pd.read_csv(OUT / "table5_excess_fasting.csv")
sen = pd.read_csv(OUT / "table6_sensitivity.csv")
gat = pd.read_csv(OUT / "pilot_gates.csv")
flow = pd.read_csv(OUT / "cohort_flow.csv")
reg = pd.read_csv(OUT / "exploratory_attempts.csv")
eic = json.load(open(OUT / "eicu_g6.json"))
frz = json.load(open(ROOT / "00_contracts" / "contract_freeze.json"))

L = []
w = L.append
w("# Supplementary Material\n")
w("**Most apparent procedure-related interruption of nutrition support in the ICU "
  "is chance co-occurrence**\n")
w("---\n")

w("## S1. Frozen analysis contract\n")
w(f"- Contract: `00_contracts/N2_analysis_contract_v1.md`")
w(f"- SHA-256: `{frz['contract_sha256']}`")
w(f"- Frozen (UTC): {frz['frozen_utc']}")
w(f"- Nutrition item list SHA-256: `{frz['itemids_sha256']}` ({frz['n_nutrition_itemids']} items)\n")
w("Every cohort criterion, item list, interruption rule, procedure class, attribution "
  "window, guideline-defensible fasting window, target, falsification test, and "
  "stop-loss gate was fixed in this contract before any estimate in the manuscript "
  "was computed.\n")

w("## S2. Cohort flow\n")
w(flow.to_markdown(index=False) + "\n")

w("## S3. Binding gate results\n")
g = gat.copy()
g["pass"] = g["pass"].map({True: "PASS", False: "FAIL"}).fillna("interpretive")
w(g.to_markdown(index=False) + "\n")
w("**G5 (natural experiment) failed and was dropped, not relaxed.** `ERCP (Done in "
  "unit)` has 12 events in all of MIMIC-IV v3.1 and `Portable CT scan` has none, "
  "despite both appearing in the item dictionary. No substitute pairing was "
  "introduced.\n")
w("**G6 (eICU replication) failed on semantics, not population.** eICU has 47 "
  f"hospitals with >=20 eligible stays and {eic['stays_ge_2_nutrition_days']:,} stays "
  "with >=2 nutrition days, but its intake records carry neither an infusion rate nor "
  "a status field, so paused/stopped states cannot be reconstructed.\n")

w("## S4. Delivery adequacy by ICU day\n")
a = adq.rename(columns={
    "icu_day": "ICU day", "n_stay_days": "Patient-days",
    "kcal_per_kg_median": "kcal/kg (median)", "kcal_pct_median": "Energy % target",
    "kcal_pct_q1": "Q1", "kcal_pct_q3": "Q3", "prot_pct_median": "Protein % target",
    "fed_h_median": "Feeding h (median)", "pct_days_ge80": "% days >=80%",
    "pct_days_ge100": "% days >=100%"})
w(a.to_markdown(index=False) + "\n")

w("## S5. Attribution specificity, all placebo shifts\n")
b = attr.copy()
b["label"] = b["class"].map(CLASS_LABEL)
b = b.rename(columns={
    "class": "Class", "label": "Procedure class", "n_procedure_events": "Events",
    "observed_pct": "Observed %", "placebo48_pct": "Placebo +48h %",
    "placebo_mean_pct": "Placebo mean %", "placebo_range_pct": "Placebo range %",
    "excess_pp": "Excess (pp)", "specificity_ratio": "Specificity ratio"})
w(b.to_markdown(index=False) + "\n")
w("Placebo shifts: +24 h, +48 h (primary), +72 h, and -48 h. Per-class rates are "
  "unconditional (the priority rule is not applied), so classes may overlap.\n")

w("## S6. Excess fasting by class\n")
c = ex.copy()
c["label"] = c["proc_class"].map(CLASS_LABEL)
c["survives_placebo"] = c["proc_class"].map(
    lambda k: "yes" if attr.set_index("class").loc[k, "excess_pp"] > 0.5 else "NO - chance")
c = c[["proc_class", "label", "n", "defensible_h", "gap_median", "excess_median",
       "excess_total", "excess_kcal_total", "survives_placebo"]]
c = c.rename(columns={
    "proc_class": "Class", "label": "Procedure class", "n": "Interruptions",
    "defensible_h": "Defensible window (h)", "gap_median": "Median gap (h)",
    "excess_median": "Median excess (h)", "excess_total": "Total excess (h)",
    "excess_kcal_total": "Total excess (kcal)",
    "survives_placebo": "Attribution survives placebo"})
w(c.to_markdown(index=False) + "\n")
w("Rows marked *NO - chance* are shown only to illustrate what an uncorrected "
  "attribution would have concluded. They are **not** avoidable loss.\n")

w("## S7. Sensitivity analyses\n")
w(sen.rename(columns={"analysis": "Analysis", "metric": "Metric",
                      "value": "Value"}).to_markdown(index=False) + "\n")

w("## S8. Post-freeze decision registry\n")
w(reg.to_markdown(index=False) + "\n")

w("## S9. eICU interface audit\n")
w("```json")
w(json.dumps({k: v for k, v in eic.items() if not k.endswith("columns")}, indent=2))
w("```\n")
w(f"- `intakeOutput` columns: `{', '.join(eic['intakeOutput_columns'])}`")
w(f"- `infusionDrug` columns: `{', '.join(eic['infusionDrug_columns'])}`\n")

ci7 = pd.read_csv(OUT / "table7_attribution_ci.csv")
w("## S9b. Attribution with bootstrap 95% CIs (circular-shift null)\n")
w(ci7.rename(columns={"class": "Class", "label": "Procedure class",
                      "observed_pct": "Observed %", "observed_ci": "Observed 95% CI",
                      "null_pct": "Circular null %", "excess_pp": "Excess (pp)",
                      "excess_ci": "Excess 95% CI",
                      "significant": "CI excludes 0"}).to_markdown(index=False) + "\n")
w("2,000 bootstrap replicates resampling ICU stays. The circular shift preserves the "
  "number and density of in-window procedures exactly; the contract's simple +48 h "
  "shift does not, and inflates the excess (10.8 pp vs 8.7 pp).\n")

nl = pd.read_csv(OUT / "null_distribution.csv")
w("## S9c. Empirical null distribution (30 circular shifts)\n")
w(nl.rename(columns={"shift_h": "Shift (h)",
                     "null_attr_pct": "Attribution under null (%)"})
  .round(2).to_markdown(index=False) + "\n")

tod = pd.read_csv(OUT / "table8_time_of_day.csv")
w("## S9d. Time-of-day distribution of interruption onset\n")
w(tod.rename(columns={"hour": "Hour of onset", "attributed": "Attributed",
                      "unattributed": "Unattributed"}).to_markdown(index=False) + "\n")
w("The modal onset hour of 00:00 is most plausibly a charting-rollover artefact and is "
  "not interpreted as a clinical signal.\n")

w("## S10. Reproducibility manifest\n")
rows = []
for p in sorted(list((ROOT / "01_scripts").glob("*.py"))
                + list((ROOT / "00_contracts").glob("*"))
                + list(OUT.glob("*.csv")) + list(OUT.glob("*.json"))
                + list((ROOT / "04_figures").glob("*.pdf"))):
    rows.append({"file": str(p.relative_to(ROOT)).replace("\\", "/"),
                 "bytes": p.stat().st_size,
                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16]})
mf = pd.DataFrame(rows)
mf.to_csv(OUT / "reproducibility_manifest.csv", index=False)
w(mf.to_markdown(index=False) + "\n")

import sys
w("## S11. Environment\n")
w("```")
w(f"python {sys.version.split()[0]}")
for m in ("pandas", "numpy", "matplotlib", "scipy"):
    try:
        w(f"{m} {__import__(m).__version__}")
    except Exception:
        pass
w(f"generated {datetime.now(timezone.utc).isoformat()}")
w("```")

(MAN / "supplement.md").write_text("\n".join(L), encoding="utf-8")
print(f"supplement written: {len(L)} blocks, {len(mf)} manifest entries")
print(f"-> {MAN / 'supplement.md'}")
