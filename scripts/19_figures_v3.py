"""N2 step 19 - revised figure set (post-review).

Fig 2C  now decomposes the FULL shortfall over all alive-in-ICU hours.
Fig 3   now uses the clock-preserving case-crossover null (1,000 replicates).
Fig 4   now shows the energy estimand run THROUGH the null, plus the sensitivity
        range; the negative control is shown separately from the target classes.
Palette: slots 1-3 of the dataviz reference palette, unmodified.
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, FIG = ROOT / "03_outputs", ROOT / "04_figures"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a86", "#e3e3e0"

mpl.rcParams.update({
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.labelcolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def panel(ax, letter, dx=-0.14, dy=1.06):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=11, fontweight="bold",
            va="top", ha="left", color=INK)


def save(fig, name):
    for ext in ("png", "pdf", "tif"):
        kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tif" else {}
        fig.savefig(FIG / f"{name}.{ext}", facecolor="white", **kw)
    plt.close(fig)
    print(f"  wrote {name} (png/pdf/tif)", flush=True)


adq = pd.read_csv(OUT / "table2_delivery_adequacy.csv")
rate = pd.read_csv(OUT / "canonical" / "canonical_class_results.csv")
ecls = pd.read_csv(OUT / "canonical" / "canonical_class_results.csv")
sens = pd.read_csv(OUT / "canonical" / "canonical_sensitivity.csv")
nulld = pd.read_csv(OUT / "canonical" / "canonical_null_distribution.csv")
rev = json.load(open(OUT / "rev_results.json"))
rr = json.load(open(OUT / "canonical" / "canonical_primary.json"))['rate']
r2 = json.load(open(OUT / "canonical" / "canonical_primary.json"))
dn = json.load(open(OUT / "rev3_day_preserving_null.json"))

SHORT = {"P1": "Airway /\nsedation", "P2": "GI\nendoscopic", "P3": "Off-unit\ntransport",
         "P4": "Bedside\ninvasive", "P5": "Renal\nreplacement",
         "P0": "Bedside diagnostics\n(negative control)"}


def ci(s):
    a, b = str(s).replace("\u2212", "-").split(" to ")
    return float(a), float(b)


# ================================================= Figure 1 (unchanged content)
print("[Fig 1]", flush=True)
main = [("ICU stays in MIMIC-IV v3.1", 94458), ("First ICU stay per patient", 65366),
        ("ICU length of stay \u2265 48 h", 31143),
        ("\u2265 2 nutrition days in ICU days 1\u20137\n(analysis cohort)", 6883)]
excl = ["29,092 repeat ICU stays", "34,223 ICU stay < 48 h",
        "24,260 no qualifying nutrition\nsupport in days 1\u20137"]
fig, ax = plt.subplots(figsize=(5.0, 4.4))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
ys, bx, bw = [8.9, 6.4, 3.9, 1.3], 0.3, 5.0
for i, ((lbl, n), y) in enumerate(zip(main, ys)):
    last = i == len(main) - 1
    ax.add_patch(FancyBboxPatch((bx, y - 0.6), bw, 1.2,
                                boxstyle="round,pad=0.06,rounding_size=0.12",
                                facecolor="#eaf2fc" if last else "white",
                                edgecolor=BLUE if last else MUTED,
                                linewidth=1.1 if last else 0.7))
    ax.text(bx + bw / 2, y, f"{lbl}\nn = {n:,}", ha="center", va="center",
            fontsize=8, color=INK, linespacing=1.35)
for (y0, y1), e in zip(zip(ys[:-1], ys[1:]), excl):
    ax.add_patch(FancyArrowPatch((bx + bw / 2, y0 - 0.63), (bx + bw / 2, y1 + 0.63),
                                 arrowstyle="-|>", mutation_scale=9, color=MUTED, lw=0.7))
    ym = (y0 + y1) / 2
    ax.add_patch(FancyArrowPatch((bx + bw / 2, ym), (bx + bw + 0.5, ym),
                                 arrowstyle="-|>", mutation_scale=8, color=MUTED, lw=0.6))
    ax.text(bx + bw + 0.65, ym, "Excluded:\n" + e, ha="left", va="center",
            fontsize=7, color=INK2, linespacing=1.3)
save(fig, "figure1_cohort_flow")

# ================================================= Figure 2
print("[Fig 2]", flush=True)
fig = plt.figure(figsize=(7.2, 5.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.80], hspace=0.62, wspace=0.28)

ax = fig.add_subplot(gs[0, 0]); panel(ax, "A")
ax.fill_between(adq.icu_day, adq.kcal_pct_q1, adq.kcal_pct_q3, color=BLUE,
                alpha=0.16, lw=0, label="Energy IQR")
ax.plot(adq.icu_day, adq.kcal_pct_median, color=BLUE, lw=2, marker="o", ms=4.5,
        label="Energy", zorder=3)
ax.plot(adq.icu_day, adq.prot_pct_median, color=ORANGE, lw=2, marker="s", ms=4.5,
        ls="--", label="Protein", zorder=3)
ax.axhline(100, color=MUTED, lw=0.8, ls=":")
ax.text(7.05, 102, "reference", fontsize=6.8, color=MUTED, va="bottom", ha="right")
ax.set_xlabel("ICU day"); ax.set_ylabel("% of reference target")
ax.set_title("Delivery on nutrition-support days", loc="left", color=INK)
ax.set_xticks(range(1, 8)); ax.set_ylim(0, 112)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", handlelength=1.6)

ax = fig.add_subplot(gs[0, 1]); panel(ax, "B")
x = np.arange(len(adq))
ax.bar(x - 0.19, adq.pct_days_ge80, 0.36, color=BLUE, label="\u2265 80% of reference")
ax.bar(x + 0.19, adq.pct_days_ge100, 0.36, color=AQUA, hatch="///",
       edgecolor="white", lw=0.5, label="\u2265 100% of reference")
ax.set_xticks(x); ax.set_xticklabels(adq.icu_day)
ax.set_xlabel("ICU day"); ax.set_ylabel("% of nutrition-support days")
ax.set_title("Days reaching the reference", loc="left", color=INK)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_ylim(0, 30)
ax.legend(frameon=False, loc="upper left", handlelength=1.6)

ax = fig.add_subplot(gs[1, :]); panel(ax, "C", dx=-0.062, dy=1.18)
c = rev["shortfall_components_pct"]
segs = [("Before feeding started", c["pre"], MUTED, ""),
        ("Feeding running below reference", c["running"], "#b9c9dc", ""),
        ("After feeding stopped", c["post"], "#cfd8e3", "\\\\"),
        ("Longer or sub-2 h gaps", c["othergap"], "#e2e2de", "//"),
        ("Qualifying 2\u201324 h interruptions", c["short"], ORANGE, "")]
left = 0
for lab, v, col, hh in segs:
    ax.barh([0], [v], left=left, height=0.42, color=col, hatch=hh,
            edgecolor="white", lw=0.7, label=f"{lab} ({v:.1f}%)")
    if v > 8:
        ax.text(left + v / 2, 0, f"{v:.1f}%", ha="center", va="center",
                fontsize=8, fontweight="bold",
                color="white" if col == MUTED else INK)
    left += v
ax.set_xlim(0, 100); ax.set_ylim(-0.62, 0.75); ax.set_yticks([])
ax.set_xlabel("% of the 64.9 million kcal shortfall")
ax.set_title("Where the first-week shortfall accrues (all alive-in-ICU hours, days 1\u20137)",
             loc="left", color=INK)
ax.spines["left"].set_visible(False)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.annotate(f"chance-corrected procedural\nshare = {r2['target_pct']:.2f}%",
            xy=(100 - c["short"] / 2, 0.22), xytext=(78, 0.66), fontsize=7.5,
            color=INK, fontweight="bold", ha="center",
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.92),
          ncol=2, handlelength=1.5, labelspacing=0.35, columnspacing=1.4)
save(fig, "figure2_delivery_and_shortfall")

# ================================================= Figure 3
print("[Fig 3]", flush=True)
r = rate.copy()
r = r.rename(columns={"rate_observed_pct": "observed_pct",
                      "rate_null_pct": "null_pct",
                      "rate_excess_pp": "excess_pp"})
r["significant"] = r["rate_null_excluded"].astype(bool)
r["lo"] = r["rate_excess_lo"]; r["hi"] = r["rate_excess_hi"]
r = r.sort_values("excess_pp").reset_index(drop=True)
r["short"] = r["class"].map(SHORT)
y = np.arange(len(r))

fig = plt.figure(figsize=(7.2, 5.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.85], hspace=0.64, wspace=0.30)

ax = fig.add_subplot(gs[0, 0]); panel(ax, "A")
ax.barh(y + 0.19, r.observed_pct, 0.36, color=BLUE, label="Observed")
ax.barh(y - 0.19, r.null_pct, 0.36, color=MUTED, hatch="///", edgecolor="white",
        lw=0.5, label="Case-crossover null")
ax.set_yticks(y); ax.set_yticklabels(r.short, fontsize=7)
ax.set_xlabel("% of interruptions with a procedure in window")
ax.set_title("Observed vs background rate (non-exclusive)", loc="left",
             color=INK, pad=16)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_xlim(0, 19)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2,
          handlelength=1.5, columnspacing=1.0)

ax = fig.add_subplot(gs[0, 1]); panel(ax, "B")
cols = [AQUA if sg else MUTED for sg in r.significant]
ax.barh(y, r.excess_pp, 0.5, color=cols,
        xerr=[r.excess_pp - r.lo, r.hi - r.excess_pp],
        error_kw=dict(ecolor=INK2, elinewidth=0.8, capsize=2))
ax.axvline(0, color=INK, lw=0.9)
ax.set_yticks(y); ax.set_yticklabels([])
ax.set_xlabel("Excess over null, pp (95% CI)")
ax.set_title("Excess surviving the null", loc="left", color=INK, pad=16)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
for yi, (v, lo, hi) in enumerate(zip(r.excess_pp, r.lo, r.hi)):
    ax.text(hi + 0.15, yi, f"{v:+.1f}{'*' if r.significant.iloc[yi] else ''}",
            va="center", ha="left", fontsize=7.5, color=INK, fontweight="bold")
ax.set_xlim(-1.6, 8.6)

ax = fig.add_subplot(gs[1, :]); panel(ax, "C", dx=-0.062, dy=1.14)
nd = nulld["null_attr_pct"].values
ax.hist(nd, bins=30, color=MUTED, alpha=0.55, edgecolor="white", lw=0.4,
        label=f"Case-crossover null ({len(nd):,} replicates)")
ax.axvline(rr["obs_pct"], color=ORANGE, lw=2.2, zorder=5)
ax.annotate(f"Observed {rr['obs_pct']:.1f}%\nempirical p = {rr['p']:.3f}",
            xy=(rr["obs_pct"], ax.get_ylim()[1] * 0.66),
            xytext=(rr["obs_pct"] - 1.6, ax.get_ylim()[1] * 0.88),
            fontsize=7.8, color=INK, fontweight="bold", ha="right",
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.1))
ax.set_xlabel("% of interruptions attributed to any prespecified procedure class")
ax.set_ylabel("Replicates")
ax.set_title("Observed rate against its null distribution", loc="left", color=INK)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", handlelength=1.5)
save(fig, "figure3_attribution")

# ================================================= Figure 4
print("[Fig 4]", flush=True)
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.9), gridspec_kw={"width_ratios": [1, 1.30]})

ax = axes[0]; panel(ax, "A", dx=-0.30)
e = ecls.copy()
e["short"] = e["class"].map(lambda k: SHORT[k].replace("\n", " "))
e["is_target"] = e["role"].str.startswith("target")
e = pd.concat([e[~e.is_target],
               e[e.is_target].sort_values("energy_excess_kcal")]
              ).reset_index(drop=True)
yy = np.arange(len(e))
ax.barh(yy + 0.19, e.energy_obs_kcal / 1000, 0.36, color=BLUE, label="Observed")
ax.barh(yy - 0.19, e.energy_null_kcal / 1000, 0.36, color=MUTED, hatch="///",
        edgecolor="white", lw=0.5, label="Null")
ax.set_yticks(yy); ax.set_yticklabels(e.short, fontsize=7)
ax.set_xlabel("Energy assigned beyond the defensible window (thousand kcal)")
ax.set_title("Energy beyond the defensible window", loc="left", color=INK,
             pad=16, fontsize=8)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2,
          handlelength=1.5, columnspacing=1.0)
for yi, v in zip(yy, e.energy_excess_kcal / 1000):
    ax.text(max(e.energy_obs_kcal.iloc[yi], e.energy_null_kcal.iloc[yi]) / 1000 + 8, yi,
            f"{v:+.0f}k", va="center", fontsize=7, color=INK, fontweight="bold")
ax.set_xlim(0, 380)
_sep = 0.5
ax.axhline(_sep, color=INK2, lw=0.8, ls=":")
ax.set_ylabel("")
ax.text(0.99, 0.02, "below the line: negative control (diagnostic only)",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=6.2,
        color=INK2, style="italic")

ax = axes[1]; panel(ax, "B", dx=-0.10)
s = sens[~sens.analysis.str.contains("mixed")].sort_values("pct_of_shortfall").reset_index(drop=True)
yy = np.arange(len(s))
ax.barh(yy, s.pct_of_shortfall, 0.62, color=AQUA, edgecolor="white", lw=0.4)
ax.set_yticks(yy)
ax.set_yticklabels([a.replace(" (n=", "\n(n=") for a in s.analysis], fontsize=6.2)
ax.axvline(1.3, color=ORANGE, lw=1.6, ls="--")
ax.set_xlabel("Chance-corrected procedural share of shortfall (%)")
ax.set_title("Sensitivity analyses of the chance-corrected procedural share",
             loc="left", color=INK, pad=16, fontsize=8)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.set_xlim(0, max(0.55, s.pct_of_shortfall.max() * 1.25))
for yi, v in zip(yy, s.pct_of_shortfall):
    ax.text(v + 0.02, yi, f"{v:.3f}", va="center", fontsize=6.2, color=INK2)
fig.subplots_adjust(left=0.16, right=0.985, wspace=0.62, top=0.84, bottom=0.16)
save(fig, "figure4_energy_through_null")

print("\nDONE")
