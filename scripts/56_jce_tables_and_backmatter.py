"""N2 step 56 - tables, figure legends and back matter for the JCE version.

Idempotent: any previously inserted block is removed before a new one is written.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, REV = ROOT / "03_outputs", ROOT / "03_outputs" / "canonical", ROOT / "03_outputs" / "review6"
P = ROOT / "07_manuscript" / "JCE_main_manuscript.md"
t = P.read_text(encoding="utf-8")

T1 = pd.read_csv(OUT / "table1_cohort.csv")
V = dict(zip(T1.iloc[:, 0], T1.iloc[:, 1].astype(str)))
R = json.load(open(OUT / "rev_sensitivity.json"))["stay_route_counts"]
C = json.load(open(CAN / "canonical_primary.json"))
S6 = json.load(open(REV / "review6_supplementary.json"))
R6 = json.load(open(REV / "review6_recompute.json"))
WIN = pd.read_csv(REV / "window_definition_sensitivity.csv")
STR = pd.read_csv(REV / "gap_duration_strata.csv")
n = int(str(V["N (first ICU stays)"]).replace(",", ""))
pct = lambda x: f"{x:,} ({100*x/n:.1f})"

tbl1 = f"""**Table 1.** Characteristics of the nutrition-support cohort.

| Characteristic | Value |
|---|---|
| First ICU stays, n | {V['N (first ICU stays)']} |
| Age, years, median (IQR) | 65 (53\u201376) |
| Female, n (%) | {V['Female, n (%)']} |
| Weight, kg, median (IQR) | 79.2 (65.6\u201395.9) |
| ICU length of stay, h, median (IQR) | 214.2 (137.3\u2013342.0) |
| Invasively ventilated, n (%) | 6,304 (91.6) |
| Vasopressor exposed, n (%) | 4,455 (64.7) |
| In-hospital death, n (%) | {V['In-hospital death, n (%)']} |
| Alive-in-ICU hours contributed, days 1\u20137 | 1,021,294 |
| Enteral only / parenteral only / mixed, n (%) | {pct(R['EN'])} / {pct(R['PN'])} / {pct(R['mixed'])} |
| Analysable interruptions, n | {C['n_analysis_set']:,} |
| **Excluded by the cohort definition** | |
| Stays with LOS \u226548 h and no artificial nutrition in days 1\u20137, n | {S6['m7_cohort']['never_fed']:,} |
| Stays fed on exactly one day, n | {S6['m7_cohort']['fed_one_day']:,} |
"""

rows = [f"| {r.window.replace(' (original)','').replace(' (wrong causal direction; shown for completeness)','')} "
        f"| {r.observed_pct} | {r.background_pct} | {r.excess_pp} | {r.ci_lo} to {r.ci_hi} |"
        for r in WIN[WIN.scope.str.startswith("target")].itertuples()]
strat = "\n".join(
    f"| {r.gap_stratum} events (n={r.n:,}), mean window {r.mean_window_h} h | {r.observed_pct} "
    f"| {r.background_pct} | {r.excess_pp} | \u2013 |" for r in STR.itertuples())
tbl2 = f"""**Table 2.** Attribution rate under alternative windows and by event duration, target
classes only. The primary window is the event duration plus 2 h (median
{R6['window_length_h']['median']} h, maximum {R6['window_length_h']['max']} h) and therefore
lengthens with the event; the excess is nevertheless largest where windows are shortest.

| Definition | Observed % | Background % | Excess, pp | 95% CI |
|---|---|---|---|---|
{chr(10).join(rows)}
| **By event duration (primary window)** | | | | |
{strat}
"""

LEGENDS = """## Figure legends

**Fig. 1.** Cohort selection. Of 94,458 ICU stays in MIMIC-IV v3.1, 6,883 first ICU stays
met all criteria.

**Fig. 2.** Attribution against matched control times within the same stay. (A) Percentage
of events with a candidate cause of each class in the attribution window, observed and at
matched control times; classes are assessed non-exclusively and do not sum to the
any-class rate, and the negative control is shown separately. (B) Excess over background
for each class with bootstrap 95% confidence intervals; asterisks mark intervals excluding
zero. (C) The observed any-class rate against the distribution obtained at matched control
times over 1,000 replicates.

