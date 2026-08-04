"""N2 step 28 - fourth-round review corrections; all numbers from canonical only."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
MS = ROOT / "07_manuscript" / "FrontNutr_main_manuscript.md"
OUT = ROOT / "03_outputs"
C = json.load(open(OUT / "canonical" / "canonical_primary.json"))
cls = {r["class"]: r for r in
       csv.DictReader(open(OUT / "canonical" / "canonical_class_results.csv", encoding="utf-8"))}
dn = json.load(open(OUT / "rev3_day_preserving_null.json"))
t = MS.read_text(encoding="utf-8")

# de-render citations so numbering regenerates after edits
om = {int(x["number"]): x["key"] for x in
      csv.DictReader(open(OUT / "citation_order_check.csv", encoding="utf-8"))}
Nref = len(om)
a, b = t.index("\n## References\n"), t.index("\n## Data availability statement")
t = t[:a] + t[b:]


def back(m):
    nums = []
    for part in re.split(r",\s*", m.group(1)):
        rr = re.match(r"^(\d+)\s*[\u2013-]\s*(\d+)$", part.strip())
        if rr:
            nums += list(range(int(rr.group(1)), int(rr.group(2)) + 1))
        elif part.strip().isdigit():
            nums.append(int(part.strip()))
    if not nums or any(x < 1 or x > Nref for x in nums):
        return m.group(0)
    return "{{" + ",".join(om[x] for x in nums) + "}}"


t = re.sub(r" \((\d+(?:[,\u2013\-\s]+\d+)*)\)", back, t)

E = f"{C['target_excess_kcal']:,.0f}"
CI = f"{C['target_excess_ci'][0]:,.0f}\u2013{C['target_excess_ci'][1]:,.0f}"
PCT = f"{C['target_pct']:.2f}"
PCTCI = f"{C['target_pct_ci'][0]:.2f}\u2013{C['target_pct_ci'][1]:.2f}"
PER = str(C["target_per_stay"])
OBS = f"{C['target_obs_kcal']:,.0f}"
NUL = f"{C['target_null_kcal']:,.0f}"
SMIN, SMAX = C["sensitivity_pct_min"], C["sensitivity_pct_max"]
P0E = f"{abs(C['p0_energy_excess_kcal']):,.0f}"
P0CI = f"{C['p0_energy_ci'][0]:,.0f} to {C['p0_energy_ci'][1]:,.0f}"

SUBS = [
# ---- abstract: canonical numbers + drop the "conservative" claim
("""Chance-corrected excess energy across the five candidate classes was 114,660 kcal (95% CI
84,948\u2013145,360) \u2014 **0.18% of the shortfall, or 16.7 kcal per ICU stay**. A complementary
null preserving ICU day gave a larger excess (0.34%), so the primary estimate is
conservative.""",
 f"""Chance-corrected excess energy across the five candidate classes was {E} kcal (95% CI
{CI}) \u2014 **{PCT}% of the shortfall, or {PER} kcal per ICU stay**; {SMIN:.2f}\u2013{SMAX:.2f}%
across sensitivity specifications. A complementary across-patient null preserving ICU day
gave {dn['pct_of_shortfall']:.2f}%."""),

# ---- results 3.5 wording and canonical numbers
("""Running the energy pipeline through the null across the five target classes gives
observed excess energy of 492,113 kcal against a null of
377,453 kcal. The **chance-corrected excess is
114,660 kcal (95% CI 84,948\u2013145,360)** \u2014 clearly distinguishable from zero, and equal to
**0.18% of the 64.9 million kcal shortfall
(0.13\u20130.22%), or 16.7 kcal per ICU stay** (Figure 4A). Under the complementary
day-preserving null the excess was 221,920 kcal
(0.34% of the shortfall), so the conclusion does not depend on
which null is used.""",
 f"""Running the energy pipeline through the null across the five target classes gives
observed **assigned** energy of {OBS} kcal against a null of {NUL} kcal. The
**chance-corrected excess is {E} kcal (95% CI {CI})** \u2014 clearly distinguishable from zero,
and equal to **{PCT}% of the 64.9 million kcal shortfall ({PCTCI}%), or {PER} kcal per ICU
stay** (Figure 4A). Under the complementary across-patient null the excess was
{dn['energy_excess_kcal']:,.0f} kcal ({dn['pct_of_shortfall']:.2f}% of the shortfall). The
conclusion does not depend on which null is used, although the two nulls are not
interchangeable (see 4.1)."""),

# ---- results 3.6 canonical range
("""The chance-corrected share remained between 0.14% and 0.35% of the shortfall under every
specification tested. Varying the defensible fasting window from 0 to 8 h moved it from
0.347% to 0.140%; restricting to enteral-only stays gave 0.179%, excluding midnight-onset
interruptions 0.167%, alternative class-priority rules 0.152\u20130.191%, and reference targets
of 20 and 30 kcal/kg/day 0.241% and 0.138%.""",
 f"""The chance-corrected share remained between {SMIN:.2f}% and {SMAX:.2f}% of the
