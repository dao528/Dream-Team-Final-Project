"""Step 8: put the CARs in economic terms (audit finding A7).

For each event x anchor in outputs/car_windows.csv:
- market value on the trading day before day 0, from CRSP (mktcap is in $ thousands).
  2026 events have no CRSP data yet, so they use the yfinance close on day -1 times the last CRSP
  share count (2025-12-31). CRSP counts only the listed share class, so firms with an unlisted
  class (COIN's class B) are understated.
- dollar CAR[0,+1] = CAR[0,+1] x market value: how much value the two days added or removed.
- quoted bid-ask spread on day -1 (CRSP bid and ask), a rough cost of one round trip for a
  trader. 2026 events use the median over the last 20 CRSP days of 2025.
For the 2022+ announcement rows, also split the announcement CAR at the first moment anyone
could trade. S&P publishes after the close, so the day 0 AR starts from a close before the
news; a trader can only buy from the day 0 close on. car_day1_to_rebalance is the CAR from
announcement day +1 through the rebalance close (effective day 0), the window a trader who
buys after the news and sells to the index funds would hold.

Output: outputs/magnitudes.csv  one row = event x anchor (key: event_id, anchor)
"""
import pandas as pd
import pyarrow.dataset as ds

from config import CLEAN, CRSP_DAILY, CRSP_END, OUTPUTS, RAW

OUT = OUTPUTS / "magnitudes.csv"

crsp = ds.dataset(CRSP_DAILY)
events = pd.read_csv(CLEAN / "events.csv")
car_windows = pd.read_csv(OUTPUTS / "car_windows.csv", parse_dates=["day0"])
prices = pd.read_csv(RAW / "prices.csv", index_col="Date", parse_dates=True)
event_panel = pd.read_csv(CLEAN / "event_panel.csv")


def crsp_rows(event):
    """CRSP price, shares, market value and quotes for one event's firm (by ticker if no permno)."""
    by = ds.field("permno") == int(event.permno) if pd.notna(event.permno) else ds.field("ticker") == event.ticker
    rows = (crsp.to_table(columns=["date", "prc", "shrout", "mktcap", "bid", "ask"], filter=by).to_pandas()
            .astype({"date": "datetime64[ns]"}).set_index("date").sort_index())
    priced = rows.dropna(subset=["prc"])  # a few days in the full history sample have no price and no mktcap
    assert ((priced["prc"].abs() * priced["shrout"] - priced["mktcap"]).abs() < 1).all()  # mktcap = |prc| x shrout
    return rows


def quoted_spread(quotes):
    quotes = quotes.query("bid > 0 and ask > 0")
    return ((quotes["ask"] - quotes["bid"]) / ((quotes["ask"] + quotes["bid"]) / 2)).median()


rows = []
for event in car_windows.merge(events[["event_id", "permno"]], on="event_id", how="left",
                               validate="many_to_one").itertuples():
    firm = crsp_rows(event)
    if event.day0 <= CRSP_END:
        day_before = firm[firm.index < event.day0].iloc[[-1]]
        market_value = day_before["mktcap"].iloc[0] * 1000
        spread, source = quoted_spread(day_before), "CRSP, day -1"
    else:
        close = prices[event.ticker][prices.index < event.day0].iloc[-1]
        market_value = close * firm["shrout"].iloc[-1] * 1000
        spread, source = quoted_spread(firm.tail(20)), "yfinance close day -1 x CRSP shares 2025-12-31"
    rows.append({"event_id": event.event_id, "anchor": event.anchor, "sample": event.sample, "era": event.era,
                 "day0": event.day0.date(), "car_0_p1": event.car_0_p1, "market_value_bn": market_value / 1e9,
                 "dollar_car_0_p1_bn": event.car_0_p1 * market_value / 1e9,
                 "quoted_spread": spread, "market_value_source": source})
magnitudes = pd.DataFrame(rows)

# Announcement rows: the day 0 AR (from the close before the news) vs. what a trader could still earn.
announce = car_windows.query("anchor == 'announce'").set_index("event_id")["gap_trading_days"]
split = []
for event_id, gap in announce.items():
    ar = event_panel.query("event_id == @event_id and anchor == 'announce'").set_index("event_day")["ar"]
    split.append({"event_id": event_id, "anchor": "announce", "gap_trading_days": int(gap),
                  "ar_day0": ar.loc[0], "car_day1_to_rebalance": ar.loc[1:int(gap)].sum()})
magnitudes = magnitudes.merge(pd.DataFrame(split), on=["event_id", "anchor"], how="left", validate="one_to_one")
assert not magnitudes.duplicated(subset=["event_id", "anchor"]).any()
magnitudes = magnitudes.sort_values(["sample", "anchor", "day0"])
magnitudes.to_csv(OUT, index=False)

pd.set_option("display.width", 200)
print(magnitudes.drop(columns=["market_value_source", "sample"]).round(4).to_string(index=False))
recent = magnitudes.query("sample == 'releases_2022on'")
print(recent.groupby("anchor")[["car_0_p1", "dollar_car_0_p1_bn", "quoted_spread", "ar_day0",
                                "car_day1_to_rebalance"]].mean().round(4).to_string())
print(f"saved {OUT.name}")
