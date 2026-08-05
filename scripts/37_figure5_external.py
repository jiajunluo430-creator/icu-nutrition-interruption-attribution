"""N2 step 37 - Figure 5: external validation in eICU-CRD.

Same palette, rcParams and save contract as script 09, so the figure set is visually
one piece. Every value is read from the deposited outputs, none typed here.

A  background rate: eICU pooled and best-documenting vs the like-for-like MIMIC-IV rate
B  spread of the measured background rate across hospitals, all vs best-documenting
C  documentation lag against the +/-1 h attribution window
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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


def panel(ax, letter, dx=-0.20, dy=1.24):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top", ha="left", color=INK)


def save(fig, name):
    for ext in ("png", "pdf", "tif"):
        kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tif" else {}
        fig.savefig(FIG / f"{name}.{ext}", facecolor="white", **kw)
    plt.close(fig)
    print(f"  wrote {name} (png/pdf/tif)")


EB = json.load(open(OUT / "eicu_background_rate.json"))
EA = json.load(open(OUT / "eicu_ascertainment_diagnostic.json"))
EI = json.load(open(OUT / "eicu_interface_audit.json"))
HOSP = pd.read_csv(OUT / "eicu_hospital_ascertainment.csv")

fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.05))

# ---------------------------------------------------------------- A
ax = axes[0]
# kept very short: at this bar spacing anything longer overlaps the neighbouring tick
labels = ["MIMIC-IV", f"eICU\nall {EB['hospitals']}",
          f"eICU\nbest {EA['restricted_n_hospitals']}"]
vals = [EB["mimic_p1_background_pct"], EB["eicu_background_pct"], EA["restricted_median_pct"]]
errs = [[0, EB["eicu_background_pct"] - EB["eicu_background_ci"][0], 0],
        [0, EB["eicu_background_ci"][1] - EB["eicu_background_pct"], 0]]
cols = [BLUE, ORANGE, ORANGE]
b = ax.bar(range(3), vals, color=cols, width=0.62, edgecolor="white", linewidth=0.8)
b[2].set_hatch("///")
ax.errorbar(range(3), vals, yerr=errs, fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2.5)
for i, v in enumerate(vals):
    ax.text(i, v + 0.45, f"{v}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
ax.set_xticks(range(3))
ax.set_xticklabels(labels, fontsize=7.2)
ax.set_ylabel("Background co-occurrence rate (%)")
ax.set_ylim(0, 11)
ax.yaxis.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
ax.set_title("Same answer, two databases", fontsize=8.5, pad=12)
panel(ax, "A")

# ---------------------------------------------------------------- B
ax = axes[1]
med = HOSP["pct_stays_with_any_event"].median()
allr = HOSP["background_rate_pct"].values
hir = HOSP.loc[HOSP["pct_stays_with_any_event"] >= med, "background_rate_pct"].values
bp = ax.boxplot([allr, hir], orientation="vertical", widths=0.5, showfliers=True, patch_artist=True,
                flierprops=dict(marker="o", markersize=2, markerfacecolor=MUTED,
                                markeredgecolor="none", alpha=0.55),
                medianprops=dict(color=INK, linewidth=1.2),
                whiskerprops=dict(color=INK2, linewidth=0.7),
                capprops=dict(color=INK2, linewidth=0.7))
for pat, c, h in zip(bp["boxes"], [MUTED, ORANGE], ["", "///"]):
    pat.set_facecolor(c)
    pat.set_alpha(0.55 if c == MUTED else 0.85)
    pat.set_edgecolor("white")
    pat.set_hatch(h)
ax.axhline(EB["mimic_p1_background_pct"], color=BLUE, linewidth=1.1, linestyle="--", zorder=0)
ax.text(2.48, EB["mimic_p1_background_pct"], " MIMIC-IV", color=BLUE, fontsize=6.8,
        va="center", ha="left")
ax.set_xticks([1, 2])
ax.set_xticklabels([f"All\n{len(allr)}", f"Best-documenting\n{len(hir)}"],
                   fontsize=7)
ax.set_ylabel("Background rate by hospital (%)")
ax.yaxis.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
lo, hi = EA["restricted_p10_p90"]
ax.set_title(f"Spans {lo}\u2013{hi}% between units", fontsize=8.5, pad=12)
panel(ax, "B")

# ---------------------------------------------------------------- C
ax = axes[2]
mn, p95, pct = EI["doc_lag_median_min"], EI["doc_lag_p95_min"], EI["doc_lag_pct_over_60min"]
ax.barh([0], [pct], color=ORANGE, height=0.5, edgecolor="white", linewidth=0.8)
ax.barh([0], [100 - pct], left=[pct], color=GRID, height=0.5,
        edgecolor="white", linewidth=0.8)
ax.text(pct / 2, 0, f"{pct}%", ha="center", va="center", fontsize=8.5,
        fontweight="bold", color="white")
ax.text(pct + (100 - pct) / 2, 0, f"{100-pct:.1f}%", ha="center", va="center",
        fontsize=8, color=INK2)
ax.set_xlim(0, 100)
ax.set_ylim(-1.15, 0.85)
ax.set_yticks([])
ax.set_xlabel("Nursing records (%)")
ax.spines["left"].set_visible(False)
ax.text(0, 0.52, "Lag exceeds the \u00b11 h attribution window",
        fontsize=7, color=INK, transform=ax.get_yaxis_transform(), ha="left")
ax.text(0, -0.72, f"median {mn:.0f} min   95th centile {p95:.0f} min\n"
                  f"{EI['doc_lag_n']:,} paired event and entry times",
        fontsize=6.8, color=INK2, ha="left")
ax.set_title("Charted time is not event time", fontsize=8.5, pad=12)
panel(ax, "C", dx=-0.09)

fig.subplots_adjust(wspace=0.46, top=0.80)
save(fig, "figure5_external_validation")
print("Figure 5 built from deposited outputs only")
