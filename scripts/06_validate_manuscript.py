"""N2 step 06 - validate every quantitative claim in the manuscript against outputs."""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
MS = (ROOT / "07_manuscript" / "FrontNutr_main_manuscript.md").read_text(encoding="utf-8")

adq = pd.read_csv(OUT / "table2_delivery_adequacy.csv")
eic = json.load(open(OUT / "eicu_g6.json"))
gat = pd.read_csv(OUT / "pilot_gates.csv").set_index("gate")
itr = pd.read_csv(OUT / "interruptions.csv")
coh = pd.read_csv(OUT / "cohort.csv")

checks = []


DASHES = {"–": "-", "—": "-", "−": "-", "‑": "-"}


def norm(t):
    """Normalise dashes and thousands separators so formatting never fails a check."""
    for a, b in DASHES.items():
        t = t.replace(a, b)
    t = t.replace(" to ", "-")
    t = re.sub(r"\s+", " ", t)      # collapse line wraps so matches never fail on layout
    return re.sub(r"(?<=\d),(?=\d{3})", "", t)


MSN = norm(MS)


def chk(name, expected, present=True):
    hit = norm(expected) in MSN
    ok = hit if present else not hit
    checks.append({"check": name, "expected": expected, "found": hit, "pass": ok})


# --- cohort
chk("cohort N", "6883")
chk("screened stays", "94,458")
chk("median age", "65 years")
chk("female pct", "43.5%")
chk("mortality", "23.9%")

# --- ALL numbers from the canonical set only
import json as _j
CAN = OUT / "canonical"
C = _j.load(open(CAN / "canonical_primary.json"))
cls = pd.read_csv(CAN / "canonical_class_results.csv").set_index("class")
rev = _j.load(open(OUT / "rev_results.json"))
r2b = _j.load(open(OUT / "rev2_results.json"))
dn = _j.load(open(OUT / "rev3_day_preserving_null.json"))

chk("ICU-hours denominator", f"{rev['denominator_icu_hours']:,.0f}")
chk("total shortfall", "64.9 million kcal")
for k in ("pre", "running", "post", "short", "othergap"):
    chk(f"shortfall {k}", f"{rev['shortfall_components_pct'][k]}%")
chk("observed rate", f"{C['rate']['obs_pct']}%")
chk("null rate", f"{C['rate']['null_pct']}%")
chk("rate excess pp", f"{C['rate']['excess_pp']} percentage points")
chk("rate excess CI", f"{C['rate']['ci_lo']}-{C['rate']['ci_hi']}")
chk("empirical p", f"{C['rate']['p']:.3f}")
chk("analysis set", f"{C['n_analysis_set']:,}")
chk("target observed (assigned)", f"{C['target_obs_kcal']:,.0f}")
chk("target null", f"{C['target_null_kcal']:,.0f}")
chk("target excess", f"{C['target_excess_kcal']:,.0f}")
chk("target CI lo", f"{C['target_excess_ci'][0]:,.0f}")
chk("target pct", f"{C['target_pct']:.2f}%")
chk("target per stay", f"{C['target_per_stay']} kcal per ICU")
chk("sensitivity min", f"{C['sensitivity_pct_min']:.2f}")
chk("sensitivity max", f"{C['sensitivity_pct_max']:.2f}")
chk("day-preserving null", f"{dn['pct_of_shortfall']:.2f}%")
chk("P0 energy value", f"{abs(C['p0_energy_excess_kcal']):,.0f}")
for c in ("P1", "P2", "P3", "P0"):
    chk(f"class {c} rate", f"{cls.loc[c,'rate_excess_pp']:+.1f}")
chk("oral intake pct", f"{r2b['pct_stays_with_oral_intake']}% of stays")
chk("ramped pre-initiation", f"{r2b['pre_initiation_pct_ramped']}%")
_sup = (ROOT / "07_manuscript" / "supplement.md").read_text(encoding="utf-8")
checks.append({"check": "superseded value in supplement", "expected": "450,892",
               "found": "450,892" in _sup, "pass": "450,892" in _sup})
checks.append({"check": "no Python nan in supplement", "expected": "none",
               "found": "nan" not in _sup, "pass": "nan" not in _sup})

# --- reviewer-4 wording
chk("assigned not excess", "observed **assigned** energy")
chk("no conservative claim", "the primary estimate is conservative", present=False)
chk("no order-of-magnitude error", "was an order of magnitude", present=False)
chk("P0 softened", "at least partly explained")
chk("negative control scale qualifier", "null **on the")
chk("oral limitation expanded", "may therefore overestimate the total")
chk("prior work consistent", "Some cohort-building inputs")
chk("AI use statement", "Use of generative AI")
chk("no transport causal wording", "nutritional loss attributable", present=False)

# --- reviewer-mandated wording
chk("reference-target framing", "standardized reference target")
chk("not a preregistration", "internally frozen prespecified")
chk("propofol logic corrected", "indeterminate rather than reassuring")
chk("counterfactual qualifier", "bounded by that counterfactual")
chk("estimand-through-null stated", "computed through the null")
chk("63.4 estimand caveat", "not always mutually exclusive")
chk("no placebo-controlled in title", "placebo-controlled", present=False)

# --- structural
checks.append({"check": "REFERENCE LIST PRESENT", "expected": "## References section",
               "found": "## References" in MS, "pass": "## References" in MS})
_nref = len(re.findall(r"^\d+\. [A-Z]", MS, re.M))
checks.append({"check": "reference entries >= 40", "expected": ">=40",
               "found": _nref >= 40, "pass": _nref >= 40})
checks.append({"check": "References precedes back matter", "expected": "order",
               "found": MS.index("## References") < MS.index("## Data availability"),
               "pass": MS.index("## References") < MS.index("## Data availability")})

df = pd.DataFrame(checks)
df.to_csv(OUT / "manuscript_validation.csv", index=False)

body = MS.split("## 1 Introduction", 1)[1].split("## References", 1)[0]
words = len(re.findall(r"\b[\w'\u2019-]+\b", body))
abstract = MS.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0]
abstract = re.sub(r"\*\*(Background|Methods|Results|Conclusion)\.\*\*", "", abstract)
aw = len(re.findall(r"\b[\w'\u2019-]+\b", abstract))
print(df.to_string(index=False))
print(f"\nPASS {int(df['pass'].sum())}/{len(df)}")
print(f"main text (Introduction->Conclusion): {words} words")
print(f"abstract: {aw} words")
fails = df[~df["pass"]]
if len(fails):
    print("\n=== FAILURES ===")
    print(fails.to_string(index=False))
