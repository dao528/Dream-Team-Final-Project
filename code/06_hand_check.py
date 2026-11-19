"""Step 6: recompute numbers by hand, with different code, and compare to the pipeline.

1. COIN, announced 2025-05-12 at 18:00 ET (after the close), so day 0 = 2025-05-13. Recompute beta
   and CAR[0,+1] from the raw CRSP file with np.polyfit and positional indexing.
   News check: Nasdaq/CNBC reported COIN "soars 24%" on May 13, 2025
   (https://www.nasdaq.com/articles/coinbase-soars-24-sp-500-inclusion-what-lies-ahead-etfs).
2. CRSP vs. yfinance: the same stock-days from both sources should agree for the 2022+ additions
   that use CRSP. COIN and DASH pay no dividends, so also compare 2025 for the yfinance-source
   additions (MRVL pays a dividend), to catch a difference in dividend handling.
3. The effective day 0 rule on the history sample: Tesla, Key Dev date 2020-12-21. Its record
   closing auction was Friday 2020-12-18 (docs/effective_day_convention.md). Recompute the CRSP
   volume peak by hand and check that the rule in 03b (the trading day before the Key Dev date)
   gives that day.
4. Announcement times (audit A5). Step 2 reads each release's time from the newsroom page's ITEMDATE
   comment and assumes US Eastern. PR Newswire's own copy of the release, on prnewswire.com, shows the
   time in ET and also a machine-readable UTC timestamp (its "datePublished" tag). If ITEMDATE is
   Eastern time, converting it to UTC must give PR Newswire's UTC time, in winter (EST, UTC-5) and in
   summer (EDT, UTC-4). Values copied by hand from the pages on 2026-11-19. Caveat: PR Newswire is the
   wire service S&P uses, so this checks the time zone and our parsing, not S&P's clock.
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
for ticker in events.query("sample == 'releases_2022on' and ret_source == 'yfinance'")["ticker"]:
    from_crsp = (crsp.to_table(columns=["date", "ret_adj"],
                               filter=(ds.field("ticker") == ticker) & (ds.field("date") >= pd.Timestamp("2025-01-01")))
                 .to_pandas()
                 .astype({"date": "datetime64[ns]"})
                 .set_index("date")["ret_adj"])
    gap = (from_crsp - yf_returns[ticker].reindex(from_crsp.index)).abs()
    print(f"{ticker} 2025: {gap.notna().sum()} days, max gap CRSP vs. yfinance {gap.max() * 1e4:.1f}bp")
    assert gap.notna().sum() > 200 and gap.max() < 0.002

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

# 4. Announcement times: our ITEMDATE vs. PR Newswire's copy of the same release.
PRNEWSWIRE = [  # ticker, time shown on prnewswire.com, its datePublished tag, page
    ("CEG", "Jan 26, 2022, 18:44 ET", "2022-01-26T23:44:00Z",
     "https://www.prnewswire.com/news-releases/constellation-energy-set-to-join-sp-500-others-to-join-sp-midcap-400-and-sp-smallcap-600-301469198.html"),
    ("COIN", "May 12, 2025, 18:00 ET", "2025-05-12T23:00:00+01:00",
     "https://www.prnewswire.com/news-releases/coinbase-global-set-to-join-sp-500-302453020.html"),
    ("MRVL", "Jun 05, 2026, 19:25 ET", "2026-06-06T00:25:00+01:00",
     "https://www.prnewswire.com/news-releases/marvell-technology-and-flex-set-to-join-sp-500-others-to-join-sp-midcap-400-and-sp-smallcap-600-302793159.html"),
]
actions = pd.read_csv(CLEAN / "spdji_sp500_actions.csv", parse_dates=["published_et"]).query('action == "Addition"')
for ticker, prn_et, prn_utc, _ in PRNEWSWIRE:
    ours = actions.loc[actions["ticker"] == ticker, "published_et"].iloc[0]
    ours_utc = ours.tz_localize("America/New_York").tz_convert("UTC")
    theirs_utc = pd.Timestamp(prn_utc).tz_convert("UTC")
    print(f"{ticker}: ITEMDATE {ours} ET = {ours_utc:%Y-%m-%d %H:%M} UTC.  PR Newswire: {prn_et}, "
          f"{theirs_utc:%Y-%m-%d %H:%M} UTC")
    assert ours == pd.to_datetime(prn_et.replace(" ET", ""), format="%b %d, %Y, %H:%M")
    assert ours_utc == theirs_utc
print("hand checks passed")
