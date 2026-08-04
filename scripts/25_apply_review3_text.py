"""N2 step 25 - apply third-round review corrections to the manuscript."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
MS = ROOT / "07_manuscript" / "FrontNutr_main_manuscript.md"
OUT = ROOT / "03_outputs"
r3 = json.load(open(OUT / "rev3_results.json"))
dn = json.load(open(OUT / "rev3_day_preserving_null.json"))
r2 = json.load(open(OUT / "rev2_results.json"))
t = MS.read_text(encoding="utf-8")

# de-render citations so numbering can be regenerated after edits
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

E = f"{r3['target_excess_kcal']:,.0f}"
CI = f"{r3['target_excess_ci'][0]:,.0f}\u2013{r3['target_excess_ci'][1]:,.0f}"
PCT = f"{r3['target_pct_of_shortfall']:.2f}"
PCTCI = f"{r3['target_pct_ci'][0]:.2f}\u2013{r3['target_pct_ci'][1]:.2f}"
PER = str(r3["target_kcal_per_stay"])
NSET = f"{r3['n_analysis_set']:,}"

SUBS = [
# ---------------- abstract
("""Across the
five candidate classes, chance-corrected excess energy was 113,763 kcal (95% CI
83,304\u2013142,384) \u2014 **0.18% of the shortfall, or 16.5 kcal per ICU stay** (0.14\u20130.35% across
sensitivity specifications). The negative control is not part of this total.""",
 f"""Across the five
candidate classes, chance-corrected excess energy was {E} kcal (95% CI {CI}) \u2014
**{PCT}% of the shortfall, or {PER} kcal per ICU stay**. A complementary null preserving
ICU day rather than patient identity gave a larger excess ({dn['pct_of_shortfall']:.2f}%),
so the primary estimate is the conservative one."""),

# ---------------- methods: exclusive vs non-exclusive
("""The five clinical classes P1\u2013P5 constitute the **target set** for the energy estimand.""",
 """Class-specific **attribution-rate** analyses are **non-exclusive**: each class is
assessed independently for presence in the window, so a single interruption can count
towards more than one class and the class-specific percentages do not sum to the
any-class rate. The priority rule below is applied **only** when a single class must be
assigned for the **energy** estimand, which is therefore mutually exclusive.

The five clinical classes P1\u2013P5 constitute the **target set** for the energy estimand."""),

# ---------------- methods: analysis set
("""A referent day existed for
99.9% of interruptions; the 4 without one contribute zero to
both observed and null and cannot bias the difference.""",
 f"""A referent day existed for
99.9% of interruptions; the {r3['n_excluded_no_referent']} without one are **excluded from
the matched analysis**, giving an analysis set of {NSET} interruptions."""),

# ---------------- methods: two nulls, locked draws
("""A clock-preserving circular shift (whole-day multiples) is reported as a secondary null.
Both the attribution rate and the energy estimand are referred to the same primary null.""",
 f"""Because the within-stay design does not preserve day of stay, a **complementary
secondary null** was added that preserves ICU day and clock hour exactly by borrowing
another patient's procedure timeline at the same ICU day and the same wall-clock hour.
The two nulls are complementary rather than nested: the primary preserves patient identity
and clock hour, the secondary preserves ICU day and clock hour. Procedure density by ICU
day and class is reported in the Supplementary Material.

One locked set of referent draws (seed {r3['seed']}, {r3['n_replicates']:,} replicates) was
generated once, saved, and reused for every estimate reported here, so that all values are
mutually consistent rather than each analysis re-randomising its own null. Both the
attribution rate and the energy estimand are referred to the same primary null."""),

# ---------------- results 3.3
("""A procedure of some prespecified class fell within the attribution window of 2,141 of
5,499 interruptions (38.9%). Under the case-crossover null, in which no true
correspondence can exist, **29.1%** still met the same criterion. The excess was **9.9
percentage points (95% CI 8.7\u201311.2)**, with an empirical p of 0.001 across 1,000
replicates (Figure 3).""",
 f"""A procedure of some prespecified class fell within the attribution window of 38.9% of
the {NSET} interruptions in the matched analysis set. Under the case-crossover null, in
which no true correspondence can exist, **{r3['rate_null_pct']}%** still met the same
criterion. The excess was **{r3['rate_excess_pp']} percentage points (95% CI
{r3['rate_excess_ci_pp'][0]}\u2013{r3['rate_excess_ci_pp'][1]})**, with an empirical p of
{r3['empirical_p']:.3f} across {r3['n_replicates']:,} replicates (Figure 3).

Under the complementary null that preserves ICU day rather than patient identity, the null
rate was {dn['rate_null_pct']}% and the excess {dn['rate_excess_pp']} pp. Procedure density
is strongly concentrated on ICU day 1 (Supplementary Material), so a null that does not
hold patient identity fixed absorbs less of the shared patient-level intensity of
procedures and interruptions. The within-stay design is therefore the **conservative**
choice, and the concern that failing to preserve day of stay might inflate the estimate
points in the opposite direction."""),

# ---------------- results 3.4 (per-class rates, non-exclusive)
("""Class-specific excesses separate along clinical lines (Figure 3A,B). Airway and sedation
events showed +5.8 pp (95% CI 4.9\u20136.7), off-unit transport +5.5 pp (4.7\u20136.4) and GI
endoscopic procedures +0.6 pp (0.3\u20130.9).""",
 """Class-specific excesses, assessed non-exclusively, separate along clinical lines
