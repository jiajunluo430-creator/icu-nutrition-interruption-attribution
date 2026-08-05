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
    # never delete .git - the release dir is a working git repo pushed to GitHub
    for _p in REL.iterdir():
        if _p.name == ".git":
            continue
        shutil.rmtree(_p) if _p.is_dir() else _p.unlink()

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

# the canonical set is what every reported number comes from - it must ship.
# .npy is excluded on purpose: obs/null_assigned_primary.npy carry one element per
# interruption in the same row order as interruptions.csv, i.e. derived row-level data.
# They are deterministic from seed 20260807, so scripts 23 and 27 regenerate them.
(REL / "outputs" / "canonical").mkdir()
for f in sorted((ROOT / "03_outputs" / "canonical").glob("*")):
    if f.suffix == ".npy":
        continue
    shutil.copy(f, REL / "outputs" / "canonical" / f.name); copied.append(f.name)
# and the tables the canonical set superseded, so the record is auditable
(REL / "outputs" / "superseded").mkdir()
for f in sorted((ROOT / "03_outputs" / "_superseded").glob("*")):
    shutil.copy(f, REL / "outputs" / "superseded" / f.name); copied.append(f.name)
for n in ("rev3_day_preserving_null.json", "rev3_p0_diagnostics.csv",
          "rate_ci_locked.json", "eicu_interface_audit.json",
          "eicu_background_rate.json", "eicu_ascertainment_diagnostic.json",
          "eicu_background_by_hospital.csv", "eicu_hospital_ascertainment.csv",
          "eicu_hospital_stay_counts.csv", "critcare_validation.csv"):
    src = ROOT / "03_outputs" / n
    if src.exists():
        shutil.copy(src, REL / "outputs" / n); copied.append(n)

leaked = sorted(set(copied) & DENY)
if leaked:
    raise SystemExit(f"ABORT: row-level files would be published: {leaked}")

# --- structural guard: a filename denylist only catches files we thought of.
# Nothing may ship that is one-row-per-patient-record or an opaque binary array.
N_REPLICATES, ID_COLS = 1000, ("stay_id", "subject_id", "hadm_id", "patientunitstayid")
struct = []
for f in sorted(REL.rglob("*")):
    rel = f.relative_to(REL).parts
    if not f.is_file() or ".git" in rel or rel[0] in ("scripts", "figures"):
        continue
    if f.suffix in (".npy", ".npz", ".pkl", ".parquet", ".feather"):
        struct.append(f"{f.name}: binary array")
        continue
    if f.suffix != ".csv":
        continue
    with open(f, encoding="utf-8", errors="replace") as fh:
        hdr = [c.strip().lower() for c in (fh.readline().split(","))]
        n = sum(1 for _ in fh)
    hit = sorted(set(hdr) & set(ID_COLS))
    if hit:
        struct.append(f"{f.name}: identifier column {hit}")
    elif n > N_REPLICATES:
        struct.append(f"{f.name}: {n} rows > {N_REPLICATES} replicates")
if struct:
    raise SystemExit("ABORT: structural row-level check failed:\n  " + "\n  ".join(struct))

(REL / "requirements.txt").write_text(
    "pandas>=3.0\nnumpy>=2.0\nmatplotlib>=3.10\nscipy>=1.17\npython-docx>=1.2\n"
    "tabulate>=0.9\n", encoding="utf-8")