shortfall under every specification tested. Varying the defensible fasting window from 0 to
8 h moved it from 0.344% to 0.141%; restricting to enteral-only stays gave 0.178%,
excluding midnight-onset interruptions 0.165%, alternative class-priority rules
0.155\u20130.192%, and reference targets of 20 and 30 kcal/kg/day 0.242% and 0.139%."""),

# ---- results 3.3: remove the "conservative / opposite direction" claim
("""Under the complementary null that preserves ICU day rather than patient identity, the null
rate was 21.2% and the excess 17.7 pp. Procedure density
is strongly concentrated on ICU day 1 (Supplementary Material), so a null that does not
hold patient identity fixed absorbs less of the shared patient-level intensity of
procedures and interruptions. The within-stay design is therefore the **conservative**
choice, and the concern that failing to preserve day of stay might inflate the estimate
points in the opposite direction.""",
 """Under the complementary across-patient null, which preserves ICU day and clock hour but
exchanges procedure timelines between patients, the null rate was 21.2% and the excess
17.7 pp. Procedure density is strongly concentrated on ICU day 1 (Supplementary Material),
so ICU-day structure is real. However, the difference between the two estimates cannot be
attributed to day-of-stay alignment alone: the complementary design also removes
patient-level matching, and patients differ in ICU type, severity, ventilation status,
surgical status, procedure propensity and recording density. We therefore treat the two
designs as complementary sensitivity analyses under different exchangeability assumptions,
not as lower and upper bounds."""),

# ---- results 3.4 P0: soften causal attribution, add scale qualifier
("""Diagnostics locate the cause in the exclusive-assignment rule rather than in
residual confounding of the target classes: evaluated **non-exclusively**, P0 energy is
null (\u221218,798 kcal, 95% CI \u221254,535 to 13,356), and the negative excess concentrates almost
entirely in 12\u201324 h gaps (\u221247,809 of \u221254,612 kcal) \u2014 the long, high-energy interruptions
that the priority rule reassigns away from P0 whenever a candidate procedure is also
present.""",
 f"""Diagnostics suggest this is at least partly explained by competition under exclusive
priority assignment rather than by residual confounding of the target classes: evaluated
**non-exclusively**, P0 energy is null (\u221218,798 kcal, 95% CI \u221254,535 to 13,356), and the
negative excess concentrates almost entirely in 12\u201324 h gaps (\u221247,809 of {P0E} kcal) \u2014 the
long, high-energy interruptions that the priority rule reassigns away from P0 whenever a
candidate procedure is also present. We cannot exclude that the same competition also
loads high-energy gaps onto the target classes, and we therefore do not claim the target
estimate is free of residual non-exchangeability on the energy scale."""),

("""Under priority assignment its chance-corrected
energy was \u221254,612 kcal (95% CI \u221283,306 to \u221228,676), which
excludes zero.""",
 f"""Under priority assignment its chance-corrected energy was \u2212{P0E} kcal (95% CI {P0CI}),
which excludes zero."""),

("""The rule is positive where fasting is clinically expected and null where it is not.""",
 """The rule is positive where a procedural link is clinically plausible or a defensible
fasting window can be specified, and null where neither applies."""),

("""**negative-control class (+0.0 pp, \u22121.0 to 1.0)** all had intervals including
zero on this scale.""",
 """**negative-control class (+0.0 pp, \u22121.0 to 1.0)** all had intervals including zero on the
attribution-rate scale."""),

# ---- discussion: order-of-magnitude error
("""The difference between
those two procedures was an order of magnitude in our own data.""",
 """The two procedures produced materially different point estimates in our own data \u2014
roughly a factor of two."""),

# ---- discussion: transport causal wording
("""and transport is independently recognised as a period of elevated risk and disrupted
care{{parmentier2013,schwebel2013}}; the nutritional loss attributable to it is
nonetheless small, as is that around bedside procedures under
sedation{{trach2026}}.""",
 """and transport is independently recognised as a period of elevated risk and disrupted
care{{parmentier2013,schwebel2013}}; the excess energy assigned to transport-associated
interruption is nonetheless small, as is that around bedside procedures under
sedation{{trach2026}}."""),

# ---- limitations: oral intake, spelled out
("""Charted *Paused* and *Stopped* events may represent order changes, formula switches or
documentation practices rather than bedside cessation;""",
 """Structured oral-intake documentation was sparse and may not capture all calories consumed
orally, particularly after cessation of artificial nutrition support. The all-ICU-hour
denominator may therefore overestimate the total enteral/parenteral support shortfall and,
correspondingly, understate the proportional contribution of interruptions. The estimand
should be read as recorded enteral and parenteral nutrition-support delivery relative to a
standardized reference, not as total caloric intake. Even under the alternative denominator
and null specifications tested, the procedural share remained below 0.4%.

Charted *Paused* and *Stopped* events may represent order changes, formula switches or
documentation practices rather than bedside cessation;"""),

# ---- prior work: consistent with the cover letter
("""Estimands, exposures, outcome variables and source tables are disjoint:
that work analysed serum phosphate and phosphate administration; the present work analyses
nutrition infusion, derived-ingredient and procedure records. Neither result depends on
the other.""",
 """Some cohort-building inputs and the nutrition item definitions are shared. The research
question, primary exposure, outcome variables, null models, analysis tables and reported
results are distinct: that work analysed serum phosphate and phosphate administration; the
present work analyses nutrition infusion, derived-ingredient and procedure records. Neither
result depends on the other."""),
]

miss = []
for old, new in SUBS:
    if old in t:
        t = t.replace(old, new, 1)
    else:
        miss.append(old[:65].replace("\n", " "))
MS.write_text(t, encoding="utf-8")
print(f"applied {len(SUBS) - len(miss)}/{len(SUBS)}")
for m in miss:
    print("  NOT FOUND:", m)
