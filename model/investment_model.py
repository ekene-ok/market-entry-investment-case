"""Five-year city launch model with Monte Carlo uncertainty.

Per city and year:
  orders        = population x adult share x regular-user share x orders per user x 12
                  x market share x ramp (40% of steady share in year 1, 75% in year 2, 100% from year 3)
  revenue       = orders x (avg order value x commission + consumer fees)
  variable cost = orders x (courier cost + avg order value x other variable cost)
  marketing     = launch marketing per resident x population (full in year 1, half in year 2,
                  a quarter from year 3 to keep the brand visible)
  team cost     = local operations team per year. Cities can share a team (see plans)
  cash flow     = revenue - variable cost - marketing - team cost
NPV discounts five annual cash flows at 10%. No terminal value is added (conservative).

Market-wide inputs are drawn once per simulation and shared by every city (if Atlantic
Canadians order less than assumed, they do so in every city), so city results are correlated
the way they would be in reality. Inputs use triangular distributions (low, most likely, high).
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
YEARS = 5
RAMP = np.array([0.40, 0.75, 1.00, 1.00, 1.00])
MARKETING_DECAY = np.array([1.0, 0.5, 0.25, 0.25, 0.25])
DISCOUNT = 0.10
DISC = 1 / (1 + DISCOUNT) ** np.arange(1, YEARS + 1)


def load():
    a = pd.read_csv(HERE / "assumptions.csv").set_index("parameter")
    c = pd.read_csv(HERE / "cities.csv")
    return a, c


def draw(a: pd.DataFrame, n: int, rng) -> dict:
    return {p: rng.triangular(r["low"], r["mode"], r["high"], n) for p, r in a.iterrows()}


def mode_inputs(a: pd.DataFrame) -> dict:
    return {p: np.array([r["mode"]]) for p, r in a.iterrows()}


def city_cash_flows(pop: float, x: dict, teams: float = 1.0) -> dict:
    """Arrays shaped (n, YEARS) for each line, plus NPVs shaped (n,).
    `teams` = share of a local operations team this city carries (1.0 standalone)."""
    steady_orders = (pop * x["adult_share"] * x["regular_user_share"] * x["orders_per_user_month"] * 12
                     * x["market_share_year3"])[:, None]
    orders = steady_orders * RAMP
    rev_per_order = (x["avg_order_value"] * x["merchant_commission"] + x["consumer_fees"])[:, None]
    var_per_order = (x["courier_cost"] + x["avg_order_value"] * x["other_variable_cost"])[:, None]
    revenue = orders * rev_per_order
    contribution = orders * (rev_per_order - var_per_order)
    marketing = (pop * x["launch_marketing_per_resident"])[:, None] * MARKETING_DECAY
    team = (x["fixed_cost_per_city"] * teams)[:, None] * np.ones(YEARS)
    cash = contribution - marketing - team
    return {"orders": orders, "revenue": revenue, "contribution": contribution, "marketing": marketing,
            "team": team, "cash": cash, "npv": cash @ DISC,
            "contribution_per_order": (rev_per_order - var_per_order)[:, 0]}
