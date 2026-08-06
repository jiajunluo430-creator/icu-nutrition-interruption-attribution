"""N2 step 51 - Additional file 1 for BMJ Quality & Safety.

Starts from the validated Critical Care additional file (S1-S17), then:
  - prepends the STROBE checklist, which BMJ requires and which was previously claimed
    in the text but never supplied
  - adds S18 window definitions, S19 scale and priority-free estimand, S20 hospital
    shrinkage, S21 like-for-like airway comparison, S22 cohort selection,
    S23 exposure validation, S24 severity and E-value
  - rewrites S12 so the withdrawn replication claim cannot survive in the appendix
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, REV = ROOT / "03_outputs", ROOT / "03_outputs" / "canonical", ROOT / "03_outputs" / "review6"
MAN = ROOT / "07_manuscript"

SRC = (MAN / "CritCare_additional_file.md").read_text(encoding="utf-8")
R6 = json.load(open(REV / "review6_recompute.json"))
S6 = json.load(open(REV / "review6_supplementary.json"))
SH = json.load(open(REV / "hospital_shrinkage.json"))
LF = json.load(open(REV / "like_for_like_airway.json"))
WIN = pd.read_csv(REV / "window_definition_sensitivity.csv")
STR = pd.read_csv(REV / "gap_duration_strata.csv")
SCL = pd.read_csv(REV / "scale_and_priority_free.csv")
SEV = pd.read_csv(REV / "severity_strata.csv")
VAL = pd.read_csv(REV / "interruption_validation.csv")
VST = pd.read_csv(REV / "interruption_validation_strata.csv")
COH = pd.read_csv(REV / "cohort_selection_m7.csv")

STROBE = [
    ("1a", "Study design indicated in title/abstract", "Title; Abstract"),
    ("1b", "Balanced summary in abstract", "Abstract"),
    ("2", "Scientific background and rationale", "Introduction"),
    ("3", "Specific objectives", "Introduction, final paragraph"),
    ("4", "Study design presented early", "Methods, Design and analysis plans"),
    ("5", "Setting, locations, periods", "Methods, Design; Cohort"),
    ("6a", "Eligibility criteria and selection", "Methods, Cohort; figure 1; table 1"),
    ("7", "Variables defined", "Methods, Interruptions and attribution; Energy"),
    ("8", "Data sources and measurement", "Methods; Additional file S4, S12"),
    ("9", "Efforts to address bias",
     "Methods, Background rate; negative control; Results, E-value; S23, S24"),
    ("10", "Study size", "Methods, Cohort; figure 1"),
    ("11", "Quantitative variables handled", "Methods, Energy; S18 window definitions"),
    ("12a", "Statistical methods", "Methods, Background rate; Energy"),
    ("12b", "Subgroups and interactions", "Results, severity strata; S24"),
    ("12c", "Missing data", "Methods, Cohort; S22"),
    ("12e", "Sensitivity analyses", "Results; S9, S18, S19"),
    ("13", "Participants at each stage", "figure 1; S2 cohort flow"),
    ("14", "Descriptive data", "table 1; S22"),
    ("15", "Outcome data", "Results"),
    ("16", "Main results with precision", "Results; tables 1-2; figures 2-3"),
    ("17", "Other analyses", "Results; S15-S24"),
    ("18", "Key results summarised", "Discussion, first paragraph"),
    ("19", "Limitations", "Discussion, Limitations"),
    ("20", "Interpretation", "Discussion"),
    ("21", "Generalisability", "Discussion, Limitations"),
    ("22", "Funding", "Declarations"),
]
strobe_md = ("## S0. STROBE checklist\n\nCohort-study checklist. Item numbers follow the "
             "STROBE statement.\n\n| Item | Recommendation | Where reported |\n|---|---|---|\n"
             + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in STROBE) + "\n")

wt = WIN[WIN.scope.str.startswith("target")]
wa = WIN[WIN.scope.str.startswith("any")]


def tbl(df, cols, hdr):
    out = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in df.itertuples():
        out.append("| " + " | ".join(str(getattr(r, c)) for c in cols) + " |")
    return "\n".join(out)


extra = f"""
## S18. Attribution window definitions

The primary window ran from 1 h before gap onset to 1 h after gap end, i.e. the gap
duration plus 2 h: median {R6['window_length_h']['median']} h
(IQR {R6['window_length_h']['iqr'][0]}\u2013{R6['window_length_h']['iqr'][1]}), maximum
{R6['window_length_h']['max']} h. Earlier drafts described this as a flat \u00b11 h window,
which was wrong (registry E35). Because feeding is stopped *in preparation for* a
procedure, a causally coherent narrow window places the procedure inside the gap; a window
before gap onset reverses the causal direction and is shown only for completeness.

### Target classes only

{tbl(wt, ["window", "observed_pct", "background_pct", "excess_pp", "ci_lo", "ci_hi"],
     ["Window", "Observed %", "Background %", "Excess pp", "CI low", "CI high"])}

### Any class, including the negative control

{tbl(wa, ["window", "observed_pct", "background_pct", "excess_pp", "ci_lo", "ci_hi"],
     ["Window", "Observed %", "Background %", "Excess pp", "CI low", "CI high"])}

### By gap duration

{tbl(STR, ["gap_stratum", "n", "mean_window_h", "observed_pct", "background_pct", "excess_pp"],
     ["Gap", "n", "Mean window h", "Observed %", "Background %", "Excess pp"])}

