"""Step 6: recompute one event by hand, with different code, and compare to the pipeline.

Event: COIN, announced 2025-05-12 at 18:00 ET (after the close), so day 0 = 2025-05-13.
News check: Nasdaq/CNBC reported COIN "soars 24%" on May 13, 2025
(https://www.nasdaq.com/articles/coinbase-soars-24-sp-500-inclusion-what-lies-ahead-etfs).
"""
import numpy as np
import pandas as pd

from config import CLEAN, OUTPUTS, RAW

TICKER, DAY0 = "COIN", pd.Timestamp("2025-05-13")

prices = pd.read_csv(RAW / "prices.csv", index_col="Date", parse_dates=True)[[TICKER, "SPY"]]
raw_return_day0 = prices.loc[DAY0, TICKER] / prices.shift(1).loc[DAY0, TICKER] - 1
print(f"{TICKER} raw return on {DAY0.date()}: {raw_return_day0:.4f}  (news: about +24%)")

# Market model with np.polyfit on trading days -250 ... -30 before day 0 (counted by position).
returns = prices.pct_change().dropna()
day0_pos = returns.index.get_loc(DAY0)
est = returns.iloc[day0_pos - 250: day0_pos - 30 + 1]
beta, alpha = np.polyfit(est["SPY"], est[TICKER], 1)
ar = returns[TICKER] - (alpha + beta * returns["SPY"])
car_0_p1_by_hand = ar.iloc[day0_pos: day0_pos + 2].sum()

pipeline = pd.read_csv(OUTPUTS / "poc_car_windows.csv").query('ticker == @TICKER & anchor == "announce"').iloc[0]
panel = pd.read_csv(CLEAN / "event_panel.csv").query('ticker == @TICKER & anchor == "announce"')

print(f"beta      by hand {beta:.4f}   pipeline {pipeline['beta']:.4f}")
print(f"CAR[0,1]  by hand {car_0_p1_by_hand:.4f}   pipeline {pipeline['car_0_p1']:.4f}")
assert pipeline["day0"] == str(DAY0.date())
assert len(est) == pipeline["n_est"]
assert np.isclose(beta, pipeline["beta"]) and np.isclose(car_0_p1_by_hand, pipeline["car_0_p1"])
assert np.isclose(panel.query("event_day == 0")["ret"].iloc[0], raw_return_day0)
print("hand check passed")
