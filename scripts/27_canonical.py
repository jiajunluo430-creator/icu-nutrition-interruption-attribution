"""N2 step 27 - ONE canonical result set.

Root cause of the conflicting primary values: scripts 17, 20 and 23 each created their
own RNG and their own replicate count; only 23 used the locked draws, and the supplement
then pulled tables from all three. This script recomputes EVERYTHING - primary,
per-class rate and energy, every sensitivity, every denominator variant - from the single
locked referent draw set, and writes canonical_*.csv files with hard assertions.

Nothing downstream may read rev_*, rev2_* or rev3_* tables after this.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
CANON = OUT / "canonical"
CANON.mkdir(exist_ok=True)

TARGET = ["P1", "P2", "P3", "P4", "P5"]
ALL = TARGET + ["P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
DEF6 = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W, DAY, N_BOOT, SEED = 3600, 86400, 1000, 20260807

DRAWS = np.load(OUT / "locked_referent_draws.npy")
N_CC, N = DRAWS.shape
itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
part = pd.read_csv(OUT / "rev_time_partition.csv")
seg = pd.read_csv(OUT / "segments_final.csv")
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
krate = itr["kcal_rate_pre"].fillna(0).values
gaph = itr["gap_h"].values
hour = itr["gap_start"].dt.hour.values
KEEP = np.array([DRAWS[:, i].any() for i in range(N)])

seg["route"] = seg["route"].fillna("unknown")
rby = seg.groupby("stay_id")["route"].agg(
    lambda s: "EN" if set(s.dropna()) <= {"EN", "unknown"} else
              ("PN" if set(s.dropna()) <= {"PN", "unknown"} else "mixed"))
route = itr["stay_id"].map(rby).values

pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values

ORDERS = {
    "primary": ALL,
    "transport_first": ["P3", "P1", "P2", "P4", "P5", "P0"],
    "negcontrol_first": ["P0", "P1", "P2", "P3", "P4", "P5"],
}
C2I = {c: i for i, c in enumerate(ALL)}
NONE = np.int8(-1)


def assign(shift_row, order):
    """Assigned class index per interruption (-1 = none) plus non-exclusive presence."""
    pri = {c: i for i, c in enumerate(order)}
    out = np.full(N, NONE, dtype=np.int8)
    pres = np.zeros((N, len(ALL)), dtype=bool)
    for i in range(N):
        if not KEEP[i]:
            continue
        sh = int(shift_row[i]) * DAY
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        j0 = np.searchsorted(arr, g0[i] + sh - ATTR_W)
        j1 = np.searchsorted(arr, g1[i] + sh + ATTR_W, "right")
        if j1 <= j0:
            continue
        cs = pcls[stays[i]][j0:j1]
        for c in set(cs):
            pres[i, C2I[c]] = True
        out[i] = C2I[min(cs, key=lambda c: pri[c])]
    return out, pres


print("computing assignments from locked draws…", flush=True)
OBS, OBS_PRES = {}, None
NULLC = {}
for nm, order in ORDERS.items():
    o, p = assign(np.zeros(N, dtype=np.int64), order)
    OBS[nm] = o
    if nm == "primary":
        OBS_PRES = p
    NULLC[nm] = np.full((N_CC, N), NONE, dtype=np.int8)
NULL_PRES = np.zeros((N, len(ALL)), dtype=np.float64)
for b in range(N_CC):
    for nm, order in ORDERS.items():
        c, p = assign(DRAWS[b], order)
        NULLC[nm][b] = c
        if nm == "primary":
            NULL_PRES += p
    if (b + 1) % 200 == 0:
        print(f"  {b+1}/{N_CC}", flush=True)
NULL_PRES /= N_CC
np.save(CANON / "obs_assigned_primary.npy", OBS["primary"])
np.save(CANON / "null_assigned_primary.npy", NULLC["primary"])

TOT = float(part["deficit_total"].sum())
uniq = np.unique(stays[KEEP])
idx = {s: np.where((stays == s) & KEEP)[0] for s in uniq}
brng = np.random.default_rng(SEED + 99)
BOOT_PICKS = [brng.choice(uniq, size=len(uniq), replace=True) for _ in range(N_BOOT)]
BOOT_IDX = [np.concatenate([idx[s] for s in p]) for p in BOOT_PICKS]


def energy(assigned, defens, mask=None, classes=TARGET):
    e = np.zeros(N)
    keep_i = np.array([C2I[c] for c in classes])
    for ci in keep_i:
        m = assigned == ci
        if mask is not None:
            m = m & mask
        e[m] = np.maximum(0.0, gaph[m] - defens[ALL[ci]]) * krate[m]
    return e


def boot_ci(vec):
    bs = np.array([vec[ii].sum() for ii in BOOT_IDX])
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def estimate(order="primary", defens=DEF6, mask=None, classes=TARGET):
    o = energy(OBS[order], defens, mask, classes)
    nl = np.zeros(N)
    for b in range(N_CC):
        nl += energy(NULLC[order][b], defens, mask, classes)
    nl /= N_CC
    d = o - nl
    lo, hi = boot_ci(d)
    m = KEEP if mask is None else (KEEP & mask)
    return dict(obs=float(o[m].sum()), null=float(nl[m].sum()),
                excess=float(d[m].sum()), lo=lo, hi=hi)


# ---------------------------------------------------------------- primary
print("\n[canonical primary]", flush=True)
P = estimate()
P.update(pct=round(100 * P["excess"] / TOT, 3),
         pct_lo=round(100 * P["lo"] / TOT, 3), pct_hi=round(100 * P["hi"] / TOT, 3),
         per_stay=round(P["excess"] / len(coh), 1))
print(f"  observed assigned {P['obs']:,.0f} | null {P['null']:,.0f} | "
      f"excess {P['excess']:,.0f} ({P['lo']:,.0f} to {P['hi']:,.0f}) = {P['pct']}%")

# ---------------------------------------------------------------- per class
rows = []
for c in ALL:
    ci_ = C2I[c]
    o = energy(OBS["primary"], DEF6, classes=[c])
    nl = np.zeros(N)
    for b in range(N_CC):
        nl += energy(NULLC["primary"][b], DEF6, classes=[c])
    nl /= N_CC
    elo, ehi = boot_ci(o - nl)
    ro, rn = OBS_PRES[:, ci_], NULL_PRES[:, ci_]
    rbs = np.array([(ro[ii].astype(float) - rn[ii]).mean() for ii in BOOT_IDX])
    rlo, rhi = np.percentile(rbs, [2.5, 97.5])
    rows.append({
        "class": c, "label": LABEL[c],
        "role": "negative control" if c == "P0" else "target",
        "rate_observed_pct": round(100 * ro[KEEP].mean(), 1),
        "rate_null_pct": round(100 * rn[KEEP].mean(), 1),
        "rate_excess_pp": round(100 * (ro[KEEP].mean() - rn[KEEP].mean()), 1),
        "rate_excess_lo": round(100 * rlo, 2), "rate_excess_hi": round(100 * rhi, 2),
        "rate_null_excluded": bool(not (rlo < 0 < rhi)),
        "energy_obs_kcal": round(o[KEEP].sum()), "energy_null_kcal": round(nl[KEEP].sum()),
        "energy_excess_kcal": round((o - nl)[KEEP].sum()),
        "energy_excess_lo": round(elo), "energy_excess_hi": round(ehi),
        "energy_null_excluded": bool(not (elo < 0 < ehi)),
    })
    print(f"  {c}: rate {rows[-1]['rate_excess_pp']:+.1f} pp | "
          f"energy {rows[-1]['energy_excess_kcal']:+,.0f}")
cls = pd.DataFrame(rows)
cls.to_csv(CANON / "canonical_class_results.csv", index=False)

# ---- ASSERTION: class energies must sum to the primary total
s_obs = cls[cls.role == "target"].energy_obs_kcal.sum()
s_nul = cls[cls.role == "target"].energy_null_kcal.sum()
s_exc = cls[cls.role == "target"].energy_excess_kcal.sum()
assert abs(s_obs - P["obs"]) < 2, (s_obs, P["obs"])
assert abs(s_nul - P["null"]) < 2, (s_nul, P["null"])
assert abs(s_exc - P["excess"]) < 2, (s_exc, P["excess"])
print(f"  ASSERT OK: class sums == primary total ({s_exc:,.0f})")

# ---------------------------------------------------------------- rate, any class
anyo = OBS_PRES.any(axis=1)
anyn = np.zeros(N)
nullrate = np.empty(N_CC)
for b in range(N_CC):
    a = NULLC["primary"][b] != NONE
    anyn += a
    nullrate[b] = a[KEEP].mean()
anyn /= N_CC
rb = np.array([(anyo[ii].astype(float) - anyn[ii]).mean() for ii in BOOT_IDX])
rate = dict(obs_pct=round(100 * anyo[KEEP].mean(), 1),
            null_pct=round(100 * anyn[KEEP].mean(), 1),
            excess_pp=round(100 * (anyo[KEEP].mean() - anyn[KEEP].mean()), 1),
            ci_lo=round(100 * np.percentile(rb, 2.5), 1),
            ci_hi=round(100 * np.percentile(rb, 97.5), 1),
            p=float((np.sum(nullrate >= anyo[KEEP].mean()) + 1) / (N_CC + 1)))
print(f"\n  any-class rate {rate['obs_pct']}% vs {rate['null_pct']}% = "
      f"{rate['excess_pp']} pp ({rate['ci_lo']} to {rate['ci_hi']}), p={rate['p']:.3f}")
pd.DataFrame({"replicate": range(1, N_CC + 1),
              "null_attr_pct": 100 * nullrate}).to_csv(
    CANON / "canonical_null_distribution.csv", index=False)

# ---------------------------------------------------------------- sensitivities
print("\n[canonical sensitivities]", flush=True)
rev2 = json.load(open(OUT / "rev2_results.json"))
sens = []


def add(name, r, tot=TOT, note=""):
    sens.append({"analysis": name, "observed_kcal": round(r["obs"]),
                 "null_kcal": round(r["null"]), "excess_kcal": round(r["excess"]),
                 "ci": f"{r['lo']:,.0f} to {r['hi']:,.0f}",
                 "pct_of_shortfall": round(100 * r["excess"] / tot, 3),
                 "kcal_per_stay": round(r["excess"] / len(coh), 1), "note": note})
    print(f"  {name:48s} {r['excess']:>9,.0f}  {100*r['excess']/tot:6.3f}%")


add("Primary (all routes, 6 h defensible window)", P)
for w in (0.0, 2.0, 4.0, 8.0):
    d = {**DEF6, "P1": w, "P2": w}
    add(f"Defensible window for P1/P2 = {w:.0f} h", estimate(defens=d))
add("Route: enteral-only stays", estimate(mask=(route == "EN")))
add("Excluding interruptions starting at 00:00", estimate(mask=(hour != 0)))
add("Excluding interruptions starting 23:00-01:00",
    estimate(mask=~np.isin(hour, [23, 0, 1])))
add("Priority: transport first", estimate(order="transport_first"))
add("Priority: negative control first", estimate(order="negcontrol_first"))
for kk, tot_k in [(20.0, None), (30.0, None)]:
    tgt = part["wkg"] * kk / 24.0
    tk = ((tgt * part["obs_h"]) - part["kcal_del"]).clip(lower=0).sum()
    add(f"Reference target {kk:.0f} kcal/kg/day", P, tot=tk,
        note=f"shortfall {tk/1e6:.1f} M kcal")
add("Denominator censored at first recorded oral intake", P,
    tot=rev2["oral_censored_shortfall_kcal"], note="numerator unchanged")
add("Ramped reference target (40/70/100% days 1/2/3+)", P,
    tot=rev2["ramped_shortfall_kcal"], note="numerator unchanged")
dn = json.load(open(OUT / "rev3_day_preserving_null.json"))
sens.append({"analysis": "Complementary across-patient null (ICU day + clock hour)",
             "observed_kcal": "", "null_kcal": "",
             "excess_kcal": round(dn["energy_excess_kcal"]),
             "ci": f"{dn['energy_excess_ci'][0]:,.0f} to {dn['energy_excess_ci'][1]:,.0f}",
             "pct_of_shortfall": dn["pct_of_shortfall"],
             "kcal_per_stay": round(dn["energy_excess_kcal"] / len(coh), 1),
             "note": "different exchangeability assumption; not a bound"})
print(f"  {'Complementary across-patient null':48s} "
      f"{dn['energy_excess_kcal']:>9,.0f}  {dn['pct_of_shortfall']:6.3f}%")
sdf = pd.DataFrame(sens)
sdf.to_csv(CANON / "canonical_sensitivity.csv", index=False)

main = sdf[sdf.analysis.str.startswith(("Primary", "Defensible", "Route", "Excluding",
                                        "Priority", "Reference", "Denominator", "Ramped"))]
canon = {
    "seed": SEED, "n_replicates": N_CC, "n_analysis_set": int(KEEP.sum()),
    "n_excluded_no_referent": int((~KEEP).sum()),
    "shortfall_total_kcal": TOT,
    "target_obs_kcal": P["obs"], "target_null_kcal": P["null"],
    "target_excess_kcal": P["excess"],
    "target_excess_ci": [P["lo"], P["hi"]],
    "target_pct": P["pct"], "target_pct_ci": [P["pct_lo"], P["pct_hi"]],
    "target_per_stay": P["per_stay"],
    "rate": rate,
    "p0_energy_excess_kcal": float(cls.loc[cls["class"] == "P0", "energy_excess_kcal"].iloc[0]),
    "p0_energy_ci": [float(cls.loc[cls["class"] == "P0", "energy_excess_lo"].iloc[0]),
                     float(cls.loc[cls["class"] == "P0", "energy_excess_hi"].iloc[0])],
    "sensitivity_pct_min": float(main.pct_of_shortfall.min()),
    "sensitivity_pct_max": float(main.pct_of_shortfall.max()),
    "day_preserving_pct": dn["pct_of_shortfall"],
}
json.dump(canon, open(CANON / "canonical_primary.json", "w"), indent=2)
print(f"\nsensitivity range {canon['sensitivity_pct_min']}%-{canon['sensitivity_pct_max']}%")
print(f"\nCANONICAL PRIMARY = {P['excess']:,.0f} kcal ({P['pct']}%), "
      f"{P['per_stay']} kcal/stay")
print(json.dumps(canon, indent=2)[:400])
