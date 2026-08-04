"""N2 step 21 - apply the second-round review corrections to the manuscript text."""
import json
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
MS = ROOT / "07_manuscript" / "FrontNutr_main_manuscript.md"
r2 = json.load(open(ROOT / "03_outputs" / "rev2_results.json"))
t = MS.read_text(encoding="utf-8")

# strip rendered citations back to markers so numbering can restart at the Introduction
import csv
om = {int(x["number"]): x["key"] for x in
      csv.DictReader(open(ROOT / "03_outputs" / "citation_order_check.csv", encoding="utf-8"))}
N = len(om)
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
    if not nums or any(x < 1 or x > N for x in nums):
        return m.group(0)
    return "{{" + ",".join(om[x] for x in nums) + "}}"


t = re.sub(r" \((\d+(?:[,\u2013\-\s]+\d+)*)\)", back, t)

E = f"{r2['target_excess_kcal']:,.0f}"
CI = f"{r2['target_excess_ci'][0]:,.0f}\u2013{r2['target_excess_ci'][1]:,.0f}"
PCT = f"{r2['target_pct_of_shortfall']:.2f}"
PCTCI = f"{r2['target_pct_ci'][0]:.2f}\u2013{r2['target_pct_ci'][1]:.2f}"
PER = f"{r2['target_kcal_per_stay']}"
P0 = f"{abs(r2['p0_diagnostic_kcal']):,.0f}"

