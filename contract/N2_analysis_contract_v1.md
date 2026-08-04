# N2 analysis contract v1 — ICU enteral/parenteral nutrition delivery gap and procedure-attributable fasting

- Project root: `D:\N2_icu_nutrition_delivery_gap`
- Date frozen: 2026-08-02
- Status: **BINDING**. No definition below may be changed after any estimate in section 6–9 is computed.
- Source data (read-only): `D:\respiratory_icu_qdp\MIMIC-IV\mimic-iv-3.1`,
  `D:\respiratory_icu_qdp\eicu-collaborative-research-database-2.0.zip`
- Prior project with cohort overlap: `D:\GI_CHARLS_NHANES\ND03_refeeding_phosphate_qdp` (must be disclosed; see §11)

---

## 0. Pre-contract feasibility probes (already executed, recorded for transparency)

These were interface/coverage audits run before this contract was written. They are
**not** outcome analyses and did not involve any exposure–outcome comparison. They are
recorded here so the record is complete, following the ND03 precedent (D009/D011).

| Probe | Result | Date |
|---|---|---|
| `inputevents` total rows | 10,953,713 | 2026-08-02 |
| Rows matching the 114 ND03 strict nutrition itemids | 241,118 | 2026-08-02 |
| Distinct ICU stays with nutrition rows | 15,242 | 2026-08-02 |
| Distinct subjects | 11,743 | 2026-08-02 |
| `rate` present | 99.7% | 2026-08-02 |
| `patientweight` present | 100.0% | 2026-08-02 |
| `statusdescription` distribution | FinishedRunning 51.98%, ChangeDose/Rate 26.64%, Stopped 13.32%, Paused 8.03% | 2026-08-02 |
| Nutrition `linkorderid` count | 166,417 | 2026-08-02 |
| Orders with native `Calories` (226060) | 158,661 (95.3%) | 2026-08-02 |
| Orders with native `Protein` (220454) | 158,580 (95.3%) | 2026-08-02 |
| `poe` order types (first 3,000,001 rows) | Nutrition 122,757; TPN 4,639 | 2026-08-02 |

Gates G2 (record usability ≥80%) and G4 (native kcal coverage ≥80%) are therefore
already **PASS** at contract time and are not re-litigated.

---

## 1. Clinical question

Among adults receiving enteral or parenteral nutrition in the ICU, how many hours of
feeding time and how much energy and protein are lost to interruptions that can be
attributed to timestamped clinical procedures, and how much of that loss exceeds a
guideline-defensible fasting window?

## 2. What this study is NOT

Binding prohibitions. Violating any of these voids the contract:

1. **No outcome-association or causal model of any kind** linking energy/protein deficit,
   interruption hours, or fasting hours to mortality, ventilator liberation, infection,
   length of stay, or any patient outcome.
2. No early-versus-delayed nutrition comparison.
3. No nutrition dose–response analysis.
4. No machine learning, reinforcement learning, prediction model, nomogram, or SHAP.
5. No framing as "prevalence and causes of enteral nutrition interruption" (occupied by
   PMID 41551853).
6. No claim that reducing fasting improves outcomes.

## 3. Cohort (frozen)

- Source: MIMIC-IV v3.1, `icu/icustays` joined to `hosp/patients`, `hosp/admissions`.
- Unit of analysis: **first ICU stay per `subject_id`** (ND03 D002 precedent).
- Inclusion:
  1. `anchor_age` ≥ 18 at the corresponding admission;
  2. ICU length of stay ≥ 48 h;
  3. ≥ 1 nutrition segment (§4) within ICU days 1–7;
  4. ≥ 2 distinct calendar days with a nutrition segment within ICU days 1–7;
  5. `patientweight` recorded and in [30, 300] kg.
- Observation window: `intime` to `min(intime + 7 days, outtime, deathtime)`.
- Exclusions applied in the order above; a CONSORT-style flow is mandatory.

## 4. Nutrition exposure (frozen)

- Itemids: the **114 `strict` nutrition itemids** in
  `D:\GI_CHARLS_NHANES\ND03_refeeding_phosphate_qdp\config\mimic_interface_whitelist.csv`
  (`role == nutrition`, `tier == strict`, all in `icu/inputevents`).
  This list is copied verbatim into `00_contracts/nutrition_itemids_frozen.csv` and
  **must not be re-derived, extended, or trimmed.**
- The 21 `exclude` and 5 `broad_only` items from the same file are excluded.
- **Nutrition segment** = one `inputevents` row with the above itemid, `rate` > 0,
  `amountuom` = mL, valid `starttime` < `endtime`, and `starttime` inside the
  observation window.
