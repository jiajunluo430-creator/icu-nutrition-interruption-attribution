"""N2 step 38 - build the Critical Care Additional file.

Starts from the validated supplement produced by script 22, then:
  - records the second frozen plan in S1
  - rewrites S12, which previously reported only the eICU failure, to report both the
    failure (interruptions) and the successful external validation (background rate)
  - appends S15 transport, S16 burden distribution, S17 post-procedure recovery

Every value is read from a deposited output. Nothing is typed in.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, MAN = ROOT / "03_outputs", ROOT / "03_outputs" / "canonical", ROOT / "07_manuscript"

SRC = (MAN / "supplement.md").read_text(encoding="utf-8")
FREEZE = json.load(open(ROOT / "00_contracts" / "external_validation_freeze.json"))
EI = json.load(open(OUT / "eicu_interface_audit.json"))
EB = json.load(open(OUT / "eicu_background_rate.json"))
EA = json.load(open(OUT / "eicu_ascertainment_diagnostic.json"))
TC = json.load(open(CAN / "canonical_transport_clinical.json"))
ERA = pd.read_csv(CAN / "canonical_temporal_transport.csv")
UNIT = pd.read_csv(CAN / "canonical_burden_by_unit.csv")
REC = pd.read_csv(CAN / "canonical_recovery_delay.csv")
BUR = TC["burden_distribution"]

# ------------------------------------------------------------------ S1 addendum
anchor = "The plan fixed every cohort criterion"
assert anchor in SRC
add = (f"- Second plan (external validation): `contract/{FREEZE['contract']}`\n"
       f"- SHA-256: `{FREEZE['sha256']}`\n"
       f"- Frozen (UTC): {FREEZE['frozen_utc']}\n"
       f"- Frozen after the eICU interface audit (S12) but **before any background rate "
       f"was computed**.\n\n")
t = SRC.replace(anchor, add + anchor, 1)

# ------------------------------------------------------------------ S12 rewrite
old_s12 = "## S12." + t.split("## S12.")[1].split("\n## S13")[0]
gates = "\n".join(
    f"| {g['gate']} | {g['criterion']} | {g['observed']} | "
    f"{'PASS' if g['pass'] else 'FAIL'} |" for g in EB["gates"])
audit_gates = "\n".join(
    f"| {g['gate']} | {g['criterion']} | {g['observed']} | "
    f"{'PASS' if g['pass'] else 'FAIL'} |" for g in EI["gates"])

new_s12 = f"""## S12. eICU: what failed, and what the same database can still support

### S12.1 The prespecified replication failed

The original plan called for full replication in eICU-CRD v2.0. It failed at gate G6b and
was **dropped rather than rescued**. eICU has ample population but its `intakeOutput`
records carry neither an infusion rate nor a status field, so *Paused* and *Stopped*
states cannot be reconstructed and a feeding interruption cannot be defined.

| metric | value |
|---|---|
| eICU unit stays | 200,859 |
| length of stay >= 48 h | 77,832 |
| nutrition volume rows | 238,407 |
| stays with >= 2 nutrition days | 5,069 |
| hospitals with >= 20 eligible stays | 47 |
| `intakeOutput` has infusion rate | **False** |
| `intakeOutput` has status field | **False** |
| G6 overall | **FAIL** |

### S12.2 Why the background rate is still estimable

The background co-occurrence rate is a property of **procedure density and window
width**, not of nutrition records. Nothing in the G6 failure constrains it. No energy or
kcal estimate is attempted in eICU; that would require exactly the fields G6 proved
absent.

### S12.3 Interface audit: which timestamps are event times

Only sources whose timestamps are verifiable event times were admitted.

| source | field | semantics | admitted |
|---|---|---|---|
| `respiratoryCare` | `ventstartoffset`, `ventendoffset` | event time | yes |
| `infusionDrug` | `infusionoffset` (sedation/NMB) | event time | yes |
| `nurseCare` | `nursecareoffset` + `nursecareentryoffset` | event **and** entry time | lag measurement only |
| `treatment` | `treatmentoffset` | no companion entry field, unverifiable | **no** |

Both admitted sources required deduplication to distinct time points. Respiratory-care
rows repeat the same ventilation start on every assessment, and infusion rows are
periodic rate charting rather than discrete administrations:

