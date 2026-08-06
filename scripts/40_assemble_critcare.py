"""N2 step 40 - assemble and QA the Critical Care submission package."""
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
SUB, FIG, OUT, MAN = (ROOT / "08_submission", ROOT / "04_figures",
                      ROOT / "03_outputs", ROOT / "07_manuscript")
CAN = OUT / "canonical"
PKG = SUB / "critcare_package"
if PKG.exists():
    shutil.rmtree(PKG)
PKG.mkdir(parents=True)

FIGS = ["figure1_cohort_flow", "figure2_delivery_and_shortfall", "figure3_attribution",
        "figure4_energy_through_null", "figure5_external_validation"]
for i, f in enumerate(FIGS, 1):
    for ext in ("tif", "pdf"):
        src = FIG / f"{f}.{ext}"
        if src.exists():
            shutil.copy(src, PKG / f"Fig{i}.{ext}")
for src, dst in [("CritCare_manuscript.docx", "Manuscript.docx"),
                 ("CritCare_cover_letter.docx", "Cover_Letter.docx"),
                 ("CritCare_Additional_file_1.docx", "Additional_file_1.docx")]:
    shutil.copy(SUB / src, PKG / dst)
for n in ("references_verified.csv", "critcare_validation.csv"):
    shutil.copy(OUT / n, PKG / n)

ms = (MAN / "CritCare_main_manuscript.md").read_text(encoding="utf-8")
MSF = re.sub(r"\s+", " ", ms)
af = (MAN / "CritCare_additional_file.md").read_text(encoding="utf-8")
cov = (MAN / "cover_letter_critcare.md").read_text(encoding="utf-8")
val = pd.read_csv(OUT / "critcare_validation.csv")
refs = pd.read_csv(OUT / "references_verified.csv")
reg = pd.read_csv(OUT / "exploratory_attempts.csv")
C = json.load(open(CAN / "canonical_primary.json"))
EB = json.load(open(OUT / "eicu_background_rate.json"))
FREEZE = json.load(open(ROOT / "00_contracts" / "external_validation_freeze.json"))
reg_ids = sorted(reg["attempt"].astype(str))
canon = f"{C['target_excess_kcal']:,.0f}"

# citation coverage, ignoring table rows whose IQRs look like citation ranges
body = "\n".join(l for l in ms.split("\n## References", 1)[0].split("\n")
                 if not l.lstrip().startswith("|"))
cited = set()
for m in re.finditer(r"\[(\d+(?:\s*[,\u2013-]\s*\d+)*)\]", body):
    for part in re.split(r",\s*", m.group(1)):
        r = re.match(r"^(\d+)\s*[\u2013-]\s*(\d+)$", part.strip())
        if r:
            cited.update(range(int(r.group(1)), int(r.group(2)) + 1))
        elif part.strip().isdigit():
            cited.add(int(part.strip()))
nrefs = len(refs)

# superseded values are legitimate only inside the historical registry section
af_live = af.split("## S13. Post-freeze decision registry")[0]
af_live = "\n".join(l for l in af_live.split("\n")
                    if not l.strip().startswith("**Superseded:**"))
STALE = ("113,763", "114,058", "114,220", "114,317", "60,135", "450,892", "1.3%",
         "8.7 percentage", "30.3%")
orphans = sorted({v for v in STALE for txt in (ms, af_live, cov) if v in txt})

