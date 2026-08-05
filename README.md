# Background co-occurrence inflates procedure attribution of feeding interruptions in the ICU

Analysis code for a two-database study of MIMIC-IV v3.1 and eICU-CRD v2.0.

**The finding.** Feeding interruptions in the ICU are routinely attributed to procedures
because the two happened close together in time. In 6,883 MIMIC-IV first ICU stays, 38.9%
of charted interruptions had a procedure within +/-1 h. At matched control times in the
same stay, relocated by whole ICU days so the time of day is preserved but any true
correspondence destroyed, 29.1% still did: an excess of only
9.9 percentage points (95% CI 8.5-11.1).
Applying the same correction to energy gives 114,660 kcal
(95% CI 81,782-144,699) =
**0.177% of the standardized first-week shortfall**, or
16.7 kcal per ICU stay
(0.14-0.34% across specifications).

**External validation.** eICU-CRD cannot define feeding interruptions (no infusion rate,
no paused/stopped status), but the background rate is a property of procedure density, not
of nutrition records. Across 63,703 stays in 206 hospitals
it was 6.7% (95% CI 6.5-6.8),
against a like-for-like MIMIC-IV rate of 8.1%, and
7.7% among the 92 best-documenting
hospitals. But between hospitals it spans
0.8-22.9% (10th-90th centile) even after
accounting for documentation completeness, so raw attribution percentages are not
comparable across units. Documentation itself lagged events by a median
49 min, exceeding 1 h in 43.7% of
paired nursing records - the same magnitude as the attribution window.

All reported values derive from a single canonical output set (`outputs/canonical/`)
generated once from a locked referent draw set (seed 20260807, 1,000
replicates), with assertions verifying that class-level energies sum exactly to the
primary totals. Two analysis plans were frozen and SHA-256 hashed before the estimates
they govern were computed (`contract/`).

## What is and is not here

This repository contains **code, the frozen analysis contract, and aggregate results
only**. It contains **no patient-level data**. MIMIC-IV and eICU-CRD are governed by the
PhysioNet credentialed data use agreement and cannot be redistributed. To reproduce the
analysis you must obtain them yourself from PhysioNet.

- `contract/` - the analysis contract, frozen with a SHA-256 hash *before* any estimate
  was computed, plus the frozen nutrition item list
- `scripts/` - the full pipeline, numbered in execution order
- `outputs/` - aggregate tables, gate results, the post-freeze decision registry
- `figures/` - manuscript figures

## Reproducing

1. Obtain MIMIC-IV v3.1 and eICU-CRD v2.0 from PhysioNet (credentialing required).
2. Edit the two source paths at the top of `scripts/01_extract_mimic.py` and
   `scripts/03_eicu_gate_g6.py`.
3. `pip install -r requirements.txt`
4. Run in order:

```
python scripts/01_extract_mimic.py        # one pass over the source tables
python scripts/02_build_and_gate.py       # cohort, interruptions, binding gates
python scripts/03_eicu_gate_g6.py         # eICU transportability gate
python scripts/04_main_analysis.py        # primary analysis
python scripts/08_strengthen.py           # bootstrap CIs, circular null, deficit share
python scripts/09_figures_v2.py           # figures
python scripts/23_locked_null_and_p0.py   # writes locked_referent_draws.npy (seed 20260807)
python scripts/24_day_preserving_null.py  # complementary across-patient null
python scripts/26_rate_ci_from_locked.py  # rate CIs from the locked draws
python scripts/27_canonical.py            # THE single source of truth -> outputs/canonical/
python scripts/29_p0_diagnostics_canonical.py
python scripts/22_build_supplement_v2.py  # supplement, rebuilt from canonical
python scripts/10_verify_references.py    # PubMed reference verification
python scripts/14_expand_references.py
python scripts/11_insert_citations.py     # citation numbering + order check
python scripts/06_validate_manuscript.py  # checks every number against outputs
python scripts/12_build_docx.py
python scripts/13_assemble_submission.py
python scripts/15_build_code_release.py
```

`scripts/01` and `scripts/03` are the slow steps (full scans of ~11M and ~12M rows).

**`27_canonical.py` is the one that matters for reproducing the reported numbers.** An
earlier version of this pipeline let scripts 17, 20 and 23 each seed their own generator,
which produced several mutually inconsistent estimates of the same quantity. Script 27
now recomputes the primary estimand, every class, and every sensitivity specification
from one locked draw set in a single pass, and asserts that the class-level energies sum
to the primary total before writing anything. Tables that predate it are quarantined
under `outputs/superseded/` with the value that replaced them.

## Prespecification

Every cohort criterion, item list, interruption rule, procedure class, attribution
window, guideline-defensible fasting window, target and stop-loss gate was fixed in
`contract/N2_analysis_contract_v1.md` and hashed before analysis. Binding gate results:

| Gate | Criterion | Observed | Verdict |
|---|---|---|---|
| G1 | eligible first-ICU stays >= 5000 | 6883.0 | PASS |
| G2 | nutrition record usability >= 80% | 0.997 | PASS |
| G3a | qualifying interruptions >= 5000 | 5499.0 | PASS |
| G3b | observed - placebo attribution >= 10 pp | 10.84 | PASS |
| G4 | native kcal coverage >= 80% | 0.9718 | PASS |
| G5a | ERCP travel vs in-unit >= 100 per arm | 0.0 | FAIL |
| G5b | portable CT vs CT >= 300 per arm | 0.0 | FAIL |
| G7 | negative-control P0 attribution rate (interpretive) | 0.0991 | interpretive |
| G6a | eICU >=30 hospitals with >=20 eligible stays | 47.0 | PASS |
| G6b | eICU can represent interruption semantics (rate + status) | 0.0 | FAIL |
| G6 | eICU overall (G6a AND G6b) | 0.0 | FAIL |

Two prespecified analyses failed their gates and were **dropped rather than rescued**: a
within-procedure logistics contrast (the relevant MIMIC items are nearly unpopulated)
and multicentre replication in eICU (its intake records carry no infusion rate and no
status field).

Every post-freeze decision, including one where our own prespecified falsification test
proved biased in our favour, is recorded in `outputs/exploratory_attempts.csv`.

## Citation

Luo J, Chen Q, Liu J, Lu F, Liang X. Background co-occurrence inflates procedure
attribution of feeding interruptions in the ICU: a matched-time analysis of two
critical care databases. *Submitted*.

## License

MIT (see `LICENSE`). The MIMIC-IV and eICU databases carry their own terms.
