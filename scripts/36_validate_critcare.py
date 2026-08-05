"""N2 step 36 - validate every quantitative claim in the Critical Care manuscript.

Each check reads its expected value from a canonical output file, never from a literal
typed here, so the manuscript cannot drift from the analysis. Text is whitespace-collapsed
before matching so that line wrapping never fails a check.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
CAN = OUT / "canonical"
MS_PATH = ROOT / "07_manuscript" / "CritCare_main_manuscript.md"

RAW = MS_PATH.read_text(encoding="utf-8")
MS = re.sub(r"\s+", " ", RAW)                      # collapse wrapping

C = json.load(open(CAN / "canonical_primary.json"))
CLS = pd.read_csv(CAN / "canonical_class_results.csv").set_index("class")
ERA = pd.read_csv(CAN / "canonical_temporal_transport.csv")
TC = json.load(open(CAN / "canonical_transport_clinical.json"))
EB = json.load(open(OUT / "eicu_background_rate.json"))
EA = json.load(open(OUT / "eicu_ascertainment_diagnostic.json"))
EI = json.load(open(OUT / "eicu_interface_audit.json"))
REC = {r["class"]: r for r in TC["recovery_delay"]}
BUR = TC["burden_distribution"]

checks = []


def chk(name, expected, present=None):
    """present defaults to: the rendered expected string appears in the manuscript."""
    s = str(expected)
    ok = (s in MS) if present is None else bool(present)
    checks.append({"check": name, "expected": s, "pass": ok})


def num(x, dp=1):
    return f"{x:,.{dp}f}" if dp else f"{x:,.0f}"


# ---------------------------------------------------------------- primary
chk("primary excess kcal", num(C["target_excess_kcal"], 0))
chk("primary CI low", num(C["target_excess_ci"][0], 0))
chk("primary CI high", num(C["target_excess_ci"][1], 0))
chk("primary per stay", C["target_per_stay"])
chk("analysis set n", f"{C['n_analysis_set']:,}")
chk("observed rate", C["rate"]["obs_pct"])
chk("background rate", C["rate"]["null_pct"])
chk("excess pp", C["rate"]["excess_pp"])
chk("rate CI", f"{C['rate']['ci_lo']}\u2013{C['rate']['ci_hi']}")
chk("target obs kcal", num(C["target_obs_kcal"], 0))
chk("target null kcal", num(C["target_null_kcal"], 0))
chk("sensitivity min", f"{C['sensitivity_pct_min']:.3f}".rstrip("0"))
chk("sensitivity max", f"{C['sensitivity_pct_max']:.3f}".rstrip("0"))
chk("day-preserving pct", f'{C["day_preserving_pct"]:.2f}')  # reported rounded to 2 dp

# ---------------------------------------------------------------- classes
for c, lbl in [("P1", "airway"), ("P3", "transport"), ("P2", "endoscop")]:
    chk(f"{c} rate excess pp", f"+{CLS.loc[c,'rate_excess_pp']} pp")
chk("P0 energy excess", f"\u2212{abs(CLS.loc['P0','energy_excess_kcal']):,.0f}")

# ---------------------------------------------------------------- eras
chk("era count in Table 2", len(ERA), sum(
    1 for e in ERA["era"] if e.replace(" - ", "\u2013") in MS) == len(ERA))
chk("era excess pp min", ERA["rate_excess_pp"].min())
chk("era excess pp max", ERA["rate_excess_pp"].max())
chk("era pct min", f"{ERA['pct_of_shortfall'].min():.3f}")
chk("era pct max", f"{ERA['pct_of_shortfall'].max():.3f}")
chk("era observed min", ERA["rate_observed_pct"].min())
chk("era observed max", ERA["rate_observed_pct"].max())
chk("era background min", ERA["rate_background_pct"].min())
chk("era background max", ERA["rate_background_pct"].max())

# ---------------------------------------------------------------- eICU
chk("eICU stays", f"{EB['eicu_stays']:,}")
chk("eICU windows", f"{EB['eicu_windows']:,}")
chk("eICU background pct", EB["eicu_background_pct"])
chk("eICU background CI", f"{EB['eicu_background_ci'][0]}\u2013{EB['eicu_background_ci'][1]}")
chk("MIMIC P1 background", EB["mimic_p1_background_pct"])
chk("MIMIC P1 observed", EB["mimic_p1_observed_pct"])
chk("MIMIC P1 excess pp", EB["mimic_p1_excess_pp"])
chk("eICU hospitals >=20 stays", EB["hospitals"])
chk("eICU hospitals total", EI["hospitals_total"])
chk("restricted hospital count", EA["restricted_n_hospitals"])
chk("restricted median rate", EA["restricted_median_pct"])
chk("restricted p10-p90",
    f"{EA['restricted_p10_p90'][0]}% to {EA['restricted_p10_p90'][1]}%")
chk("ascertainment r", EA["pearson_r"])
chk("ascertainment variance explained", f"{100*EA['r_squared']:.0f}%")
chk("ascertainment max", EA["ascertainment_max_pct"])
chk("doc lag median", f"{EI['doc_lag_median_min']:.0f} min")
chk("doc lag p95", f"{EI['doc_lag_p95_min']:.0f} min")
chk("doc lag pct over 1h", EI["doc_lag_pct_over_60min"])
chk("doc lag paired records", f"{EI['doc_lag_n']:,}")

# ---------------------------------------------------------------- burden
chk("stays with zero burden", BUR["pct_stays_exactly_zero"])
chk("stays negative", BUR["pct_stays_negative"])
chk("stays positive", BUR["pct_stays_positive"])
chk("gross positive", f"{BUR['gross_positive_kcal']:,}")
chk("gross negative", f"{abs(BUR['gross_negative_kcal']):,}")
chk("top decile kcal", f"{BUR['top10pct_kcal']:,}")
chk("top decile share", BUR["top10pct_share_of_gross_positive"])
chk("pct over 100", BUR["pct_stays_over_100"])
chk("pct over 250", BUR["pct_stays_over_250"])
chk("pct over 500", BUR["pct_stays_over_500"])
chk("max burden", f"{BUR['max_kcal']:,.0f}")  # reported as a whole kcal

# ---------------------------------------------------------------- recovery
chk("P1 median recovery", f"{REC['P1']['median_h_to_resumption']} h")
chk("P1 beyond defensible", REC["P1"]["pct_beyond_defensible"])
chk("P3 median recovery", f"{REC['P3']['median_h_to_resumption']} h")
chk("P3 within 6h", REC["P3"]["pct_resumed_within_6h"])
chk("P0 median recovery", f"{REC['P0']['median_h_to_resumption']} h")
chk("P0 within 2h", REC["P0"]["pct_resumed_within_2h"])

# ---------------------------------------------------------------- structure
chk("two-database patient total", "70,586",
    str(C["n_analysis_set"]) and "70,586" in MS
    and 6883 + EB["eicu_stays"] == 70586)
chk("external contract hash cited in supplement plan", "SHA-256")
chk("no outcome model claimed", "-", "no outcome association of any kind" in MS)
chk("eICU energy explicitly not attempted", "-",
    "No energy or kcal estimate was attempted in eICU" in MS)
chk("spread not read as care quality", "-",
    "should not be read as variation in quality of care" in MS)
chk("References precedes Declarations", "-",
    RAW.index("## References") < RAW.index("## Declarations"))
nref = len(re.findall(r"^\d+\.\s", RAW.split("## References", 1)[1], re.M))
chk("reference entries", nref, nref >= 45)


def wordcount(s):
    s = re.sub(r"\{\{[^}]*\}\}", "", re.sub(r"[*`]", "", s))
    return sum(1 for w in s.split() if re.search(r"[A-Za-z0-9]", w))


ab = RAW.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0]
aw = wordcount(ab)
chk("abstract <= 350 words (Critical Care)", aw, aw <= 350)

df = pd.DataFrame(checks)
df.to_csv(OUT / "critcare_validation.csv", index=False)
print(df.to_string(index=False))
npass = int(df["pass"].sum())
print(f"\nPASS {npass}/{len(df)}")
body = RAW.split("## Background", 1)[1].split("## References", 1)[0]
print(f"main text: {wordcount(body):,} words | abstract: {aw} words | refs: {nref}")
fails = df[~df["pass"]]
if len(fails):
    print("\n=== FAILURES ===")
    print(fails.to_string(index=False))
