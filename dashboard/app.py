"""Dashboard skeleton (Checkpoint 2, v0).

Run it locally from the repo root:
    streamlit run dashboard/app.py

It only reads files the pipeline already wrote (run_all.py), so it never touches
the licensed WRDS data:
    data/clean/event_panel.csv     one row = event x anchor x trading day (-10..+10)
    outputs/car_windows.csv        one row = event x anchor, with CARs over 3 windows
    outputs/car_summary.csv        mean CAR and t-test by sample x anchor x era x window
    outputs/fig_mean_car_by_era.png
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "clean" / "event_panel.csv"
WINDOWS = ROOT / "outputs" / "car_windows.csv"
SUMMARY = ROOT / "outputs" / "car_summary.csv"
FIGURE = ROOT / "outputs" / "fig_mean_car_by_era.png"

st.set_page_config(page_title="The Disappearing Index Effect", layout="wide")


@st.cache_data
def load():
    panel = pd.read_csv(PANEL)
    windows = pd.read_csv(WINDOWS)
    summary = pd.read_csv(SUMMARY)
    return panel, windows, summary


panel, windows, summary = load()

st.title("The Disappearing Index Effect")
st.caption("Dream Team, FIN 331, Fall 2026. v0: small sample, placeholder text.")

intro, method, results, explore = st.tabs(["Intro", "Methodology", "Results", "Explore"])

# ---------------------------------------------------------------- Intro
with intro:
    st.header("Does a stock still jump when it joins the S&P 500?")
    st.write(
        "PLACEHOLDER. One or two sentences on the question, why it matters, "
        "and who would pay for the answer."
    )

    # One headline example, pulled from the data so it always matches outputs/
    coin = windows.query("event_id == 'COIN_2025' and anchor == 'announce'")
    n_events = windows["event_id"].nunique()
    c1, c2, c3 = st.columns(3)
    c1.metric("Additions in this version", n_events)
    c2.metric("Years covered", f"{panel['era'].min()[:4]}–{panel['era'].max()[-4:]}")
    if not coin.empty:
        c3.metric("Coinbase, 2 days after announcement (CAR[0,+1])",
                  f"{coin['car_0_p1'].iloc[0]:+.1%}")

# ---------------------------------------------------------------- Methodology
with method:
    st.header("Methodology")
    st.write("PLACEHOLDER. Plain-language version of the steps below.")
    st.markdown(
        """
1. **List the additions.** S&P's own press releases (2022 on) give the announcement
   time and the effective date. Capital IQ Key Dev gives effective dates for 2001–2021.
2. **Get daily returns.** CRSP through 2025, yfinance after that.
3. **Two "day 0"s per addition.** *Announce*: the first trading day after S&P's
   release (releases come out after the close). *Effective*: the rebalance close,
   when index funds buy.
4. **Abnormal return** = the stock's return minus what the market model (vs. SPY)
   predicts, using trading days −250 to −30 before the announcement.
5. **Add them up** over short windows (CAR[0,+1], CAR[−1,+1]) and a long one
   (CAR[−10,+10]), then average by era and test whether the average is zero.
"""
    )
    st.subheader("Sample in this version")
    counts = (windows.groupby(["sample", "era", "anchor"])["event_id"]
              .nunique().reset_index(name="additions"))
    st.dataframe(counts, hide_index=True)

# ---------------------------------------------------------------- Results
with results:
    st.header("Results")
    st.write("PLACEHOLDER. The main takeaway in one sentence goes here.")
    if FIGURE.exists():
        st.image(str(FIGURE), caption="Mean CAR by era (outputs/fig_mean_car_by_era.png)")

    st.subheader("Mean CAR by era (outputs/car_summary.csv)")
    window = st.radio("Window", sorted(summary["window"].unique()), horizontal=True)
    table = summary[summary["window"] == window].copy()
    table["mean"] = table["mean"].map("{:+.2%}".format)
    table["t_stat"] = table["t_stat"].round(2)
    table["p_value"] = table["p_value"].round(3)
    st.dataframe(table.drop(columns="window"), hide_index=True)
    st.caption("v0 has only 3 to 5 additions per era, so none of these are reliable yet.")

# ---------------------------------------------------------------- Explore
with explore:
    st.header("Explore one addition")
    labels = (panel[["event_id", "ticker", "era"]].drop_duplicates()
              .sort_values(["era", "ticker"]))
    pick = st.selectbox(
        "Pick an addition",
        labels["event_id"],
        format_func=lambda e: f"{e} ({labels.set_index('event_id').loc[e, 'era']})",
    )
    one = panel[panel["event_id"] == pick]

    chart = (
        alt.Chart(one)
        .mark_line(point=True)
        .encode(
            x=alt.X("event_day:Q", title="Trading days from day 0"),
            y=alt.Y("car_to_date:Q", title="Cumulative abnormal return",
                    axis=alt.Axis(format="%")),
            color=alt.Color("anchor:N", title="Day 0 is the"),
            tooltip=["anchor", "event_day", "date",
                     alt.Tooltip("ar:Q", format="+.2%"),
                     alt.Tooltip("car_to_date:Q", format="+.2%")],
        )
    )
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(strokeDash=[4, 4]).encode(x="x:Q")
    st.altair_chart(chart + rule, width="stretch")

    st.subheader("This addition's CARs (outputs/car_windows.csv)")
    mine = windows[windows["event_id"] == pick][
        ["anchor", "day0", "car_m1_p1", "car_0_p1", "car_m10_p10", "beta", "ret_source"]
    ].copy()
    for col in ["car_m1_p1", "car_0_p1", "car_m10_p10"]:
        mine[col] = mine[col].map("{:+.2%}".format)
    st.dataframe(mine, hide_index=True)