Background rises with window length but the excess falls, so the excess is not produced
by long windows.

## S19. Numerator scale and the priority rule

The denominator is the shortfall against a 25 kcal/kg/day reference. An earlier numerator
used the actual pre-interruption infusion rate, so the ratio divided two different scales:
{R6['scale_diagnostic']['reference_kcal_per_h']} kcal/h on the reference scale against
{R6['scale_diagnostic']['actual_pregap_kcal_per_h']} kcal/h on the actual scale, a factor
of {R6['scale_diagnostic']['ratio']} (registry E33).

{tbl(SCL, ["numerator_scale", "observed_kcal", "background_kcal", "excess_kcal",
           "pct_of_shortfall", "kcal_per_stay"],
     ["Numerator scale", "Observed kcal", "Background kcal", "Excess kcal",
      "% of shortfall", "kcal/stay"])}

**Priority-rule invariance.** Removing the exclusive priority rule leaves the target total
unchanged at {R6['priority_rule_invariance']['priority_free_kcal']:,} kcal (difference
{R6['priority_rule_invariance']['difference_kcal']} kcal, asserted in code).
{R6['priority_rule_invariance']['explanation']}

## S20. Between-hospital variation with shrinkage

{chr(10).join(f"- {k.replace('_', ' ')}: {v}" for k, v in SH.items())}

## S21. Like-for-like comparison with eICU-CRD

MIMIC-IV class P1 comprises six itemids, all airway: extubation, intubation,
bronchoscopy, percutaneous and open tracheostomy, and bedside surgical procedure. It
contains no sedation infusions. An earlier eICU class had added
{LF['eicu_airway_events']:,} airway events **and** sedation/neuromuscular-blocker infusion
starts, so most of its events had no counterpart in the comparator. Restricted to airway
events alone:

| Quantity | MIMIC-IV | eICU-CRD |
|---|---|---|
| Background co-occurrence rate | {LF['mimic_p1_background_pct']}% | {LF['eicu_airway_only_pct']}% (95% CI {LF['eicu_airway_only_ci'][0]}\u2013{LF['eicu_airway_only_ci'][1]}) |
| Airway events | {LF['mimic_p1_events']:,} | {LF['eicu_airway_events']:,} |
| Events per stay-day | {LF['mimic_p1_density_per_stay_day']} | {LF['eicu_airway_density_per_stay_day']} |
| Stays recording any airway event | \u2013 | {LF['eicu_pct_stays_with_airway_event']}% |

{LF['verdict']}

## S22. Cohort selection and excluded stays

{tbl(COH, ["group", "stays", "median_age", "median_los_h", "in_hospital_death_pct",
           "median_pre_initiation_h", "pre_init_share_of_obs_pct"],
     ["Group", "Stays", "Median age", "Median LOS h", "In-hospital death %",
      "Median pre-initiation h", "Pre-initiation share of observed hours %"])}

Relaxing to \u22651 nutrition day raises the pre-initiation share of observed hours from
{S6['m7_cohort']['pre_initiation_share_primary_pct']}% to
{S6['m7_cohort']['pre_initiation_share_relaxed_pct']}%. {S6['m7_cohort']['direction']}
{S6['m7_cohort']['immortal_time']}

Note that never-fed stays cannot be assumed underfed: many will have been eating orally,
which MIMIC-IV records sparsely.

## S23. Algorithmic validation of the interruption definition

{tbl(VAL, list(VAL.columns), [c.replace('_', ' ') for c in VAL.columns])}

By gap duration:

{tbl(VST, list(VST.columns), [c.replace('_', ' ') for c in VST.columns])}

{S6['m5_validation']['caveat']}

## S24. Severity strata and quantitative bias analysis

{tbl(SEV, ["stratum", "n", "observed_pct", "background_pct", "excess_pp"],
     ["Stratum", "n", "Observed %", "Background %", "Excess pp"])}

Risk ratio {S6['m11']['risk_ratio']}, **E-value {S6['m11']['e_value']}**.
{S6['m11']['interpretation']}

{S6['m11']['unavailable']}

---

*Additional file 1 generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.
All values derive from the deposited canonical, external-validation and review-round-6
outputs.*
"""

# strip the withdrawn replication language from the inherited S12
t = SRC
t = t.replace("### S12.2 Why the background rate is still estimable",
              "### S12.2 What eICU can and cannot support")
t = t.replace(
    "The background co-occurrence rate is a property of **procedure density and\nwindow\nwidth**, not of nutrition records.",
    "The background co-occurrence rate is a property of **procedure density and window "
    "width**, not of nutrition records.")
old_head = t.split("\n## S1.", 1)[0]
t = strobe_md + "\n" + "\n## S1." + t.split("\n## S1.", 1)[1]
t = t.rstrip() + "\n" + extra

for banned in ("Same answer", "replicates the", "external validation of the primary"):
    assert banned not in t, f"withdrawn claim survived in the additional file: {banned}"
assert "## S0. STROBE" in t and "## S24." in t
(MAN / "BMJQS_additional_file.md").write_text(t, encoding="utf-8")
print(f"BMJQS_additional_file.md: {t.count(chr(10) + '## S')} S-sections, {len(t):,} chars")
print("ASSERT OK: STROBE present, S18-S24 added, no withdrawn claims")
