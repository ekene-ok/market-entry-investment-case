"""Run the base case, 10,000 Monte Carlo simulations, launch plan comparison and sensitivity."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from model.investment_model import load, draw, mode_inputs, city_cash_flows, YEARS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
N, SEED = 10_000, 7
a, cities = load()
POP = dict(zip(cities.city, cities.population_2021))
NB = ["Moncton, NB", "Saint John, NB", "Fredericton, NB"]

PLANS = {
    "Halifax only": {"Halifax, NS": 1.0},
    "Halifax + St. John's": {"Halifax, NS": 1.0, "St. John's, NL": 1.0},
    "Halifax + New Brunswick cluster": {"Halifax, NS": 1.0, **{c: "shared" for c in NB}},
    "All five, one team per city": {c: 1.0 for c in POP},
    "All five, shared New Brunswick team": {"Halifax, NS": 1.0, "St. John's, NL": 1.0, **{c: "shared" for c in NB}},
}


def plan_npv(plan: dict, x: dict) -> np.ndarray:
    total = 0
    for city, teams in plan.items():
        share = x["shared_team_multiplier"] / 3 if teams == "shared" else teams
        total = total + city_cash_flows(POP[city], x, teams=share)["npv"]
    return total


# 1. Base case cash flows, each city standalone
rows = []
for city, pop in POP.items():
    r = city_cash_flows(pop, mode_inputs(a))
    for y in range(YEARS):
        rows.append({"city": city, "year": y + 1, "orders": round(r["orders"][0, y]),
                     "revenue": round(r["revenue"][0, y]), "contribution": round(r["contribution"][0, y]),
                     "marketing": round(r["marketing"][0, y]), "team": round(r["team"][0, y]),
                     "cash_flow": round(r["cash"][0, y])})
pd.DataFrame(rows).to_csv(OUT / "base_case_cash_flows.csv", index=False)

# 2. Monte Carlo by city (standalone)
x = draw(a, N, np.random.default_rng(SEED))
mc = []
for city, pop in POP.items():
    r = city_cash_flows(pop, x)
    mc.append({"city": city, "population_2021": pop,
               "base_case_npv": round(city_cash_flows(pop, mode_inputs(a))["npv"][0]),
               "median_npv": round(np.median(r["npv"])), "p10_npv": round(np.percentile(r["npv"], 10)),
               "p90_npv": round(np.percentile(r["npv"], 90)),
               "prob_npv_positive": round((r["npv"] > 0).mean(), 3),
               "prob_payback_within_5_years": round((np.cumsum(r["cash"], axis=1)[:, -1] > 0).mean(), 3),
               "base_case_year3_orders": round(city_cash_flows(pop, mode_inputs(a))["orders"][0, 2])})
mc = pd.DataFrame(mc)
mc.to_csv(OUT / "monte_carlo_by_city.csv", index=False)

# 3. Launch plans
pl = []
for name, plan in PLANS.items():
    v = plan_npv(plan, x)
    pl.append({"plan": name, "base_case_npv": round(plan_npv(plan, mode_inputs(a))[0]),
               "median_npv": round(np.median(v)), "p10_npv": round(np.percentile(v, 10)),
               "p90_npv": round(np.percentile(v, 90)), "prob_npv_positive": round((v > 0).mean(), 3),
               "expected_npv": round(v.mean())})
pl = pd.DataFrame(pl).sort_values("median_npv", ascending=False)
pl.to_csv(OUT / "plan_comparison.csv", index=False)
best = pl.iloc[0]["plan"]

# 3b. What has to be true for Halifax: outcomes when key inputs land in a given range.
from model.investment_model import DISC
full = city_cash_flows(POP["Halifax, NS"], x)["npv"]
conds = {
    "All simulations": np.ones(N, bool),
    "Courier cost at or below $9.00 per order": x["courier_cost"] <= 9.0,
    "Market share at or above 10% by year 3": x["market_share_year3"] >= 0.10,
    "Both of the above": (x["courier_cost"] <= 9.0) & (x["market_share_year3"] >= 0.10),
}
wht = pd.DataFrame([{"condition": k, "share_of_simulations": round(m.mean(), 3),
                     "prob_npv_positive": round((full[m] > 0).mean(), 3),
                     "expected_npv": round(full[m].mean()), "median_npv": round(np.median(full[m]))}
                    for k, m in conds.items()])
wht.to_csv(OUT / "what_has_to_be_true.csv", index=False)

# 4. Sensitivity of the best plan: swing each input from low to high, others at most likely
tor = []
for p, r in a.iterrows():
    lo, hi = mode_inputs(a), mode_inputs(a)
    lo[p], hi[p] = np.array([r["low"]]), np.array([r["high"]])
    v_lo, v_hi = plan_npv(PLANS[best], lo)[0], plan_npv(PLANS[best], hi)[0]
    tor.append({"input": p, "low": r["low"], "high": r["high"], "npv_at_low": round(v_lo),
                "npv_at_high": round(v_hi), "swing": round(abs(v_hi - v_lo))})
tor = pd.DataFrame(tor).sort_values("swing", ascending=False)
tor.to_csv(OUT / "sensitivity_tornado.csv", index=False)

# 5. Break-even year-3 market share for the best plan
lo_s, hi_s = 0.001, 0.5
for _ in range(60):
    mid = (lo_s + hi_s) / 2
    m = mode_inputs(a); m["market_share_year3"] = np.array([mid])
    lo_s, hi_s = (mid, hi_s) if plan_npv(PLANS[best], m)[0] < 0 else (lo_s, mid)
pd.DataFrame([{"plan": best, "break_even_market_share_year3": round(hi_s, 4)}]).to_csv(OUT / "break_even.csv", index=False)

pd.set_option("display.width", 220)
print(mc.to_string(index=False))
print(pl.to_string(index=False))
print(tor.to_string(index=False))
print(wht.to_string(index=False))
print("best:", best, "break-even share:", round(hi_s, 4))
print("contribution per order (mode):", round(city_cash_flows(1, mode_inputs(a))["contribution_per_order"][0], 2))
