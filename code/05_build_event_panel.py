"""Step 5: the final dataset. One row = one addition x anchor (announce / effective) x event day.

Day 0, on the SPY trading calendar:
  announce:  S&P publishes after the 4pm close (every release since 2022 is stamped 17:00-19:59 ET),
             so day 0 is the next trading day. A release before the open would be day 0 = that day.
  effective: changes are "effective prior to the open" on the effective date, so day 0 is the
             first trading day on or after it. Index funds trade at the close of day -1.
Market model: alpha and beta from trading days EST_WINDOW relative to the ANNOUNCEMENT day 0, used
for both anchors, so the estimation window never contains the news.

Outputs:
  data/clean/event_panel.csv     key: (ticker, anchor, event_day)
  outputs/poc_car_windows.csv    one row per addition x anchor: CAR over standard windows
"""
import numpy as np
import pandas as pd

from config import CLEAN, EST_WINDOW, EVENT_WINDOW, MARKET, MIN_EST_DAYS, OUTPUTS, POC_TICKERS, RAW

PANEL_OUT = CLEAN / "event_panel.csv"
WINDOWS_OUT = OUTPUTS / "poc_car_windows.csv"
MARKET_CLOSE_HOUR = 16
CAR_WINDOWS = {"car_m1_p1": (-1, 1), "car_0_p1": (0, 1), "car_m10_p10": EVENT_WINDOW}

additions = pd.read_csv(CLEAN / "additions.csv", parse_dates=["announce_et", "effective_date"])
if POC_TICKERS is not None:
    additions = additions.query("ticker in @POC_TICKERS")
returns = pd.read_csv(RAW / "prices.csv", index_col="Date", parse_dates=True).pct_change(fill_method=None)
trading_days = returns.index[returns[MARKET].notna()]


def first_trading_day_on_or_after(date):
    return trading_days[trading_days.searchsorted(date)]


def announce_day0(announce_et):
    """After the close: the next trading day. Otherwise: the first trading day on or after the release date."""
    after_close = announce_et.hour >= MARKET_CLOSE_HOUR
    return trading_days[trading_days.searchsorted(announce_et.normalize(), side="right" if after_close else "left")]


def event_rows(addition):
    """Market-model ARs for one addition, around both day 0s."""
    stock = returns[[addition.ticker, MARKET]].dropna().rename(columns={addition.ticker: "ret", MARKET: "mkt_ret"})
    day0s = {"announce": announce_day0(addition.announce_et),
             "effective": first_trading_day_on_or_after(addition.effective_date)}

    pos_announce = trading_days.get_loc(day0s["announce"])
    pos_effective = trading_days.get_loc(day0s["effective"])
    est_days = trading_days[pos_announce + EST_WINDOW[0]: pos_announce + EST_WINDOW[1] + 1]
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
    panel = pd.concat(rows, ignore_index=True).assign(
        ticker=addition.ticker,
        announce_et=addition.announce_et,
        effective_date=addition.effective_date,
        batch_size=addition.batch_size,
        gap_trading_days=pos_effective - pos_announce,
        alpha=alpha,
        beta=beta,
        n_est=len(est),
    )
    panel["expected_ret"] = panel["alpha"] + panel["beta"] * panel["mkt_ret"]
    panel["ar"] = panel["ret"] - panel["expected_ret"]
    panel["car_to_date"] = panel.groupby("anchor")["ar"].cumsum()
    return panel


event_panel = pd.concat([event_rows(a) for a in additions.itertuples()], ignore_index=True)
event_panel = event_panel[["ticker", "announce_et", "effective_date", "anchor", "day0", "event_day", "date",
                           "ret", "mkt_ret", "alpha", "beta", "n_est", "expected_ret", "ar", "car_to_date",
                           "batch_size", "gap_trading_days"]]

# Checks: unique key, full windows, enough estimation days.
assert not event_panel.duplicated(subset=["ticker", "anchor", "event_day"]).any()
window_length = EVENT_WINDOW[1] - EVENT_WINDOW[0] + 1
rows_per_event = event_panel.groupby(["ticker", "anchor"]).size()
print("events with an incomplete window:", rows_per_event[rows_per_event != window_length].index.tolist())
short_est = event_panel.query("n_est < @MIN_EST_DAYS")["ticker"].unique()
print(f"events with fewer than {MIN_EST_DAYS} estimation days (e.g. spin-offs):", list(short_est))
print("missing returns inside the window:", event_panel["ret"].isna().sum())
event_panel.to_csv(PANEL_OUT, index=False)
print(f"saved {PANEL_OUT.name}: {len(event_panel)} rows")

car_windows = (event_panel
               .groupby(["ticker", "anchor"])
               .apply(lambda g: pd.Series({name: g.loc[g["event_day"].between(*days), "ar"].sum()
                                           for name, days in CAR_WINDOWS.items()}))
               .reset_index()
               .merge(event_panel.drop_duplicates(["ticker", "anchor"])
                      [["ticker", "anchor", "day0", "beta", "n_est", "batch_size", "gap_trading_days"]],
                      on=["ticker", "anchor"], how="left", validate="one_to_one"))
car_windows.to_csv(WINDOWS_OUT, index=False)
print(car_windows.round({name: 4 for name in [*CAR_WINDOWS, "beta"]}).to_string())
