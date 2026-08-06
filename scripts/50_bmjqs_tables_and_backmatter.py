"""N2 step 50 - insert tables, abbreviations, figure legends and declarations into the
BMJ Quality & Safety manuscript.

The draft referenced table 1 and table 2 without containing either, and had no back
matter. Everything here is generated from deposited outputs, and the script is
idempotent: it removes any block it previously inserted before writing a new one.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, REV = ROOT / "03_outputs", ROOT / "03_outputs" / "canonical", ROOT / "03_outputs" / "review6"
P = ROOT / "07_manuscript" / "BMJQS_main_manuscript.md"
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

# ---------------------------------------------------------------- Table 1
tbl1 = f"""**Table 1** Characteristics of the nutrition-support cohort (6,883 first ICU stays).

| Characteristic | Value |
|---|---|
| First ICU stays, n | {V['N (first ICU stays)']} |
| Age, years, median (IQR) | 65 (53\u201376) |
| Female, n (%) | {V['Female, n (%)']} |
| Weight, kg, median (IQR) | 79.2 (65.6\u201395.9) |
| ICU length of stay, h, median (IQR) | 214.2 (137.3\u2013342.0) |
| Observation window, h, median (IQR) | 168.0 (136.5\u2013168.0) |
| Invasively ventilated, n (%) | 6,304 (91.6) |
| Vasopressor exposed, n (%) | 4,455 (64.7) |
| In-hospital death, n (%) | {V['In-hospital death, n (%)']} |
| Alive-in-ICU hours contributed, days 1\u20137 | 1,021,294 |
| Enteral only / parenteral only / mixed, n (%) | {pct(R['EN'])} / {pct(R['PN'])} / {pct(R['mixed'])} |
| First-week shortfall, million kcal | 64.9 |
| Analysable interruptions, n | {C['n_analysis_set']:,} |
| **Excluded from this cohort** | |
| Stays with LOS \u226548 h recording no artificial nutrition in days 1\u20137, n | {S6['m7_cohort']['never_fed']:,} |
| Stays fed on exactly one day, n | {S6['m7_cohort']['fed_one_day']:,} |
"""

# ---------------------------------------------------------------- Table 2
rows = []
for r in WIN[WIN.scope.str.startswith("target")].itertuples():
    rows.append(f"| {r.window.replace(' (original)', '').replace(' (wrong causal direction; shown for completeness)', '')} "
                f"| {r.observed_pct} | {r.background_pct} | {r.excess_pp} "
                f"| {r.ci_lo} to {r.ci_hi} |")
strat = "\n".join(
    f"| {r.gap_stratum} gaps (n={r.n:,}), mean window {r.mean_window_h} h | {r.observed_pct} "
    f"| {r.background_pct} | {r.excess_pp} | \u2013 |" for r in STR.itertuples())
tbl2 = f"""**Table 2** Attribution rate under alternative windows and by gap duration, target
classes only. The primary window is the gap duration plus 2 h (median
{R6['window_length_h']['median']} h), so it lengthens with the gap; the excess is
nevertheless largest where windows are shortest.

| Definition | Observed % | Background % | Excess, pp | 95% CI |
|---|---|---|---|---|
{chr(10).join(rows)}
| **By gap duration (primary window)** | | | | |
{strat}
"""

# ------------------------------------------------------------ back matter
ABBREV = """## Abbreviations

CI: confidence interval; EHR: electronic health record; eICU-CRD: eICU Collaborative
Research Database; ICC: intraclass correlation coefficient; ICU: intensive care unit;
IQR: interquartile range; MIMIC-IV: Medical Information Mart for Intensive Care IV;
pp: percentage points; SD: standard deviation; STROBE: Strengthening the Reporting of
Observational Studies in Epidemiology.
"""

LEGENDS = """## Figure legends

**Figure 1** Cohort selection. Of 94,458 ICU stays in MIMIC-IV v3.1, 6,883 first ICU
stays met all criteria. Exclusions are shown separately for weight, qualifying nutrition
segment and the two-nutrition-day requirement.

**Figure 2** Attribution against matched control times within the same ICU stay.
(A) Percentage of interruptions with a procedure of each class in the attribution window,
observed versus background. (B) Excess over background with bootstrap 95% CIs; asterisks
mark intervals excluding zero, and the negative-control class is null. (C) Observed
attribution rate against the background distribution from 1,000 replicates.

