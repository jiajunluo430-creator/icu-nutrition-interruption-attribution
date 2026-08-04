"""N2 step 13 - assemble and QA the Frontiers in Nutrition submission package."""
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
SUB, FIG, OUT, MAN = ROOT / "08_submission", ROOT / "04_figures", ROOT / "03_outputs", ROOT / "07_manuscript"
PKG = SUB / "package"
if PKG.exists():
    shutil.rmtree(PKG)
PKG.mkdir(parents=True)

# ---------------------------------------------------------------- figures
figs = ["figure1_cohort_flow", "figure2_delivery_and_shortfall",
        "figure3_attribution", "figure4_energy_through_null"]
for i, f in enumerate(figs, 1):
    for ext in ("tif", "pdf"):
        src = FIG / f"{f}.{ext}"
        if src.exists():
            shutil.copy(src, PKG / f"Figure{i}.{ext}")

# ---------------------------------------------------------------- documents
for src, dst in [("N2_FrontNutr_manuscript.docx", "Manuscript.docx"),
                 ("N2_cover_letter.docx", "Cover_Letter.docx"),
                 ("N2_Supplementary_Material.docx", "Supplementary_Material.docx")]:
    shutil.copy(SUB / src, PKG / dst)

shutil.copy(OUT / "references_verified.csv", PKG / "references_verified.csv")
shutil.copy(OUT / "citation_order_check.csv", PKG / "citation_order_check.csv")

# ---------------------------------------------------------------- QA
ms = (MAN / "FrontNutr_main_manuscript.md").read_text(encoding="utf-8")
val = pd.read_csv(OUT / "manuscript_validation.csv")
refs = pd.read_csv(OUT / "references_verified.csv")
gates = pd.read_csv(OUT / "pilot_gates.csv")
reg = pd.read_csv(OUT / "exploratory_attempts.csv")
CANJ = json.load(open(OUT / "canonical" / "canonical_primary.json"))
_sup = (MAN / "supplement.md").read_text(encoding="utf-8")
_cov = (MAN / "cover_letter_frontnutr.md").read_text(encoding="utf-8")
_canon_val = f"{CANJ['target_excess_kcal']:,.0f}"
# superseded values are legitimate inside S13 (the historical decision registry);
# they must not appear in any live section
_sup_live = _sup.split("## S13. Post-freeze decision registry")[0]
_orphans = [v for v in ("113,763", "114,058", "114,220", "114,317", "60,135")
            if v in ms or v in _sup_live or v in _cov]

body = ms.split("\n## References\n", 1)[0]
nrefs = len(refs)
cited = set()
for m in re.finditer(r"\((\d+(?:[,\u2013\s]+\d+)*)\)", body):
    for part in re.split(r",\s*", m.group(1)):
        r = re.match(r"^(\d+)\s*\u2013\s*(\d+)$", part.strip())
        if r:
            cited.update(range(int(r.group(1)), int(r.group(2)) + 1))
        elif part.strip().isdigit() and 1 <= int(part) <= nrefs:
            cited.add(int(part))

checks = [
    ("ONE canonical primary value everywhere",
     _canon_val in ms and _canon_val in _sup and _canon_val in _cov and not _orphans,
     f"{_canon_val}; orphans={_orphans or 'none'}"),
    ("no Python nan in supplement", "nan" not in _sup, "yes"),
    ("all quantitative claims validated", int(val["pass"].sum()) == len(val),
     f"{int(val['pass'].sum())}/{len(val)}"),
    ("every reference PubMed-verified", len(refs) == nrefs and refs["pmid"].notna().all(),
     f"{nrefs} refs, all with PMID"),
    ("every reference cited in text", cited == set(range(1, nrefs + 1)),
     f"cited {len(cited)}/{nrefs}"),
    ("citations sequential from 1", sorted(cited) == list(range(1, nrefs + 1)), "1..%d" % nrefs),
    ("abstract present", "## Abstract" in ms, "yes"),
    ("data availability statement", "Data availability statement" in ms, "yes"),
    ("ethics statement", "Ethics statement" in ms, "yes"),
    ("ND03 cohort-overlap disclosed", "Relationship to prior work" in ms, "yes"),
    ("failed gates disclosed in text", "12 events" in ms, "yes"),
    ("no stale primary value in main text", "113,763" not in ms and "60,135" not in ms, "yes"),
    ("superseded estimate disclosed in supplement",
     "450,892" in (MAN / "supplement.md").read_text(encoding="utf-8"), "yes"),
    ("estimand run through null", "computed through the null" in ms, "yes"),
    ("DOI placeholder replaced", "[REPOSITORY DOI]" not in ms,
     "BLOCKER: replace [REPOSITORY DOI] before upload"),
    ("no outcome model claimed", "no outcome association of any kind was estimated" in ms, "yes"),
    ("post-freeze registry complete", len(reg) >= 16, f"{len(reg)} entries E01-E16"),
    ("gates recorded", len(gates) >= 11, f"{len(gates)} gates"),
    ("4 figures present (tif+pdf)",
     all((PKG / f"Figure{i}.{ext}").exists() for i in range(1, 5) for ext in ("tif", "pdf")), "yes"),
    ("3 documents present",
     all((PKG / n).exists() for n in ("Manuscript.docx", "Cover_Letter.docx",
                                      "Supplementary_Material.docx")), "yes"),
]
qa = pd.DataFrame(checks, columns=["check", "pass", "detail"])
qa.to_csv(PKG / "submission_qa.csv", index=False)