- **Route split** via `icu/ingredientevents` on the same `linkorderid`:
  enteral (226221), parenteral (227079). Oral (226506) and supplements (227080) are
  reported descriptively but are **not** part of the primary denominator.

## 5. Energy and protein (frozen)

- Delivered energy: `ingredientevents` itemid **226060 (Calories, Kcal)**.
- Delivered protein: `ingredientevents` itemid **220454 (Protein, grams)**.
- Joined to nutrition segments by `linkorderid`.
- **Caloric density** for a `linkorderid` = total kcal / total mL for that order.
  Energy rate (kcal/h) = segment `rate` (mL/h) × caloric density.
- Orders lacking native kcal (4.7%) are reported as a missingness category and are
  **not** imputed in the primary analysis.
- **Targets (prespecified, ESPEN ICU 2023):** 25 kcal/kg/day and 1.3 g protein/kg/day,
  using recorded `patientweight`.
- Sensitivity targets: 20 and 30 kcal/kg/day; ideal body weight substituted when
  BMI > 30 (from `hosp/omr` height where available).

## 6. Interruption definition (frozen)

An **interruption** is a gap between consecutive nutrition segments within one ICU stay
satisfying all of:

1. the segment immediately preceding the gap has
   `statusdescription ∈ {Paused, Stopped}`;
2. gap duration ≥ **2.0 h**;
3. gap duration ≤ **24.0 h** (gaps > 24 h terminate the nutrition episode and are
   **not** counted as interruptions);
4. both bounding segments lie inside the observation window.

A **nutrition episode** is a maximal run of segments separated by gaps ≤ 24 h.

Gaps following `FinishedRunning` or `ChangeDose/Rate` are **not** interruptions.

## 7. Procedure classes (frozen — itemids locked before any attribution is computed)

From `icu/procedureevents`. Classes and their guideline-defensible pre-procedure
fasting window `D`:

| Class | Label | itemids | D (h) |
|---|---|---|---:|
| **P1** | Airway / sedation events | 224385 Intubation; 227194 Extubation; 225448 Percutaneous Tracheostomy; 226237 Open Tracheostomy; 225400 Bronchoscopy; 229585 Surgical Procedure at Bedside | **6** |
| **P2** | GI endoscopic / oesophageal procedures | 225439 Endoscopy; 225434 Colonoscopy; 227550 ERCP (Travel to); 229576 ERCP (Done in unit); 225446 PEG Insertion; 221255 Trans Esophageal Echo | **6** |
| **P3** | Off-unit transport for imaging / intervention | 229575 Travel to Radiology; 221214 CT scan; 223253 MRI; 225427 Angiography; 225462 Interventional Radiology; 225430 Cardiac Cath; 229577 Cath Lab (Received); 229578 Cath Lab (Sent) | **0** |
| **P4** | Bedside invasive, non-airway | 225433 Chest Tube Placed; 225445 Paracentesis; 225479 Thoracentesis; 225442 Liver Biopsy; 225447 Percutaneous Drain Insertion; 229580 Line Placement at Bedside; 225399 Lumbar Puncture; 226474 ICP Bolt Inserted; 226475 Intraventricular Drain Inserted; 225449 Pericardiocentesis | **0** |
| **P5** | Renal replacement / apheresis | 225441 Hemodialysis; 227551 Plasma Pheresis | **0** |
| **P0** | **Negative control** — bedside diagnostics with no fasting rationale | 225402 EKG; 221223 EEG; 229614 EEG (Continuous); 229581 Portable Chest X-Ray; 229351 Foley Catheter; 221217 Ultrasound; 225432 Transthoracic Echo; 225457 Abdominal X-Ray; 229380 Nursing Water Swallow Screening; 229584 EMG; 228715 Transcranial Doppler | **0** |

Explicitly **excluded** from attribution: 225792 Invasive Ventilation and 225794
Non-invasive Ventilation (continuous intervals, would overlap everything);
`Access Lines - Invasive`, `Access Lines - Peripheral`, `3-Significant Events`,
`6-Cultures`, `7-Communication` categories; 225468 and 225477 Unplanned Extubation
(cannot be pre-fasted for).

Rationale for `D`: ASA fasting guidance grants 6 h for non-clear intake before
procedures involving general anaesthesia or deep sedation; ESPEN/ASPEN ICU nutrition
guidance states enteral nutrition need not be routinely withheld for bedside
diagnostics, transport, or renal replacement. Granting 6 h to P1 and P2 is the
**conservative** choice: it minimises the estimated avoidable loss.

