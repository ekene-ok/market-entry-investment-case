"""Interactive version of the market entry investment case.

Run locally:  streamlit run app.py
Change the assumptions and the model reruns 5,000 simulations of demand, pricing and cost.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from model.investment_model import load, city_cash_flows, YEARS

st.set_page_config(page_title="Should a delivery app launch in Atlantic Canada?", page_icon="🛵", layout="centered",
                   initial_sidebar_state="collapsed")
HL, GREY, INK, MUTED, RULE = "#c94f86", "#cfccc5", "#1b2a3a", "#5d6672", "#e2e4e8"
FONTS = "'Schibsted Grotesk', Helvetica, Arial, sans-serif"
VFONT = "Schibsted Grotesk, Helvetica, Arial, sans-serif"
N, SEED = 5_000, 7
NB = ["Moncton, NB", "Saint John, NB", "Fredericton, NB"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700&display=swap');
html, body, .stApp, .stMarkdown p, h1, h2, h3, label, button p, input {{ font-family: {FONTS}; }}
header[data-testid="stHeader"], [data-testid="stToolbar"], footer, [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
.block-container {{ padding-top: 2.5rem; max-width: 820px; }}
h1 {{ font-weight: 700; letter-spacing: -0.02em; font-size: 2.4rem; line-height: 1.1; color: {INK}; }}
h2 {{ font-weight: 600; font-size: 1.4rem; color: {INK}; margin-top: 2rem; }}
p, li {{ color: {INK}; font-size: 1.02rem; line-height: 1.55; }}
.sub {{ color: {MUTED}; font-size: 1.1rem; margin-top: -0.6rem; max-width: 62ch; }}
.verdict {{ border-left: 4px solid {HL}; padding: 0.4rem 0 0.4rem 1.1rem; margin: 1.6rem 0 1.2rem; }}
.verdict .big {{ font-size: 1.6rem; font-weight: 600; line-height: 1.25; color: {INK}; }}
.verdict .why {{ color: {MUTED}; margin-top: 0.4rem; }}
.figs {{ display: flex; gap: 2.5rem; flex-wrap: wrap; margin: 0.4rem 0 1rem; }}
.fig .n {{ font-size: 1.7rem; font-weight: 600; color: {INK}; font-variant-numeric: tabular-nums; }}
.fig .l {{ color: {MUTED}; font-size: 0.9rem; max-width: 22ch; line-height: 1.35; }}
.note {{ color: {MUTED}; font-size: 0.9rem; }}
.foot {{ border-top: 1px solid {RULE}; margin-top: 3rem; padding-top: 1rem; color: {MUTED}; font-size: 0.92rem; }}
.foot a {{ color: {INK}; }}
</style>""", unsafe_allow_html=True)

a, cities = load()
POP = dict(zip(cities.city, cities.population_2021))

# Inputs that move the answer most. Each sets the most likely value; low and high keep the original spread.
SLIDERS = {
    "courier_cost": ("Courier cost per order", 6.0, 14.0, 0.1, 1, "$%.2f",
                     "What the platform pays couriers for each delivery, on average"),
    "market_share_year3": ("Share of local delivery orders by year 3", 2.0, 25.0, 0.5, 100, "%.1f%%",
                           "The platform's slice of all food delivery orders in the city"),
    "merchant_commission": ("Commission charged to restaurants", 12.0, 32.0, 0.5, 100, "%.1f%%", None),
    "consumer_fees": ("Fees charged to customers per order", 2.0, 10.0, 0.25, 1, "$%.2f", None),
    "orders_per_user_month": ("Orders per regular customer per month", 1.0, 6.0, 0.1, 1, "%.1f", None),
    "launch_marketing_per_resident": ("First-year marketing per resident", 0.0, 10.0, 0.5, 1, "$%.2f", None),
}
DEFAULTS = {k: round(float(a.loc[k, "mode"]) * v[4], 2) for k, v in SLIDERS.items()}
WHERE = {"Couriers stay at $9 or less": "courier cost stays at $9 an order or less",
         "Cheap couriers and 10%+ share": "courier cost stays at $9 or less and market share reaches 10% or more"}