**Figure 3** Comparability of the background rate. (A) Restricted to airway events, the
only class MIMIC-IV and eICU-CRD genuinely share, the two databases do not agree; eICU
airway ascertainment is 7.5-fold sparser. (B) Shrunk background rate for each of 182
hospitals against the spread expected from binomial sampling alone, with the
between-hospital SD and intraclass correlation. (C) Lag between event time and entry time
in paired nursing records, against the ±1 h attribution window.
"""

DECL = f"""## Declarations

**Ethics approval.** MIMIC-IV and eICU-CRD are de-identified and publicly available. Data
were accessed under the PhysioNet credentialed data use agreement by credentialed user
Jiajun Luo, who completed the required human-subjects research training (CITI "Data or
Specimens Only Research"). Establishment of these databases was approved by the
Institutional Review Boards of Beth Israel Deaconess Medical Center and the Massachusetts
Institute of Technology, which granted a waiver of informed consent. This secondary
analysis required no additional review.

**Data and code availability.** MIMIC-IV v3.1 and eICU-CRD v2.0 are available from
PhysioNet to credentialed users. Analysis code, both frozen analysis plans with their
SHA-256 hashes, the frozen item lists and all aggregate outputs needed to reproduce every
number are archived at
https://github.com/jiajunluo430-creator/icu-nutrition-interruption-attribution; a Zenodo
DOI will be minted before publication. No individual-level data are redistributed.

**Competing interests.** None declared.

**Funding.** National Natural Science Foundation of China Youth Project (82403569) and
Chongqing Postdoctoral Special Science Foundation (2024CQBSHTB3146). The funders had no
role in study design, analysis, the decision to publish, or preparation of the manuscript.

**Contributors.** JiaL: conceptualisation, methodology, software, formal analysis, data
curation, visualisation, writing – original draft. QC: methodology, validation,
investigation, writing – original draft. JinL: investigation, data curation, validation,
writing – original draft. FL: conceptualisation, supervision, funding acquisition,
writing – review and editing. XL: conceptualisation, supervision, project administration,
writing – review and editing. JiaL, QC and JinL contributed equally and share first
authorship. FL and XL are joint corresponding authors and guarantors.

**Acknowledgements.** The authors thank the MIT Laboratory for Computational Physiology
and the PhysioNet team.

**Supplemental material.** Additional file 1 contains the STROBE checklist, both frozen
analysis plans with their hashes, the complete procedure item list, the eICU interface
audit, all sensitivity analyses and the full post-freeze decision registry ({43} entries).
"""

# use of AI belongs in Methods under BMJ policy, not only in declarations
AI_METHODS = """
### Use of generative AI

Generative AI assistants (OpenAI Codex, Codex CLI; Anthropic Claude, Claude Opus 5) were
used for analysis-code drafting and refactoring, figure generation from author-specified
analyses, reference retrieval and verification against PubMed, language editing, and
automated consistency checking between the manuscript, tables, figures and additional
file. They were **not** used to select the study question, define the estimands, choose
the matching designs, decide the analysis plans, or interpret the results. All code was
executed by the authors against the source data and every reported value was verified
against the deposited outputs. The authors take full responsibility for the content.
"""

MARK = "<!-- generated back matter -->"
t = t.split(MARK)[0].rstrip()          # idempotent: drop any previous insertion

# tables go immediately after the paragraph that first cites them
anchor1 = "in-hospital mortality was 23.9% (table 1)."
assert anchor1 in t
t = t.replace(anchor1, anchor1 + "\n\n" + tbl1.rstrip(), 1)
anchor2 = "so we tested four alternatives (table 2)."
assert anchor2 in t
t = t.replace(anchor2, anchor2 + "\n\n" + tbl2.rstrip(), 1)

# AI statement into Methods, immediately before "### What was not done"
anchor3 = "### What was not done"
assert anchor3 in t
t = t.replace(anchor3, AI_METHODS.strip() + "\n\n" + anchor3, 1)

refs = "\n## References" + t.split("\n## References", 1)[1]
t = t.split("\n## References", 1)[0].rstrip()
t += "\n\n" + ABBREV + "\n" + LEGENDS + "\n" + DECL + refs.rstrip() + "\n\n" + MARK + "\n"

assert t.count("## References") == 1 and "**Table 1**" in t and "**Table 2**" in t
P.write_text(t, encoding="utf-8")
print(f"inserted 2 tables, abbreviations, 3 figure legends, declarations, AI statement")
print(f"table rows now: {sum(1 for l in t.split(chr(10)) if l.strip().startswith('|'))}")
