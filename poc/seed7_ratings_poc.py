"""Seed 7 proof of concept: one real row of the rating-change event dataset.

Pulls broker rating changes from yfinance and computes market-model abnormal returns
around one upgrade. Shows why the timestamp's time zone decides day 0.

Run: python poc/seed7_ratings_poc.py
"""
import numpy as np
import pandas as pd
import yfinance as yf

ticker = "AAPL"
ud = yf.Ticker(ticker).upgrades_downgrades
print(f"{ticker}: {len(ud)} rows, {ud.index.min()} to {ud.index.max()}")
print(ud["Action"].value_counts())
print(ud[ud["Action"].isin(["up", "down"])].head(6))

# One event: Rothschild & Co upgrade, Neutral -> Buy, stamped 2026-08-17 20:20:47
px = yf.download([ticker, "SPY"], start="2025-06-01", end="2026-09-01",
                 auto_adjust=True, progress=False)["Close"]
ret = px.pct_change().dropna()
est = ret[ret.index < "2026-07-15"].tail(250)
beta, alpha = np.polyfit(est["SPY"], est[ticker], 1)
ar = ret[ticker] - (alpha + beta * ret["SPY"])

print(f"beta: {beta:.2f}")
print(ar["2026-08-13":"2026-08-21"].round(4))
# If the stamp is UTC, 20:20 = 4:20pm ET (after the close), so day 0 is Aug 18.
print("CAR[0,1], day0 = Aug 18:", round(ar["2026-08-18":"2026-08-19"].sum(), 4))
print("CAR[0,1], day0 = Aug 17:", round(ar["2026-08-17":"2026-08-18"].sum(), 4))
