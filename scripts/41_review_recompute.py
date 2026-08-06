"""N2 step 41 - re-estimation demanded by external review round 6.

Single pass over the locked draws, computing everything the two reviews require:

A  REFERENCE-SCALE numerator (M3). The numerator used the pre-interruption actual
   infusion rate while the denominator used the 25 kcal/kg/day reference rate, so the
   ratio divided two different scales. Recomputed on the denominator's own scale.
B  PRIORITY-FREE estimand (M5). Energy for "any target class in window", with no
   exclusive priority rule. Asserted against the priority-assigned total.
C  WINDOW DEFINITION (M4-R2). The original window ran gap_onset-1h to gap_end+1h, i.e.
   gap duration + 2 h, not a flat +/-1 h. Four alternative windows are added. Note the
   causal direction: feeding is stopped *in preparation for* a procedure, so a causally
   coherent narrow window puts the procedure INSIDE the gap, not before its onset.
D  RATIO-FORM attributable fraction (M4-R1), under an explicitly stated assumption.
E  Monte-Carlo p floor (M12), compared against the correct observed rate.
F  Gap-duration strata, since window length grows with gap duration.

Both the any-class rate (which includes the negative control, and is what the 38.9%
headline refers to) and the target-only rate are reported, because they are different
quantities and the manuscript had been quoting them interchangeably.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN = ROOT / "03_outputs", ROOT / "03_outputs" / "canonical"
REV = OUT / "review6"
REV.mkdir(exist_ok=True)

TARGET = ["P1", "P2", "P3", "P4", "P5"]
ALL = TARGET + ["P0"]
DEF6 = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
C2I = {c: i for i, c in enumerate(ALL)}
TGT = np.array([C2I[c] for c in TARGET])
ATTR, DAY, SEED = 3600, 86400, 20260807

DRAWS = np.load(OUT / "locked_referent_draws.npy")
N_CC, N = DRAWS.shape
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv")
part = pd.read_csv(OUT / "rev_time_partition.csv")
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
CANJ = json.load(open(CAN / "canonical_primary.json"))

gaph = itr["gap_h"].values
krate = itr["kcal_rate_pre"].fillna(0).values
stays = itr["stay_id"].values
g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
KEEP = np.array([DRAWS[:, i].any() for i in range(N)])
TOT = float(part["deficit_total"].sum())
NK = int(KEEP.sum())

wkg = part.set_index("stay_id")["wkg"]
ref_rate = np.nan_to_num(pd.Series(stays).map(wkg).values * 25.0 / 24.0)

pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values

# window definitions: (label, lo_offset_fn, hi_offset_fn) relative to shifted gap
WINDOWS = {
    "span": lambda a, b: (a - ATTR, b + ATTR),
    "in_gap": lambda a, b: (a, b),
    "onset_pm1h": lambda a, b: (a - ATTR, a + ATTR),
    "onset_to_2h": lambda a, b: (a, a + 2 * ATTR),
    "pre_onset_only": lambda a, b: (a - ATTR, a),
}
MODES = list(WINDOWS)


def scan(shift_row):
    """One pass: per-mode class presence for every interruption."""
    out = {m: np.zeros((N, len(ALL)), dtype=bool) for m in MODES}
    for i in range(N):
        if not KEEP[i]:
            continue
        sh = int(shift_row[i]) * DAY
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        cl = pcls[stays[i]]
        a, b = g0[i] + sh, g1[i] + sh
        for m in MODES:
            lo, hi = WINDOWS[m](a, b)
            j0 = np.searchsorted(arr, lo)
            j1 = np.searchsorted(arr, hi, "right")
            if j1 > j0:
                for c in set(cl[j0:j1]):
                    out[m][i, C2I[c]] = True
    return out


def energy_pf(pres, rate_vec):
    """Priority-free: any target class present; defensible = largest among those present."""
    e = np.zeros(N)
    any_t = pres[:, TGT].any(axis=1)
    defw = np.zeros(N)
    for c in TARGET:
        m = pres[:, C2I[c]]
        defw[m] = np.maximum(defw[m], DEF6[c])
    e[any_t] = np.maximum(0.0, gaph[any_t] - defw[any_t]) * rate_vec[any_t]
    return e


print(f"single pass over {N_CC} replicates x {len(MODES)} windows ...", flush=True)
OBS = scan(np.zeros(N, dtype=np.int64))
acc_any_t = {m: np.zeros(N) for m in MODES}
acc_any_all = {m: np.zeros(N) for m in MODES}
acc_e_actual = np.zeros(N)
acc_e_ref = np.zeros(N)
null_rate_any_all = np.empty(N_CC)
for b in range(N_CC):
    p = scan(DRAWS[b])
    for m in MODES:
        acc_any_t[m] += p[m][:, TGT].any(axis=1)
        acc_any_all[m] += p[m].any(axis=1)
    acc_e_actual += energy_pf(p["span"], krate)
    acc_e_ref += energy_pf(p["span"], ref_rate)
    null_rate_any_all[b] = p["span"].any(axis=1)[KEEP].mean()
    if (b + 1) % 250 == 0:
        print(f"  {b+1}/{N_CC}", flush=True)
for m in MODES:
    acc_any_t[m] /= N_CC
    acc_any_all[m] /= N_CC
acc_e_actual /= N_CC
acc_e_ref /= N_CC

uniq = np.unique(stays[KEEP])
sidx = {s: np.where((stays == s) & KEEP)[0] for s in uniq}
brng = np.random.default_rng(SEED + 99)
BOOT = [np.concatenate([sidx[s] for s in brng.choice(uniq, len(uniq), replace=True)])
        for _ in range(1000)]
res = {}

# ============================================================== C + F: windows
LBL = {"span": "Span: gap onset -1 h to gap end +1 h (original)",
       "in_gap": "Procedure inside the gap",
       "onset_pm1h": "Onset-centred: gap onset +/-1 h",
       "onset_to_2h": "Gap onset to onset +2 h",
       "pre_onset_only": "1 h before gap onset only (wrong causal direction; shown for completeness)"}
rows = []
for m in MODES:
    for scope, obs_v, bg_v in [("any class (incl. negative control)",
                                OBS[m].any(axis=1), acc_any_all[m]),
                               ("target classes only", OBS[m][:, TGT].any(axis=1),
                                acc_any_t[m])]:
        d = obs_v.astype(float) - bg_v
        bs = np.array([d[i].mean() for i in BOOT])
        rows.append({"window": LBL[m], "scope": scope,
                     "observed_pct": round(100 * obs_v[KEEP].mean(), 1),
                     "background_pct": round(100 * bg_v[KEEP].mean(), 1),
                     "excess_pp": round(100 * d[KEEP].mean(), 1),
                     "ci_lo": round(100 * float(np.percentile(bs, 2.5)), 1),
                     "ci_hi": round(100 * float(np.percentile(bs, 97.5)), 1)})
win = pd.DataFrame(rows)
win.to_csv(REV / "window_definition_sensitivity.csv", index=False)
print("\n[C] window definition\n", win.to_string(index=False))

wl = gaph[KEEP] + 2.0
res["window_length_h"] = {
    "median": round(float(np.median(wl)), 1),
    "iqr": [round(float(np.percentile(wl, 25)), 1), round(float(np.percentile(wl, 75)), 1)],
    "max": round(float(wl.max()), 1),
    "note": "span window = gap duration + 2 h; the text had implied a flat +/-1 h"}

strata = []
for lbl, msk in [("2-6 h", gaph < 6), ("6-12 h", (gaph >= 6) & (gaph < 12)),
                 ("12-24 h", gaph >= 12)]:
    k = KEEP & msk
    o = OBS["span"][:, TGT].any(axis=1)
    strata.append({"gap_stratum": lbl, "n": int(k.sum()),
                   "mean_window_h": round(float((gaph[k] + 2).mean()), 1),
                   "observed_pct": round(100 * o[k].mean(), 1),
                   "background_pct": round(100 * acc_any_t["span"][k].mean(), 1),
                   "excess_pp": round(100 * (o[k].mean() - acc_any_t["span"][k].mean()), 1)})
st = pd.DataFrame(strata)
st.to_csv(REV / "gap_duration_strata.csv", index=False)
print("\n[F] gap-duration strata\n", st.to_string(index=False))

# ========================================================= A + B: scale, priority
print("\n[A/B] scale and priority-free estimand")
sc_rows = []
for scale, obs_e, nl_e in [
        ("actual pre-gap infusion rate (original numerator)",
         energy_pf(OBS["span"], krate), acc_e_actual),
        ("reference 25 kcal/kg/day (same scale as the denominator)",
         energy_pf(OBS["span"], ref_rate), acc_e_ref)]:
    d = obs_e - nl_e
    bs = np.array([d[i].sum() for i in BOOT])
    sc_rows.append({"numerator_scale": scale,
                    "observed_kcal": round(obs_e[KEEP].sum()),
                    "background_kcal": round(nl_e[KEEP].sum()),
                    "excess_kcal": round(d[KEEP].sum()),
                    "ci_lo": round(float(np.percentile(bs, 2.5))),
                    "ci_hi": round(float(np.percentile(bs, 97.5))),
                    "pct_of_shortfall": round(100 * d[KEEP].sum() / TOT, 3),
                    "kcal_per_stay": round(d[KEEP].sum() / len(coh), 1)})
    print(f"  {scale:56s} {d[KEEP].sum():>9,.0f}  {100*d[KEEP].sum()/TOT:6.3f}%")
sc = pd.DataFrame(sc_rows)
sc.to_csv(REV / "scale_and_priority_free.csv", index=False)

pf_actual = float((energy_pf(OBS["span"], krate) - acc_e_actual)[KEEP].sum())
res["priority_rule_invariance"] = {
    "priority_assigned_kcal": round(CANJ["target_excess_kcal"]),
    "priority_free_kcal": round(pf_actual),
    "difference_kcal": round(pf_actual - CANJ["target_excess_kcal"], 1),
    "explanation": ("An interruption contributes to the target total iff ANY target class "
                    "is in window, and the defensible window is the largest among the "
                    "classes present under both rules. The priority rule therefore fixes "
                    "the per-class split and the negative-control diagnostic, but leaves "
                    "the target total exactly unchanged."),
}
assert abs(pf_actual - CANJ["target_excess_kcal"]) < 2, (pf_actual, CANJ["target_excess_kcal"])
print(f"  ASSERT OK: priority-free == priority-assigned ({pf_actual:,.0f} kcal); "
      f"the priority rule does not touch the target total")

int_h = float(gaph[KEEP].sum())
res["scale_diagnostic"] = {
    "interruption_hours": round(int_h),
    "reference_kcal_per_h": round(float((ref_rate[KEEP] * gaph[KEEP]).sum() / int_h), 1),
    "actual_pregap_kcal_per_h": round(float((krate[KEEP] * gaph[KEEP]).sum() / int_h), 1)}
res["scale_diagnostic"]["ratio"] = round(
    res["scale_diagnostic"]["reference_kcal_per_h"]
    / res["scale_diagnostic"]["actual_pregap_kcal_per_h"], 2)
print(f"  scale: reference {res['scale_diagnostic']['reference_kcal_per_h']} vs "
      f"actual {res['scale_diagnostic']['actual_pregap_kcal_per_h']} kcal/h "
      f"(x{res['scale_diagnostic']['ratio']})")

# ====================================================== D: ratio-form fraction
res["attributable_fraction"] = {}
for scope, obs_v, bg_v in [("any_class", OBS["span"].any(axis=1), acc_any_all["span"]),
                           ("target_only", OBS["span"][:, TGT].any(axis=1),
                            acc_any_t["span"])]:
    o, b_ = obs_v[KEEP].mean(), bg_v[KEEP].mean()
    c = (o - b_) / (1 - b_)
    cb = [(obs_v[i].mean() - bg_v[i].mean()) / (1 - bg_v[i].mean()) for i in BOOT]
    res["attributable_fraction"][scope] = {
        "observed_pct": round(100 * o, 1), "background_pct": round(100 * b_, 1),
        "excess_pp": round(100 * (o - b_), 1),
        "causal_fraction_pct": round(100 * c, 1),
        "ci": [round(100 * float(np.percentile(cb, 2.5)), 1),
               round(100 * float(np.percentile(cb, 97.5)), 1)],
        "genuine_share_of_observed_pct": round(100 * c / o, 1)}
    print(f"\n[D] {scope}: obs {100*o:.1f}%, background {100*b_:.1f}%, "
          f"c={100*c:.1f}%, genuine share of observed {100*c/o:.1f}%")
res["attributable_fraction"]["assumption"] = (
    "identified only if every truly procedure-caused interruption has that procedure in "
    "window and obs = c + (1-c)*b; reported as a bounded interpretation, not the primary "
    "estimand")

# ============================================================ E: p-value floor
obs_any = OBS["span"].any(axis=1)[KEEP].mean()
n_ge = int((null_rate_any_all >= obs_any).sum())
res["p_value"] = {"replicates": N_CC, "n_null_ge_observed": n_ge,
                  "observed_pct": round(100 * obs_any, 1),
                  "null_mean_pct": round(100 * float(null_rate_any_all.mean()), 1),
                  "null_max_pct": round(100 * float(null_rate_any_all.max()), 1),
                  "p_reported": (f"< {1/(N_CC+1):.4f}" if n_ge == 0
                                 else f"{(n_ge+1)/(N_CC+1):.4f}"),
                  "note": "empirical floor is 1/(B+1); report as an inequality"}
print(f"\n[E] observed {100*obs_any:.1f}% vs null max {100*null_rate_any_all.max():.1f}%; "
      f"p {res['p_value']['p_reported']}")

json.dump(res, open(REV / "review6_recompute.json", "w"), indent=2)
print(f"\nwrote {REV}")
