"""Shared settings for the index-effect pipeline. Every script imports from here."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RELEASE_CACHE = RAW / "spdji_releases"  # one cached HTML file per press release (git-ignored)
CLEAN = ROOT / "data" / "clean"
OUTPUTS = ROOT / "outputs"
for folder in (RAW, RELEASE_CACHE, CLEAN, OUTPUTS):
    folder.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Lehigh FIN 377 student project)"}

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

# Checkpoint 1 proof of concept: run returns and ARs on these additions only.
# Set to None to run every matched addition.
POC_TICKERS = ["FLEX", "MRVL", "VEEV", "DASH", "COIN"]
