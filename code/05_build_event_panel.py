"""Step 5: the final dataset. One row = one addition x anchor (announce / effective) x event day.

Day 0, on the SPY trading calendar:
  announce:  S&P publishes after the 4pm close (every release since 2022 is stamped 17:00-19:59 ET),
             so day 0 is the next trading day. A release before the open would be day 0 = that day.
             Only the 2022+ release sample has announcement times. History additions (Key Dev,
             2001-2021) get the effective anchor only.
  effective: changes are "effective prior to the open" on the effective date, so S&P implements them
             at the close of the last trading day BEFORE that date, and index funds buy in that
             closing auction. Day 0 is that rebalance day, so the day-0 return (close -1 to close 0)
             ends at the price index funds pay, and day +1 is the first day as a member.
             See docs/effective_day_convention.md (changed after Checkpoint 1 feedback, spec #2).
Market model: alpha and beta from trading days EST_WINDOW relative to the ANNOUNCEMENT day 0, used
for both anchors, so the estimation window never contains the news. History additions have no
announcement date, so their window is EST_WINDOW relative to the effective day 0 (est_anchor column).

Outputs:
  data/clean/event_panel.csv     key: (event_id, anchor, event_day)
  outputs/car_windows.csv        one row per addition x anchor: CAR over standard windows
  outputs/dropped_short_history.csv   additions dropped for fewer than MIN_EST_DAYS estimation days
"""
import numpy as np
import pandas as pd

from config import CLEAN, EST_WINDOW, EVENT_WINDOW, MARKET, MIN_EST_DAYS, OUTPUTS, RAW

PANEL_OUT = CLEAN / "event_panel.csv"
WINDOWS_OUT = OUTPUTS / "car_windows.csv"
DROPPED_OUT = OUTPUTS / "dropped_short_history.csv"
MARKET_CLOSE_HOUR = 16
CAR_WINDOWS = {"car_m1_p1": (-1, 1), "car_0_p1": (0, 1), "car_m10_p10": EVENT_WINDOW}
EVENT_COLUMNS = ["event_id", "sample", "era", "ticker", "permno", "announce_et", "effective_date",
                 "batch_size", "ret_source"]

events = pd.read_csv(CLEAN / "events.csv", parse_dates=["announce_et", "effective_date", "rebalance_day"])
stock_returns = pd.read_parquet(CLEAN / "stock_returns.parquet")
market_returns = (pd.read_csv(RAW / "prices.csv", index_col="Date", parse_dates=True)[MARKET]
                  .pct_change(fill_method=None)
                  .rename("mkt_ret"))
trading_days = market_returns.index[market_returns.notna()]


def rebalance_day(effective_date):
    """Last trading day strictly before the effective date: the close where index funds trade."""
    return trading_days[trading_days.searchsorted(effective_date) - 1]


def announce_day0(announce_et):
    """After the close: the next trading day. Otherwise: the first trading day on or after the release date."""
    after_close = announce_et.hour >= MARKET_CLOSE_HOUR
    return trading_days[trading_days.searchsorted(announce_et.normalize(), side="right" if after_close else "left")]


