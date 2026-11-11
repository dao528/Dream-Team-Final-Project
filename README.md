**DASHBOARD**
https://dream-team-index-effect.streamlit.app/

# The disappearing index effect

When a company is added to the S&P 500, does its stock still jump? And is the jump on the day the addition is **announced** or the day it **takes effect**? Shleifer (1986) found a large jump; Greenwood & Sammon (_The Disappearing Index Effect_) find it has mostly vanished. We measure it for every S&P 500 addition since 2022, with both dates, and on the effective date back to 2001 to see how the jump changed over time.

Status: Checkpoint 2 (v0, small sample, every step runs). The Checkpoint 1 memo is [`STATUS.md`](STATUS.md). The candidate ideas from Checkpoint 0 are in [`docs/checkpoint0_candidates.md`](docs/checkpoint0_candidates.md).

## How to run

First get the WRDS files. Prof. Bowen shared them as the Google Drive folder `dao528_request`. Download it and put its contents in `data/raw/wrds/`, so that `data/raw/wrds/outputs/crsp_daily_sp500_ever.parquet` exists. The folder is git-ignored because CRSP and Capital IQ are licensed (and the CRSP file is 201 MB). `run_all.py` stops with a message if the files are missing.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py           # uses the raw files in data/raw/ where they exist
.venv/bin/python run_all.py --fresh   # deletes data/raw/ (except wrds/) and downloads everything again
```

No API keys. v0 runs 5 additions from 2022 on (`POC_TICKERS` in [`code/config.py`](code/config.py)) and 4 history additions per era (`HISTORY_PER_ERA`). Set both to `None` for the full sample.

## Folder layout

```
run_all.py                         runs code/01 ... 07 in order
code/
  config.py                        paths, pinned sources, windows, sample
  01_download_index_changes.py     Wikipedia changes table (pinned revision) -> data/raw/wiki_sp500_changes.csv
  02_download_announcements.py     S&P DJI press releases -> data/raw/spdji_release_list.csv, data/clean/spdji_sp500_actions.csv
  03_build_additions.py            one row per addition, both dates -> data/clean/additions.csv
  03b_build_history_additions.py   Key Dev additions 2001-2021, effective date only -> data/clean/history_additions.csv, outputs/history_date_check.csv, outputs/history_dropped.csv
  04_download_returns.py           one event list + daily returns (CRSP, yfinance after 2025) -> data/clean/events.csv, data/clean/stock_returns.parquet (git-ignored), data/raw/prices.csv
  05_build_event_panel.py          market-model ARs -> data/clean/event_panel.csv, outputs/car_windows.csv, outputs/dropped_short_history.csv, outputs/announce_effective_gap.csv
  06_hand_check.py                 recomputes COIN's CAR from raw CRSP, compares CRSP with yfinance (incl. a dividend payer), checks Tesla's rebalance day
  07_summarize.py                  mean CARs and t-tests by era -> outputs/car_summary.csv, outputs/fig_mean_car_by_era.png
