"""README charts: one message per chart, one highlight colour, direct labels."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
import brand_style as b

ROOT = Path(__file__).resolve().parents[1]
RES, OUT = ROOT / "results", ROOT / "charts"
OUT.mkdir(exist_ok=True)
HL = b.PROJECT["market-entry-investment-case"]
SRC = "10,000 Monte Carlo simulations of demand, pricing and cost; assumptions in model/assumptions.csv"

# Chart 1: chance of a positive five-year NPV by city
mc = pd.read_csv(RES / "monte_carlo_by_city.csv").sort_values("prob_npv_positive", ascending=False)
fig, ax = b.chart(height=4.2, label_in=1.35)
b.hbar(ax, mc.city.tolist(), (mc.prob_npv_positive * 100).tolist(), {0}, lambda v: f"{v:.0f}%", HL)
b.titles(fig, "Halifax is the only city with a real chance of paying back",
         "Chance of a positive five-year NPV for a standalone launch")
b.credit(fig, SRC)
b.save(fig, OUT / "01_chance_of_payback_by_city.png")

# Chart 2: what has to be true for Halifax
w = pd.read_csv(RES / "what_has_to_be_true.csv")
labels = {"All simulations": "Base case", "Courier cost at or below $9.00 per order": "Cheap couriers",
          "Market share at or above 10% by year 3": "High market share", "Both of the above": "Both"}
subs = {"All simulations": "today's assumptions", "Courier cost at or below $9.00 per order": "$9 or less per order",
        "Market share at or above 10% by year 3": "10% or more by year 3", "Both of the above": "both conditions hold"}
hi = list(w.condition).index("Courier cost at or below $9.00 per order")
fig, ax = b.chart(height=4.2, label_in=1.75)
b.hbar(ax, w.condition.map(labels).tolist(), (w.expected_npv / 1e6).tolist(), {hi},
       lambda v: f"{'+' if v > 0 else '-'}${abs(v):.2f}M", HL,
       sublabels=w.condition.map(subs).tolist())
b.titles(fig, "Halifax only makes money if couriers cost $9 an order or less",
         "Expected five-year value (NPV) of launching in Halifax, if each condition holds")
b.credit(fig, SRC)
b.save(fig, OUT / "02_what_has_to_be_true.png")
print("Charts saved to charts/")