def event_rows(event):
    """Market-model ARs for one addition, around each of its day 0s."""
    stock = (stock_returns.query("event_id == @event.event_id")
             .set_index("date")[["ret"]]
             .join(market_returns, how="inner", validate="one_to_one")
             .dropna())
    day0s = {"effective": rebalance_day(event.effective_date)}
    assert day0s["effective"] == event.rebalance_day  # same rule as step 4 (and 3b, on the CRSP calendar)
    if pd.notna(event.announce_et):
        day0s = {"announce": announce_day0(event.announce_et), **day0s}

    est_anchor = "announce" if "announce" in day0s else "effective"
    pos_est_anchor = trading_days.get_loc(day0s[est_anchor])
    est_days = trading_days[pos_est_anchor + EST_WINDOW[0]: pos_est_anchor + EST_WINDOW[1] + 1]
    est = stock.loc[stock.index.isin(est_days)]
    beta = est["ret"].cov(est["mkt_ret"]) / est["mkt_ret"].var()
    alpha = est["ret"].mean() - beta * est["mkt_ret"].mean()

    rows = []
    for anchor, day0 in day0s.items():
        pos = trading_days.get_loc(day0)
        window = pd.DataFrame({"date": trading_days[pos + EVENT_WINDOW[0]: pos + EVENT_WINDOW[1] + 1]})
        window["event_day"] = np.arange(EVENT_WINDOW[0], EVENT_WINDOW[0] + len(window))
        rows.append(window
                    .merge(stock, left_on="date", right_index=True, how="left", validate="one_to_one")
                    .assign(anchor=anchor, day0=day0))
    gap = (trading_days.get_loc(day0s["effective"]) - trading_days.get_loc(day0s["announce"])
           if "announce" in day0s else np.nan)
    panel = pd.concat(rows, ignore_index=True).assign(
        **{col: getattr(event, col) for col in EVENT_COLUMNS},
        gap_trading_days=gap,
        est_anchor=est_anchor,
        alpha=alpha,
        beta=beta,
        n_est=len(est),
    )
    panel["expected_ret"] = panel["alpha"] + panel["beta"] * panel["mkt_ret"]
    panel["ar"] = panel["ret"] - panel["expected_ret"]
    panel["car_to_date"] = panel.groupby("anchor")["ar"].cumsum()
    return panel


event_panel = pd.concat([event_rows(e) for e in events.itertuples()], ignore_index=True)
event_panel = event_panel[["ticker", "announce_et", "effective_date", "anchor", "day0", "event_day", "date",
                           "ret", "mkt_ret", "alpha", "beta", "n_est", "expected_ret", "ar", "car_to_date",
                           "batch_size", "gap_trading_days",
                           "event_id", "sample", "era", "permno", "ret_source", "est_anchor"]]

# Checks: unique key, full windows, enough estimation days.
assert not event_panel.duplicated(subset=["event_id", "anchor", "event_day"]).any()
window_length = EVENT_WINDOW[1] - EVENT_WINDOW[0] + 1
rows_per_event = event_panel.groupby(["event_id", "anchor"]).size()
print("events with an incomplete window:", rows_per_event[rows_per_event != window_length].index.tolist())
print("missing returns inside the window:", event_panel["ret"].isna().sum())

# Drop events without enough estimation history (mostly spin-offs) and keep a record of them.
dropped = (event_panel.query("n_est < @MIN_EST_DAYS")
           .drop_duplicates("event_id")[["event_id", "sample", "ticker", "announce_et", "effective_date", "n_est"]])
dropped.to_csv(DROPPED_OUT, index=False)
print(f"dropped {len(dropped)} of {event_panel['event_id'].nunique()} additions with fewer than "
      f"{MIN_EST_DAYS} estimation days (e.g. spin-offs): {dropped['event_id'].tolist()}")
event_panel = event_panel.query("n_est >= @MIN_EST_DAYS").reset_index(drop=True)
event_panel.to_csv(PANEL_OUT, index=False)
print(f"saved {PANEL_OUT.name}: {len(event_panel)} rows")

car_by_window = (event_panel
                 .groupby(["event_id", "anchor"])
                 .apply(lambda g: pd.Series({name: g.loc[g["event_day"].between(*days), "ar"].sum()
                                             for name, days in CAR_WINDOWS.items()}))
                 .reset_index())
car_windows = car_by_window.merge(
    event_panel.drop_duplicates(["event_id", "anchor"])
    [["event_id", "anchor", "ticker", "sample", "era", "day0", "beta", "n_est", "batch_size",
      "gap_trading_days", "ret_source"]],
    on=["event_id", "anchor"], how="left", validate="one_to_one")
car_windows.to_csv(WINDOWS_OUT, index=False)
print(car_windows.round({name: 4 for name in [*CAR_WINDOWS, "beta"]}).to_string())
