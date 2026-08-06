"""N2 step 47 - validate every quantitative claim in the BMJ Quality & Safety manuscript.

Expected values are read from deposited outputs, never typed here. Also enforces the
retractions agreed in review round 6: no replication language, no patient-targeting
claim, no "prespecified before any estimate" claim, no unstable fold-range.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, REV = ROOT / "03_outputs", ROOT / "03_outputs" / "canonical", ROOT / "03_outputs" / "review6"
MS_PATH = ROOT / "07_manuscript" / "BMJQS_main_manuscript.md"
RAW = MS_PATH.read_text(encoding="utf-8")
MS = re.sub(r"\s+", " ", RAW)

C = json.load(open(CAN / "canonical_primary.json"))
CLS = pd.read_csv(CAN / "canonical_class_results.csv").set_index("class")
ERA = pd.read_csv(CAN / "canonical_temporal_transport.csv")
TC = json.load(open(CAN / "canonical_transport_clinical.json"))
R6 = json.load(open(REV / "review6_recompute.json"))
S6 = json.load(open(REV / "review6_supplementary.json"))
SH = json.load(open(REV / "hospital_shrinkage.json"))
LF = json.load(open(REV / "like_for_like_airway.json"))
EI = json.load(open(OUT / "eicu_interface_audit.json"))
EB = json.load(open(OUT / "eicu_background_rate.json"))
EA = json.load(open(OUT / "eicu_ascertainment_diagnostic.json"))
WIN = pd.read_csv(REV / "window_definition_sensitivity.csv")
STR = pd.read_csv(REV / "gap_duration_strata.csv")
SCL = pd.read_csv(REV / "scale_and_priority_free.csv")
SEV = pd.read_csv(REV / "severity_strata.csv")
BUR = TC["burden_distribution"]
AF = R6["attributable_fraction"]["target_only"]
WT = lambda w, s: WIN[(WIN.window.str.startswith(w)) & (WIN.scope.str.startswith(s))].iloc[0]

checks = []


def chk(name, expected, present=None):
    s = str(expected)
    checks.append({"check": name, "expected": s,
                   "pass": (s in MS) if present is None else bool(present)})


# ------------------------------------------------- primary rate (target only)
tgt = WT("Span", "target")
chk("target observed rate", tgt.observed_pct)
chk("target background rate", tgt.background_pct)
chk("target excess pp", tgt.excess_pp)
chk("target excess CI", f"{tgt.ci_lo} to {tgt.ci_hi}")
chk("analysis set n", f"{C['n_analysis_set']:,}")
chk("any-class observed", C["rate"]["obs_pct"])
chk("any-class background", C["rate"]["null_pct"])
chk("any-class excess", C["rate"]["excess_pp"])
chk("p reported as inequality", "p<0.001", "p<0.001" in MS and "p = 0.001" not in MS)
chk("null maximum", R6["p_value"]["null_max_pct"])
chk("causal fraction", AF["causal_fraction_pct"])
chk("causal fraction CI", f"{AF['ci'][0]} to {AF['ci'][1]}")

# ------------------------------------------------------------------ windows
chk("in-gap excess", WT("Procedure inside", "target").excess_pp)
chk("onset +/-1h excess", WT("Onset-centred", "target").excess_pp)
chk("onset-to-2h excess", WT("Gap onset to", "target").excess_pp)
chk("pre-onset excess (negative)", f"\u2212{abs(WT('1 h before', 'target').excess_pp)}")
chk("window median length", R6["window_length_h"]["median"])
chk("window max length", int(R6["window_length_h"]["max"]))
for r in STR.itertuples():
    chk(f"stratum {r.gap_stratum} background", r.background_pct)
chk("strata excess sequence",
    ", ".join(str(x) for x in STR.excess_pp),
    all(str(x) in MS for x in STR.excess_pp))

# ------------------------------------------------------------------- energy
ref = SCL[SCL.numerator_scale.str.startswith("reference")].iloc[0]
act = SCL[SCL.numerator_scale.str.startswith("actual")].iloc[0]
chk("reference-scale kcal", f"{ref.excess_kcal:,}")
chk("reference-scale pct", ref.pct_of_shortfall)
chk("actual-scale kcal", f"{act.excess_kcal:,}")
chk("actual-scale pct", act.pct_of_shortfall)
chk("scale rates", f"{R6['scale_diagnostic']['actual_pregap_kcal_per_h']} kcal/h")
chk("reference rate per h", R6["scale_diagnostic"]["reference_kcal_per_h"])
chk("priority-free invariance stated", "exactly unchanged",
    "exactly unchanged" in MS and "<2 kcal" in MS)
chk("sensitivity min", f"{C['sensitivity_pct_min']:.2f}")
chk("sensitivity max", f"{C['sensitivity_pct_max']:.2f}")
chk("era excess range", f"{ERA.rate_excess_pp.min()} to {ERA.rate_excess_pp.max()}")
chk("era pct min", f"{ERA.pct_of_shortfall.min():.3f}")
chk("era pct max", f"{ERA.pct_of_shortfall.max():.3f}")

# ------------------------------------------------------------------ burden
for k in ("pct_stays_exactly_zero", "pct_stays_negative", "top10pct_share_of_gross_positive"):
    chk(f"burden {k}", BUR[k])
chk("gross positive", f"{BUR['gross_positive_kcal']:,}")
chk("gross negative", f"{abs(BUR['gross_negative_kcal']):,}")

# -------------------------------------------------------- hospitals / eICU
chk("tau", SH["tau_pp"])
chk("ICC", SH["icc"])
chk("shrunk p10-p90", f"{SH['shrunk_p10_p90'][0]}% to {SH['shrunk_p10_p90'][1]}%")
chk("noise-only p10-p90",
    f"{SH['sampling_noise_only_p10_p90'][0]}% to {SH['sampling_noise_only_p10_p90'][1]}%")
chk("pooled hospital rate", SH["pooled_rate_pct"])
chk("median windows per hospital", f"{SH['median_windows_per_hospital']:,}")
chk("hospitals", SH["hospitals"])
chk("eICU stays", f"{EB['eicu_stays']:,}")
chk("ascertainment r", EA["pearson_r"])
chk("ascertainment variance", f"{100*EA['r_squared']:.0f}%")
chk("airway-only eICU rate", LF["eicu_airway_only_pct"])
chk("airway-only CI", f"{LF['eicu_airway_only_ci'][0]} to {LF['eicu_airway_only_ci'][1]}")
chk("MIMIC airway rate", LF["mimic_p1_background_pct"])
chk("density ratio", LF["density_ratio_mimic_over_eicu"])
chk("eICU airway density", LF["eicu_airway_density_per_stay_day"])
chk("MIMIC airway density", LF["mimic_p1_density_per_stay_day"])
chk("pct eICU stays with airway", LF["eicu_pct_stays_with_airway_event"])
chk("doc lag median", f"{EI['doc_lag_median_min']:.0f} min")
chk("doc lag p95", f"{EI['doc_lag_p95_min']:.0f} min")
chk("doc lag pct", EI["doc_lag_pct_over_60min"])
chk("doc lag n", f"{EI['doc_lag_n']:,}")

# ------------------------------------------------- supplementary analyses
chk("never fed", f"{S6['m7_cohort']['never_fed']:,}")
chk("fed one day", f"{S6['m7_cohort']['fed_one_day']:,}")
chk("pre-init primary", S6["m7_cohort"]["pre_initiation_share_primary_pct"])
chk("pre-init relaxed", S6["m7_cohort"]["pre_initiation_share_relaxed_pct"])
chk("same formula resumed", S6["m5_validation"]["same_formula_resumed_pct"])
chk("same formula and order", S6["m5_validation"]["same_formula_and_order_pct"])
chk("formula switch", S6["m5_validation"]["formula_switch_pct"])
chk("midnight artifact", S6["m5_validation"]["midnight_artifact_pct"])
chk("E-value", S6["m11"]["e_value"])
chk("risk ratio", S6["m11"]["risk_ratio"])
chk("severity strata range",
    f"{SEV.excess_pp.min()} pp", f"{SEV.excess_pp.min()}" in MS and f"{SEV.excess_pp.max()}" in MS)

# ------------------------------------------------- retractions and structure
# ban only AFFIRMATIVE replication claims. The manuscript must remain able to say
# that the prespecified replication FAILED, and "1,000 replicates" is the draw count.
BANNED = [("this replicated", "replication claim"),
          ("replicating across", "replication claim"),
          ("two independent databases", "replication claim"),
          ("external validation", "validation claim"),
          ("Same answer", "two-database slogan"),
          ("stand to gain nothing", "patient-targeting claim"),
          ("29-fold", "unstable fold range"),
          ("before any estimate was computed", "overstated prespecification")]
for tok, why in BANNED:
    chk(f"retracted: {why}", f"no '{tok}'", tok not in MS)
chk("no replication claimed explicitly", "-", "we make no claim of replication" in MS)
chk("EHR-attribution scope limited", "-",
    "does not evaluate, and cannot invalidate, reasons recorded prospectively" in MS)
chk("prespecification described honestly", "-",
    "not** a prespecified confirmatory analysis" in MS)
chk("spread not read as care quality", "-",
    "must not be read as variation in quality of care" in MS)
chk("nutrition-support cohort stated", "-", "not an ICU cohort" in MS)
chk("immortal time disclosed", "-", "immortal-time selection" in MS)
chk("key messages box present", "-", "## Key messages" in RAW)
nref = len(re.findall(r"^\d+\.\s", RAW.split("## References", 1)[1], re.M))
chk("references", nref, nref >= 25)
chk("Vancouver style", "-",
    bool(re.search(r"\d{4};\d+:", RAW)) and "(2009)" not in RAW)


def wc(s):
    return sum(1 for w in re.sub(r"[*`]", "", s).split() if re.search(r"[A-Za-z0-9]", w))


ab = wc(RAW.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0])
bd = wc(RAW.split("## Introduction", 1)[1].split("## References", 1)[0])
chk("abstract <= 250 words", ab, ab <= 250)
chk("main text <= 4000 words", bd, bd <= 4000)

df = pd.DataFrame(checks)
df.to_csv(OUT / "bmjqs_validation.csv", index=False)
print(df.to_string(index=False))
print(f"\nPASS {int(df['pass'].sum())}/{len(df)}")
print(f"abstract {ab} words | main text {bd:,} words | refs {nref}")
f = df[~df["pass"]]
if len(f):
    print("\n=== FAILURES ===")
    print(f.to_string(index=False))