**Fig. 3.** Between-site variability of the background rate. (A) Restricted to airway
events, the only class the two databases share, background co-occurrence differs
severalfold; eICU airway ascertainment is 7.5-fold sparser. (B) Shrunk background rate for
each of 182 hospitals against the spread expected from binomial sampling alone, with the
between-site standard deviation and intraclass correlation. (C) Lag between event time and
entry time in paired nursing records, against the ±1 h attribution window.
"""

DECL = f"""## Declarations

**Ethics.** MIMIC-IV and eICU-CRD are de-identified and publicly available. Data were
accessed under the PhysioNet credentialed data use agreement by credentialed user Jiajun
Luo, who completed the required human-subjects research training. Establishment of these
databases was approved by the Institutional Review Boards of Beth Israel Deaconess Medical
Center and the Massachusetts Institute of Technology, with a waiver of informed consent.
This secondary analysis required no additional review.

**Data and code availability.** MIMIC-IV v3.1 and eICU-CRD v2.0 are available from
PhysioNet to credentialed users. Analysis code, both frozen analysis plans with their
SHA-256 hashes, the frozen item lists and all aggregate outputs required to reproduce
every reported number are archived at
https://github.com/jiajunluo430-creator/icu-nutrition-interruption-attribution; a Zenodo
DOI will be minted before publication. No individual-level data are redistributed.

**Funding.** National Natural Science Foundation of China Youth Project (82403569) and
Chongqing Postdoctoral Special Science Foundation (2024CQBSHTB3146). The funders had no
role in study design, analysis, the decision to publish, or preparation of the manuscript.

**Declaration of competing interest.** The authors declare that they have no known
competing financial interests or personal relationships that could have appeared to
influence the work reported in this paper.

**CRediT authorship contribution statement.** **Jiajun Luo:** Conceptualization,
Methodology, Software, Formal analysis, Data curation, Visualization, Writing – original
draft. **Qinglong Chen:** Methodology, Validation, Investigation, Writing – original
draft. **Jing Liu:** Investigation, Data curation, Validation, Writing – original draft.
**Fanghui Lu:** Conceptualization, Supervision, Funding acquisition, Writing – review &
editing. **Xiaolong Liang:** Conceptualization, Supervision, Project administration,
Writing – review & editing. Jiajun Luo, Qinglong Chen and Jing Liu contributed equally.
Fanghui Lu and Xiaolong Liang are joint corresponding authors.

**Acknowledgements.** The authors thank the MIT Laboratory for Computational Physiology
and the PhysioNet team.

**Supplementary Material.** Contains the STROBE checklist, both frozen analysis plans with
their hashes, the complete item list, the interface audit, all sensitivity analyses and
the full post-freeze decision registry (43 entries).
"""

MARK = "<!-- generated back matter -->"
t = t.split(MARK)[0].rstrip()

a1 = "in-hospital mortality 23.9% (Table 1)."
assert a1 in t, "Table 1 anchor missing"
t = t.replace(a1, a1 + "\n\n" + tbl1.rstrip(), 1)
a2 = "we tested four alternatives (Table 2)."
assert a2 in t, "Table 2 anchor missing"
t = t.replace(a2, a2 + "\n\n" + tbl2.rstrip(), 1)

refs = "\n## References" + t.split("\n## References", 1)[1]
t = t.split("\n## References", 1)[0].rstrip()
t += "\n\n" + LEGENDS + "\n" + DECL + refs.rstrip() + "\n\n" + MARK + "\n"

assert t.count("## References") == 1 and "**Table 1.**" in t and "**Table 2.**" in t
P.write_text(t, encoding="utf-8")


def wc(s):
    s = "\n".join(l for l in s.split("\n")
                  if not l.lstrip().startswith("|") and not l.startswith("**Table "))
    return sum(1 for w in re.sub(r"[*`]", "", s).split() if re.search(r"[A-Za-z0-9]", w))


ab = wc(t.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0])
bd = wc(t.split("## 1. Introduction", 1)[1].split("## Figure legends", 1)[0])
print(f"inserted 2 tables, 3 figure legends, declarations")
print(f"abstract {ab} words | main text {bd:,} words | "
      f"tables rows {sum(1 for l in t.split(chr(10)) if l.strip().startswith('|'))}")