## 8. Attribution rule (frozen)

An interruption with gap interval `[g0, g1]` is attributed to class `C` if **any**
procedure with an itemid in `C` has `starttime ∈ [g0 − 1 h, g1 + 1 h]`.

- Multiple-class attribution is resolved by priority **P1 > P2 > P3 > P4 > P5 > P0**,
  i.e. the interruption is assigned to the most fasting-defensible class present. This
  is conservative: it minimises the estimated avoidable loss.
- Interruptions with no procedure in window are **unattributed** and reported as their
  own category. They are not redistributed.

**Excess fasting hours** for an attributed interruption
= `max(0, gap_hours − D(class))`.

**Attributable energy loss** = `gap_hours × (energy rate of the segment immediately
preceding the gap)`. Protein loss computed identically. This assumes feeding would have
continued at the pre-interruption rate; it is an explicitly stated counterfactual, not
a causal estimate.

## 9. Placebo / falsification test (frozen, mandatory)

The entire attribution pipeline is re-run with every procedure `starttime` shifted by
**+48 h** within the same ICU stay. This yields the **placebo attribution rate**.

If observed attribution is not clearly separated from placebo attribution, the
attribution rule is non-specific and the primary claim is void (see G3).

## 10. Natural experiment (frozen)

Same clinical procedure, different logistics. Outcome: interruption hours and energy
loss per procedure event.

- **Pair A (primary):** 227550 ERCP (Travel to) vs 229576 ERCP (Done in unit).
- **Pair B (secondary):** 229582 Portable CT scan vs 221214 CT scan.

The chest radiograph pair is **not** used: itemid 225459 cannot be reliably classified
as departmental versus portable.

Comparisons are unadjusted primary, with a prespecified sensitivity adjusting for
SOFA-proxy (vasopressor use), invasive ventilation status, and anchor-year group.
This is a within-procedure logistics contrast, **not** a treatment effect.

## 11. Cohort-overlap disclosure (binding)

The cohort is drawn from the same MIMIC-IV nutrition population used in ND03
(refeeding hypophosphataemia monitoring). The manuscript **must** state this in the
Methods and the cover letter, and specify that the estimands, exposure, outcome
variables, and source tables do not overlap: ND03 analysed serum phosphate from
`labevents` and phosphate administration from `emar`; N2 analyses nutrition delivery
from `inputevents`/`ingredientevents` and procedures from `procedureevents`.

## 12. Binding gates

| ID | Gate | Action if failed |
|---|---|---|
| G1 | Eligible first-ICU stays ≥ 5,000 | NO-GO |
| G2 | Nutrition record usability ≥ 80% | **PASS (99.7%)** |
| G3 | ≥ 5,000 qualifying interruptions **and** observed attribution rate exceeds the +48 h placebo attribution rate by ≥ 10 absolute percentage points | NO-GO for the attribution claim; demote to descriptive delivery-gap report |
| G4 | Native kcal coverage ≥ 80% | **PASS (95.3%)** |
| G5 | Pair A ≥ 100 events per arm; Pair B ≥ 300 events per arm | Drop the failing pair. **Do not relax the pairing definition.** |
| G6 | eICU: ≥ 30 hospitals with ≥ 20 eligible stays each **and** delivered volume representable | Demote eICU to an interface-audit appendix (ND03 D013 precedent); MIMIC-only manuscript with lowered journal target |
| G7 | Negative-control class P0 attributable rate, interpreted jointly with G3 placebo | Not a kill gate. If P0 ≈ fasting-indicated classes **and** placebo is low → workflow-driven interruption (strengthens the avoidable claim). If P0 high **and** placebo also high → attribution rule non-specific → G3 fails. |

No gate threshold may be changed after the corresponding value is observed.

## 13. Required outputs

- CONSORT-style cohort flow
- `pilot_gates.csv` with every gate's observed value and PASS/FAIL
- Delivery adequacy by ICU day (energy and protein, % of target)
- Interruption hours and energy/protein loss by procedure class
- Excess fasting hours by class
- Placebo-shift comparison
- Natural experiment Pair A (and Pair B if G5 passes)
- Negative-control table
- Sensitivity: target definition, gap thresholds (1.5 h / 3 h), attribution window
  (±0.5 h / ±2 h), enteral-only, exclusion of parenteral
- Full reproducibility manifest with script hashes and `sessionInfo`

## 14. Exploratory branch registry

Every data-driven deviation must be logged in
`03_outputs/exploratory_attempts.csv` with reason, attempt number, result, and
disposition (ND03 D007 precedent). Statistical significance alone cannot promote a
branch.
