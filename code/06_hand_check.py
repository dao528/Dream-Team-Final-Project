"""Step 6: recompute numbers by hand, with different code, and compare to the pipeline.

1. COIN, announced 2025-05-12 at 18:00 ET (after the close), so day 0 = 2025-05-13. Recompute beta
   and CAR[0,+1] from the raw CRSP file with np.polyfit and positional indexing.
   News check: Nasdaq/CNBC reported COIN "soars 24%" on May 13, 2025
   (https://www.nasdaq.com/articles/coinbase-soars-24-sp-500-inclusion-what-lies-ahead-etfs).
2. CRSP vs. yfinance: the same stock-days from both sources should agree for the 2022+ additions
   that use CRSP.
3. The effective day 0 rule on the history sample: Tesla, Key Dev date 2020-12-21. Its record
   closing auction was Friday 2020-12-18 (docs/effective_day_convention.md). Recompute the CRSP
   volume peak by hand and check that the rule in 03b (the trading day before the Key Dev date)
   gives that day.
"""
import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from config import CLEAN, CRSP_DAILY, KEYDEV_EVENTS, MARKET, OUTPUTS, RAW

crsp = ds.dataset(CRSP_DAILY)
prices = pd.read_csv(RAW / "prices.csv", index_col="Date", parse_dates=True)
spy_returns = prices[MARKET].pct_change()

# 1. COIN announcement CAR, from the raw CRSP file.
TICKER, DAY0 = "COIN", pd.Timestamp("2025-05-13")
coin = (crsp.to_table(columns=["date", "ret_adj"], filter=ds.field("ticker") == TICKER).to_pandas()
        .astype({"date": "datetime64[ns]"})
        .set_index("date")["ret_adj"])
both = pd.concat({"stock": coin, "spy": spy_returns}, axis=1, join="inner").dropna()
day0_pos = both.index.get_loc(DAY0)
est = both.iloc[day0_pos - 250: day0_pos - 30 + 1]
beta, alpha = np.polyfit(est["spy"], est["stock"], 1)
ar = both["stock"] - (alpha + beta * both["spy"])
car_0_p1_by_hand = ar.iloc[day0_pos: day0_pos + 2].sum()

pipeline = pd.read_csv(OUTPUTS / "car_windows.csv").query('event_id == "COIN_2025" & anchor == "announce"').iloc[0]
panel = pd.read_csv(CLEAN / "event_panel.csv").query('event_id == "COIN_2025" & anchor == "announce"')
print(f"{TICKER} CRSP return on {DAY0.date()}: {coin[DAY0]:.4f}  (news: about +24%)")
print(f"beta      by hand {beta:.4f}   pipeline {pipeline['beta']:.4f}")
print(f"CAR[0,1]  by hand {car_0_p1_by_hand:.4f}   pipeline {pipeline['car_0_p1']:.4f}")
assert pipeline["day0"] == str(DAY0.date())
assert len(est) == pipeline["n_est"]
assert np.isclose(beta, pipeline["beta"]) and np.isclose(car_0_p1_by_hand, pipeline["car_0_p1"])
assert np.isclose(panel.query("event_day == 0")["ret"].iloc[0], coin[DAY0])

# 2. CRSP vs. yfinance on the same stock-days.
events = pd.read_csv(CLEAN / "events.csv")
stock_returns = pd.read_parquet(CLEAN / "stock_returns.parquet")
crsp_release_events = events.query("sample == 'releases_2022on' and ret_source == 'crsp'")
yf_returns = prices.pct_change(fill_method=None)
for event in crsp_release_events.itertuples():
    from_crsp = stock_returns.query("event_id == @event.event_id").set_index("date")["ret"]
    from_yf = yf_returns[event.ticker].reindex(from_crsp.index)
    gap = (from_crsp - from_yf).abs()
    print(f"{event.ticker}: {gap.notna().sum()} days in both sources, correlation "
          f"{from_crsp.corr(from_yf):.4f}, median gap {gap.median() * 1e4:.2f}bp, max gap {gap.max() * 1e4:.1f}bp")
    assert from_crsp.corr(from_yf) > 0.99
assert abs(coin[DAY0] - yf_returns.loc[DAY0, TICKER]) < 0.001

# 3. Tesla: CRSP volume peak vs. the day 0 rule.
keydev_date = pd.Timestamp("2020-12-21")
tesla_event = (pd.read_parquet(KEYDEV_EVENTS)
               .query("action == 'add' and announcedate == @keydev_date and headline.str.contains('Tesla')"))
assert len(tesla_event) == 1
tesla = (crsp.to_table(columns=["date", "vol"], filter=ds.field("permno") == int(tesla_event["permno"].iloc[0]))
         .to_pandas()
         .astype({"date": "datetime64[ns]"})
         .set_index("date")["vol"])
at = tesla.index.searchsorted(keydev_date)
around = tesla.iloc[at - 15: at + 16]
rule_day0 = tesla.index[at - 1]
print(f"TSLA: volume peak {around.idxmax().date()} ({around.max() / around.median():.1f}x the median), "
      f"rule gives day 0 = {rule_day0.date()}")
assert around.idxmax() == rule_day0 == pd.Timestamp("2020-12-18")
print("hand checks passed")
