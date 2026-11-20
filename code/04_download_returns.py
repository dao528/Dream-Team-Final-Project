"""Step 4: one event list for both samples, and daily stock returns for every event.

Return sources:
  CRSP (data/raw/wrds/, ret_adj = return including any delisting return) for every event whose
    event window ends by CRSP_END. 2022+ additions are linked to a permno by their ticker in CRSP
    on the announcement date. History additions already have a permno from Key Dev.
  yfinance (adjusted closes) for 2022+ additions whose window runs past CRSP_END, or that have no
    CRSP row at the announcement (spin-offs that were not trading yet).
  One source per event, never mixed inside an event's estimation or event window.
The market is SPY from yfinance for every event (one market proxy across all years). yfinance closes
are downloaded for every 2022+ addition, also the CRSP ones, so 06_hand_check.py can compare sources.

Outputs:
  data/raw/prices.csv              wide: one column per ticker, adjusted Close (yfinance)
  data/clean/events.csv            one row = one addition (key: event_id), both samples
  data/clean/stock_returns.parquet one row = one event x trading day (key: event_id, date); CRSP data, git-ignored
  outputs/yfinance_fallback.csv    one row = one 2022+ addition (all of them, not only v0) that uses
                                   yfinance, with the reason (audit A2)
"""
import pandas as pd
import pyarrow.dataset as ds
import yfinance as yf

from config import (CLEAN, CRSP_DAILY, CRSP_END, EVENT_WINDOW, HISTORY_START, MARKET, OUTPUTS, POC_TICKERS,
                    PRICES_END, RAW, era_of)

PRICES_OUT = RAW / "prices.csv"
FALLBACK_OUT = OUTPUTS / "yfinance_fallback.csv"
EVENTS_OUT = CLEAN / "events.csv"
RETURNS_OUT = CLEAN / "stock_returns.parquet"
CALENDAR_DAYS_BEFORE = 420  # covers the 250-trading-day estimation window before day 0
CALENDAR_DAYS_AFTER = 40  # covers the +10 trading days after the effective day 0
LINK_TOLERANCE = pd.Timedelta(days=10)  # CRSP row for the ticker at most this long before the announcement

# The two samples, in one event-level table. The CRSP link below runs on every 2022+ addition, so
# yfinance_fallback.csv covers the full sample. Prices and returns are pulled for the v0 sample only.
all_release_adds = (pd.read_csv(CLEAN / "additions.csv", parse_dates=["announce_et", "effective_date"])
                    .assign(sample="releases_2022on",
                            event_id=lambda d: d["ticker"] + "_" + d["effective_date"].dt.year.astype(str)))
release_adds = (all_release_adds if POC_TICKERS is None
                else all_release_adds.query("ticker in @POC_TICKERS"))
history_adds = pd.read_csv(CLEAN / "history_additions.csv", parse_dates=["effective_date", "rebalance_day"])
history_adds = history_adds.assign(sample="keydev_history")

# yfinance: SPY for the whole period, plus every 2022+ addition.
tickers = sorted(release_adds["ticker"]) + [MARKET]
price_start = HISTORY_START - pd.Timedelta(days=CALENDAR_DAYS_BEFORE)
# Reuse the cached file only if it has every ticker and the same start and end the code asks for.
cached_dates = (pd.read_csv(PRICES_OUT, usecols=["Date"], parse_dates=["Date"])["Date"]
                if PRICES_OUT.exists() else pd.Series(dtype="datetime64[ns]"))
have_all = (PRICES_OUT.exists()
            and set(tickers) <= set(pd.read_csv(PRICES_OUT, nrows=0).columns)
            and price_start <= cached_dates.min() <= price_start + pd.Timedelta(days=7)
            and PRICES_END - pd.Timedelta(days=7) <= cached_dates.max() < PRICES_END)
if have_all:
    print(f"{PRICES_OUT.name} exists with all {len(tickers)} tickers from {price_start.date()}, skipping download")
else:
    prices = yf.download(tickers, start=price_start, end=PRICES_END, auto_adjust=True, progress=False)["Close"]
    prices.to_csv(PRICES_OUT)
    print(f"saved {PRICES_OUT.name}: {prices.shape[0]} days x {prices.shape[1]} tickers, "
          f"{prices.index.min().date()} to {prices.index.max().date()}")
prices = pd.read_csv(PRICES_OUT, index_col="Date", parse_dates=True)
trading_days = prices.index[prices[MARKET].notna()]

# Link 2022+ additions to a CRSP permno: the permno that had the ticker on the latest CRSP day
# on or before the announcement date.
crsp_tickers = (ds.dataset(CRSP_DAILY)
                .to_table(columns=["permno", "date", "ticker"],
                          filter=ds.field("date") >= all_release_adds["announce_et"].min() - LINK_TOLERANCE)
                .to_pandas()
                .astype({"ticker": str, "date": "datetime64[ns]"}))
assert not crsp_tickers.duplicated(subset=["ticker", "date"]).any()
all_release_adds = (all_release_adds
                    .assign(announce_date=all_release_adds["announce_et"].dt.normalize().astype("datetime64[ns]"))
                    .sort_values("announce_date"))
