"""N2 step 08 - strengthening analyses for the Frontiers in Nutrition submission.

Four additions, all logged in the exploratory registry:

E07  Bootstrap 95% CIs (clustered by ICU stay) on every attribution estimate.
E08  CIRCULAR within-window shift null. The contract's simple +48 h shift pushes
     procedures past the end of the observation window, where they can no longer
     match. That deflates the placebo rate and therefore INFLATES the excess.
     A circular shift preserves the exact number and density of in-window
     procedures. The prespecified +48 h value is retained as primary; the
     circular null is the honest bias-corrected version and is reported alongside.
E09  Share of the total energy deficit attributable to interruptions.
E10  Time-of-day pattern of interruptions (workflow signature).
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260802)
ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"

ATTR_WIN_H = 1.0
CLASSES = ["P1", "P2", "P3", "P4", "P5", "P0"]
LABEL = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics (negative control)"}
N_BOOT = 2000

itr = pd.read_csv(OUT / "interruptions.csv", parse_dates=["gap_start", "gap_end"])
prc = pd.read_csv(OUT / "procedures_in_window.csv",
                  parse_dates=["starttime", "intime", "win_end"])
coh = pd.read_csv(OUT / "cohort.csv", parse_dates=["intime", "win_end"])
day = pd.read_csv(OUT / "stay_days.csv")
res = {}

win = timedelta(hours=ATTR_WIN_H)
wsec = {r.stay_id: (r.win_end - r.intime).total_seconds()
        for r in coh.itertuples()}
intime = {r.stay_id: r.intime for r in coh.itertuples()}

by_stay = {k: (v["starttime"].values.astype("datetime64[s]").astype(np.int64),
               v["proc_class"].values)
           for k, v in prc.groupby("stay_id", sort=False)}

g0s = itr["gap_start"].values.astype("datetime64[s]").astype(np.int64)
g1s = itr["gap_end"].values.astype("datetime64[s]").astype(np.int64)
stays = itr["stay_id"].values
W = int(ATTR_WIN_H * 3600)


def hits(shift_h=0.0, circular=False):
    """Per-class boolean hit matrix for all interruptions."""
    out = {c: np.zeros(len(itr), dtype=bool) for c in CLASSES}
    sh = int(shift_h * 3600)
    for i in range(len(itr)):
        sid = stays[i]
        arr = by_stay.get(sid)
        if arr is None:
            continue
        t, cls = arr
        if sh:
            if circular:
                t0 = np.int64(intime[sid].timestamp())
                D = np.int64(wsec[sid])
                if D <= 0:
                    continue
                t = t0 + np.mod(t - t0 + sh, D)
            else:
                t = t + sh
        lo, hi = g0s[i] - W, g1s[i] + W
        m = (t >= lo) & (t <= hi)
        if m.any():
            for c in np.unique(cls[m]):
                out[c][i] = True
    return out


print("[1] observed + prespecified +48h + circular nulls", flush=True)
obs = hits(0.0)
pbo_simple = hits(48.0, circular=False)
pbo_circ = hits(48.0, circular=True)

any_obs = np.any([obs[c] for c in CLASSES], axis=0)
any_simple = np.any([pbo_simple[c] for c in CLASSES], axis=0)
any_circ = np.any([pbo_circ[c] for c in CLASSES], axis=0)
print(f"  observed            {any_obs.mean():.3%}")
print(f"  placebo +48h simple {any_simple.mean():.3%}  (contract primary)")
print(f"  placebo +48h circ   {any_circ.mean():.3%}  (bias-corrected)")

# ---------------------------------------------------- E08 circular null distribution
print("\n[2] circular null distribution", flush=True)
SHIFTS = [s for s in range(-96, 97, 6) if abs(s) >= 12]
null_any, null_cls = [], {c: [] for c in CLASSES}
for s in SHIFTS:
    h = hits(float(s), circular=True)
    null_any.append(np.any([h[c] for c in CLASSES], axis=0).mean())
    for c in CLASSES:
        null_cls[c].append(h[c].mean())
null_any = np.array(null_any)
print(f"  {len(SHIFTS)} circular shifts; null mean {null_any.mean():.3%} "
      f"(range {null_any.min():.3%}-{null_any.max():.3%})")
emp_p = (np.sum(null_any >= any_obs.mean()) + 1) / (len(null_any) + 1)
print(f"  observed {any_obs.mean():.3%}; empirical p = {emp_p:.4f}")
res["null_mean_pct"] = round(100 * float(null_any.mean()), 1)
res["null_min_pct"] = round(100 * float(null_any.min()), 1)
res["null_max_pct"] = round(100 * float(null_any.max()), 1)
res["empirical_p"] = float(emp_p)
res["excess_vs_circular_null_pp"] = round(100 * float(any_obs.mean() - null_any.mean()), 1)
pd.DataFrame({"shift_h": SHIFTS, "null_attr_pct": 100 * null_any}).to_csv(
    OUT / "null_distribution.csv", index=False)

# ---------------------------------------------------- E07 bootstrap CIs
print("\n[3] bootstrap CIs (clustered by stay)", flush=True)
uniq = np.unique(stays)
idx_by_stay = {s: np.where(stays == s)[0] for s in uniq}
null_mean_cls = {c: np.mean(null_cls[c]) for c in CLASSES}


def boot_ci(vec_obs, vec_null):
    """Percentile CI for mean(obs), mean(null), and their difference."""
    d = np.empty(N_BOOT); o = np.empty(N_BOOT); n = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx_by_stay[s] for s in pick])
        o[b] = vec_obs[ii].mean()
        n[b] = vec_null[ii].mean()
        d[b] = o[b] - n[b]
    q = lambda a: (np.percentile(a, 2.5), np.percentile(a, 97.5))
    return q(o), q(n), q(d)

rows = []
(oc, nc, dc) = boot_ci(any_obs, any_circ)
rows.append({"class": "ANY", "label": "Any prespecified class",
             "observed_pct": round(100 * any_obs.mean(), 1),
             "observed_ci": f"{100*oc[0]:.1f}-{100*oc[1]:.1f}",
             "null_pct": round(100 * any_circ.mean(), 1),
             "excess_pp": round(100 * (any_obs.mean() - any_circ.mean()), 1),
             "excess_ci": f"{100*dc[0]:.1f} to {100*dc[1]:.1f}",
             "significant": not (dc[0] < 0 < dc[1])})
for c in CLASSES:
    (oc, nc, dc) = boot_ci(obs[c], pbo_circ[c])
    ex = obs[c].mean() - pbo_circ[c].mean()
    rows.append({"class": c, "label": LABEL[c],
                 "observed_pct": round(100 * obs[c].mean(), 1),
                 "observed_ci": f"{100*oc[0]:.1f}-{100*oc[1]:.1f}",
                 "null_pct": round(100 * pbo_circ[c].mean(), 1),
                 "excess_pp": round(100 * ex, 1),
                 "excess_ci": f"{100*dc[0]:.1f} to {100*dc[1]:.1f}",
                 "significant": not (dc[0] < 0 < dc[1])})
ci = pd.DataFrame(rows)
print(ci.to_string(index=False))
ci.to_csv(OUT / "table7_attribution_ci.csv", index=False)

# ---------------------------------------------------- E09 share of total deficit
print("\n[4] share of total energy deficit", flush=True)
day["deficit"] = (day["kcal_target"] - day["kcal"]).clip(lower=0)
total_deficit = day["deficit"].sum()
total_lost = itr["kcal_lost"].sum()
itr2 = itr.copy()
attr_lost = itr2.loc[itr2["proc_class"].isin(["P1", "P2", "P3"]), "excess_kcal"].sum()
res["total_energy_deficit_kcal"] = float(total_deficit)
res["kcal_lost_to_interruptions"] = float(total_lost)
res["pct_deficit_from_interruptions"] = round(100 * total_lost / total_deficit, 1)
res["avoidable_excess_kcal_validated"] = float(attr_lost)
res["pct_deficit_avoidable_validated"] = round(100 * attr_lost / total_deficit, 1)
print(f"  total deficit               {total_deficit:,.0f} kcal")
print(f"  lost to interruptions       {total_lost:,.0f} ({100*total_lost/total_deficit:.1f}%)")
print(f"  avoidable (validated cls)   {attr_lost:,.0f} ({100*attr_lost/total_deficit:.1f}%)")

# ---------------------------------------------------- E10 time-of-day
print("\n[5] time-of-day pattern", flush=True)
itr2["hour"] = itr2["gap_start"].dt.hour
tod = (itr2.groupby(["hour", itr2["proc_class"].notna()]).size()
       .unstack(fill_value=0).rename(columns={False: "unattributed", True: "attributed"})
       .reindex(range(24), fill_value=0).reset_index())
tod.to_csv(OUT / "table8_time_of_day.csv", index=False)
una = itr2[itr2["proc_class"].isna()]
peak = tod.set_index("hour")["unattributed"].idxmax()
night = una[(una["hour"] >= 22) | (una["hour"] < 6)].shape[0] / max(len(una), 1)
res["unattributed_n"] = int(len(una))
res["unattributed_pct"] = round(100 * len(una) / len(itr2), 1)
res["unattributed_peak_hour"] = int(peak)
res["unattributed_night_share_pct"] = round(100 * night, 1)
res["unattributed_median_h"] = round(float(una["gap_h"].median()), 1)
print(f"  unattributed {len(una):,} ({100*len(una)/len(itr2):.1f}%), "
      f"median {una['gap_h'].median():.1f} h, peak start hour {peak}:00, "
      f"{100*night:.1f}% start 22:00-06:00")

# ---------------------------------------------------- per-patient framing
n_stay = len(coh)
res["avoidable_kcal_per_stay"] = round(float(attr_lost / n_stay), 0)
res["transport_excess_h_per_affected_event"] = round(
    float(itr2.loc[itr2["proc_class"] == "P3", "excess_h"].median()), 1)
print(f"\n  avoidable energy per ICU stay: {attr_lost/n_stay:,.0f} kcal")

json.dump(res, open(OUT / "strengthen_results.json", "w"), indent=2)
print("\nDONE")
print(json.dumps(res, indent=2))