# Scenarios match the README: keep only the simulated futures where these conditions hold
SCENARIOS = {
    "Today's assumptions": {},
    "Couriers stay at $9 or less": {"courier_cost": ("max", 9.0)},
    "Cheap couriers and 10%+ share": {"courier_cost": ("max", 9.0), "market_share_year3": ("min", 0.10)},
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


st.title("Should a delivery app launch in Atlantic Canada?")
st.markdown("<p class='sub'>A five-year business case for Halifax, St. John's, Moncton, Saint John and Fredericton. "
            "Pick a scenario or change the assumptions, and the case is re-run 5,000 times with realistic "
            "ups and downs in demand, prices and costs.</p>", unsafe_allow_html=True)

scenario = st.segmented_control("Scenario", list(SCENARIOS), key="scenario", default="Today's assumptions") or "Today's assumptions"
picked = st.pills("Cities to launch", list(POP), selection_mode="multi", default=["Halifax, NS"])

with st.expander("Change the assumptions"):
    cols = st.columns(2)
    for i, (key, (label, lo, hi, step, scale, fmt, help_)) in enumerate(SLIDERS.items()):
        cols[i % 2].slider(label, lo, hi, key=key, step=step, format=fmt, help=help_)
    shared_nb = st.checkbox("One shared operations team for the New Brunswick cities", value=True)
    st.markdown("<p class='note'>Each slider sets the most likely value. The model keeps the original range of "
                "possible values around it.</p>", unsafe_allow_html=True)

chosen = {k: st.session_state[k] / SLIDERS[k][4] for k in SLIDERS}


def inputs(n, rng, conditions=None):
    """Draw n futures. With conditions, draw extra and keep only futures where every condition holds."""
    if conditions:
        x = inputs(n * 8, rng)
        keep = np.ones(n * 8, bool)
        for p, (kind, bound) in conditions.items():
            keep &= (x[p] <= bound) if kind == "max" else (x[p] >= bound)
        idx = np.flatnonzero(keep)[:n]
        return {p: v[idx] for p, v in x.items()}
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


def money(v, d=2):
    return f"{'-' if v < 0 else ''}${abs(v) / 1e6:,.{d}f}M"


if not picked:
    st.markdown("<p class='note'>Pick at least one city to see the result.</p>", unsafe_allow_html=True)
    st.stop()

x = inputs(N, np.random.default_rng(SEED), SCENARIOS[scenario])
kept = len(x["courier_cost"])
npv = plan_npv(x, picked)
base = plan_npv(mode_inputs(), picked)[0]
p_pos = (npv > 0).mean()
N_SHOWN = len(npv)
futures = int(round(p_pos * 100))
where = picked[0].split(",")[0] if len(picked) == 1 else f"these {len(picked)} cities"

if p_pos >= 0.5 and npv.mean() > 0:
    big = f"Launch {where}."
    why = f"It makes money over five years in {futures} of 100 simulated futures, and {money(npv.mean())} on average."
elif base > 0:
    big = f"Don't launch {where} yet."
    why = (f"The most likely case makes {money(base)}, but it makes money in only {futures} of 100 simulated futures. "
           "Costs can run much higher than planned, so on average it loses " + money(abs(npv.mean())) + ".")
else:
    big = f"Don't launch {where}."
    why = f"It makes money in only {futures} of 100 simulated futures and loses {money(abs(npv.mean()))} on average."
st.markdown(f"<div class='verdict'><div class='big'>{big}</div><div class='why'>{why}</div></div>", unsafe_allow_html=True)
if SCENARIOS[scenario]:
    st.markdown(f"<p class='note'>Showing only the {kept:,} simulated futures where {WHERE[scenario]}.</p>",
                unsafe_allow_html=True)
st.markdown(f"""<div class='figs'>
<div class='fig'><div class='n'>{futures} of 100</div><div class='l'>simulated futures make money over five years</div></div>
<div class='fig'><div class='n'>{money(npv.mean())}</div><div class='l'>average result over five years, in today's dollars</div></div>
<div class='fig'><div class='n'>{money(base)}</div><div class='l'>result if every assumption lands on its most likely value</div></div>
</div>""", unsafe_allow_html=True)

# 100 futures: one dot per future, coloured when the launch makes money
order = np.sort(npv)[np.linspace(0, N_SHOWN - 1, 100).astype(int)][::-1]
dots = pd.DataFrame({"i": range(100), "v": order})
dots["col"], dots["row"] = dots["i"] % 20, dots["i"] // 20
dots["c"] = np.where(dots["v"] > 0, HL, GREY)
dots["label"] = dots["v"].map(lambda v: f"{money(v)} over five years")
grid = alt.Chart(dots).mark_circle(size=170, opacity=1).encode(
    x=alt.X("col:O", axis=None), y=alt.Y("row:O", axis=None), color=alt.Color("c:N", scale=None),
    tooltip=[alt.Tooltip("label:N", title="This future")])
st.markdown(f"<p style='font-weight:600;font-size:1.1rem;margin:1.2rem 0 0'>{futures} of 100 futures make money</p>"
            "<p class='note'>Each dot is one simulated future, from best to worst. Coloured dots make money over five years.</p>",
            unsafe_allow_html=True)
st.altair_chart(grid.properties(height=170).configure_view(stroke=None), width='stretch')

# Each city on its own, with the same assumptions
st.header("How each city does on its own")
st.markdown("<p class='note'>Chance of making money over five years if the city launched alone, with the assumptions above.</p>",
            unsafe_allow_html=True)
rows = pd.DataFrame([(c, (city_cash_flows(POP[c], x)["npv"] > 0).mean()) for c in POP], columns=["city", "p"])
rows = rows.sort_values("p", ascending=False)
rows["c"] = np.where(rows["p"] == rows["p"].max(), HL, GREY)
rows["t"] = rows["p"].map(lambda p: f"{p:.0%}")
bars = alt.Chart(rows).mark_bar(height=22, cornerRadiusEnd=2).encode(
    y=alt.Y("city:N", sort=None, title=None, axis=alt.Axis(domain=False, ticks=False, labelFontSize=13, labelColor=INK, labelPadding=8, labelFont=VFONT)),
    x=alt.X("p:Q", axis=None, scale=alt.Scale(domain=[0, 1.15])), color=alt.Color("c:N", scale=None))
txt = bars.mark_text(align="left", dx=6, fontSize=13, font=VFONT).encode(text="t:N", color=alt.value(INK))
st.altair_chart((bars + txt).properties(height=200).configure_view(stroke=None), width='stretch')

with st.expander("Most likely case, year by year"):
    m = mode_inputs()
    out = []
    for c in picked:
        r = city_cash_flows(POP[c], m)
        for y in range(YEARS):
            out.append({"Year": y + 1, "Orders": r["orders"][0, y], "Revenue": r["revenue"][0, y],
                        "Left after delivery costs": r["contribution"][0, y], "Marketing": r["marketing"][0, y],
                        "Local team": r["team"][0, y]})
    cf = pd.DataFrame(out).groupby("Year").sum()
    if shared_nb and len([c for c in picked if c in NB]) > 1:
        n_nb = len([c for c in picked if c in NB])
        cf["Local team"] -= (n_nb - float(m["shared_team_multiplier"][0])) * float(m["fixed_cost_per_city"][0])
    cf["Money in minus money out"] = cf["Left after delivery costs"] - cf["Marketing"] - cf["Local team"]
    fmt = cf.copy()
    fmt["Orders"] = fmt["Orders"].map("{:,.0f}".format)
    for col in ["Revenue", "Left after delivery costs", "Marketing", "Local team", "Money in minus money out"]:
        fmt[col] = fmt[col].map(money)
    st.dataframe(fmt, width='stretch')
    st.markdown(f"<p class='note'>Likely range of five-year results (middle 80% of futures): {money(np.percentile(npv, 10), 1)} "
                f"to {money(np.percentile(npv, 90), 1)}. The app runs {N:,} simulations, so results can differ slightly "
                "from the 10,000-run analysis on GitHub.</p>", unsafe_allow_html=True)

st.markdown("""<div class='foot'>Made by Ekene Okafor. Read the <a href="https://github.com/ekene-ok/market-entry-investment-case">full analysis and code on GitHub</a>,
or <a href="https://linkedin.com/in/cnokafor">connect on LinkedIn</a>.<br>
Sources: Statistics Canada 2021 Census; Dalhousie Agri-Food Analytics Lab survey (2025); DoorDash merchant research;
Vividata (2020). Other inputs are labelled planning assumptions in the repository.</div>""", unsafe_allow_html=True)
