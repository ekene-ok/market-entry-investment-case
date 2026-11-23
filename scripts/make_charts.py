"""README charts: one message per chart, one highlight colour, direct labels."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RES, OUT = ROOT / "results", ROOT / "charts"
OUT.mkdir(exist_ok=True)
SURFACE, INK, INK2 = "#ffffff", "#1a1a1a", "#6b6a66"
HIGHLIGHT, CONTEXT = "#c94f86", "#d9d8d3"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})


def titles(fig, title, subtitle):
    fig.text(0.03, 0.97, title, fontsize=15, fontweight="bold", va="top")
    fig.text(0.03, 0.885, subtitle, fontsize=10.5, color=INK2, va="top")


def style_h(ax, hi_idx, n):
    for i, lbl in enumerate(ax.get_yticklabels()):
        lbl.set_color(INK if i == hi_idx else INK2)
        lbl.set_fontweight("bold" if i == hi_idx else "normal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=8)


# Chart 1: chance of a positive five-year NPV by city
mc = pd.read_csv(RES / "monte_carlo_by_city.csv").sort_values("prob_npv_positive")
fig, ax = plt.subplots(figsize=(9, 4.6))
hi = len(mc) - 1
ax.barh(mc["city"], mc["prob_npv_positive"] * 100, height=0.55,
        color=[HIGHLIGHT if i == hi else CONTEXT for i in range(len(mc))])
for y, v in enumerate(mc["prob_npv_positive"]):
    ax.text(v * 100 + 0.8, y, f"{v:.0%}", va="center", fontsize=12 if y == hi else 11,
            fontweight="bold" if y == hi else "normal", color=INK if y == hi else INK2)
style_h(ax, hi, len(mc))
ax.set_xlim(0, 50)
titles(fig, "Halifax is the only city with a real chance of paying back",
       "Chance of a positive five-year NPV for a standalone launch, across 10,000 simulations\n"
       "of demand, pricing and cost.")
fig.subplots_adjust(left=0.2, right=0.97, top=0.72, bottom=0.04)
fig.savefig(OUT / "01_chance_of_payback_by_city.png", dpi=200)
plt.close(fig)

# Chart 2: what has to be true for Halifax
w = pd.read_csv(RES / "what_has_to_be_true.csv")
labels = {"All simulations": "As assumed today",
          "Courier cost at or below $9.00 per order": "Courier cost $9 or less",
          "Market share at or above 10% by year 3": "Share 10% or more",
          "Both of the above": "Both"}
w["label"] = w["condition"].map(labels)
w = w.iloc[::-1].reset_index(drop=True)
hi = int(w.index[w["condition"] == "Courier cost at or below $9.00 per order"][0])
vals = w["expected_npv"] / 1e6
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.barh(w["label"], vals, height=0.55, color=[HIGHLIGHT if i == hi else CONTEXT for i in range(len(w))])
ax.axvline(0, color=INK2, linewidth=0.8)
for y, v in enumerate(vals):
    txt = f"{'+' if v > 0 else '-'}${abs(v):.2f}M"
    ax.text(v + (0.06 if v >= 0 else -0.06), y, txt, va="center", ha="left" if v >= 0 else "right",
            fontsize=12 if y == hi else 11, fontweight="bold" if y == hi else "normal",
            color=INK if y == hi else INK2)
style_h(ax, hi, len(w))
ax.set_xlim(-1.6, 2.0)
titles(fig, "Efficient courier operations turn Halifax from a loss to a gain",
       "Expected five-year NPV of a Halifax launch, overall and in the simulations where each\n"
       "condition holds.")
fig.subplots_adjust(left=0.27, right=0.97, top=0.72, bottom=0.04)
fig.savefig(OUT / "02_what_has_to_be_true.png", dpi=200)
plt.close(fig)
print("Charts saved to charts/")
