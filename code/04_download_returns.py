"""Step 4: daily adjusted closes for the additions and SPY, downloaded once.

Output: data/raw/prices.csv (wide: one column per ticker, adjusted Close)
"""
import pandas as pd
import yfinance as yf

from config import CLEAN, MARKET, POC_TICKERS, RAW

OUT = RAW / "prices.csv"
CALENDAR_DAYS_BEFORE = 420  # covers the 250-trading-day estimation window before the announcement

additions = pd.read_csv(CLEAN / "additions.csv", parse_dates=["announce_et"])
if POC_TICKERS is not None:
    additions = additions.query("ticker in @POC_TICKERS")
tickers = sorted(additions["ticker"]) + [MARKET]

if OUT.exists() and set(tickers) <= set(pd.read_csv(OUT, nrows=0).columns):
    print(f"{OUT.name} exists with all {len(tickers)} tickers, skipping download")
else:
    start = additions["announce_et"].min().normalize() - pd.Timedelta(days=CALENDAR_DAYS_BEFORE)
    prices = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    prices.to_csv(OUT)
    print(f"saved {OUT.name}: {prices.shape[0]} days x {prices.shape[1]} tickers, "
          f"{prices.index.min().date()} to {prices.index.max().date()}")

prices = pd.read_csv(OUT, index_col="Date", parse_dates=True)
print("first and last date with a price, per ticker:")
print(prices.apply(lambda col: pd.Series({"first": col.first_valid_index(), "last": col.last_valid_index(),
                                          "n_days": col.notna().sum()})).T)
