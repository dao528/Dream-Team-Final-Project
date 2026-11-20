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
4. Announcement times (audit finding A5). Every 2022+ release page stamps its publication time as
   "ITEMDATE: 2025-05-12 18:00:00 EDT". Re-read the stamp from the committed page with a separate
   regex and check that (a) it equals announce_et in additions.csv, (b) its zone label is the one US
   Eastern time uses on that date (EDT in summer, EST in winter, from zoneinfo), so the stamp is
   Eastern time and not UTC, and (c) it is after the 4pm close. Not yet checked against a source
   outside S&P (a news story with the release time): still open.
5. History effective dates against S&P's releases (audit finding A1). The rebalance day in
   outputs/history_dates.csv should be the close the release names. HP and MRNA must match.
   PTC is a known miss: its dates are "ambiguous" (Wikipedia one day before Key Dev), 03b keeps
   Key Dev there, and Key Dev is one day late. RRC (2007): no release found yet, not checked.
"""
import re
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from config import CLEAN, CRSP_DAILY, KEYDEV_EVENTS, MARKET, OUTPUTS, RAW, RELEASE_CACHE

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

# 4. Announcement time stamps, re-read from the committed release pages.
EASTERN = ZoneInfo("America/New_York")
additions = pd.read_csv(CLEAN / "additions.csv", parse_dates=["announce_et"])
for addition in additions.itertuples():
    page = (RELEASE_CACHE / (addition.announce_url.rsplit("/", 1)[1][:150] + ".html")).read_text(encoding="utf-8")
    stamp, zone = re.search(r"ITEMDATE: (\S+ \S+) (E[DS]T)", page).groups()
    stamp = pd.Timestamp(stamp)
    assert stamp == addition.announce_et, addition.ticker
    assert zone == stamp.to_pydatetime().replace(tzinfo=EASTERN).tzname(), f"{addition.ticker}: {zone} on {stamp}"
    assert stamp.hour >= 16, f"{addition.ticker} released before the close"
    if addition.ticker in ("COIN", "DASH", "SMCI"):
        print(f"{addition.ticker}: page stamp {stamp} {zone}, after the close, matches additions.csv")
print(f"announcement stamps: all {len(additions)} are US Eastern, after 16:00, and match additions.csv")

# 5. History effective dates vs. S&P's releases, looked up on 2026-11-20.
#   HP:   S&P release of 2010-02-22, HP replaces IMS Health "after the close of trading on Friday,
#         February 26" (PR Newswire copy, https://marketscreener.com/quote/stock/IMS-HEALTH-INC-14310/news/IMS-HEALTH-USD-Standard-Poor-s-Announces-Changes-to-U-S-Indices-13329415)
#   MRNA: "effective prior to the opening of trading on Wednesday, July 21"
#         (https://press.spglobal.com/2021-07-15-Moderna-Set-to-Join-S-P-500)
#   PTC:  "effective prior to the open of trading on Tuesday, April 20" (https://press.spglobal.com/2021-04-15-PTC-Set-to-Join-S-P-500-Lattice-Semiconductor-Progyny-to-Join-S-P-MidCap-400-Domtar-to-Join-S-P-SmallCap-600)
RELEASE_REBALANCE_DAYS = {"HP": "2010-02-26", "MRNA": "2021-07-20", "PTC": "2021-04-19"}
KNOWN_MISSES = {"PTC"}  # ambiguous dates, 03b keeps Key Dev, which is one day late here
history_dates = pd.read_csv(OUTPUTS / "history_dates.csv", parse_dates=["rebalance_day"])
for ticker, release_day in RELEASE_REBALANCE_DAYS.items():
    release_day = pd.Timestamp(release_day)
    row = history_dates[(history_dates["ticker"] == ticker)
                        & ((history_dates["rebalance_day"] - release_day).abs() < pd.Timedelta(days=30))]
    assert len(row) == 1, ticker
    ours, rule = row["rebalance_day"].iloc[0], row["date_rule"].iloc[0]
    print(f"{ticker}: release rebalance close {release_day.date()}, ours {ours.date()} ({rule})")
    if ticker in KNOWN_MISSES:
        assert rule == "ambiguous" and ours != release_day
    else:
        assert ours == release_day, ticker
print("hand checks passed")
