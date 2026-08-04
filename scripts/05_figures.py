"""N2 step 05 - manuscript figures.

Palette: slots 1-3 of the dataviz reference categorical palette, used unmodified
(#2a78d6 blue, #eb6834 orange, #1baf7a aqua). That file documents this three-slot
subset as all-pairs validated in light mode (CVD dE 9.2, normal-vision dE 24.0).
Print journal target: light surface only, grayscale-safe via hatch + direct labels
so identity is never colour-alone.
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT = ROOT / "03_outputs"
FIG = ROOT / "04_figures"
FIG.mkdir(exist_ok=True)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8a86"
GRID = "#e3e3e0"

mpl.rcParams.update({
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.labelcolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", facecolor="white")
    plt.close(fig)
    print(f"  wrote {name}.png / .pdf", flush=True)


# ==================================================== Figure 1: cohort flow
print("[Fig 1] cohort flow", flush=True)
flow = pd.read_csv(OUT / "cohort_flow.csv")
main = [
    ("ICU stays in MIMIC-IV v3.1", 94458),
    ("First ICU stay per patient", 65366),
    ("ICU length of stay \u2265 48 h", 31143),
    ("\u2265 1 nutrition segment in ICU days 1\u20137", None),
    ("\u2265 2 distinct nutrition days\n(analysis cohort)", 6883),
]
excl = [
    "29,092 repeat ICU stays",
    "34,223 ICU stay < 48 h",
    "24,260 no qualifying nutrition\nsupport in days 1\u20137",
]
fig, ax = plt.subplots(figsize=(5.2, 5.0))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
ys = [9.2, 7.3, 5.4, 3.5, 1.4]
box_x, box_w = 0.4, 5.2
for i, ((lbl, n), y) in enumerate(zip(main, ys)):
    if n is None:
        continue
    txt = f"{lbl}\nn = {n:,}"
    face = "#eaf2fc" if i == len(main) - 1 else "white"
    edge = BLUE if i == len(main) - 1 else MUTED
    ax.add_patch(FancyBboxPatch((box_x, y - 0.55), box_w, 1.1,
                                boxstyle="round,pad=0.06,rounding_size=0.12",
                                facecolor=face, edgecolor=edge,
                                linewidth=1.1 if i == len(main) - 1 else 0.7))
    ax.text(box_x + box_w / 2, y, txt, ha="center", va="center", fontsize=8,
            color=INK, linespacing=1.35)
draw_ys = [9.2, 7.3, 5.4, 1.4]
for y0, y1 in zip(draw_ys[:-1], draw_ys[1:]):
    ax.add_patch(FancyArrowPatch((box_x + box_w / 2, y0 - 0.58),
                                 (box_x + box_w / 2, y1 + 0.58),
                                 arrowstyle="-|>", mutation_scale=9,
                                 color=MUTED, linewidth=0.7))
for (y0, y1), e in zip(zip(draw_ys[:-1], draw_ys[1:]), excl):
    ymid = (y0 + y1) / 2
    ax.add_patch(FancyArrowPatch((box_x + box_w / 2, ymid), (box_x + box_w + 0.55, ymid),
                                 arrowstyle="-|>", mutation_scale=8,
                                 color=MUTED, linewidth=0.6))
    ax.text(box_x + box_w + 0.7, ymid, "Excluded:\n" + e, ha="left", va="center",
            fontsize=7, color=INK2, linespacing=1.3)
save(fig, "figure1_cohort_flow")

# ============================ Figure 2: delivery adequacy by ICU day
print("[Fig 2] delivery adequacy", flush=True)
adq = pd.read_csv(OUT / "table2_delivery_adequacy.csv")
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))

ax = axes[0]
ax.fill_between(adq.icu_day, adq.kcal_pct_q1, adq.kcal_pct_q3,
                color=BLUE, alpha=0.16, linewidth=0, label="Energy IQR")
ax.plot(adq.icu_day, adq.kcal_pct_median, color=BLUE, linewidth=2,
        marker="o", markersize=4.5, label="Energy", zorder=3)
ax.plot(adq.icu_day, adq.prot_pct_median, color=ORANGE, linewidth=2,
        marker="s", markersize=4.5, linestyle="--", label="Protein", zorder=3)
ax.axhline(100, color=MUTED, linewidth=0.8, linestyle=":")
ax.text(7.05, 101, "target", fontsize=6.8, color=MUTED, va="bottom", ha="right")
ax.set_xlabel("ICU day"); ax.set_ylabel("% of guideline target")
ax.set_title("Nutrition delivered vs target", loc="left", color=INK)
ax.set_xticks(range(1, 8)); ax.set_ylim(0, 110)
ax.grid(axis="y", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
ax.annotate(f"{adq.kcal_pct_median.iloc[5]:.0f}%", (6, adq.kcal_pct_median.iloc[5]),
            textcoords="offset points", xytext=(2, 7), fontsize=7.5, color=BLUE,
            fontweight="bold")
ax.legend(frameon=False, loc="upper left", handlelength=1.6)

ax = axes[1]
x = np.arange(len(adq))
ax.bar(x - 0.19, adq.pct_days_ge80, 0.36, color=BLUE, label="\u2265 80% of target")
ax.bar(x + 0.19, adq.pct_days_ge100, 0.36, color=AQUA, hatch="///",
       edgecolor="white", linewidth=0.5, label="\u2265 100% of target")
ax.set_xticks(x); ax.set_xticklabels(adq.icu_day)
ax.set_xlabel("ICU day"); ax.set_ylabel("% of patient-days")
ax.set_title("Patient-days reaching target", loc="left", color=INK)
ax.grid(axis="y", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
ax.set_ylim(0, 30)
ax.legend(frameon=False, loc="upper left", handlelength=1.6)
fig.tight_layout()
save(fig, "figure2_delivery_adequacy")

# ================== Figure 3: attribution specificity (primary figure)
print("[Fig 3] attribution specificity", flush=True)
attr = pd.read_csv(OUT / "table4_attribution_specificity.csv")
attr = attr.sort_values("excess_pp", ascending=True).reset_index(drop=True)
short = {"P1": "Airway / sedation", "P2": "GI endoscopic", "P3": "Off-unit transport",
         "P4": "Bedside invasive", "P5": "Renal replacement",
         "P0": "Bedside diagnostics\n(negative control)"}
attr["short"] = attr["class"].map(short)

fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4),
                         gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
y = np.arange(len(attr))
ax.barh(y + 0.19, attr.observed_pct, 0.36, color=BLUE, label="Observed")
ax.barh(y - 0.19, attr.placebo48_pct, 0.36, color=MUTED, hatch="///",
        edgecolor="white", linewidth=0.5, label="Placebo (+48 h shift)")
ax.set_yticks(y); ax.set_yticklabels(attr.short)
ax.set_xlabel("% of interruptions with a procedure in window")
ax.set_title("Observed vs chance attribution", loc="left", color=INK, pad=18)
ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.005),
          ncol=2, handlelength=1.6, columnspacing=1.2)
for yi, o in zip(y, attr.observed_pct):
    ax.text(o + 0.35, yi + 0.19, f"{o:.1f}", va="center", fontsize=7, color=INK2)
ax.set_xlim(0, 19)

ax = axes[1]
cols = [AQUA if v > 0.5 else MUTED for v in attr.excess_pp]
ax.barh(y, attr.excess_pp, 0.5, color=cols)
ax.axvline(0, color=INK2, linewidth=0.8)
ax.set_yticks(y); ax.set_yticklabels([])
ax.set_xlabel("Chance-corrected excess (pp)")
ax.set_title("Attribution surviving the placebo test", loc="left", color=INK)
ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
for yi, v in zip(y, attr.excess_pp):
    ax.text(v + (0.16 if v >= 0 else -0.16), yi, f"{v:+.1f}",
            va="center", ha="left" if v >= 0 else "right",
            fontsize=7.5, color=INK, fontweight="bold")
ax.set_xlim(-1.9, 9.2)
fig.tight_layout()
save(fig, "figure3_attribution_specificity")

# ============ Figure 4: naive vs chance-corrected avoidable fasting burden
print("[Fig 4] excess fasting burden", flush=True)
ex = pd.read_csv(OUT / "table5_excess_fasting.csv")
sp = attr.set_index("class")["excess_pp"].to_dict()
ex["validated"] = ex["proc_class"].map(lambda c: sp.get(c, 0) > 0.5)
ex = ex.sort_values("excess_total", ascending=True).reset_index(drop=True)
ex["short"] = ex["proc_class"].map(short)

fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
for ax, col, lab, ttl in (
    (axes[0], "excess_total", "Excess fasting hours", "Excess fasting time"),
    (axes[1], "excess_kcal_total", "Excess energy loss (kcal)", "Energy not delivered"),
):
    y = np.arange(len(ex))
    colors = [ORANGE if v else MUTED for v in ex.validated]
    hatches = ["" if v else "xxx" for v in ex.validated]
    bars = ax.barh(y, ex[col], 0.6, color=colors, edgecolor="white", linewidth=0.5)
    for b, h in zip(bars, hatches):
        b.set_hatch(h)
    ax.set_yticks(y); ax.set_yticklabels(ex.short if ax is axes[0] else [])
    ax.set_xlabel(lab)
    ax.set_title(ttl, loc="left", color=INK)
    ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    for yi, v in zip(y, ex[col]):
        ax.text(v * 1.02, yi, f"{v:,.0f}", va="center", fontsize=7, color=INK2)
    ax.set_xlim(0, ex[col].max() * 1.22)
h1 = mpl.patches.Patch(facecolor=ORANGE, label="Attribution survives placebo test")
h2 = mpl.patches.Patch(facecolor=MUTED, hatch="xxx", edgecolor="white",
                       label="Chance attribution (not avoidable loss)")
fig.legend(handles=[h1, h2], frameon=False, ncol=2, loc="lower center",
           bbox_to_anchor=(0.5, -0.06), handlelength=1.6)
fig.tight_layout()
save(fig, "figure4_excess_fasting_burden")

print("\nDONE")
