# Chance co-occurrence inflates procedure attribution of enteral nutrition interruption

Analysis code for the manuscript submitted to *Frontiers in Nutrition* (Clinical
Nutrition).

**Short version of the finding.** In 6,883 first ICU stays from MIMIC-IV v3.1, 38.9% of
charted enteral/parenteral feeding interruptions had a clinical procedure in the
attribution window. Under a circular within-stay time shift that destroys true temporal
correspondence while preserving procedure density, 30.3% still did. The chance-corrected
excess is 8.7 percentage points (95% CI 7.1-10.3), so most apparent attribution is
chance. Procedure-related interruption explains 1.3% of the cohort's total energy
deficit.

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
python scripts/10_verify_references.py    # PubMed reference verification
python scripts/14_expand_references.py
python scripts/11_insert_citations.py     # citation numbering + order check
python scripts/06_validate_manuscript.py  # checks every number against outputs
python scripts/12_build_docx.py
python scripts/13_assemble_submission.py
python scripts/15_build_code_release.py
```

`scripts/01` and `scripts/03` are the slow steps (full scans of ~11M and ~12M rows).

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

Luo J, Chen Q, Liu J, Lu F, Liang X. Chance co-occurrence inflates procedure attribution
of enteral nutrition interruption: a placebo-controlled analysis of the ICU energy
deficit in 6,883 critically ill adults. *Submitted*.

## License

MIT (see `LICENSE`). The MIMIC-IV and eICU databases carry their own terms.