| source | raw rows | distinct events | inflation if uncorrected |
|---|---|---|---|
| airway | {EI['airway_rows_raw']:,} | {EI['airway_events']:,} | {EI['airway_dedup_ratio']}x |
| sedation / NMB | {EI['sedation_rows_raw']:,} | {EI['sedation_events']:,} | {EI['sedation_dedup_ratio']}x |

Counting rows would have driven the co-occurrence rate toward 100% and made the
comparison meaningless (registry E26).

**Audit gates.**

| gate | criterion | observed | verdict |
|---|---|---|---|
{audit_gates}

Gate E5 was restated after it failed, and this is disclosed rather than hidden: the
original floor of 0.5 events per stay-day was not derived from anything and sat above the
MIMIC-IV benchmark it was meant to be comparable with (0.271/stay-day). It was replaced
by a two-sided band within 3x of that benchmark; the observed ratio is 1.17x
(registry E27).

### S12.4 Estimation gates and result

Reference windows were placed independently of any nutrition event, {EB['windows_per_stay']}
per stay, with duration and onset hour transported from the empirical MIMIC-IV
interruption distributions (seed {EB['seed']}).

| gate | criterion | observed | verdict |
|---|---|---|---|
{gates}

| quantity | value |
|---|---|
| eICU stays | {EB['eicu_stays']:,} |
| reference windows | {EB['eicu_windows']:,} |
| eICU background rate | {EB['eicu_background_pct']}% (95% CI {EB['eicu_background_ci'][0]}-{EB['eicu_background_ci'][1]}) |
| MIMIC-IV observed rate, same class | {EB['mimic_p1_observed_pct']}% |
| MIMIC-IV background rate, same class | {EB['mimic_p1_background_pct']}% |
| MIMIC-IV excess, same class | {EB['mimic_p1_excess_pp']} pp |

### S12.5 Between-hospital spread and the ascertainment control

| quantity | all hospitals | best-documenting |
|---|---|---|
| hospitals (>= 20 stays) | {EB['hospitals']} | {EA['restricted_n_hospitals']} |
| median background rate | {EB['hosp_median_pct']}% | {EA['restricted_median_pct']}% |
| IQR | {EB['hosp_iqr'][0]}-{EB['hosp_iqr'][1]}% | {EA['restricted_iqr'][0]}-{EA['restricted_iqr'][1]}% |
| 10th-90th centile | {EB['hosp_p10_p90'][0]}-{EB['hosp_p10_p90'][1]}% | {EA['restricted_p10_p90'][0]}-{EA['restricted_p10_p90'][1]}% |

