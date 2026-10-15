"""Seed 3 proof of concept: one real row of the index-addition event dataset.

Pulls S&P 500 changes from an archived Wikipedia revision (the current page dropped
the "Selected changes" table in Aug 2026), then computes market-model abnormal returns
for one addition around its EFFECTIVE date. Announcement dates still need S&P DJI
press releases.

Run: python poc/seed3_index_effect_poc.py
"""
import io

import numpy as np
import pandas as pd
import requests
import yfinance as yf

HEADERS = {"User-Agent": "Mozilla/5.0 (Lehigh FIN 377 student project)"}
# Last revision (2026-08-10) that still contains the changes table. Pinned for reproducibility.
WIKI_REVID = 1368675864

html = requests.get(
    "https://en.wikipedia.org/w/index.php", params={"oldid": WIKI_REVID}, headers=HEADERS
).text
changes = pd.read_html(io.StringIO(html))[1]
changes.columns = ["effective_date", "add_ticker", "add_name", "rem_ticker", "rem_name", "reason"]
changes["effective_date"] = pd.to_datetime(changes["effective_date"], errors="coerce")

since_2022 = changes[changes["effective_date"] >= "2022-01-01"]
print(f"change rows since 2022: {len(since_2022)}, with an addition: {since_2022['add_ticker'].notna().sum()}")

# One event: FLEX added effective 2026-06-22
ticker, day0 = "FLEX", pd.Timestamp("2026-06-22")
px = yf.download([ticker, "SPY"], start=day0 - pd.Timedelta(days=400),
                 end=day0 + pd.Timedelta(days=15), auto_adjust=True, progress=False)["Close"]
ret = px.pct_change().dropna()
est = ret[ret.index < day0 - pd.Timedelta(days=30)].tail(250)  # estimation window ends ~1 month before
beta, alpha = np.polyfit(est["SPY"], est[ticker], 1)
ar = ret[ticker] - (alpha + beta * ret["SPY"])

print(f"{ticker} market beta: {beta:.2f}")
print(ar[day0 - pd.Timedelta(days=7): day0 + pd.Timedelta(days=7)].round(4))
