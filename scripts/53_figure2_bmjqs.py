"""N2 step 53 - Figure 2 for BMJ Quality & Safety, terminology unified with the text.

Changes from the earlier attribution figure:
  - "case-crossover null" -> "matched control times" throughout, matching the manuscript
  - "chance-corrected" / "excess over null" -> "excess over background"
  - empirical p reported as an inequality (its floor is 1/(B+1)), not as 0.001
  - panel B carries its own class labels instead of relying on row alignment with A
  - the negative-control pair in A is separated from the target classes so its
    observed and background bars are distinguishable
  - greyscale-safe: every series differs by hatch as well as fill, and the legend
    never refers to colour (BMJ prints figures in black and white)
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, CAN, REV, FIG = (ROOT / "03_outputs", ROOT / "03_outputs" / "canonical",
                      ROOT / "03_outputs" / "review6", ROOT / "04_figures")

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

CLS = pd.read_csv(CAN / "canonical_class_results.csv")
ND = pd.read_csv(CAN / "canonical_null_distribution.csv")
R6 = json.load(open(REV / "review6_recompute.json"))
C = json.load(open(CAN / "canonical_primary.json"))

SHORT = {"P1": "Airway", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics\n(negative control)"}
order = ["P1", "P3", "P2", "P4", "P5", "P0"]
d = CLS.set_index("class").loc[order]

fig = plt.figure(figsize=(7.5, 5.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], width_ratios=[1.06, 1.0],
                      hspace=0.55, wspace=0.52)


def panel(ax, letter, dx=-0.16, dy=1.16):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=11, fontweight="bold",
            va="top", ha="left", color=INK)


# ------------------------------------------------------------------ A
ax = fig.add_subplot(gs[0, 0])
y = np.arange(len(order))[::-1].astype(float)
y[-1] -= 0.55                                   # detach the negative control
ax.barh(y + 0.19, d["rate_observed_pct"], 0.36, color=BLUE, edgecolor="white",
        lw=0.6, label="Observed")
ax.barh(y - 0.19, d["rate_null_pct"], 0.36, color=MUTED, hatch="///",
        edgecolor="white", lw=0.6, label="Matched control times")
for yy, o, n in zip(y, d["rate_observed_pct"], d["rate_null_pct"]):
    ax.text(o + 0.35, yy + 0.19, f"{o:.1f}", va="center", fontsize=6.6, color=INK2)
    ax.text(n + 0.35, yy - 0.19, f"{n:.1f}", va="center", fontsize=6.6, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels([SHORT[c] for c in order], fontsize=7.2)
ax.set_xlabel("Interruptions with a procedure in window (%)")
ax.set_xlim(0, 20)
ax.xaxis.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
ax.legend(loc="center right", frameon=False, handlelength=1.5,
          bbox_to_anchor=(1.0, 0.42))
ax.set_title("Observed and background rate\n(classes assessed non-exclusively)",
             loc="left", fontsize=8.3, pad=8)
panel(ax, "A", dx=-0.42)

# ------------------------------------------------------------------ B
ax = fig.add_subplot(gs[0, 1])
sig = d["rate_null_excluded"].values
cols = [AQUA if s else MUTED for s in sig]
ax.barh(y, d["rate_excess_pp"], 0.5, color=cols, edgecolor="white", lw=0.6)
for b, s in zip(ax.patches, sig):
    if not s:
        b.set_hatch("\\\\\\")
ax.errorbar(d["rate_excess_pp"], y,
            xerr=[d["rate_excess_pp"] - d["rate_excess_lo"],
                  d["rate_excess_hi"] - d["rate_excess_pp"]],
            fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
for yy, v, s, hi in zip(y, d["rate_excess_pp"], sig, d["rate_excess_hi"]):
    ax.text(hi + 0.35, yy, f"{v:+.1f}{'*' if s else ''}", va="center",
            fontsize=7.2, fontweight="bold" if s else "normal", color=INK)
ax.axvline(0, color=INK, lw=0.9)
ax.set_yticks(y)
ax.set_yticklabels([SHORT[c] for c in order], fontsize=7.2)
ax.set_xlabel("Excess over background, pp (95% CI)")
ax.set_xlim(-1.6, 8.6)
ax.xaxis.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
ax.set_title("Excess over background\n*interval excludes zero", loc="left",
             fontsize=8.3, pad=10)
panel(ax, "B", dx=-0.34)

# ------------------------------------------------------------------ C
ax = fig.add_subplot(gs[1, :])
v = ND["null_attr_pct"].values
ax.hist(v, bins=44, color=MUTED, alpha=0.75, edgecolor="white", linewidth=0.4,
        label=f"Matched control times ({len(v):,} replicates)")
obs = C["rate"]["obs_pct"]
ax.axvline(obs, color=ORANGE, lw=2.0)
ax.annotate(f"Observed {obs}%\np<0.001", xy=(obs, ax.get_ylim()[1] * 0.60),
            xytext=(obs - 3.4, ax.get_ylim()[1] * 0.86), fontsize=8,
            fontweight="bold", ha="right", color=INK,
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.0))
ax.text(v.max() + 0.25, ax.get_ylim()[1] * 0.22,
        f"highest of {len(v):,}\ncontrol replicates\n{v.max():.1f}%",
        fontsize=6.6, color=INK2, ha="left", va="center")
ax.set_xlabel("Interruptions with a procedure of any prespecified class in window (%)")
ax.set_ylabel("Replicates")
ax.set_xlim(v.min() - 0.8, obs + 1.4)
ax.yaxis.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False)
ax.set_title("No control replicate reached the observed rate", loc="left",
             fontsize=8.3, pad=10)
panel(ax, "C", dx=-0.075, dy=1.13)

for ext, dpi in (("png", 300), ("pdf", 300), ("tif", 300)):
    kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tif" else {}
    fig.savefig(FIG / f"figure2_attribution_bmjqs.{ext}", facecolor="white", dpi=dpi, **kw)
plt.close(fig)
print("wrote figure2_attribution_bmjqs (png/pdf/tif)")
