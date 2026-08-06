"""N2 step 43 - registry entries E33-E39 for external review round 6."""
import csv
import json
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
P = ROOT / "03_outputs" / "exploratory_attempts.csv"
REV = ROOT / "03_outputs" / "review6"

# the fold-range metric divides by a 10th centile near zero and is not stable; drop it
sh = json.load(open(REV / "hospital_shrinkage.json"))
for k in ("raw_fold_range", "shrunk_fold_range"):
    sh.pop(k, None)
sh["fold_range_note"] = ("deliberately not reported: the 10th centile is near zero, so any "
                         "ratio is numerically unstable. Spread is reported as tau, ICC and "
                         "the absolute 10th-90th centile against a sampling-noise reference.")
json.dump(sh, open(REV / "hospital_shrinkage.json", "w"), indent=2)

rows = list(csv.DictReader(open(P, encoding="utf-8")))
flds = list(rows[0].keys())
have = {r["attempt"] for r in rows}

NEW = [
    dict(attempt="E33", date="2026-08-05", domain="estimand scale",
         change="Energy numerator recomputed on the reference 25 kcal/kg/day scale, the "
                "same scale as the denominator",
         reason="External review identified that the numerator used the actual "
                "pre-interruption infusion rate while the denominator used the reference "
                "rate, so the reported percentage divided two different scales.",
         result="Reference scale gives 205,512 kcal = 0.317% of the shortfall, against "
                "114,660 kcal = 0.177% on the actual-rate scale. The rate mismatch is "
                "87.8 vs 49.7 kcal/h, a factor of 1.77.",
         disposition="ADOPTED. The reference-scale figure becomes the primary ratio; the "
                     "actual-rate figure is retained as the recoverable-energy framing. "
                     "Both are reported with their scales named.",
         contract_compliant="correction of error"),
    dict(attempt="E34", date="2026-08-05", domain="estimand",
         change="Priority-free estimand computed to test whether exclusive priority "
                "assignment contaminates the target total",
         reason="External review argued the priority rule could competitively load "
                "high-energy long gaps onto the target classes.",
         result="Priority-free and priority-assigned target totals are IDENTICAL "
                "(114,660 kcal, asserted to <2 kcal). An interruption enters the target "
                "total iff any target class is in window, and the defensible window is the "
                "largest among classes present, under both rules.",
         disposition="ADOPTED as a formal check. The priority rule fixes only the "
                     "per-class split and the negative-control diagnostic; it leaves the "
                     "target total unchanged. The reviewer's premise does not hold.",
         contract_compliant="yes"),
    dict(attempt="E35", date="2026-08-05", domain="attribution window",
         change="Four alternative attribution windows added; the original window "
                "re-described accurately",
         reason="The text implied a flat +/-1 h window. The actual window ran gap onset "
                "-1 h to gap end +1 h, i.e. gap duration + 2 h (median 8.7 h, max 26 h), "
                "so longer gaps received longer windows.",
         result="Target-class excess: span 11.1 pp; procedure inside the gap 12.7 pp; "
                "onset +/-1 h 3.2 pp; onset to +2 h 6.4 pp; 1 h before onset only -0.3 pp. "
                "By gap stratum the excess FALLS as windows lengthen (13.9, 10.8, 6.5 pp "
                "for 2-6, 6-12, 12-24 h).",
         disposition="ADOPTED. The excess is not an artifact of long windows; it is "
                     "largest where windows are shortest. Window length is now described "
                     "accurately everywhere.",
         contract_compliant="correction of description"),
    dict(attempt="E36", date="2026-08-05", domain="headline rate",
         change="Primary attribution rate switched from any-class (which includes the "
                "negative control) to target classes only",
         reason="The 38.9% headline counted the P0 negative control, while the energy "
                "estimand explicitly excludes it. The two constructs were being quoted "
                "interchangeably.",
         result="Target-only 29.0% observed vs 17.8% background, excess 11.1 pp "
                "(95% CI 9.9-12.4). Any-class remains 38.9% vs 29.1%, excess 9.9 pp.",
         disposition="ADOPTED. Target-only is primary because it matches the energy "
                     "estimand's class set. Both are reported so the change is visible.",
         contract_compliant="correction of error"),
    dict(attempt="E37", date="2026-08-05", domain="external validation",
         change="eICU comparison restricted to airway events, the only class the two "
                "databases genuinely share; the replication claim is WITHDRAWN",
         reason="MIMIC P1 contains six itemids, all airway (extubation, intubation, "
                "bronchoscopy, tracheostomy, bedside surgery) and NO sedation infusions. "
                "The eICU class had added 100,640 sedation/NMB infusion starts against "
                "7,644 airway events, so 93% of its events had no counterpart.",
         result="Airway-only eICU background rate is 0.74% (95% CI 0.71-0.78) against "
                "MIMIC P1 8.1%; eICU airway density is 7.5x lower (0.024 vs 0.180 per "
                "stay-day) and only 8.7% of eICU stays record any airway event. The "
                "databases do NOT agree on the rate.",
         disposition="ADOPTED. All claims of replication, external validation and 'the "
                     "same answer in two databases' are withdrawn from title, abstract, "
                     "results, discussion and cover letter. eICU is retained only as "
                     "evidence that background co-occurrence is non-zero and strongly "
                     "heterogeneous between hospitals.",
         contract_compliant="correction of error"),
    dict(attempt="E38", date="2026-08-05", domain="between-hospital variation",
         change="Hospital background rates reported with beta-binomial empirical-Bayes "
                "shrinkage instead of raw rates",
         reason="Raw between-hospital spread counts binomial sampling noise as though it "
                "were real variation.",
         result="Median 996 windows per hospital. Pooled 6.67%, between-hospital SD "
                "tau = 7.08 pp, ICC = 0.074. Shrunk 10th-90th centile 0.2-14.8% versus a "
                "sampling-noise-only reference of 5.7-7.8%. The heterogeneity is real and "
                "survives shrinkage. The '29-fold' framing is dropped: the 10th centile is "
                "near zero so any ratio is numerically unstable.",
         disposition="ADOPTED. Spread reported as tau, ICC and absolute centiles against "
                     "the noise reference.",
         contract_compliant="yes"),
    dict(attempt="E39", date="2026-08-05", domain="reporting",
         change="Empirical p reported as an inequality; ratio-form attributable fraction "
                "added alongside the additive excess",
         reason="p = 0.001 is the 1/(B+1) floor of 1,000 replicates, the same artifact "
                "criticised in E08. Separately, review asked for a ratio-form fraction.",
         result="0 of 1,000 replicates reached the observed rate (null max 30.9% vs "
                "observed 38.9%), so p < 0.001. Ratio form under obs = c + (1-c)b gives "
                "c = 13.9% of all interruptions, i.e. 35.7% of observed attributions "
                "genuine; the 'roughly three-quarters is background' phrasing is replaced.",
         disposition="ADOPTED. The additive excess remains the primary estimand; the "
                     "ratio form is reported as a bounded interpretation with its "
                     "assumption stated.",
         contract_compliant="correction of error"),
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