(Figure 3A,B). Airway and sedation events showed +5.7 pp, off-unit transport +5.5 pp and
GI endoscopic procedures +0.6 pp."""),

("""Bedside invasive procedures (+0.2 pp, \u22120.1 to 0.6), renal replacement (+0.2 pp, \u22120.0 to
0.4) and the **negative-control class (+0.1 pp, \u22120.9 to 1.0)** all had intervals including
zero and are treated as null throughout.""",
 """Bedside invasive procedures (+0.2 pp), renal replacement (+0.2 pp) and the
**negative-control class (+0.0 pp)** were all indistinguishable from the null on this
scale."""),

("""A secondary circular-shift null that did not preserve clock hour produced a spuriously
*negative* negative-control estimate; that artefact disappears under the clock-preserving
case-crossover design, which we take as evidence that hour-of-day structure must be
preserved in nulls of this kind.""",
 f"""**The negative control is null on the attribution-rate scale but not on the energy
scale, and this must be stated plainly.** Under priority assignment its chance-corrected
energy was {r3['p0_energy_excess_kcal']:,.0f} kcal (95% CI {r3['p0_energy_ci']}), which
excludes zero. Diagnostics locate the cause in the exclusive-assignment rule rather than in
residual confounding of the target classes: evaluated **non-exclusively**, P0 energy is
null (\u221218,798 kcal, 95% CI \u221254,535 to 13,356), and the negative excess concentrates almost
entirely in 12\u201324 h gaps (\u221247,809 of \u221254,612 kcal) \u2014 the long, high-energy interruptions
that the priority rule reassigns away from P0 whenever a candidate procedure is also
present. Excluding swallow screening, the P0 item most plausibly linked to nutrition
decisions, does not change it (\u221256,014 kcal).

We therefore do **not** claim that the energy scale is validated by the negative control.
The rate scale is; the energy scale carries a residual non-exchangeability under exclusive
assignment whose direction and magnitude we report rather than assume away."""),

# ---------------- results 3.5
("""Running the energy pipeline through the null across the five target classes gives observed
excess energy of 495,197 kcal against a null of
381,434 kcal. The **chance-corrected excess is 113,763 kcal (95% CI
83,304\u2013142,384)** \u2014 clearly distinguishable from zero, and equal to **0.18% of the 64.9 million
kcal shortfall (0.13\u20130.22%), or 16.5 kcal per ICU stay** (Figure 4A).""",
 f"""Running the energy pipeline through the null across the five target classes gives
observed excess energy of {r3['target_obs_kcal']:,.0f} kcal against a null of
{r3['target_null_kcal']:,.0f} kcal. The **chance-corrected excess is {E} kcal (95% CI
{CI})** \u2014 clearly distinguishable from zero, and equal to **{PCT}% of the 64.9 million kcal
shortfall ({PCTCI}%), or {PER} kcal per ICU stay** (Figure 4A). Under the complementary
day-preserving null the excess was {dn['energy_excess_kcal']:,.0f} kcal
({dn['pct_of_shortfall']:.2f}% of the shortfall), so the conclusion does not depend on
which null is used."""),

("""The negative control is reported separately, as a diagnostic rather than a component of
the burden: its chance-corrected energy was \u221254,673 kcal, consistent with its null
attribution rate. Including it in the total, as an earlier version of this analysis did,
would have offset the candidate classes and roughly halved the estimate.""",
 """The negative control is reported separately, as a diagnostic rather than a component of
the burden (see 3.4). Including it in the total, as an earlier version of this analysis
did, would have offset the candidate classes and roughly halved the estimate."""),

# ---------------- results 3.7 stale numbers
("""excluding those events changes the chance-corrected share only from 0.09% to
0.11%.""",
 """excluding those events changes the chance-corrected share only from 0.176% to
0.167%."""),

# ---------------- discussion opener
("""In a large ICU cohort, nearly half the first-week nutrition shortfall accrued before
feeding was ever started; qualifying interruptions accounted for 7.0% of it; roughly
three-quarters of apparent procedure attribution reflected background co-occurrence; and
the chance-corrected procedural contribution was under 0.1% of the shortfall.""",
 f"""In a large ICU cohort, nearly half the first-week nutrition shortfall accrued before
feeding was ever started; qualifying interruptions accounted for 7.0% of it; the background
rate was approximately three-quarters of the observed attribution rate; and the
chance-corrected procedural contribution was approximately {PCT}% of the shortfall under
the primary null and {dn['pct_of_shortfall']:.2f}% under a day-preserving alternative \u2014
well below 1% either way."""),

# ---------------- discussion self-contradiction
("""Our results argue that a
background rate should accompany such an analysis as routinely as a confidence interval,
that the null must preserve clock hour and day-of-stay structure, and that the estimand of
interest must be run *through* the null rather than screened on it.""",
 """Our results argue that a background rate should accompany such an analysis as routinely
as a confidence interval, and that the estimand of interest must be run *through* the null
rather than screened on it. They also show that no single null preserves everything: our
primary design holds patient identity and clock hour fixed but not ICU day, the
complementary design the reverse, and the two bracket the estimate rather than agreeing
exactly. Reporting more than one null, and stating which is conservative, is more
informative than asserting that one has preserved all relevant structure."""),

("""Eliminating
all chance-corrected procedural fasting in the target classes would recover roughly
16.5 kcal per ICU stay, and no specification tested exceeded 0.35% of the shortfall.""",
 f"""Eliminating all chance-corrected procedural fasting in the target classes would recover
roughly {PER} kcal per ICU stay, and no specification tested exceeded 0.35% of the
shortfall under the primary null."""),
]

miss = []
for old, new in SUBS:
    if old in t:
        t = t.replace(old, new, 1)
    else:
        miss.append(old[:70].replace("\n", " "))
MS.write_text(t, encoding="utf-8")
print(f"applied {len(SUBS) - len(miss)}/{len(SUBS)}")
for m in miss:
    print("  NOT FOUND:", m)
