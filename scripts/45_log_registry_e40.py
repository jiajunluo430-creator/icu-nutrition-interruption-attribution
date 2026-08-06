"""N2 step 45 - registry entries E40-E43 for the review-6 supplementary analyses."""
import csv
from pathlib import Path

P = Path(r"D:\N2_icu_nutrition_delivery_gap\03_outputs\exploratory_attempts.csv")
rows = list(csv.DictReader(open(P, encoding="utf-8")))
flds = list(rows[0].keys())
have = {r["attempt"] for r in rows}

NEW = [
    dict(attempt="E40", date="2026-08-05", domain="cohort selection",
         change="Characteristics of stays excluded by the two-nutrition-day rule reported, "
                "with a relaxed >= 1 nutrition-day comparison",
         reason="External review noted that requiring nutrition on two distinct days "
                "removes exactly the patients with the largest pre-initiation gap, and "
                "conditions on surviving long enough to be fed twice (immortal time).",
         result="Of adult first ICU stays with LOS >= 48 h, 26,553 recorded NO enteral or "
                "parenteral nutrition in days 1-7 and 1,290 were fed on exactly one day, "
                "against ~7,900 in an approximate reconstruction of the primary cohort. "
                "Relaxing to >= 1 nutrition day raises the pre-initiation share of "
                "observed hours from 35.3% to 38.5%.",
         disposition="ADOPTED as a limitation with a quantified direction. The never-fed "
                     "group cannot be assumed underfed: many will have been eating "
                     "orally, which MIMIC-IV records sparsely. The cohort is therefore "
                     "described throughout as a NUTRITION-SUPPORT cohort, and the "
                     "pre-initiation figure as conditional on receiving support.",
         contract_compliant="yes"),
    dict(attempt="E41", date="2026-08-05", domain="exposure validation",
         change="Algorithmic validation of the charted-interruption definition using "
                "formula and order continuity across each gap",
         reason="External review noted that charted Paused/Stopped may represent an order "
                "switch or charting artifact rather than a bedside cessation, and that "
                "the midnight mode is direct evidence some are artifacts.",
         result="89.5% of gaps resume the SAME formula (33.8% under the same order, 55.7% "
                "re-ordered on restart, which is the normal MIMIC-IV pattern for a genuine "
                "pause). 8.0% are formula switches and 2.5% are midnight-boundary "
                "candidates. Same-formula resumption falls from 93.7% in 2-6 h gaps to "
                "81.2% in 12-24 h gaps, where midnight candidates rise from 0.8% to 6.6%.",
         disposition="ADOPTED. Reported as algorithmic validation, explicitly not a manual "
                     "chart review. An initial labelling that treated re-ordering as "
                     "evidence against a true pause was corrected before reporting.",
         contract_compliant="yes"),
    dict(attempt="E42", date="2026-08-05", domain="residual confounding",
         change="Severity proxies added and an E-value computed for the attribution excess",
         reason="External review asked for severity characterisation and a quantitative "
                "bias analysis rather than an acknowledgement that confounding 'remains "
                "possible'.",
         result="Excess is present in every stratum: ventilated 10.1 pp vs not ventilated "
                "7.4 pp; vasopressor-exposed 9.1 pp vs unexposed 11.3 pp; by care unit "
                "6.1 pp (MICU/SICU) to 19.4 pp (Neuro SICU). Risk ratio 1.34, E-value "
                "2.01. SOFA and SAPS-II are not computable from the modules available.",
         disposition="ADOPTED. The E-value is reported with its interpretation; the "
                     "unavailability of SOFA/SAPS-II is stated rather than worked around.",
         contract_compliant="yes"),
    dict(attempt="E43", date="2026-08-05", domain="scope and target journal",
         change="Reframed from an ICU nutrition paper to a measurement paper about "
                "timestamp-proximity attribution; target changed to BMJ Quality & Safety",
         reason="Two independent external reviews converged: the defensible contribution "
                "is that timestamp-proximity attribution carries a large, "
                "hospital-dependent background rate, not that procedures are unimportant "
                "in nutrition. The between-hospital heterogeneity survives shrinkage "
                "(E38) and is the strongest finding.",
         result="Title, abstract, framing and discussion rebuilt around comparability of "
                "attribution-based quality metrics. Claims about prior bedside literature "
                "narrowed to EHR timestamp-derived attribution only.",
         disposition="ADOPTED.",
         contract_compliant="yes"),
]
added = 0
for r in NEW:
    if r["attempt"] not in have:
        rows.append({k: r.get(k, "") for k in flds})
        added += 1
with open(P, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=flds)
    w.writeheader()
    w.writerows(rows)
ids = [r["attempt"] for r in rows]
print(f"added {added}; registry now {len(rows)} entries {ids[0]}..{ids[-1]}")
assert ids == [f"E{i:02d}" for i in range(1, len(ids) + 1)]
print("ASSERT OK: sequential, no gaps")