(REL / ".gitignore").write_text(
    "# Never commit derived patient-level data\n"
    "*intermediates*/\ncohort.csv\ninterruptions.csv\nsegments_final.csv\n"
    "procedures_in_window.csv\nstay_days.csv\n*.gz\n__pycache__/\n*.pyc\n"
    "# derived per-interruption arrays - regenerable from seed 20260807\n*.npy\n",
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

import json as _json
gates = list(csv.DictReader(open(ROOT / "03_outputs" / "pilot_gates.csv", encoding="utf-8")))
C = _json.load(open(ROOT / "03_outputs" / "canonical" / "canonical_primary.json"))
EB = _json.load(open(ROOT / "03_outputs" / "eicu_background_rate.json"))
EA = _json.load(open(ROOT / "03_outputs" / "eicu_ascertainment_diagnostic.json"))
EI = _json.load(open(ROOT / "03_outputs" / "eicu_interface_audit.json"))
README = f"""# Background co-occurrence inflates procedure attribution of feeding interruptions in the ICU

Analysis code for a two-database study of MIMIC-IV v3.1 and eICU-CRD v2.0.

**The finding.** Feeding interruptions in the ICU are routinely attributed to procedures
because the two happened close together in time. In 6,883 MIMIC-IV first ICU stays, 38.9%
of charted interruptions had a procedure within +/-1 h. At matched control times in the
same stay, relocated by whole ICU days so the time of day is preserved but any true
correspondence destroyed, {C["rate"]["null_pct"]}% still did: an excess of only
{C["rate"]["excess_pp"]} percentage points (95% CI {C["rate"]["ci_lo"]}-{C["rate"]["ci_hi"]}).
Applying the same correction to energy gives {C["target_excess_kcal"]:,.0f} kcal
(95% CI {C["target_excess_ci"][0]:,.0f}-{C["target_excess_ci"][1]:,.0f}) =
**{C["target_pct"]}% of the standardized first-week shortfall**, or
{C["target_per_stay"]} kcal per ICU stay
({C["sensitivity_pct_min"]:.2f}-{C["sensitivity_pct_max"]:.2f}% across specifications).

**External validation.** eICU-CRD cannot define feeding interruptions (no infusion rate,
no paused/stopped status), but the background rate is a property of procedure density, not
of nutrition records. Across {EB["eicu_stays"]:,} stays in {EI["hospitals_total"]} hospitals
it was {EB["eicu_background_pct"]}% (95% CI {EB["eicu_background_ci"][0]}-{EB["eicu_background_ci"][1]}),
against a like-for-like MIMIC-IV rate of {EB["mimic_p1_background_pct"]}%, and
{EA["restricted_median_pct"]}% among the {EA["restricted_n_hospitals"]} best-documenting
hospitals. But between hospitals it spans
{EA["restricted_p10_p90"][0]}-{EA["restricted_p10_p90"][1]}% (10th-90th centile) even after
accounting for documentation completeness, so raw attribution percentages are not
comparable across units. Documentation itself lagged events by a median
{EI["doc_lag_median_min"]:.0f} min, exceeding 1 h in {EI["doc_lag_pct_over_60min"]}% of
paired nursing records - the same magnitude as the attribution window.

All reported values derive from a single canonical output set (`outputs/canonical/`)
generated once from a locked referent draw set (seed {C["seed"]}, {C["n_replicates"]:,}
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

Luo J, Chen Q, Liu J, Lu F, Liang X. Background co-occurrence inflates procedure
attribution of feeding interruptions in the ICU: a matched-time analysis of two
critical care databases. *Submitted*.

## License

MIT (see `LICENSE`). The MIMIC-IV and eICU databases carry their own terms.
"""
(REL / "README.md").write_text(README, encoding="utf-8")

def _shipped(f):
    """Files that belong in the manifest/zip: everything except the git metadata."""
    return f.is_file() and ".git" not in f.relative_to(REL).parts


rows = []
for f in sorted(REL.rglob("*")):
    if _shipped(f):
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
        if _shipped(f):
            z.write(f, f.relative_to(REL))

print(f"files: {len(rows)}   (denylist violations: 0)")
for d in sorted({r['path'].split('/')[0] for r in rows}):
    n = sum(1 for r in rows if r['path'].split('/')[0] == d)
    print(f"  {d:22s} {n:>3}")
print(f"\nrelease dir : {REL}")
print(f"release zip : {zp}  ({zp.stat().st_size/1e6:.2f} MB)")
print(f"generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