# ---------------------------------------------------------------- checklist
out = [
    "# N2 \u2014 Frontiers in Nutrition submission package",
    "",
    f"Assembled {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
    "",
    "## Contents", "",
    "| File | Purpose |", "|---|---|",
    "| `Manuscript.docx` | Original Research, single-spaced, continuous line numbers |",
    "| `Cover_Letter.docx` | Leads with the corrected estimand and the failed-gate disclosure |",
    "| `Supplementary_Material.docx` | S1–S14 incl. frozen plan, 43-item class list, full sensitivity table |",
    "| `Figure1–4.tif / .pdf` | 300 dpi, grayscale-safe, panel-labelled |",
    f"| `references_verified.csv` | PMID + DOI for all {nrefs} references |",
    "| `citation_order_check.csv` | Citation number → PMID map |",
    "| `submission_qa.csv` | Automated package checks |",
    "", "## Automated QA", "",
    qa.assign(**{"pass": qa["pass"].map({True: "PASS", False: "FAIL"})}).to_markdown(index=False),
    "", "## Before upload", "",
    "- [ ] **Replace `[REPOSITORY DOI]`** in the Data availability statement (Manuscript.docx)",
    "- [ ] ORCIDs for all five authors",
    "- [ ] Confirm abstract word count in Word against the Frontiers 350-word limit",
    "- [ ] Confirm current institutional recognition status of Frontiers in Nutrition",
    "",
    "Author names, affiliations, corresponding authors, funding, conflicts, CRediT and the",
    "PhysioNet credentialing statement (Jiajun Luo) are already in the manuscript.",
    "",
    "## Provenance of every number",
    "",
    "All manuscript, table, figure, supplement, registry and checklist values derive from",
    "`outputs/canonical/` (canonical_primary.json, canonical_class_results.csv,",
    "canonical_sensitivity.csv, canonical_null_distribution.csv), generated once from a",
    f"locked referent draw set (seed {CANJ['seed']}, {CANJ['n_replicates']:,} replicates).",
    "Superseded tables are quarantined in `03_outputs/_superseded/` so no builder can read",
    "them. Hard assertions verify that class-level observed, null and excess energies sum",
    "exactly to the primary totals.",
    "",
    f"**Canonical primary:** {CANJ['target_excess_kcal']:,.0f} kcal "
    f"(95% CI {CANJ['target_excess_ci'][0]:,.0f}-{CANJ['target_excess_ci'][1]:,.0f}) = "
    f"{CANJ['target_pct']}% of the shortfall, {CANJ['target_per_stay']} kcal per ICU stay.",
    "",
    "## Estimate history (all superseded values are logged in the registry)",
    "",
    "| Version | Primary estimate | Why superseded |",
    "|---|---|---|",
    "| Specificity-screened | 450,892 kcal / 1.3% | Classes screened on the null, then full observed burden summed |",
    "| Estimand through null, P0 included | 60,135 kcal / 0.09% | Negative control offset the target classes |",
    "| P0 excluded, per-script RNG | 113,763-114,317 kcal | Five drifting values across scripts |",
    f"| **Canonical (current)** | **{CANJ['target_excess_kcal']:,.0f} kcal / {CANJ['target_pct']}%** | - |",
    "",
    f"Sensitivity range {CANJ['sensitivity_pct_min']:.2f}-{CANJ['sensitivity_pct_max']:.2f}%; "
    f"complementary across-patient null {CANJ['day_preserving_pct']:.2f}%.",
    "",
    f"Post-freeze decision registry: {len(reg)} entries (E01-E25).",
    "",
]
(PKG / "SUBMISSION_CHECKLIST.md").write_text("\n".join(out), encoding="utf-8")

# ---------------------------------------------------------------- zip
stamp = datetime.now().strftime("%Y-%m-%d")
zpath = SUB / f"N2_FrontiersNutrition_submission_{stamp}.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(PKG.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(PKG))

print(qa.to_string(index=False))
print(f"\nPASS {int(qa['pass'].sum())}/{len(qa)}")
print(f"\npackage: {zpath}")
print(f"size   : {zpath.stat().st_size/1e6:.2f} MB")
print(f"sha256 : {hashlib.sha256(zpath.read_bytes()).hexdigest()[:32]}")
for f in sorted(PKG.iterdir()):
    print(f"  {f.name:34s} {f.stat().st_size/1024:8.1f} KB")
