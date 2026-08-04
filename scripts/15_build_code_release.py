"""N2 step 15 - build the public code-release package for GitHub/Zenodo.

HARD RULE: the PhysioNet data use agreement forbids redistributing MIMIC-IV or eICU
data. Only code, the frozen contract, and AGGREGATE outputs go in. Every file is
checked against a row-level denylist before it is copied, and the script aborts if a
denied file would be included.
"""
import csv
import hashlib
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
REL = ROOT / "09_code_release"
if REL.exists():
    shutil.rmtree(REL)

# --- files that contain row-level, patient-linked records: never publish
DENY = {
    "cohort.csv", "interruptions.csv", "segments_final.csv",
    "procedures_in_window.csv", "stay_days.csv",
    "nutrition_segments_raw.csv", "nutrition_ingredients.csv",
    "icustays.csv", "procedures.csv", "covariates.csv", "vent_intervals.csv",
}

AGGREGATE = [
    "table1_cohort.csv", "table2_delivery_adequacy.csv",
    "table3_interruption_burden.csv", "table4_attribution_specificity.csv",
    "table5_excess_fasting.csv", "table6_sensitivity.csv",
    "table7_attribution_ci.csv", "table8_time_of_day.csv",
    "pilot_gates.csv", "gate_summary.json", "main_results.json",
    "strengthen_results.json", "null_distribution.csv", "eicu_g6.json",
    "eicu_hospital_counts.csv", "exploratory_attempts.csv", "cohort_flow.csv",
    "references_verified.csv", "citation_order_check.csv",
    "manuscript_validation.csv", "reproducibility_manifest.csv",
]

(REL / "scripts").mkdir(parents=True)
(REL / "contract").mkdir()
(REL / "outputs").mkdir()
(REL / "figures").mkdir()

copied = []
for f in sorted((ROOT / "01_scripts").glob("*.py")):
    shutil.copy(f, REL / "scripts" / f.name); copied.append(f.name)
for f in sorted((ROOT / "00_contracts").iterdir()):
    shutil.copy(f, REL / "contract" / f.name); copied.append(f.name)
for n in AGGREGATE:
    src = ROOT / "03_outputs" / n
    if src.exists():
        shutil.copy(src, REL / "outputs" / n); copied.append(n)
for f in sorted((ROOT / "04_figures").glob("*")):
    if f.suffix in (".png", ".pdf"):
        shutil.copy(f, REL / "figures" / f.name); copied.append(f.name)

leaked = sorted(set(copied) & DENY)
if leaked:
    raise SystemExit(f"ABORT: row-level files would be published: {leaked}")

(REL / "requirements.txt").write_text(
    "pandas>=3.0\nnumpy>=2.0\nmatplotlib>=3.10\nscipy>=1.17\npython-docx>=1.2\n"
    "tabulate>=0.9\n", encoding="utf-8")

(REL / ".gitignore").write_text(
    "# Never commit derived patient-level data\n"
    "*intermediates*/\ncohort.csv\ninterruptions.csv\nsegments_final.csv\n"
    "procedures_in_window.csv\nstay_days.csv\n*.gz\n__pycache__/\n*.pyc\n",
    encoding="utf-8")

(REL / "LICENSE").write_text(
    "MIT License\n\n"
    "Copyright (c) 2026 Jiajun Luo, Qinglong Chen, Jing Liu, Fanghui Lu, Xiaolong Liang\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy of "
    "this software and associated documentation files (the \"Software\"), to deal in "
    "the Software without restriction, including without limitation the rights to use, "
    "copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the "
    "Software, and to permit persons to whom the Software is furnished to do so, "
    "subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all "
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS "
    "FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR "
    "COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN "
    "AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION "
    "WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n",
    encoding="utf-8")

gates = list(csv.DictReader(open(ROOT / "03_outputs" / "pilot_gates.csv", encoding="utf-8")))
README = f"""# Chance co-occurrence inflates procedure attribution of enteral nutrition interruption

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
""" + "\n".join(
    f"| {g['gate']} | {g['criterion']} | {g['observed']} | "
    f"{'PASS' if g['pass']=='True' else ('FAIL' if g['pass']=='False' else 'interpretive')} |"
    for g in gates) + """

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
"""
(REL / "README.md").write_text(README, encoding="utf-8")

rows = []
for f in sorted(REL.rglob("*")):
    if f.is_file():
        rows.append({"path": str(f.relative_to(REL)).replace("\\", "/"),
                     "bytes": f.stat().st_size,
                     "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
with open(REL / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"]); w.writeheader()
    w.writerows(rows)

stamp = datetime.now().strftime("%Y-%m-%d")
zp = ROOT / "08_submission" / f"N2_code_release_{stamp}.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(REL.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(REL))

print(f"files: {len(rows)}   (denylist violations: 0)")
for d in sorted({r['path'].split('/')[0] for r in rows}):
    n = sum(1 for r in rows if r['path'].split('/')[0] == d)
    print(f"  {d:22s} {n:>3}")
print(f"\nrelease dir : {REL}")
print(f"release zip : {zp}  ({zp.stat().st_size/1e6:.2f} MB)")
print(f"generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
