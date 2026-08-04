"""N2 step 23 - third revision round.

R3-4  ONE locked set of referent draws. Saved to disk and reused by every estimate, so
      the primary number is identical everywhere instead of drifting between scripts.
R3-1  Secondary null that preserves BOTH ICU day and clock hour, by borrowing another
      patient's procedure timeline at the same ICU day and same wall-clock hour.
R3-2  Diagnostics for why the negative control is null on the rate scale but not on the
      energy scale: non-exclusive P0, per-item breakdown, and stratification.
R3-3  Class-specific attribution rates are NON-EXCLUSIVE by construction; the priority
      rule applies only to the energy estimand. Both are computed here explicitly.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
SEED = 20260807
TARGET = ["P1", "P2", "P3", "P4", "P5"]
ALL = TARGET + ["P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
DEFENSIBLE = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W, DAY, N_CC, N_DAY, N_BOOT = 3600, 86400, 1000, 500, 1000

itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
part = pd.read_csv(OUT / "rev_time_partition.csv")
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")
TOT = float(part["deficit_total"].sum())
res = {}

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
t0 = itr["intime"].values.astype("datetime64[s]").astype(np.int64)
t1 = itr["win_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
krate = itr["kcal_rate_pre"].fillna(0).values
gaph = itr["gap_h"].values
N = len(g0)

pmap, pcls, pitem = {}, {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values
    pitem[k] = o["itemid"].values
PRI = {c: i for i, c in enumerate(ALL)}

# ------------------------------------------------ analysis set (drop unmatchable)
valid_k = []
for i in range(N):
    ks = [k for k in range(-6, 7) if k != 0
          and g0[i] + k * DAY >= t0[i] and g1[i] + k * DAY <= t1[i]]
    valid_k.append(np.array(ks, dtype=np.int64) if ks else np.array([], dtype=np.int64))
keep = np.array([len(v) > 0 for v in valid_k])
n_drop = int((~keep).sum())
print(f"analysis set: {int(keep.sum()):,} of {N:,} interruptions "
      f"({n_drop} excluded for having no referent day)")
res["n_analysis_set"] = int(keep.sum())
res["n_excluded_no_referent"] = n_drop

# ------------------------------------------------ R3-4 locked referent draws
rng = np.random.default_rng(SEED)
DRAWS = np.zeros((N_CC, N), dtype=np.int64)
for b in range(N_CC):
    for i in range(N):
        if keep[i]:
            DRAWS[b, i] = valid_k[i][rng.integers(len(valid_k[i]))]
np.save(OUT / "locked_referent_draws.npy", DRAWS)
print(f"locked referent draws saved: {DRAWS.shape}, seed {SEED}")
res["seed"] = SEED
res["n_replicates"] = N_CC


def attribute(a, b, i):
    arr = pmap.get(stays[i])
    if arr is None:
        return None, ()
    j0 = np.searchsorted(arr, a - ATTR_W)
    j1 = np.searchsorted(arr, b + ATTR_W, "right")
    if j1 <= j0:
        return None, ()
    cs = pcls[stays[i]][j0:j1]
    return min(cs, key=lambda c: PRI[c]), tuple(set(cs))


def run(shift_row):
    """Return per-class exclusive energy and non-exclusive rate indicators."""
    e = {c: np.zeros(N) for c in ALL}
    r = {c: np.zeros(N, dtype=bool) for c in ALL}
    anyr = np.zeros(N, dtype=bool)
    for i in range(N):
        if not keep[i]:
            continue
        sh = shift_row[i] * DAY
        best, present = attribute(g0[i] + sh, g1[i] + sh, i)
        if best is None:
            continue
        anyr[i] = True
        for c in present:
            r[c][i] = True
        e[best][i] = max(0.0, gaph[i] - DEFENSIBLE[best]) * krate[i]
    return e, r, anyr


print("\n[observed]", flush=True)
obs_e, obs_r, obs_any = run(np.zeros(N, dtype=np.int64))

print("[null over locked draws]", flush=True)
null_e = {c: np.zeros(N) for c in ALL}
null_r = {c: np.zeros(N) for c in ALL}
null_any = np.zeros(N)
null_any_rate = np.empty(N_CC)
for b in range(N_CC):
    e, r, a = run(DRAWS[b])
    for c in ALL:
        null_e[c] += e[c]
        null_r[c] += r[c]
    null_any += a
    null_any_rate[b] = a[keep].mean()
    if (b + 1) % 250 == 0:
        print(f"  {b+1}/{N_CC}", flush=True)
for c in ALL:
    null_e[c] /= N_CC
    null_r[c] /= N_CC
null_any /= N_CC

K = keep
uniq = np.unique(stays[K])
idx = {s: np.where((stays == s) & K)[0] for s in uniq}
brng = np.random.default_rng(SEED + 1)


def boot(vec, n_rep=N_BOOT):
    out = np.empty(n_rep)
    for b in range(n_rep):
        pick = brng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx[s] for s in pick])
        out[b] = vec[ii].sum()
    return np.percentile(out, [2.5, 97.5])


# ---------------- primary energy estimand (P1-P5, priority-assigned)
obs_t = sum(obs_e[c] for c in TARGET)
null_t = sum(null_e[c] for c in TARGET)
E = (obs_t - null_t)[K].sum()
lo, hi = boot(obs_t - null_t)
res["target_obs_kcal"] = float(obs_t[K].sum())
res["target_null_kcal"] = float(null_t[K].sum())
res["target_excess_kcal"] = float(E)
res["target_excess_ci"] = [float(lo), float(hi)]
res["target_pct_of_shortfall"] = round(100 * E / TOT, 3)
res["target_pct_ci"] = [round(100 * lo / TOT, 3), round(100 * hi / TOT, 3)]
res["target_kcal_per_stay"] = round(float(E / len(coh)), 1)
print(f"\nPRIMARY (locked): {E:,.0f} kcal ({lo:,.0f} to {hi:,.0f}) = "
      f"{100*E/TOT:.3f}%  {E/len(coh):.1f} kcal/stay")

# ---------------- rates (NON-EXCLUSIVE) and energy (exclusive) per class
rows = []
for c in ALL:
    lo_r, hi_r = boot((obs_r[c].astype(float) - null_r[c]) / len(uniq) * 0 +
                      (obs_r[c].astype(float) - null_r[c]), 400)
    n_stay = len(uniq)
    d_rate = (obs_r[c][K].astype(float).mean() - null_r[c][K].mean())
    lo_e, hi_e = boot(obs_e[c] - null_e[c], 400)
    rows.append({
        "class": c, "label": LABEL[c],
        "role": "negative control" if c == "P0" else "target",
        "rate_observed_pct": round(100 * obs_r[c][K].mean(), 1),
        "rate_null_pct": round(100 * null_r[c][K].mean(), 1),
        "rate_excess_pp": round(100 * d_rate, 1),
        "energy_obs_kcal": round(obs_e[c][K].sum()),
        "energy_null_kcal": round(null_e[c][K].sum()),
        "energy_excess_kcal": round((obs_e[c] - null_e[c])[K].sum()),
        "energy_excess_ci": f"{lo_e:,.0f} to {hi_e:,.0f}",
        "energy_null_excluded": not (lo_e < 0 < hi_e),
    })
    print(f"  {c}: rate {100*d_rate:+.1f} pp | energy "
          f"{(obs_e[c]-null_e[c])[K].sum():+9,.0f} ({lo_e:,.0f} to {hi_e:,.0f})")
pd.DataFrame(rows).to_csv(OUT / "rev3_by_class.csv", index=False)

anyo, anyn = obs_any[K].mean(), null_any[K].mean()
lo_a, hi_a = boot(obs_any.astype(float) - null_any)
res["rate_obs_pct"] = round(100 * anyo, 1)
res["rate_null_pct"] = round(100 * anyn, 1)
res["rate_excess_pp"] = round(100 * (anyo - anyn), 1)
res["rate_excess_ci_pp"] = [round(100 * lo_a / int(K.sum()), 1),
                            round(100 * hi_a / int(K.sum()), 1)]
res["empirical_p"] = float((np.sum(null_any_rate >= anyo) + 1) / (N_CC + 1))
print(f"\nANY rate: {100*anyo:.1f}% vs {100*anyn:.1f}% = {100*(anyo-anyn):+.1f} pp "
      f"({res['rate_excess_ci_pp'][0]} to {res['rate_excess_ci_pp'][1]}), "
      f"p={res['empirical_p']:.3f}")

# ---------------- R3-2 P0 energy diagnostics
print("\n[R3-2] P0 energy diagnostics", flush=True)
SWALLOW = {229380}
diag = []


def p0_variant(name, exclude_items=frozenset(), nonexclusive=False):
    o = np.zeros(N); nl = np.zeros(N)
    def one(row, acc):
        for i in range(N):
            if not keep[i]:
                continue
            sh = row[i] * DAY
            arr = pmap.get(stays[i])
            if arr is None:
                continue
            a, b = g0[i] + sh, g1[i] + sh
            j0 = np.searchsorted(arr, a - ATTR_W)
            j1 = np.searchsorted(arr, b + ATTR_W, "right")
            if j1 <= j0:
                continue
            cs = pcls[stays[i]][j0:j1]
            its = pitem[stays[i]][j0:j1]
            m = ~np.isin(its, list(exclude_items))
            cs, its = cs[m], its[m]
            if len(cs) == 0:
                continue
            if nonexclusive:
                if "P0" in cs:
                    acc[i] += gaph[i] * krate[i]
            else:
                if min(cs, key=lambda x: PRI[x]) == "P0":
                    acc[i] += gaph[i] * krate[i]
    one(np.zeros(N, dtype=np.int64), o)
    for b in range(0, N_CC, 5):
        one(DRAWS[b], nl)
    nl /= (N_CC // 5)
    d = (o - nl)[K].sum()
    l, h = boot(o - nl, 200)
    diag.append({"variant": name, "obs_kcal": round(o[K].sum()),
                 "null_kcal": round(nl[K].sum()), "excess_kcal": round(d),
                 "ci": f"{l:,.0f} to {h:,.0f}", "null_excluded": not (l < 0 < h)})
    print(f"  {name:46s} {d:+9,.0f}  ({l:,.0f} to {h:,.0f})")


p0_variant("P0 priority-assigned (as in primary)")
p0_variant("P0 non-exclusive (any P0 in window)", nonexclusive=True)
p0_variant("P0 excluding swallow screening", exclude_items=SWALLOW)
pd.DataFrame(diag).to_csv(OUT / "rev3_p0_diagnostics.csv", index=False)

# stratification of P0 by gap duration and pre-gap rate
d0 = (obs_e["P0"] - null_e["P0"])
strat = []
for nm, m in [("gap 2-6 h", (gaph < 6) & K), ("gap 6-12 h", (gaph >= 6) & (gaph < 12) & K),
              ("gap 12-24 h", (gaph >= 12) & K),
              ("pre-gap rate < median", (krate < np.median(krate[K])) & K),
              ("pre-gap rate >= median", (krate >= np.median(krate[K])) & K)]:
    strat.append({"stratum": nm, "n": int(m.sum()),
                  "P0_excess_kcal": round(d0[m].sum()),
                  "target_excess_kcal": round((obs_t - null_t)[m].sum())})
    print(f"  {nm:26s} P0 {d0[m].sum():+9,.0f} | target {(obs_t-null_t)[m].sum():+9,.0f}")
pd.DataFrame(strat).to_csv(OUT / "rev3_p0_strata.csv", index=False)
res["p0_energy_excess_kcal"] = float(d0[K].sum())
res["p0_energy_ci"] = diag[0]["ci"]
res["p0_energy_null_excluded"] = bool(diag[0]["null_excluded"])

json.dump(res, open(OUT / "rev3_results.json", "w"), indent=2)
print("\nDONE")
print(json.dumps(res, indent=2))
