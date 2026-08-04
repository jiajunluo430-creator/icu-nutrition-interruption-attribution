"""N2 step 20 - second revision round.

R2-1  Primary energy estimand is P1-P5 ONLY. The negative control P0 is a diagnostic
      and must not offset the candidate procedural classes. Full bootstrap on the
      P1-P5 sum, not P0 added back.
R2-2a Oral intake: hours after recorded oral/supplement intake begins are censored,
      because MIMIC energy comes from EN/PN records and oral intake would otherwise
      be counted as zero delivery.
R2-2b Ramped reference target: 40% on ICU day 1, 70% on day 2, 100% from day 3,
      instead of full target from hour zero.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260806)
ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, INT = ROOT / "03_outputs", ROOT / "02_intermediates"

TARGET = ["P1", "P2", "P3", "P4", "P5"]        # candidate procedural classes
ALL = TARGET + ["P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
DEFENSIBLE = {"P1": 6.0, "P2": 6.0, "P3": 0.0, "P4": 0.0, "P5": 0.0, "P0": 0.0}
ATTR_W, DAY, N_CC, N_BOOT, KCAL_KG = 3600, 86400, 1000, 1000, 25.0

itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv", parse_dates=["starttime"])
part = pd.read_csv(OUT / "rev_time_partition.csv")
seg = pd.read_csv(OUT / "segments_final.csv", parse_dates=["starttime", "endtime"])
res = {}
itr = itr.merge(coh[["stay_id", "intime", "win_end"]], on="stay_id", how="left")

g0 = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1 = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
t0 = itr["intime"].values.astype("datetime64[s]").astype(np.int64)
t1 = itr["win_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
krate = itr["kcal_rate_pre"].fillna(0).values
N = len(g0)

pmap, pcls = {}, {}
for k, v in prc.groupby("stay_id", sort=False):
    o = v.sort_values("starttime")
    pmap[k] = o["starttime"].values.astype("datetime64[s]").astype(np.int64)
    pcls[k] = o["proc_class"].values

valid_k, n_no_ctrl = [], 0
for i in range(N):
    ks = [k for k in range(-6, 7) if k != 0
          and g0[i] + k * DAY >= t0[i] and g1[i] + k * DAY <= t1[i]]
    if not ks:
        n_no_ctrl += 1
    valid_k.append(np.array(ks) if ks else np.array([0]))
PRI = {c: i for i, c in enumerate(ALL)}


def per_class_kcal(a, b):
    """Excess kcal per interruption, per assigned class."""
    out = {c: np.zeros(N) for c in ALL}
    for i in range(N):
        arr = pmap.get(stays[i])
        if arr is None:
            continue
        j0 = np.searchsorted(arr, a[i] - ATTR_W)
        j1 = np.searchsorted(arr, b[i] + ATTR_W, "right")
        if j1 <= j0:
            continue
        c = min(pcls[stays[i]][j0:j1], key=lambda x: PRI[x])
        out[c][i] = max(0.0, (b[i] - a[i]) / 3600.0 - DEFENSIBLE[c]) * krate[i]
    return out


print("[R2-1] primary estimand = P1-P5 only; P0 reported as diagnostic", flush=True)
obs = per_class_kcal(g0, g1)
null_acc = {c: np.zeros(N) for c in ALL}
for b in range(N_CC):
    k = np.array([v[rng.integers(len(v))] for v in valid_k]) * DAY
    r = per_class_kcal(g0 + k, g1 + k)
    for c in ALL:
        null_acc[c] += r[c]
    if (b + 1) % 250 == 0:
        print(f"  replicate {b+1}/{N_CC}", flush=True)
null = {c: null_acc[c] / N_CC for c in ALL}

obs_t = sum(obs[c] for c in TARGET)
null_t = sum(null[c] for c in TARGET)
E_obs, E_null = obs_t.sum(), null_t.sum()
E_exc = E_obs - E_null

uniq = np.unique(stays)
idx = {s: np.where(stays == s)[0] for s in uniq}
bs = np.empty(N_BOOT)
for b in range(N_BOOT):
    pick = rng.choice(uniq, size=len(uniq), replace=True)
    ii = np.concatenate([idx[s] for s in pick])
    bs[b] = obs_t[ii].sum() - null_t[ii].sum()
lo, hi = np.percentile(bs, [2.5, 97.5])

TOT = float(part["deficit_total"].sum())
print(f"  P1-P5 observed {E_obs:,.0f} | null {E_null:,.0f} | excess {E_exc:,.0f}")
print(f"  95% CI {lo:,.0f} to {hi:,.0f}")
print(f"  share of shortfall {100*E_exc/TOT:.3f}%  ({E_exc/len(coh):.1f} kcal per stay)")
res.update(target_obs_kcal=float(E_obs), target_null_kcal=float(E_null),
           target_excess_kcal=float(E_exc),
           target_excess_ci=[float(lo), float(hi)],
           target_pct_of_shortfall=round(100 * E_exc / TOT, 3),
           target_pct_ci=[round(100 * lo / TOT, 3), round(100 * hi / TOT, 3)],
           target_kcal_per_stay=round(float(E_exc / len(coh)), 1),
           n_without_control_day=int(n_no_ctrl))

rows = []
for c in ALL:
    d = obs[c] - null[c]
    bb = np.empty(400)
    for b in range(400):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx[s] for s in pick])
        bb[b] = d[ii].sum()
    l2, h2 = np.percentile(bb, [2.5, 97.5])
    rows.append({"class": c, "label": LABEL[c],
                 "role": "negative control (diagnostic)" if c == "P0" else "target class",
                 "obs_kcal": round(obs[c].sum()), "null_kcal": round(null[c].sum()),
                 "excess_kcal": round(d.sum()),
                 "excess_ci": f"{l2:,.0f} to {h2:,.0f}",
                 "pct_of_shortfall": round(100 * d.sum() / TOT, 4)})
    print(f"    {c} {rows[-1]['role'][:18]:18s} excess {d.sum():>9,.0f}  ({l2:,.0f} to {h2:,.0f})")
pd.DataFrame(rows).to_csv(OUT / "rev2_energy_by_class.csv", index=False)
res["p0_diagnostic_kcal"] = float((obs["P0"] - null["P0"]).sum())

# ================================================== R2-2a oral intake
print("\n[R2-2a] oral-intake censoring", flush=True)
po = pd.read_csv(INT / "po_intake.csv", parse_dates=["starttime"])
po = po[po["stay_id"].isin(set(coh["stay_id"]))]
first_po = po.groupby("stay_id")["starttime"].min().rename("po_start")
c2 = coh.merge(first_po, on="stay_id", how="left")
c2 = c2.merge(part[["stay_id", "wkg", "kcal_del", "fed_h", "pre_h", "post_h",
                    "short_gap_h", "other_gap_h", "obs_h"]], on="stay_id", how="inner")
has_po = c2["po_start"].notna()
print(f"  stays with recorded oral/supplement intake: {has_po.sum():,} "
      f"({100*has_po.mean():.1f}%)")

c2["win_end_po"] = np.where(has_po, np.minimum(c2["win_end"].values,
                                               c2["po_start"].values), c2["win_end"].values)
c2["obs_h_po"] = ((pd.to_datetime(c2["win_end_po"]) - c2["intime"]).dt.total_seconds()
                  / 3600.0).clip(lower=0)
c2["trate"] = c2["wkg"] * KCAL_KG / 24.0
# conservative: keep delivered as recorded, shrink the denominator hours
short_po = (c2["trate"] * c2["obs_h_po"] - c2["kcal_del"]).clip(lower=0).sum()
res["oral_censored_shortfall_kcal"] = float(short_po)
res["oral_censored_pct_of_original"] = round(100 * short_po / TOT, 1)
res["pct_stays_with_oral_intake"] = round(100 * float(has_po.mean()), 1)
res["target_pct_oral_censored"] = round(100 * E_exc / short_po, 3)
print(f"  shortfall after censoring at first oral intake: {short_po/1e6:.1f} M kcal "
      f"({100*short_po/TOT:.0f}% of the uncensored value)")
print(f"  procedural share under this denominator: {100*E_exc/short_po:.3f}%")

# ================================================== R2-2b ramped target
print("\n[R2-2b] ramped reference target (40% d1, 70% d2, 100% d3+)", flush=True)
ramp = {1: 0.40, 2: 0.70}
tot_ramp = 0.0
for r in part.itertuples():
    h_left, tgt = r.obs_h, 0.0
    for d in range(1, 8):
        h = min(24.0, max(0.0, h_left))
        tgt += (r.wkg * KCAL_KG / 24.0) * h * ramp.get(d, 1.0)
        h_left -= h
        if h_left <= 0:
            break
    tot_ramp += max(0.0, tgt - r.kcal_del)
res["ramped_shortfall_kcal"] = float(tot_ramp)
res["target_pct_ramped"] = round(100 * E_exc / tot_ramp, 3)
print(f"  ramped shortfall {tot_ramp/1e6:.1f} M kcal "
      f"({100*tot_ramp/TOT:.0f}% of flat-target value)")
print(f"  procedural share under ramped target: {100*E_exc/tot_ramp:.3f}%")

# recompute the pre-initiation share under the ramped target
pre_ramp = 0.0
for r in part.itertuples():
    h_left, pre_left, tgt_pre = r.obs_h, r.pre_h, 0.0
    for d in range(1, 8):
        h = min(24.0, max(0.0, h_left))
        take = min(h, max(0.0, pre_left))
        tgt_pre += (r.wkg * KCAL_KG / 24.0) * take * ramp.get(d, 1.0)
        pre_left -= take
        h_left -= h
        if h_left <= 0 or pre_left <= 0:
            break
    pre_ramp += tgt_pre
res["pre_initiation_pct_ramped"] = round(100 * pre_ramp / tot_ramp, 1)
print(f"  pre-initiation share under ramped target: {100*pre_ramp/tot_ramp:.1f}% "
      f"(flat target gave 48.5%)")

json.dump(res, open(OUT / "rev2_results.json", "w"), indent=2)
print("\nDONE")
print(json.dumps(res, indent=2))