data/raw/                          downloads, never edited (release HTML cache and wrds/ are git-ignored)
data/clean/                        built by code/
outputs/                           tables and figures
poc/                               Checkpoint 0 one-event scripts (superseded by code/)
docs/                              Checkpoint 0 ideas; effective-day convention; pre-2022 and ownership data sources
specs_tried.md                     every specification we have run
```

## Data and provenance

| Raw file | Source | How we get it again |
|---|---|---|
| `data/raw/spdji_release_list.csv` | S&P DJI newsroom search, [press.spglobal.com](https://press.spglobal.com/index.php?s=2429), keywords "Join S&P 500", "Added to the S&P 500", "S&P 500". The `pulled_on` column has the date. | `code/02_download_announcements.py` |
| `data/raw/spdji_releases/*.html` (git-ignored) | Each release page. Announcement time = the page's `ITEMDATE` comment (ET). | same script, cached on first run |
| `data/raw/wiki_sp500_changes.csv` | Wikipedia "List of S&P 500 companies", revision [1368675864](https://en.wikipedia.org/w/index.php?oldid=1368675864) (2026-08-10), the last one with the changes table | `code/01_download_index_changes.py` |
| `data/raw/prices.csv` | yfinance 1.7.0, `auto_adjust=True` Close: SPY from 1999-11-08 to 2026-11-09 (the market for every event) and the 2022+ additions (their returns after CRSP ends, and a cross-check). Pulled on 2026-11-10; the end date is fixed in `code/config.py` (`PRICES_END`). yfinance revises adjusted prices, so a new pull can move the 2026 numbers slightly. | `code/04_download_returns.py` |
| `data/raw/wrds/outputs/crsp_daily_sp500_ever.parquet` (git-ignored) | CRSP daily stock file (`crsp.dsf_v2`), 2000-01-03 to 2025-12-31, for the 1,130 permnos in membership spells that Prof. Bowen rebuilt from Key Dev and Compustat (the official `dsp500list` was not available, see the Drive folder's README). We use `ret_adj` (return including the delisting return), `ticker`, `comnam`, `vol`. | Pulled from WRDS by Prof. Bowen on 2026-11-04 and shared as the Google Drive folder `dao528_request`. Its `README.md` and `code/` folder document the pull. |
| `data/raw/wrds/outputs/keydev_sp500_events.parquet` (git-ignored) | Capital IQ Key Developments, S&P 500 adds and drops (event types 95 and 75), linked to permno, with a volume check of the date (`trading_days_to_peak`) | same Drive folder |
| `data/raw/wrds/outputs/market_daily.parquet` (git-ignored) | CRSP market returns. We only use its dates, as the trading calendar in step 3b. | same Drive folder |

## One row of the final dataset

`data/clean/event_panel.csv`, key (`event_id`, `anchor`, `event_day`): one S&P 500 addition × one anchor (`announce` or `effective`) × one trading day from −10 to +10. History additions (`sample == "keydev_history"`) only have the effective anchor.

| event_id | sample | era | announce_et | effective_date | anchor | day0 | event_day | ret | mkt_ret | beta | ar | car_to_date | ret_source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| COIN_2025 | releases_2022on | 2022-2026 | 2025-05-12 18:00 | 2025-05-19 | announce | 2025-05-13 | 0 | 0.2397 | 0.0066 | 3.44 | 0.2178 | 0.0404 | crsp |
| COIN_2025 | releases_2022on | 2022-2026 | 2025-05-12 18:00 | 2025-05-19 | effective | 2025-05-16 | 0 | 0.0901 | 0.0063 | 3.44 | 0.0690 | 0.1076 | crsp |
| HLT_2017 | keydev_history | 2015-2021 | | 2017-06-19 | effective | 2017-06-16 | 0 | -0.0066 | 0.0002 | 1.30 | -0.0072 | -0.0088 | crsp |

Day 0 rules and the market model are documented at the top of [`code/05_build_event_panel.py`](code/05_build_event_panel.py).

## Threats to validity (so far)

- **Two dates.** Wikipedia only has effective dates. Announcement dates come from S&P's releases, and all releases since 2022 came out after the close.
- **Fake additions.** 5 Wikipedia "additions" since 2022 are ticker changes or a merger (CPAY, DAY, EG, WTW, WBD). We drop them; `code/03_build_additions.py` asserts that every Wikipedia-only row is one of these.
- **Batches.** 51 of 84 additions share a release with at least one other addition, so they are not fully independent. Per Prof. Bowen's Checkpoint 1 feedback we keep the tests simple (plain means and t-tests over short windows) and just note this.
- **Overlapping windows.** For every 2022+ addition the announcement day 0 is inside the effective [-10,+10] window (the gap is at most 10 trading days). For 29 of 84 it is also inside the effective CAR[-1,+1], and for 4 inside CAR[0,+1] (`outputs/announce_effective_gap.csv`). So the effective-date CARs partly measure the announcement jump. COIN's effective CAR[-10,+10] (+4.9%) includes its +21.8% announcement-day AR. We still have to decide how to handle this in v1 (only events with a longer gap, or effective windows that start after announcement day +1).
- **Releases after the fact.** VYLR's release (2026-10-01) reports an addition that already happened (a Corteva spin-off). Its rebalance day is before the announcement day 0, so there was no index-fund trade to anticipate. Step 5 drops events like this and lists them in `outputs/dropped_short_history.csv`.
- **Confounding news.** Earnings inside the window (COIN, MRVL in the proof of concept). Not yet flagged in the data.
- **Spin-offs** with no return history before the announcement (e.g. GE Vernova, Solventum, Kenvue) cannot get a market model. Events with fewer than 200 estimation days (`MIN_EST_DAYS`) are dropped and counted (approved by Prof. Bowen at Checkpoint 1).
- **Survivorship.** Additions are taken from S&P's own announcements (and Key Dev before 2022), not from today's constituent list, so firms deleted later are still in the sample. Returns come from CRSP, which keeps delisted firms and includes delisting returns. yfinance is only used after CRSP ends (2026 additions).
- **Key Dev dates before 2022 are effective dates.** For 2001-2021 we only study the effective date. Of 555 Key Dev additions, 377 are kept (`outputs/history_date_check.csv`, each dropped one is in `outputs/history_dropped.csv`):
  - 36 are not additions. They are a Key Dev backfill dated Saturday 2005-01-29 (AT&T, Fannie Mae and other long-time members, no matching drops).
  - 80 were not trading on the rebalance day (spin-offs and new listings).
  - 4 have no volume test, and 58 have their CRSP volume peak on another day than our rebalance day.
- **The volume filter is a look-ahead.** The volume peak is searched within 15 trading days on both sides, so the filter uses data from after day 0, and the kept additions are the ones with a clear index-fund trade. That can bias the history CARs. It also drops real additions whose Key Dev date is one day off (peak on day 0 or -2). In v1 we want dates that don't depend on volume: the old S&P releases, or Wikipedia from 2007 on. Until then, v1 will also report the history CARs without the volume filter.
- **The announcement is inside the effective window before 2022 too.** Back then S&P often announced about a week before the effective date, so the effective-date CAR over [-10,+10] includes the announcement jump. We can't measure the gap yet because we have no announcement dates for 2001-2021.
- **Two return sources.** CRSP up to 2025, yfinance for 2026 additions, never mixed within one event (`ret_source`). Where both exist they agree (`code/06_hand_check.py`).
- **New permnos.** Some firms get a new CRSP permno (Ensco after its 2012 move to the UK, Invesco after its 2007 move to the NYSE), so they look like they have no history and are dropped (`outputs/dropped_short_history.csv`).
- **Index-fund ownership** is not in the data yet. The WRDS account could not read the mutual fund tables.