SUBS = [
# ---------- abstract ----------
("""Chance-corrected excess energy was 60,135 kcal (95% CI
24,335\u201398,159) \u2014 **0.09% of the
shortfall, or 8.7 kcal per ICU stay**; across all sensitivity specifications 0.06\u20130.26%.""",
 f"""Across the five candidate procedural classes, chance-corrected
excess energy was {E} kcal (95% CI {CI}) \u2014 **{PCT}% of the shortfall
({PCTCI}%), or {PER} kcal per ICU stay**; 0.13\u20130.26% across sensitivity
specifications. The negative control is reported separately as a diagnostic and is not
part of this total."""),

("""**Conclusion.** Roughly three-quarters of apparent procedure attribution reflects
background co-occurrence. Procedural interruption accounts for well under 1% of the
first-week shortfall, nearly half of which accrues before feeding is ever started.
Timestamp-based attribution requires an explicit background rate.""",
 """**Conclusion.** The background rate was approximately three-quarters of the observed
attribution rate. Procedural interruption accounted for well below 1% of the standardized
first-week shortfall, most of which accrues before feeding is started or while it runs
below reference. Timestamp-based attribution requires an explicit background rate."""),

# ---------- intro: soften process-failure ----------
("""Whether or not more energy helps, a unit that intends to deliver a given amount and
does not is running a process failure, and locating that failure is a tractable quality
problem""",
 """Whether or not more energy helps, describing where delivery diverges from a common
reference is a tractable measurement problem, and a prerequisite for deciding what, if
anything, is worth changing"""),

# ---------- methods: target classes vs negative control ----------
("""An interruption was attributed to a class if the **start time** of any procedure of that
class fell in the interval from 1 h before the gap onset to 1 h after the gap end.""",
 """The five clinical classes P1\u2013P5 constitute the **target set** for the energy estimand.
P0 is a negative control: it is reported as a diagnostic and is **not** included in the
target burden, so that its excess cannot offset the candidate classes.

An interruption was attributed to a class if the **start time** of any procedure of that
class fell in the interval from 1 h before the gap onset to 1 h after the gap end."""),

# ---------- methods: protein target ----------
("""The comparator is a **standardized reference target** of 25 kcal/kg/day using recorded
actual body weight, with 20 and 30 kcal/kg/day as sensitivity analyses.""",
 """The comparator is a **standardized reference target** of 25 kcal/kg/day for energy and
1.3 g/kg/day for protein, using recorded actual body weight, with 20 and 30 kcal/kg/day as
energy sensitivity analyses. Protein is reported descriptively only; the shortfall
decomposition and all attribution analyses concern energy."""),

# ---------- methods: honest case-crossover description ----------
("""The primary null is a **within-stay case-crossover**{{maclure1991,mittleman2014}}: each
interruption window is relocated by a whole number of ICU days within the same stay,
preserving clock hour, day-of-stay availability and all patient-level structure while
destroying true temporal correspondence with procedures. A same-clock-hour control day
existed for 99.9% of interruptions. One thousand replicates were drawn.""",
 f"""The primary null is a **within-stay case-crossover**{{{{maclure1991,mittleman2014}}}}:
each interruption window is relocated by a whole number of ICU days within the same stay.
This preserves clock hour and patient identity exactly, and restricts referent windows to
ICU days available within the same observation window, while destroying true temporal
correspondence with procedures. It does **not** preserve day of stay: a day-1 interruption
may be referred to a day-4 window, and procedure density differs between early
resuscitation and later stabilisation, which is a residual limitation of the design.

Candidate referent days are all whole-day offsets from \u22126 to +6 excluding zero (the index
day is excluded) whose relocated window falls entirely inside the observation window; one
is drawn uniformly at random per interruption per replicate, independently for each
interruption including multiple interruptions in the same stay. A referent day existed for
99.9% of interruptions; the {r2['n_without_control_day']} without one contribute zero to
both observed and null and cannot bias the difference. One thousand replicates were drawn.
The bootstrap resamples ICU stays over the per-interruption observed and mean-null values
rather than re-running the null inside each bootstrap draw."""),

# ---------- methods: oral intake and ramp sensitivities ----------
("""A clock-preserving circular shift (whole-day multiples) is reported as a secondary null.
Both the attribution rate and the energy estimand are referred to the same primary null.""",
 """A clock-preserving circular shift (whole-day multiples) is reported as a secondary null.
Both the attribution rate and the energy estimand are referred to the same primary null.

Two further sensitivity analyses address the denominator. First, energy in MIMIC-IV comes
from enteral and parenteral records, so oral intake would otherwise be counted as zero
delivery; we therefore repeated the analysis censoring each stay at its first recorded
oral or supplement intake. Second, applying a full reference target from the first ICU
hour is clinically strong, since early critical illness is a resuscitation and ramp-up
phase; we therefore repeated the analysis with a ramped reference of 40% on ICU day 1, 70%
on day 2 and 100% from day 3."""),

# ---------- results 3.5 ----------
("""### 3.5 Chance-corrected procedural energy loss is under 0.1% of the shortfall

Running the energy pipeline through the null gives observed excess energy of 745,300 kcal
against a null of 685,165 kcal. The **chance-corrected excess is 60,135 kcal (95% CI
24,335\u201398,159)** \u2014 statistically distinguishable from zero, and equal to **0.09% of the
64.9 million kcal shortfall, or 8.7 kcal per ICU stay**.

By class, chance-corrected energy was +66,296 kcal for airway/sedation, +32,796 for
off-unit transport and +16,163 for GI endoscopy, with the negative control and bedside
invasive procedures negative (\u221253,651 and \u22123,989), consistent with their null attribution.

For comparison, the specificity-screened quantity used in an earlier version of this
analysis \u2014 selecting classes on attribution excess and summing their full observed burden
\u2014 was 450,892 kcal. That procedure overstates the chance-corrected value by roughly an
order of magnitude and should not be used.""",
 f"""### 3.5 Chance-corrected procedural energy is a small fraction of the shortfall

Running the energy pipeline through the null across the five target classes gives observed
excess energy of {r2['target_obs_kcal']:,.0f} kcal against a null of
{r2['target_null_kcal']:,.0f} kcal. The **chance-corrected excess is {E} kcal (95% CI
{CI})** \u2014 clearly distinguishable from zero, and equal to **{PCT}% of the 64.9 million
kcal shortfall ({PCTCI}%), or {PER} kcal per ICU stay** (Figure 4A).

The negative control is reported separately, as a diagnostic rather than a component of
the burden: its chance-corrected energy was \u2212{P0} kcal, consistent with its null
attribution rate. Including it in the total, as an earlier version of this analysis did,
would have offset the candidate classes and roughly halved the estimate."""),

# ---------- results 3.6 ----------
("""The chance-corrected share ranged **0.06% to 0.26%** of the shortfall across every
specification tested: enteral-only stays 0.090%; defensible fasting window 0 h 0.261%, 2 h
0.194%, 4 h 0.138%, 6 h 0.092%, 8 h 0.057%; excluding interruptions starting at midnight
0.114%; excluding 23:00\u201301:00 onsets 0.110%; transport-first priority 0.107%;
negative-control-first priority 0.122%; reference target 20 kcal/kg 0.126% and 30 kcal/kg
0.072%. No specification approached 1%.

The enteral-only result (0.090%, 5,312 interruptions) is essentially identical to the
primary estimate, so the finding is not an artefact of pooling parenteral nutrition.""",
 f"""The chance-corrected share remained below 0.3% of the shortfall under every
specification tested. Varying the defensible fasting window from 0 to 8 h moved it between
approximately 0.11% and 0.49%; restricting to enteral-only stays, excluding midnight-onset
interruptions, altering the class-priority rule and varying the reference target between
20 and 30 kcal/kg/day all left it within the same range. Full values are in the
Supplementary Material.

Two denominator sensitivities address the concern that hours without recorded enteral or
parenteral nutrition may not be hours without nutrition. Only
{r2['pct_stays_with_oral_intake']}% of stays had any recorded oral or supplement intake
within the window; censoring each stay at its first such record reduced the shortfall by
only 2.3%, to {r2['oral_censored_shortfall_kcal']/1e6:.1f} million kcal, and moved the
procedural share to {r2['target_pct_oral_censored']:.2f}%. Applying a ramped reference
target (40% on day 1, 70% on day 2, 100% thereafter) reduced the shortfall to
{r2['ramped_shortfall_kcal']/1e6:.1f} million kcal and moved the procedural share to
{r2['target_pct_ramped']:.2f}%; pre-initiation remained the largest single component at
{r2['pre_initiation_pct_ramped']}% rather than 48.5%."""),

# ---------- results 3.4 tidy ----------
("""Bedside invasive procedures (+0.2 pp, \u22120.1 to
0.6), renal replacement (+0.2 pp, \u22120.0 to 0.4) and the **negative-control class (+0.1 pp,
\u22120.9 to 1.0)** were all indistinguishable from the null.""",
 """Bedside invasive procedures (+0.2 pp, \u22120.1 to 0.6), renal replacement (+0.2 pp, \u22120.0 to
0.4) and the **negative-control class (+0.1 pp, \u22120.9 to 1.0)** all had intervals including
zero and are treated as null throughout."""),

# ---------- discussion ----------
("""Under a null that preserves clock hour, day of stay and all patient structure, 29.1% of
interruptions still had a procedure in the attribution window.""",
 """Under a null that preserves clock hour and patient identity, 29.1% of interruptions still
had a procedure in the attribution window \u2014 a background rate approximately
three-quarters the size of the observed rate."""),

("""The magnitude result is the more important one. The excess is statistically robust \u2014 the
confidence interval excludes zero under every specification \u2014 and it is tiny. Eliminating
all chance-corrected procedural fasting would recover roughly 9 kcal per ICU stay, and
even the most permissive specification, granting no fasting justification at all for
airway or endoscopic procedures, reaches only 0.26% of the shortfall.""",
 f"""The magnitude result is the more important one. The excess is statistically robust \u2014 the
confidence interval excludes zero under every specification \u2014 and it is small. Eliminating
all chance-corrected procedural fasting in the target classes would recover roughly
{PER} kcal per ICU stay, and no specification tested exceeded 0.3% of the shortfall."""),

("""A quality intervention
operating orders of magnitude below the differences those trials tested and found inert is
very unlikely to matter clinically. Observational associations between higher intake and
better outcomes{{alberda2009,compher2017}} do not change that arithmetic.""",
 """The average energy magnitude recoverable here is small
relative to the contrasts those trials tested; its clinical consequences were not evaluated
in this study. Observational associations between higher intake and better
outcomes{{alberda2009,compher2017}} do not alter the magnitude arithmetic."""),

("""Where the shortfall actually lives is now measured rather than asserted: 48.5% before
initiation and 26.9% while feeding runs below target. Effort directed at how quickly
feeding is started and escalated, and at how requirements are
estimated{{tatucu2016,berger2019,preiser2015,phase2026}}, addresses three-quarters of the
shortfall; effort directed at protecting feeding around procedures addresses under a
hundredth of it.""",
 """Where the shortfall accrues is now measured rather than asserted: 48.5% before initiation
and 26.9% while feeding runs below reference, or 40.3% and correspondingly more under a
ramped reference. Those two periods **constitute** roughly three-quarters of the
shortfall, and procedural interruption under a hundredth of it. Whether the
pre-initiation period represents avoidable delay or appropriate clinical staging cannot be
determined from these data, because the prescribed plan is not
recorded{{tatucu2016,berger2019,preiser2015,phase2026}}; it does, however, locate where any
future intervention would have to act."""),

("""Where real procedural loss exists, it is in off-unit transport and in fasting extending
beyond the window already conceded to airway procedures.""",
 """Real procedural loss concentrates in three classes \u2014 airway/sedation, off-unit transport
and, to a much smaller degree, GI endoscopy \u2014 with airway and transport contributing the
two largest excesses."""),

("""Off-unit transport remains one of only two classes with a clearly positive excess,""",
 """Off-unit transport is one of the two largest excesses,"""),
]

miss = []
for old, new in SUBS:
    if old in t:
        t = t.replace(old, new, 1)
    else:
        miss.append(old[:70])
MS.write_text(t, encoding="utf-8")
print(f"applied {len(SUBS) - len(miss)}/{len(SUBS)} substitutions")
for m in miss:
    print("  NOT FOUND:", m)
