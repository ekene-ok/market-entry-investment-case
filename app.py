"""Interactive version of the market entry investment case.

Run locally:  streamlit run app.py
Change the assumptions on the left; the model reruns 5,000 Monte Carlo simulations instantly.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st
from model.investment_model import load, city_cash_flows, YEARS

st.set_page_config(page_title="Market Entry Investment Case", layout="wide")
HIGHLIGHT, CONTEXT, INK, INK2 = "#c94f86", "#d9d8d3", "#1a1a1a", "#6b6a66"
N, SEED = 5_000, 7
NB = ["Moncton, NB", "Saint John, NB", "Fredericton, NB"]

a, cities = load()
POP = dict(zip(cities.city, cities.population_2021))

st.title("Should a delivery platform launch in Atlantic Canada?")
st.write("A five-year investment case for five cities. Change the assumptions on the left and the model reruns "
         f"{N:,} simulations of demand, pricing and cost. [Read the full analysis]"
         "(https://github.com/ekene-ok/market-entry-investment-case)")

# Sidebar: the inputs that move the answer most. Each slider sets the most likely value;
# the low and high ends keep the same proportions as the original assumptions.
st.sidebar.header("Your assumptions")
SLIDERS = {
    "market_share_year3": ("Market share by year 3 (%)", 2.0, 25.0, 0.5, 100),
    "courier_cost": ("Courier cost per order ($)", 6.0, 14.0, 0.1, 1),
    "merchant_commission": ("Merchant commission (%)", 12.0, 32.0, 0.5, 100),
    "consumer_fees": ("Consumer fees per order ($)", 2.0, 10.0, 0.25, 1),
    "orders_per_user_month": ("Orders per regular user per month", 1.0, 6.0, 0.1, 1),
    "launch_marketing_per_resident": ("Year-1 marketing per resident ($)", 0.0, 10.0, 0.5, 1),
}
chosen = {}
for key, (label, lo, hi, step, scale) in SLIDERS.items():
    default = float(a.loc[key, "mode"]) * scale
    chosen[key] = st.sidebar.slider(label, lo, hi, round(default, 2), step) / scale
st.sidebar.caption("Low and high values move with the most likely value, keeping the original spread.")

st.sidebar.header("Launch plan")
picked = st.sidebar.multiselect("Cities", list(POP), default=["Halifax, NS"])
shared_nb = st.sidebar.checkbox("One shared team for the New Brunswick cities", value=True)


def inputs(n, rng):
    x = {}
    for p, r in a.iterrows():
        lo, mode, hi = r["low"], r["mode"], r["high"]
        if p in chosen:
            k = chosen[p] / mode if mode else 1
            lo, mode, hi = lo * k, chosen[p], hi * k
        x[p] = rng.triangular(lo, mode, hi, n) if hi > lo else np.full(n, mode)
    return x


def mode_inputs():
    return {p: np.array([chosen.get(p, r["mode"])]) for p, r in a.iterrows()}


def plan_npv(x, plan):
    nb_in_plan = [c for c in plan if c in NB]
    total = 0
    for c in plan:
        share = (x["shared_team_multiplier"] / len(nb_in_plan)) if (shared_nb and c in NB and len(nb_in_plan) > 1) else 1.0
        total = total + city_cash_flows(POP[c], x, teams=share)["npv"]
    return total


if not picked:
    st.info("Pick at least one city on the left.")
    st.stop()

def money(v, d=2):
    return f"{'-' if v < 0 else ''}${abs(v) / 1e6:,.{d}f}M"


x = inputs(N, np.random.default_rng(SEED))
npv = plan_npv(x, picked)
base = plan_npv(mode_inputs(), picked)[0]
p_pos = (npv > 0).mean()

c1, c2, c3 = st.columns(3)
c1.metric("Chance of a positive NPV", f"{p_pos:.0%}")
c2.metric("Expected NPV", money(npv.mean()))
c3.metric("Most likely case NPV", money(base))
st.caption(f"Likely range (10th to 90th percentile): {money(np.percentile(npv, 10), 1)} to {money(np.percentile(npv, 90), 1)}. "
           f"The app runs {N:,} simulations, so results can differ slightly from the 10,000-run analysis in the repository.")

left, right = st.columns(2)

# Chart 1: distribution of outcomes, positive outcomes highlighted
with left:
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    vals = npv / 1e6
    bins = np.linspace(np.percentile(vals, 0.5), np.percentile(vals, 99.5), 40)
    counts, edges = np.histogram(vals, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    ax.bar(centers, counts, width=np.diff(edges) * 0.9, color=[HIGHLIGHT if c > 0 else CONTEXT for c in centers])
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.set_yticks([])
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.set_xlabel("Five-year NPV ($ millions)", color=INK2)
    ax.set_title(f"{p_pos:.0%} of simulated outcomes pay back", loc="left", fontsize=13, fontweight="bold", color=INK)
    st.pyplot(fig)

# Chart 2: chance of payback for each city on its own, with current assumptions
with right:
    rows = [(c, (city_cash_flows(POP[c], x)["npv"] > 0).mean()) for c in POP]
    rows.sort(key=lambda r: r[1])
    best = max(rows, key=lambda r: r[1])[0]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.barh([r[0] for r in rows], [r[1] * 100 for r in rows], height=0.55,
            color=[HIGHLIGHT if r[0] == best else CONTEXT for r in rows])
    for y, (c, v) in enumerate(rows):
        ax.text(v * 100 + 1, y, f"{v:.0%}", va="center", color=INK if c == best else INK2,
                fontweight="bold" if c == best else "normal")
    ax.set_xticks([])
    ax.set_xlim(0, 115)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title(f"{best.split(',')[0]} has the best odds on its own", loc="left", fontsize=13,
                 fontweight="bold", color=INK)
    st.pyplot(fig)

# Most likely case cash flows for the plan
st.subheader("Most likely case, year by year")
m = mode_inputs()
rows = []
for c in picked:
    r = city_cash_flows(POP[c], m)
    for y in range(YEARS):
        rows.append({"Year": y + 1, "Orders": r["orders"][0, y], "Revenue": r["revenue"][0, y],
                     "Contribution": r["contribution"][0, y], "Marketing": r["marketing"][0, y],
                     "Local team": r["team"][0, y]})
cf = pd.DataFrame(rows).groupby("Year").sum()
if shared_nb and len([c for c in picked if c in NB]) > 1:
    n_nb = len([c for c in picked if c in NB])
    cf["Local team"] -= (n_nb - float(m["shared_team_multiplier"][0])) * float(m["fixed_cost_per_city"][0])
cf["Cash flow"] = cf["Contribution"] - cf["Marketing"] - cf["Local team"]
fmt = cf.copy()
fmt["Orders"] = fmt["Orders"].map("{:,.0f}".format)
for col in ["Revenue", "Contribution", "Marketing", "Local team", "Cash flow"]:
    fmt[col] = fmt[col].map(money)
st.dataframe(fmt, width="stretch")
st.caption("Sources: Statistics Canada 2021 Census; Dalhousie Agri-Food Analytics Lab survey (2025); DoorDash merchant "
           "research; Vividata (2020). Other inputs are labelled planning assumptions. See the repository for details.")
