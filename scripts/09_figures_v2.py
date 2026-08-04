"""N2 step 09 - Frontiers in Nutrition figure set (v2).

Changes from v1: panel labels (A/B/C), bootstrap CIs on all attribution estimates,
circular-shift null replaces the biased simple shift, new deficit-decomposition
panel, new empirical-null panel.

Palette: slots 1-3 of the dataviz reference categorical palette, unmodified
(#2a78d6, #eb6834, #1baf7a) - documented there as all-pairs validated in light mode.
Grayscale-safe via hatch + direct labels.
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
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top", ha="left", color=INK)


def save(fig, name):
    """Write every format. pil_kwargs is TIFF-only - the PDF backend rejects it."""
    for ext in ("png", "pdf", "tif"):
        kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tif" else {}
        fig.savefig(FIG / f"{name}.{ext}", facecolor="white", **kw)
    plt.close(fig)
    print(f"  wrote {name} (png/pdf/tif)", flush=True)


adq = pd.read_csv(OUT / "table2_delivery_adequacy.csv")
ci = pd.read_csv(OUT / "table7_attribution_ci.csv")
ex = pd.read_csv(OUT / "table5_excess_fasting.csv")
nullд = pd.read_csv(OUT / "null_distribution.csv")
st = json.load(open(OUT / "strengthen_results.json"))
res = json.load(open(OUT / "main_results.json"))

SHORT = {"P1": "Airway /\nsedation", "P2": "GI\nendoscopic",
         "P3": "Off-unit\ntransport", "P4": "Bedside\ninvasive",
         "P5": "Renal\nreplacement", "P0": "Bedside diagnostics\n(negative control)"}


def parse_ci(s):
    s = str(s).replace("−", "-")
    if " to " in s:
        a, b = s.split(" to ")
    else:
        a, b = s.rsplit("-", 1) if s.count("-") == 1 else s.split("-", 1)
    return float(a), float(b)


# ============================================== Figure 1 - cohort flow
print("[Fig 1] cohort flow", flush=True)
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

# ==================== Figure 2 - delivery, and where the deficit comes from
print("[Fig 2] delivery + deficit decomposition", flush=True)
fig = plt.figure(figsize=(7.2, 5.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.72], hspace=0.55, wspace=0.28)

ax = fig.add_subplot(gs[0, 0]); panel(ax, "A")
ax.fill_between(adq.icu_day, adq.kcal_pct_q1, adq.kcal_pct_q3, color=BLUE,
                alpha=0.16, lw=0, label="Energy IQR")
ax.plot(adq.icu_day, adq.kcal_pct_median, color=BLUE, lw=2, marker="o", ms=4.5,
        label="Energy", zorder=3)
ax.plot(adq.icu_day, adq.prot_pct_median, color=ORANGE, lw=2, marker="s", ms=4.5,
        ls="--", label="Protein", zorder=3)
ax.axhline(100, color=MUTED, lw=0.8, ls=":")
ax.text(7.05, 102, "target", fontsize=6.8, color=MUTED, va="bottom", ha="right")
ax.set_xlabel("ICU day"); ax.set_ylabel("% of guideline target")
ax.set_title("Delivery never approaches target", loc="left", color=INK)
ax.set_xticks(range(1, 8)); ax.set_ylim(0, 112)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", handlelength=1.6)

ax = fig.add_subplot(gs[0, 1]); panel(ax, "B")
x = np.arange(len(adq))
ax.bar(x - 0.19, adq.pct_days_ge80, 0.36, color=BLUE, label="\u2265 80% of target")
ax.bar(x + 0.19, adq.pct_days_ge100, 0.36, color=AQUA, hatch="///",
       edgecolor="white", lw=0.5, label="\u2265 100% of target")
ax.set_xticks(x); ax.set_xticklabels(adq.icu_day)
ax.set_xlabel("ICU day"); ax.set_ylabel("% of patient-days")
ax.set_title("Few patient-days reach target", loc="left", color=INK)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_ylim(0, 30)
ax.legend(frameon=False, loc="upper left", handlelength=1.6)

ax = fig.add_subplot(gs[1, :]); panel(ax, "C", dx=-0.062, dy=1.16)
tot = st["total_energy_deficit_kcal"]
avoid = st["avoidable_excess_kcal_validated"]
intr = st["kcal_lost_to_interruptions"] - avoid
other = tot - st["kcal_lost_to_interruptions"]
segs = [(other, "Not related to interruption", MUTED, ""),
        (intr, "Interruption, chance or guideline-defensible", "#b9c9dc", "//"),
        (avoid, "Interruption, chance-corrected avoidable", ORANGE, "")]
left = 0
for val, lab, col, hh in segs:
    ax.barh([0], [100 * val / tot], left=100 * left / tot, height=0.42, color=col,
            hatch=hh, edgecolor="white", lw=0.6, label=f"{lab} ({100*val/tot:.1f}%)")
    left += val
ax.set_xlim(0, 100); ax.set_ylim(-0.55, 0.95); ax.set_yticks([])
ax.set_xlabel("% of total energy deficit over ICU days 1\u20137")
ax.set_title(f"Where the {tot/1e6:.1f} million kcal deficit actually comes from",
             loc="left", color=INK)
ax.spines["left"].set_visible(False)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.annotate(f"{100*avoid/tot:.1f}%\n({st['avoidable_kcal_per_stay']:.0f} kcal per stay)",
            xy=(100 - 100 * avoid / tot / 2, 0.22), xytext=(88, 0.72),
            fontsize=7.5, color=INK, fontweight="bold", ha="center",
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.72),
          ncol=1, handlelength=1.6, labelspacing=0.35)
save(fig, "figure2_delivery_and_deficit")

# ==================== Figure 3 - attribution (primary figure)
print("[Fig 3] attribution with CIs and null distribution", flush=True)
c = ci[ci["class"] != "ANY"].copy()
c["lo"], c["hi"] = zip(*c["excess_ci"].map(parse_ci))
c["olo"], c["ohi"] = zip(*c["observed_ci"].map(parse_ci))
c = c.sort_values("excess_pp").reset_index(drop=True)
c["short"] = c["class"].map(SHORT)

fig = plt.figure(figsize=(7.2, 5.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.85], hspace=0.62, wspace=0.30)
y = np.arange(len(c))

ax = fig.add_subplot(gs[0, 0]); panel(ax, "A")
ax.barh(y + 0.19, c.observed_pct, 0.36, color=BLUE, label="Observed",
        xerr=[c.observed_pct - c.olo, c.ohi - c.observed_pct],
        error_kw=dict(ecolor=INK2, elinewidth=0.7, capsize=1.6))
ax.barh(y - 0.19, c.null_pct, 0.36, color=MUTED, hatch="///", edgecolor="white",
        lw=0.5, label="Circular-shift null")
ax.set_yticks(y); ax.set_yticklabels(c.short, fontsize=7)
ax.set_xlabel("% of interruptions with a procedure in window")
ax.set_title("Observed vs chance", loc="left", color=INK, pad=16)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_xlim(0, 21)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2,
          handlelength=1.5, columnspacing=1.0)

ax = fig.add_subplot(gs[0, 1]); panel(ax, "B")
cols = [AQUA if lo > 0 else (ORANGE if hi < 0 else MUTED)
        for lo, hi in zip(c.lo, c.hi)]
ax.barh(y, c.excess_pp, 0.5, color=cols,
        xerr=[c.excess_pp - c.lo, c.hi - c.excess_pp],
        error_kw=dict(ecolor=INK2, elinewidth=0.8, capsize=2))
ax.axvline(0, color=INK, lw=0.9)
ax.set_yticks(y); ax.set_yticklabels([])
ax.set_xlabel("Chance-corrected excess, pp (95% CI)")
ax.set_title("Attribution surviving the null", loc="left", color=INK, pad=16)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
for yi, (v, lo, hi) in enumerate(zip(c.excess_pp, c.lo, c.hi)):
    sig = "" if lo < 0 < hi else "*"
    if v < 0:
        ax.text(lo - 0.3, yi, f"{v:+.1f}{sig}".replace("-", "−"), va="center",
                ha="right", fontsize=7.5, color=INK, fontweight="bold")
    else:
        ax.text(hi + 0.3, yi, f"{v:+.1f}{sig}", va="center", ha="left",
                fontsize=7.5, color=INK, fontweight="bold")
ax.set_xlim(-5.6, 9.8)

ax = fig.add_subplot(gs[1, :]); panel(ax, "C", dx=-0.062, dy=1.14)
nd = nullд["null_attr_pct"].values
ax.hist(nd, bins=14, color=MUTED, alpha=0.55, edgecolor="white", lw=0.6,
        label=f"Circular-shift null ({len(nd)} shifts, |shift| 12\u201396 h)")
obsv = res["any_class_observed_pct"]
ax.axvline(obsv, color=ORANGE, lw=2.2, zorder=5)
ax.annotate(f"Observed {obsv:.1f}%\nempirical p = {st['empirical_p']:.3f}",
            xy=(obsv, ax.get_ylim()[1] * 0.72), xytext=(obsv - 5.4, ax.get_ylim()[1] * 0.86),
            fontsize=7.8, color=INK, fontweight="bold", ha="right",
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.1))
ax.set_xlabel("% of interruptions attributed to any prespecified procedure class")
ax.set_ylabel("Shifts")
ax.set_title("The observed value against its own null distribution", loc="left", color=INK)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", handlelength=1.5)
save(fig, "figure3_attribution")

# ==================== Figure 4 - excess fasting burden
print("[Fig 4] excess fasting burden", flush=True)
sig = {r["class"]: (parse_ci(r["excess_ci"])[0] > 0) for _, r in ci.iterrows()}
e = ex.copy()
e["validated"] = e["proc_class"].map(lambda k: sig.get(k, False))
e = e.sort_values("excess_total").reset_index(drop=True)
e["short"] = e["proc_class"].map(lambda k: SHORT[k].replace("\n", " "))

fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
for ax, col, lab, ttl, letter in (
    (axes[0], "excess_total", "Excess fasting hours", "Excess fasting time", "A"),
    (axes[1], "excess_kcal_total", "Excess energy loss (kcal)", "Energy not delivered", "B"),
):
    panel(ax, letter, dx=-0.30 if letter == "A" else -0.06)
    yy = np.arange(len(e))
    bars = ax.barh(yy, e[col], 0.6,
                   color=[ORANGE if v else MUTED for v in e.validated],
                   edgecolor="white", lw=0.5)
    for b, v in zip(bars, e.validated):
        if not v:
            b.set_hatch("xxx")
    ax.set_yticks(yy)
    ax.set_yticklabels(e.short if letter == "A" else [], fontsize=7)
    ax.set_xlabel(lab); ax.set_title(ttl, loc="left", color=INK)
    ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
    for yi, v in zip(yy, e[col]):
        ax.text(v * 1.02, yi, f"{v:,.0f}", va="center", fontsize=7, color=INK2)
    ax.set_xlim(0, e[col].max() * 1.25)
h1 = mpl.patches.Patch(facecolor=ORANGE, label="Attribution survives the null (95% CI excludes 0)")
h2 = mpl.patches.Patch(facecolor=MUTED, hatch="xxx", edgecolor="white",
                       label="Chance attribution \u2014 not avoidable loss")
fig.legend(handles=[h1, h2], frameon=False, ncol=1, loc="lower center",
           bbox_to_anchor=(0.5, -0.16), handlelength=1.6)
fig.tight_layout()
save(fig, "figure4_excess_fasting_burden")

print("\nDONE")
