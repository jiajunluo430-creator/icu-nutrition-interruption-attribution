"""N2 step 54 - graphical abstract.

Built from the deposited outputs rather than drawn by an image generator, because every
element here is a real number and a generated illustration cannot render real numbers.
A decorative graphical abstract carrying approximate or invented values on a measurement
paper would undercut the paper's own argument.

Three-beat story, left to right:
  1  what an EHR-derived indicator reports
  2  what the same rule returns at matched control times
  3  why the two cannot be compared between hospitals

Rendered at the BMJ banner aspect ratio (roughly 3:1) at 300 dpi.
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, REV, FIG = (ROOT / "03_outputs", ROOT / "03_outputs" / "canonical",
                      ROOT / "03_outputs" / "review6", ROOT / "04_figures")

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a86", "#e8e8e5"
mpl.rcParams.update({
    "figure.dpi": 300, "savefig.dpi": 300,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

WIN = pd.read_csv(REV / "window_definition_sensitivity.csv")
tgt = WIN[(WIN.window.str.startswith("Span")) & (WIN.scope.str.startswith("target"))].iloc[0]
SH = json.load(open(REV / "hospital_shrinkage.json"))
H = pd.read_csv(REV / "hospital_rates_shrunk.csv")
AF = json.load(open(REV / "review6_recompute.json"))["attributable_fraction"]["target_only"]

fig = plt.figure(figsize=(9.2, 3.45))
gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.05, 1.15], wspace=0.42,
                      left=0.055, right=0.975, top=0.70, bottom=0.30)

fig.text(0.055, 0.955,
         "Procedure-attributed feeding interruption rates are not comparable between ICUs",
         fontsize=11.5, fontweight="bold", color=INK, va="top")
fig.text(0.055, 0.855,
         "Attribution by record timestamps carries a large background rate \u2014 and that "
         "background differs by unit",
         fontsize=8.2, color=INK2, va="top")

# ---------------------------------------------------------------- 1
ax = fig.add_subplot(gs[0, 0])
ax.bar([0], [tgt.observed_pct], width=0.5, color=BLUE, edgecolor="white", lw=0.8)
ax.text(0, tgt.observed_pct + 1.0, f"{tgt.observed_pct}%", ha="center",
        fontsize=15, fontweight="bold", color=BLUE)
ax.set_xlim(-0.62, 0.62)
ax.set_ylim(0, 38)
ax.set_xticks([])
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_title("What the indicator reports", fontsize=9, fontweight="bold",
             loc="left", pad=6, color=INK)
fig.text(0.165, 0.235, "of feeding interruptions had\na procedure in window",
         ha="center", va="top", fontsize=7.8, color=INK2)

# ---------------------------------------------------------------- 2
ax = fig.add_subplot(gs[0, 1])
ax.bar([0], [tgt.observed_pct], width=0.5, color=GRID, edgecolor="white", lw=0.8)
ax.bar([0], [tgt.background_pct], width=0.5, color=MUTED, hatch="///",
       edgecolor="white", lw=0.8)
ax.annotate("", xy=(0.42, tgt.observed_pct), xytext=(0.42, tgt.background_pct),
            arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=1.4))
ax.text(0.50, (tgt.observed_pct + tgt.background_pct) / 2,
        f"only\n{tgt.excess_pp} pp\nexcess", fontsize=8, fontweight="bold",
        color=ORANGE, va="center")
ax.text(0, tgt.background_pct / 2, f"{tgt.background_pct}%", ha="center", va="center",
        fontsize=14, fontweight="bold", color="white")
ax.set_xlim(-0.62, 1.05)
ax.set_ylim(0, 38)
ax.set_xticks([])
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_title("At matched control times", fontsize=9, fontweight="bold",
             loc="left", pad=6, color=INK)
fig.text(0.505, 0.235, f"the same rule still fires: "
         f"{100-AF['genuine_share_of_observed_pct']:.0f}%\nof attributions are coincidental",
         ha="center", va="top", fontsize=7.8, color=INK2)

# ---------------------------------------------------------------- 3
ax = fig.add_subplot(gs[0, 2])
sh = H["background_rate_shrunk_pct"].values
lo_n, hi_n = SH["sampling_noise_only_p10_p90"]
ax.axhspan(lo_n, hi_n, color=BLUE, alpha=0.15, zorder=0)
rng = np.random.default_rng(11)
ax.scatter(rng.normal(0, 0.10, len(sh)), sh, s=5.5, color=ORANGE, alpha=0.55,
           edgecolors="none", zorder=3)
p10, p90 = SH["shrunk_p10_p90"]
for yv in (p10, p90):
    ax.hlines(yv, -0.34, 0.34, color=INK, lw=1.1, zorder=4)
ax.text(0.40, p90, f"{p90}%", fontsize=7.6, color=INK, va="center", fontweight="bold")
ax.text(0.40, p10, f"{p10}%", fontsize=7.6, color=INK, va="center", fontweight="bold")
ax.text(0.40, (lo_n + hi_n) / 2, "sampling\nnoise", fontsize=6.8, color=BLUE, va="center")
ax.set_xlim(-0.55, 1.05)
ax.set_ylim(-1.5, 31)
ax.set_xticks([])
ax.set_ylabel("Background rate (%)", fontsize=7.6)
ax.tick_params(labelsize=7)
ax.spines["bottom"].set_visible(False)
ax.set_title(f"Across {SH['hospitals']} hospitals", fontsize=9, fontweight="bold",
             loc="left", pad=6, color=INK)
fig.text(0.845, 0.235, f"the background itself varies far\nbeyond sampling noise "
         f"($\\tau$ = {SH['tau_pp']} pp)",
         ha="center", va="top", fontsize=7.8, color=INK2)

# only one connector: the second landed inside panel 3's axes
for a, b in ((0.352, 0.392),):
    fig.patches.append(FancyArrowPatch((a, 0.50), (b, 0.50), transform=fig.transFigure,
                                       arrowstyle="-|>", mutation_scale=11,
                                       color=MUTED, lw=1.0))

fig.text(0.5, 0.075,
         "Report the background rate alongside any timestamp-derived attribution "
         "percentage, or the percentage is not interpretable between units.",
         fontsize=8, color=INK, ha="center", style="italic")

for ext in ("png", "pdf", "tif"):
    kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tif" else {}
    fig.savefig(FIG / f"graphical_abstract.{ext}", facecolor="white", **kw)
plt.close(fig)
im = FIG / "graphical_abstract.png"
print(f"wrote graphical_abstract (png/pdf/tif); png {im.stat().st_size/1024:.0f} KB")