all_release_adds = pd.merge_asof(
    all_release_adds,
    crsp_tickers.rename(columns={"date": "crsp_link_date"}).sort_values("crsp_link_date"),
    left_on="announce_date", right_on="crsp_link_date", by="ticker",
    direction="backward", tolerance=LINK_TOLERANCE)
# First CRSP day of the ticker after the announcement: shows which unlinked additions were not trading yet.
all_release_adds = pd.merge_asof(
    all_release_adds,
    crsp_tickers[["ticker", "date"]].rename(columns={"date": "first_crsp_day_after"}).sort_values("first_crsp_day_after"),
    left_on="announce_date", right_on="first_crsp_day_after", by="ticker", direction="forward")

# Rebalance day (effective day 0) and the last day of its event window, on the SPY calendar.
all_release_adds["rebalance_day"] = trading_days[trading_days.searchsorted(all_release_adds["effective_date"]) - 1]
all_release_adds["window_end"] = trading_days[trading_days.searchsorted(all_release_adds["rebalance_day"])
                                              + EVENT_WINDOW[1]]
all_release_adds["ret_source"] = "yfinance"
all_release_adds.loc[all_release_adds["permno"].notna() & (all_release_adds["window_end"] <= CRSP_END),
                     "ret_source"] = "crsp"

# Every 2022+ addition that falls back to yfinance, and why (audit A2). Spin-offs and new listings
# that start trading after the announcement have no CRSP row at the announcement. Any other
# addition announced while CRSP runs must link to a permno.
fallback = all_release_adds.query("ret_source == 'yfinance'").copy()
fallback["reason"] = "no CRSP row for the ticker at or after the announcement"
fallback.loc[fallback["first_crsp_day_after"].notna(), "reason"] = "not trading at the announcement (spin-off or new listing)"
fallback.loc[fallback["announce_date"] > CRSP_END, "reason"] = "announced after CRSP ends"
fallback.loc[fallback["permno"].notna(), "reason"] = "event window ends after CRSP ends"
assert not fallback["reason"].eq("no CRSP row for the ticker at or after the announcement").any(), \
    fallback.query("reason.str.startswith('no CRSP')")["ticker"].tolist()
(fallback[["ticker", "company", "announce_et", "effective_date", "window_end", "permno", "first_crsp_day_after",
           "reason"]]
 .sort_values("announce_et")
 .to_csv(FALLBACK_OUT, index=False))
print(f"saved {FALLBACK_OUT.name}: {len(fallback)} of {len(all_release_adds)} 2022+ additions use yfinance")
print(fallback["reason"].value_counts().to_string())

release_adds = all_release_adds[all_release_adds["ticker"].isin(release_adds["ticker"])]
print("v0 2022+ additions by return source:", release_adds["ret_source"].value_counts().to_dict())

events = (pd.concat([release_adds, history_adds.assign(ret_source="crsp")], ignore_index=True)
          .astype({"permno": "Int64"}))
events["era"] = events["rebalance_day"].dt.year.map(era_of)
events = events[["event_id", "sample", "era", "ticker", "permno", "company", "announce_et", "effective_date",
                 "rebalance_day", "batch_size", "ret_source", "keydev_date", "date_rule", "passes_volume_filter",
                 "trading_days_to_peak"]]
assert not events.duplicated(subset="event_id").any()
events.to_csv(EVENTS_OUT, index=False)
print(f"saved {EVENTS_OUT.name}: {len(events)} events")
print(events.groupby(["sample", "era", "ret_source"]).size().to_string())

# Daily stock returns, one block per event, from that event's single source.
crsp_events = events.query("ret_source == 'crsp'")
crsp_returns = (ds.dataset(CRSP_DAILY)
                .to_table(columns=["permno", "date", "ret_adj"],
                          filter=ds.field("permno").isin([int(p) for p in crsp_events["permno"].unique()]))
                .to_pandas()
                .astype({"date": "datetime64[ns]"})
                .rename(columns={"ret_adj": "ret"}))
yf_returns = (prices.pct_change(fill_method=None)
              .rename_axis("date")
              .reset_index()
              .melt(id_vars="date", var_name="ticker", value_name="ret")
              .dropna(subset=["ret"]))


def event_returns(event):
    """Returns for one event, from (rebalance day - 420 days) to (rebalance day + 40 days)."""
    first = event.rebalance_day - pd.Timedelta(days=CALENDAR_DAYS_BEFORE)
    last = event.rebalance_day + pd.Timedelta(days=CALENDAR_DAYS_AFTER)
    if event.ret_source == "crsp":
        block = crsp_returns.query("permno == @event.permno")
    else:
        block = yf_returns.query("ticker == @event.ticker")
    return (block.query("@first <= date <= @last")[["date", "ret"]]
            .assign(event_id=event.event_id, ret_source=event.ret_source))


stock_returns = pd.concat([event_returns(e) for e in events.itertuples()], ignore_index=True)
assert not stock_returns.duplicated(subset=["event_id", "date"]).any()
stock_returns.to_parquet(RETURNS_OUT, index=False)
print(f"saved {RETURNS_OUT.name}: {len(stock_returns)} rows for {stock_returns['event_id'].nunique()} events")
