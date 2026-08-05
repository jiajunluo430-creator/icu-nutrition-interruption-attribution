# N2 external validation contract v1 — eICU background co-occurrence rate

**Status:** frozen before any background rate was computed.
**Parent contract:** `N2_analysis_contract_v1.md` (SHA-256 `307a6452c8a3ad171b4c235c1f82361267fbf6617c991c96fe39fa4d4a2c98a4`).
**Prerequisite:** interface audit `03_outputs/eicu_interface_audit.json`, gates E1–E5 all PASS.

## 1. Why eICU can support this when it failed gate G6

G6 failed because eICU intake records carry no infusion rate and no paused/stopped
status, so a *nutrition interruption* cannot be defined. The quantity under test here is
different: the **background co-occurrence rate** is a property of procedure density and
of the attribution window, not of nutrition records. Nothing about the G6 failure
constrains it.

This contract therefore does **not** attempt to replicate the energy estimand in eICU.
Any attempt to do so would require the fields G6 proved absent.

## 2. Estimand

For a reference window `[t0, t1]` placed in an eICU stay, the window is *attributed* if
at least one harmonized-class event falls within `[t0 − 1 h, t1 + 1 h]` — the same ±1 h
attribution window as the parent contract.

**Primary estimand:** the proportion of reference windows that are attributed, i.e. the
attribution rate that arises when no interruption has occurred at all. This is the
background rate, by construction, because reference windows are placed independently of
any nutrition event.

## 3. Harmonized event class

Only event classes whose timestamps are verifiable **event times** are eligible.

| Class | eICU source | Field | MIMIC counterpart |
|---|---|---|---|
| Airway | `respiratoryCare` | distinct `ventstartoffset`, `ventendoffset` | P1 |
| Sedation / NMB | `infusionDrug` | infusion **starts**, restart gap 240 min | P1 |

Events are deduplicated to distinct `(stay, offset)` time points (registry E26).

**Excluded from primary:** `treatment` classes (renal replacement, GI endoscopy,
surgery). `treatmentoffset` has no companion entry offset, so event-versus-documentation
semantics cannot be verified. Reported as a prespecified sensitivity only.

## 4. Reference-window construction (transport from MIMIC)

The background rate depends on window width as well as event density. Window width is
therefore **transported from MIMIC rather than invented**:

- window duration drawn from the empirical distribution of MIMIC qualifying interruption
  `gap_h` (n = 5,495);
- onset clock hour drawn from the empirical MIMIC interruption onset hour distribution;
- ICU day drawn uniformly over the stay's observed days 1–7;
- K = 5 reference windows per eICU stay;
- seed **20260805**, draws locked to `03_outputs/eicu_reference_windows.npy`.

Consequence: eICU and MIMIC background rates differ only through event density and
event ascertainment, which is the comparison of interest.

## 5. Like-for-like MIMIC comparator

The published MIMIC background rate of 29.1% covers five candidate classes plus the
negative control and is **not** comparable to a harmonized two-source class. The
comparator is therefore recomputed from the locked MIMIC draws restricted to class P1
only. Both sides use identical window rules and the identical ±1 h attribution window.

## 6. Binding gates

| Gate | Criterion | If failed |
|---|---|---|
| F1 | eICU background rate is non-trivial: 5% ≤ rate ≤ 95% | report and stop; a saturated or empty rate carries no information |
| F2 | eICU background rate within 3× of the MIMIC P1 background rate | report the discrepancy as a transportability failure; do **not** rescale |
| F3 | ≥100 hospitals with ≥20 qualifying stays contribute | drop the between-hospital analysis, keep the pooled rate |
| F4 | Bootstrap CI half-width < 5 percentage points | increase K, do not narrow by selection |

## 7. Between-hospital analysis (prespecified, primary novelty)

Background rate computed per hospital with ≥20 qualifying stays. Reported as median,
IQR, 10th–90th centile, and the ratio of the 90th to the 10th centile.

**Prespecified interpretation:** if the background rate varies materially across
hospitals, then a raw procedure-attribution percentage is not comparable between units,
and any nutrition quality metric built on timestamp proximity inherits that
non-comparability. This claim stands or falls on the observed spread and will be reported
whichever way it comes out.

## 8. Documentation-lag analysis (prespecified)

`nurseCare` is the only eICU table carrying both an event offset and an entry offset.
The lag distribution is reported as a direct measurement of how far charted time can sit
from event time, against the ±1 h attribution window. Descriptive only; it is not used to
adjust any estimate.

## 9. What will not be claimed

- No energy or kcal estimand in eICU.
- No patient outcome, in either database.
- No claim that eICU procedure ascertainment is complete. Airway capture is known to be
  hospital-dependent; the observed fraction of stays with any airway event is reported so
  readers can judge it.
- The between-hospital spread will not be interpreted as variation in *care*; it
  confounds true procedure density with documentation practice, and will be stated as
  such.