checks = [
    ("ONE canonical primary value everywhere",
     all(canon in t for t in (ms, af, cov)) and not orphans,
     f"{canon}; orphans={orphans or 'none'}"),
    ("all quantitative claims validated", int(val["pass"].sum()) == len(val),
     f"{int(val['pass'].sum())}/{len(val)}"),
    ("every reference cited", cited == set(range(1, nrefs + 1)), f"{len(cited)}/{nrefs}"),
    ("citations sequential from 1", sorted(cited) == list(range(1, nrefs + 1)),
     f"1..{nrefs}"),
    ("every reference PubMed-verified", refs["pmid"].notna().all(),
     f"{nrefs} refs with PMID"),
    ("no Python nan in additional file", "nan" not in af, "yes"),
    ("both analysis plans hashed",
     "307a6452" in af and FREEZE["sha256"][:8] in af, "primary + external"),
    ("external plan frozen before estimation",
     "before any background rate was computed" in re.sub(r"\s+", " ", af), "stated"),
    ("eICU interruption failure still disclosed",
     "G6 overall | **FAIL**" in af and "failed" in MSF, "yes"),
    ("eICU energy explicitly not attempted",
     "No energy or kcal estimate was attempted in eICU" in MSF, "yes"),
    ("hospital spread not read as care quality",
     "should not be read as variation in quality of care" in MSF, "yes"),
    # the additional file is built from supplement.md, which is generated separately;
    # pin every registry id so a stale supplement can never ship
    ("registry in additional file matches the registry CSV",
     all(rid in af for rid in reg_ids),
     f"all {len(reg_ids)} ids present"),
    ("post-hoc gate change disclosed", "post-hoc gate change" in af,
     "E27 flagged non-compliant"),
    ("negative control energy caveat retained",
     "do **not** claim that the energy scale is validated" in MSF, "yes"),
    ("no outcome model claimed",
     "no outcome association of any kind was estimated" in MSF, "yes"),
    ("post-freeze registry complete",
     reg_ids == [f"E{i:02d}" for i in range(1, len(reg) + 1)],
     f"{len(reg)} entries {reg_ids[0]}-{reg_ids[-1]}, no gaps"),
    ("repository URL present, no placeholder",
     "[REPOSITORY DOI]" not in ms and "github.com/jiajunluo430-creator" in ms,
     "public repo; Zenodo DOI to be minted"),
    ("cover letter dated", cov.strip().startswith("5 August 2026"), "5 August 2026"),
    ("two-database framing in title",
     "two critical care databases" in ms.split("\n", 1)[0], "yes"),
    ("5 figures present (tif+pdf)",
     all((PKG / f"Fig{i}.{ext}").exists() for i in range(1, 6) for ext in ("tif", "pdf")),
     "yes"),
    ("3 documents present",
     all((PKG / n).exists() for n in ("Manuscript.docx", "Cover_Letter.docx",
                                      "Additional_file_1.docx")), "yes"),
]
qa = pd.DataFrame(checks, columns=["check", "pass", "detail"])
qa.to_csv(PKG / "submission_qa.csv", index=False)

out = [
    "# Critical Care submission package", "",
    f"Assembled {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
    "## Contents", "", "| File | Purpose |", "|---|---|",
    "| `Manuscript.docx` | Research article, continuous line numbers |",
    "| `Cover_Letter.docx` | Leads with the two-database result and the quality-metric implication |",
    "| `Additional_file_1.docx` | S1-S17 incl. both frozen plans, eICU audit, decision registry |",
    "| `Fig1-5.tif / .pdf` | 300 dpi, grayscale-safe, panel-labelled |",
    f"| `references_verified.csv` | PMID + DOI for all {nrefs} references |",
    "| `critcare_validation.csv` | Every manuscript number checked against canonical outputs |",
    "| `submission_qa.csv` | Automated package checks |",
    "", "## Automated QA", "",
    qa.assign(**{"pass": qa["pass"].map({True: "PASS", False: "FAIL"})}).to_markdown(index=False),
    "", "## Before upload", "",
    "- [x] Code deposited: https://github.com/jiajunluo430-creator/icu-nutrition-interruption-attribution",
    "- [ ] Mint a Zenodo DOI from the release and add it to Availability of data and materials",
    "- [ ] ORCIDs for all five authors",
    "- [ ] Confirm abstract word count in Word against the Critical Care 350-word limit",
    "", "## Provenance", "",
    "Two analysis plans were frozen and SHA-256 hashed before the estimates they govern:",
    f"- primary `307a6452...` (2026-08-03)",
    f"- external validation `{FREEZE['sha256'][:8]}...` ({FREEZE['frozen_utc'][:10]})",
    "",
    f"**Primary:** {C['target_excess_kcal']:,.0f} kcal "
    f"(95% CI {C['target_excess_ci'][0]:,.0f}-{C['target_excess_ci'][1]:,.0f}) = "
    f"{C['target_pct']}% of the shortfall, {C['target_per_stay']} kcal per ICU stay.",
    f"**External:** eICU background {EB['eicu_background_pct']}% "
    f"vs like-for-like MIMIC-IV {EB['mimic_p1_background_pct']}%, "
    f"{EB['eicu_stays']:,} stays in {EB['hospitals']} hospitals.",
]
(PKG / "SUBMISSION_CHECKLIST.md").write_text("\n".join(out), encoding="utf-8")

stamp = datetime.now().strftime("%Y-%m-%d")
zp = SUB / f"N2_CriticalCare_submission_{stamp}.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(PKG.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(PKG))

print(qa.to_string(index=False))
print(f"\nPASS {int(qa['pass'].sum())}/{len(qa)}")
print(f"\npackage: {zp}")
print(f"size   : {zp.stat().st_size/1e6:.2f} MB")
print(f"sha256 : {hashlib.sha256(zp.read_bytes()).hexdigest()[:32]}")
for f in sorted(PKG.iterdir()):
    print(f"  {f.name:<34} {f.stat().st_size/1024:>8.1f} KB")
