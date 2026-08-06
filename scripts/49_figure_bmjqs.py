"""N2 step 49 - Figure 3 for BMJ Quality & Safety: between-hospital comparability.

Replaces the withdrawn "same answer in two databases" panel. The honest framing is:

A  Restricted to the only class the two databases share, they do NOT agree - eICU airway
   ascertainment is far sparser. The earlier agreement came from sedation infusions that
   MIMIC P1 does not contain.
B  Between-hospital spread survives shrinkage and greatly exceeds sampling noise.
C  Documentation lag is of the same magnitude as the attribution window.

Every value is read from a deposited output.
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, REV, FIG = ROOT / "03_outputs", ROOT / "03_outputs" / "review6", ROOT / "04_figures"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a86", "#e3e3e0"
mpl.rcParams.update({
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.labelcolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def panel(ax, letter, dx=-0.20, dy=1.24):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top", ha="left", color=INK)


LF = json.load(open(REV / "like_for_like_airway.json"))
SH = json.load(open(REV / "hospital_shrinkage.json"))
EI = json.load(open(OUT / "eicu_interface_audit.json"))
H = pd.read_csv(REV / "hospital_rates_shrunk.csv")

fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.05))

# ------------------------------------------------------------------- A
ax = axes[0]
vals = [LF["mimic_p1_background_pct"], LF["eicu_airway_only_pct"]]
b = ax.bar([0, 1], vals, color=[BLUE, ORANGE], width=0.55,
           edgecolor="white", linewidth=0.8)
b[1].set_hatch("///")
ax.errorbar([1], [vals[1]],
            yerr=[[vals[1] - LF["eicu_airway_only_ci"][0]],
                  [LF["eicu_airway_only_ci"][1] - vals[1]]],
            fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2.5)
for i, v in enumerate(vals):
    ax.text(i, v + 0.25, f"{v}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
ax.set_xticks([0, 1])
ax.set_xticklabels([f"MIMIC-IV\n{LF['mimic_p1_density_per_stay_day']}/stay-day",
                    f"eICU\n{LF['eicu_airway_density_per_stay_day']}/stay-day"], fontsize=7.2)
ax.set_ylabel("Background co-occurrence rate (%)")
ax.set_ylim(0, 9.6)
ax.yaxis.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
ax.set_title("Airway events only: no agreement", fontsize=8.5, pad=12)
ax.annotate("", xy=(1, vals[1] + 1.0), xytext=(1, vals[0] - 0.3),
            arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.8))
ax.text(1.08, (vals[0] + vals[1]) / 2,
        f"{LF['density_ratio_mimic_over_eicu']}x sparser\nascertainment",
        fontsize=6.6, color=INK2, va="center")
panel(ax, "A")

# ------------------------------------------------------------------- B
ax = axes[1]
sh = H["background_rate_shrunk_pct"].values
lo_n, hi_n = SH["sampling_noise_only_p10_p90"]
ax.axhspan(lo_n, hi_n, color=BLUE, alpha=0.14, zorder=0)
ax.text(0.60, (lo_n + hi_n) / 2, "sampling\nnoise alone", fontsize=6.6, color=BLUE,
        va="center", ha="center")
rngn = np.random.default_rng(7)
ax.scatter(1 + rngn.normal(0, 0.055, len(sh)), sh, s=7, color=ORANGE, alpha=0.55,
           edgecolors="none", zorder=3)
p10, p90 = SH["shrunk_p10_p90"]
# centile labels sit to the RIGHT of the swarm; on the left they collide with the ticks
for y, lab in ((p10, f"10th {p10}%"), (p90, f"90th {p90}%")):
    ax.hlines(y, 0.80, 1.20, color=INK, lw=1.1, zorder=4)
    ax.text(1.24, y, lab, fontsize=6.6, color=INK, ha="left", va="center")
ax.set_xlim(0.42, 1.72)
ax.set_xticks([])
ax.set_ylabel("Shrunk background rate by hospital (%)")
ax.set_title(f"$\\tau$ = {SH['tau_pp']} pp, ICC = {SH['icc']}", fontsize=8.5, pad=12)
ax.text(0.5, -0.13, f"{SH['hospitals']} hospitals, median "
        f"{SH['median_windows_per_hospital']:,} windows each",
        transform=ax.transAxes, fontsize=6.6, color=INK2, ha="center")
panel(ax, "B", dx=-0.24)

# ------------------------------------------------------------------- C
ax = axes[2]
pct = EI["doc_lag_pct_over_60min"]
ax.barh([0], [pct], color=ORANGE, height=0.45, edgecolor="white", linewidth=0.8)
ax.barh([0], [100 - pct], left=[pct], color=GRID, height=0.45,
        edgecolor="white", linewidth=0.8)
ax.text(pct / 2, 0, f"{pct}%", ha="center", va="center", fontsize=8.5,
        fontweight="bold", color="white")
ax.text(pct + (100 - pct) / 2, 0, f"{100-pct:.1f}%", ha="center", va="center",
        fontsize=8, color=INK2)
ax.set_xlim(0, 100)
ax.set_ylim(-1.15, 0.85)
ax.set_yticks([])
ax.set_xlabel("Paired nursing records (%)")
ax.spines["left"].set_visible(False)
ax.text(0, 0.52, "Lag exceeds the \u00b11 h attribution window", fontsize=7, color=INK,
        transform=ax.get_yaxis_transform(), ha="left")
ax.text(0, -0.72, f"median {EI['doc_lag_median_min']:.0f} min   "
        f"95th centile {EI['doc_lag_p95_min']:.0f} min\n"
        f"{EI['doc_lag_n']:,} paired event and entry times",
        fontsize=6.6, color=INK2, ha="left")
ax.set_title("Charted time is not event time", fontsize=8.5, pad=12)
panel(ax, "C", dx=-0.09)

fig.subplots_adjust(wspace=0.52, top=0.80)
for ext in ("png", "pdf", "tif"):
    kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tif" else {}
    fig.savefig(FIG / f"figure3_comparability.{ext}", facecolor="white", **kw)
plt.close(fig)
print("wrote figure3_comparability (png/pdf/tif)")