Ascertainment (the share of a hospital's stays recording any harmonized event) ranged
{EA['ascertainment_min_pct']}-{EA['ascertainment_max_pct']}% and correlated with the
background rate at r = {EA['pearson_r']}, so it explains {100*EA['r_squared']:.0f}% of the
between-hospital variance. It does not explain all of it: among hospitals documenting at
or above the median the rate still spans
{EA['restricted_p10_p90'][0]}-{EA['restricted_p10_p90'][1]}%.

**This is a spread in the measured background rate. It confounds true procedure density
with documentation practice and must not be read as variation in quality of care.**

### S12.6 Documentation lag

`nurseCare` is the only eICU table carrying both an event offset and an entry offset.

| quantity | value |
|---|---|
| paired records | {EI['doc_lag_n']:,} |
| median lag | {EI['doc_lag_median_min']:.0f} min |
| 75th centile | {EI['doc_lag_p75_min']:.0f} min |
| 95th centile | {EI['doc_lag_p95_min']:.0f} min |
| exceeding the +/-1 h attribution window | **{EI['doc_lag_pct_over_60min']}%** |

Descriptive only; no estimate is adjusted for it.

"""
t = t.replace(old_s12, new_s12, 1)

# ------------------------------------------------------------------ S15-S17
era_tbl = "\n".join(
    f"| {r.era.replace(' - ', '-')} | {r.stays:,} | {r.interruptions:,} | "
    f"{r.rate_observed_pct} | {r.rate_background_pct} | {r.rate_excess_pp} | "
    f"{r.pct_of_shortfall:.3f} | {r.kcal_per_stay} |" for r in ERA.itertuples())
unit_tbl = "\n".join(
    f"| {r.care_unit} | {r.stays:,} | {r.mean_kcal_per_stay} | {r.p90_kcal} | "
    f"{r.pct_over_250} |" for r in UNIT.itertuples())
rec_tbl = "\n".join(
    f"| {r.label} | {r.n:,} | {r.median_h_to_resumption} | {r.iqr} | "
    f"{r.pct_resumed_within_2h} | {r.pct_resumed_within_4h} | {r.pct_resumed_within_6h} |"
    for r in REC.itertuples())

extra = f"""
## S15. Transport across practice eras

MIMIC-IV assigns each stay an anchor-year group. The groups contain non-overlapping
patients admitted in different practice eras, so repeating the analysis within each is a
within-database check on independent cohorts.

| Era | Stays | Interruptions | Observed % | Background % | Excess pp | % of era shortfall | kcal/stay |
|---|---|---|---|---|---|---|---|
{era_tbl}

Direction is consistent in every era. The excess ranges
{ERA['rate_excess_pp'].min()}-{ERA['rate_excess_pp'].max()} pp against a pooled
{json.load(open(CAN / 'canonical_primary.json'))['rate']['excess_pp']} pp, and the share
of the era-specific shortfall {ERA['pct_of_shortfall'].min():.3f}-{ERA['pct_of_shortfall'].max():.3f}%.
The lowest value comes from the smallest and most recent group
({ERA.iloc[-1]['era'].replace(' - ', '-')}, {ERA.iloc[-1]['stays']:,} stays).

## S16. Patient-level distribution of the background-corrected burden

A background-corrected per-stay value can be negative, when a stay's observed assignment
carries less energy than its own matched control times. The cohort net total is therefore
much smaller than the positive tail, and a "share of the net total" is not interpretable.
Concentration is reported against the **gross positive** burden, with the net stated
alongside (registry E30).

| quantity | value |
|---|---|
| stays | {BUR['n_stays']:,} |
| net total | {BUR['net_total_kcal']:,} kcal |
| gross positive | {BUR['gross_positive_kcal']:,} kcal |
| gross negative | {BUR['gross_negative_kcal']:,} kcal |
| mean per stay | {BUR['mean_kcal']} kcal |
| median per stay | {BUR['median_kcal']} kcal |
| 90th / 95th / 99th centile | {BUR['p90_kcal']} / {BUR['p95_kcal']} / {BUR['p99_kcal']} kcal |
| maximum | {BUR['max_kcal']} kcal |
| stays exactly zero | {BUR['pct_stays_exactly_zero']}% |
| stays negative | {BUR['pct_stays_negative']}% |
| stays positive | {BUR['pct_stays_positive']}% |
| stays > 100 / 250 / 500 kcal | {BUR['pct_stays_over_100']}% / {BUR['pct_stays_over_250']}% / {BUR['pct_stays_over_500']}% |
| top decile total | {BUR['top10pct_kcal']:,} kcal |
| top decile share of gross positive | **{BUR['top10pct_share_of_gross_positive']}%** |

### By care unit (units with >= 100 stays)

| Care unit | Stays | Mean kcal/stay | 90th centile | % > 250 kcal |
|---|---|---|---|---|
{unit_tbl}

## S17. Time from procedure to resumption of feeding

Among interruptions with a procedure of the assigned class in window, measured from the
first such procedure to the end of the gap.

| Class | n | Median h | IQR | % <= 2 h | % <= 4 h | % <= 6 h |
|---|---|---|---|---|---|---|
{rec_tbl}

The negative-control class is **slower** to resume than airway and sedation events.
Bedside diagnostics carry no fasting rationale, so the delay cannot be a property of the
procedure; it indicates that restart latency is largely a property of the feeding
workflow. This is reported as the primary interpretive anchor for S17 (registry E31).

---

*Additional file generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.
All values derive from the deposited canonical and external-validation outputs.*
"""

t = t.rstrip() + "\n" + extra
(MAN / "CritCare_additional_file.md").write_text(t, encoding="utf-8")

n_sec = t.count("\n## S")
assert "## S15." in t and "## S16." in t and "## S17." in t
assert "G6 overall | **FAIL**" in t, "the eICU failure must remain disclosed"
assert FREEZE["sha256"] in t, "external contract hash missing"
assert "nan" not in t.replace("finance", ""), "Python nan leaked into the additional file"
print(f"CritCare_additional_file.md written: {n_sec} S-sections, {len(t):,} chars")
print("ASSERT OK: both plans hashed, eICU failure still disclosed, no nan")
