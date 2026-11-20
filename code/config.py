"""Shared settings for the index-effect pipeline. Every script imports from here."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RELEASE_CACHE = RAW / "spdji_releases"  # one cached HTML file per press release (committed)
CLEAN = ROOT / "data" / "clean"
OUTPUTS = ROOT / "outputs"
for folder in (RAW, RELEASE_CACHE, CLEAN, OUTPUTS):
    folder.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Lehigh FIN 331 student project)"}

# Wikipedia "List of S&P 500 companies": last revision (2026-08-10) that still has the
# "Selected changes" table. The live page dropped it in Aug 2026.
WIKI_REVID = 1368675864

# S&P Dow Jones Indices newsroom (PR Newswire-hosted). s=2429 is the index-news section.
NEWSROOM_SEARCH = "https://press.spglobal.com/index.php"
NEWSROOM_SECTION = 2429
SEARCH_KEYWORDS = ["Join S&P 500", "Added to the S&P 500", "S&P 500"]

SAMPLE_START = pd.Timestamp("2022-01-01")
MARKET = "SPY"

# Event-study windows, in trading days relative to day 0 (same choices as HW6).
EST_WINDOW = (-250, -30)  # relative to the ANNOUNCEMENT day 0, for both anchors
MIN_EST_DAYS = 200
EVENT_WINDOW = (-10, 10)

# v0 sample: run returns and ARs on these 2022+ additions only. Set to None to run every matched addition.
POC_TICKERS = ["FLEX", "MRVL", "VEEV", "DASH", "COIN"]

# WRDS pull from Prof. Bowen (Google Drive folder "dao528_request", built 2026-11-04). Not in git.
WRDS = RAW / "wrds" / "outputs"
CRSP_DAILY = WRDS / "crsp_daily_sp500_ever.parquet"
KEYDEV_EVENTS = WRDS / "keydev_sp500_events.parquet"
CRSP_MARKET = WRDS / "market_daily.parquet"  # used only for its trading calendar
CRSP_END = pd.Timestamp("2025-12-31")  # last CRSP day; events whose window runs past it use yfinance
# yfinance prices end the day before this date (yfinance's end is exclusive). Fixed, so a rerun
# downloads the same days and never a half-finished trading day. Pulled on 2026-11-10.
PRICES_END = pd.Timestamp("2026-11-10")

# History sample: Key Dev additions before our S&P-release sample starts. Before about 2021 the
# Key Dev date is the effective date (data/raw/wrds/README.md), so these get the effective anchor only.
# CRSP starts 2000-01-03 and the estimation window needs 250 trading days before day 0, so 2001.
HISTORY_START = pd.Timestamp("2001-01-01")
HISTORY_END = SAMPLE_START - pd.Timedelta(days=1)
# Key Dev can list the same firm twice a few days apart (Moderna 2021-07-20 and 2021-07-22). Additions
# of the same permno within this many trading days are one event (audit A3).
SAME_FIRM_WINDOW = 10
# Effective dates (rules in code/03b_build_history_additions.py, audit A1). "keydev+wikipedia" takes
# Wikipedia's date where Key Dev is early or lists the firm twice. "keydev" = the v0 rule.
HISTORY_DATE_SOURCE = "keydev+wikipedia"
WIKI_MATCH_DAYS = 10  # S&P announces at most 10 trading days ahead (max gap in outputs/announce_effective_gap.csv)
# v0 volume filter: keep an event only if its volume peak (within 15 trading days) is the trading day
# before the Key Dev date. It looks at volume after day 0, so it is off from v1 on (audit A1) and
# only used for a robustness test (passes_volume_filter in 03b).
HISTORY_PEAK_DAY = -1
HISTORY_VOLUME_FILTER = False
# v0 drew this many additions per era with a fixed seed. None = every addition (since the Checkpoint 2 audit).
HISTORY_PER_ERA = None
HISTORY_SEED = 331

# 7-year blocks (the last one is 2022 to now) by the year of effective day 0, fixed before looking at results.
ERAS = {"2001-2007": (2001, 2007), "2008-2014": (2008, 2014), "2015-2021": (2015, 2021), "2022-2026": (2022, 2026)}


def era_of(year):
    """Era label for a calendar year."""
    for label, (first, last) in ERAS.items():
        if first <= year <= last:
            return label
    raise ValueError(f"year {year} is outside every era")
