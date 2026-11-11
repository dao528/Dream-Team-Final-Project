"""Step 1: S&P 500 additions and their EFFECTIVE dates, from a pinned Wikipedia revision.

Output: data/raw/wiki_sp500_changes.csv (one row per change row on the page, all years)
"""
import io

import pandas as pd
import requests

from config import HEADERS, RAW, WIKI_REVID

OUT = RAW / "wiki_sp500_changes.csv"

if OUT.exists():
    print(f"{OUT.name} exists, skipping download")
else:
    html = requests.get(
        "https://en.wikipedia.org/w/index.php",
        params={"oldid": WIKI_REVID},
        headers=HEADERS,
        timeout=30,
    ).text
    tables = pd.read_html(io.StringIO(html))
    changes = tables[1]
    assert changes.shape[1] == 6, f"changes table has {changes.shape[1]} columns, expected 6"
    changes.columns = ["effective_date", "add_ticker", "add_name", "rem_ticker", "rem_name", "reason"]
    changes = changes.assign(
        effective_date=pd.to_datetime(changes["effective_date"], errors="coerce"),
        wiki_revid=WIKI_REVID,
    )
    changes.to_csv(OUT, index=False)
    print(f"saved {OUT.name}: {len(changes)} rows")

changes = pd.read_csv(OUT, parse_dates=["effective_date"])
print(f"unparseable effective dates: {changes['effective_date'].isna().sum()}")
print(changes.head())
