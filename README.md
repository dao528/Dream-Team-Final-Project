**DASHBOARD**
https://dream-team-index-effect.streamlit.app/

# The disappearing index effect

When a company is added to the S&P 500, does its stock still jump? And is the jump on the day the addition is **announced** or the day it **takes effect**? Shleifer (1986) found a large jump; Greenwood & Sammon (_The Disappearing Index Effect_) find it has mostly vanished. We measure it for every S&P 500 addition since 2022, with both dates, and on the effective date back to 2001 to see how the jump changed over time.

Status: fixing the Checkpoint 2 audit. The 2001-2021 history sample is complete, the 2022+ sample is still the 5 v0 additions. The Checkpoint 1 memo is [`STATUS.md`](STATUS.md). The candidate ideas from Checkpoint 0 are in [`docs/checkpoint0_candidates.md`](docs/checkpoint0_candidates.md).

## How to run

First get the WRDS files. Prof. Bowen shared them as the Google Drive folder `dao528_request`. Download it and put its contents in `data/raw/wrds/`, so that `data/raw/wrds/outputs/crsp_daily_sp500_ever.parquet` exists. The folder is git-ignored because CRSP and Capital IQ are licensed (and the CRSP file is 201 MB). `run_all.py` stops with a message if the files are missing.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py           # uses the raw files in data/raw/ where they exist
.venv/bin/python run_all.py --fresh   # deletes data/raw/ (except wrds/) and downloads everything again
```

No API keys. The 2022+ sample is still the 5 v0 additions (`POC_TICKERS` in [`code/config.py`](code/config.py), set it to `None` for all 84). The 2001-2021 history sample has every Key Dev addition since the Checkpoint 2 audit (`HISTORY_PER_ERA = None`). Optional: the full CRSP file `crsp_daily.parquet` from the same Drive folder (1.5 GB). Step 4 reads it for older permnos of firms that changed permno and were not in the S&P 500 before (see "New permnos" below).

## Folder layout

```
run_all.py                         runs code/01 ... 08 in order
code/
  config.py                        paths, pinned sources, windows, sample
  01_download_index_changes.py     Wikipedia changes table (pinned revision) -> data/raw/wiki_sp500_changes.csv
  02_download_announcements.py     S&P DJI press releases -> data/raw/spdji_release_list.csv, data/clean/spdji_sp500_actions.csv
  03_build_additions.py            one row per addition, both dates -> data/clean/additions.csv
  03b_build_history_additions.py   Key Dev additions 2001-2021, effective date checked against Wikipedia -> data/clean/history_additions.csv, outputs/history_dates.csv, outputs/history_date_rules.csv, outputs/history_date_check.csv, outputs/history_dropped.csv
  04_download_returns.py           one event list + daily returns (CRSP, yfinance after 2025) -> data/clean/events.csv, data/clean/stock_returns.parquet (git-ignored), data/raw/prices.csv, outputs/yfinance_fallback.csv, outputs/history_predecessors.csv
  05_build_event_panel.py          market-model ARs -> data/clean/event_panel.csv, outputs/car_windows.csv, outputs/dropped_short_history.csv, outputs/announce_effective_gap.csv
  06_hand_check.py                 recomputes COIN's CAR from raw CRSP, compares CRSP with yfinance (incl. a dividend payer), checks Tesla's rebalance day, the release times, eight history dates against S&P's releases, and Ensco's 2012 CAR by hand
  07_summarize.py                  mean CARs and t-tests by era -> outputs/car_summary.csv, outputs/car_summary_history_dates.csv, outputs/fig_mean_car_by_era.png
  08_magnitudes.py                 CARs in dollars (x market value), bid-ask spreads, tradable part of the announcement jump -> outputs/magnitudes.csv
data/raw/                          downloads, never edited (wrds/ is git-ignored; the release HTML cache is committed so step 02 runs offline)
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
| `data/raw/spdji_releases/*.html` (committed) | Each release page, downloaded once and committed so the announcement times can't change on a rerun. Announcement time = the page's `ITEMDATE` comment, e.g. `2025-05-12 18:00:00 EDT` (US Eastern; `code/06_hand_check.py` checks the EDT/EST label against the date). | same script, only for releases missing from the cache |
| `data/raw/wiki_sp500_changes.csv` | Wikipedia "List of S&P 500 companies", revision [1368675864](https://en.wikipedia.org/w/index.php?oldid=1368675864) (2026-08-10), the last one with the changes table | `code/01_download_index_changes.py` |
| `data/raw/prices.csv` | yfinance 1.7.0, `auto_adjust=True` Close: SPY from 1999-11-08 to 2026-11-09 (the market for every event) and the 2022+ additions (their returns after CRSP ends, and a cross-check). Pulled on 2026-11-10; the end date is fixed in `code/config.py` (`PRICES_END`). yfinance revises adjusted prices, so a new pull can move the 2026 numbers slightly. | `code/04_download_returns.py` |
| `data/raw/wrds/outputs/crsp_daily_sp500_ever.parquet` (git-ignored) | CRSP daily stock file (`crsp.dsf_v2`), 2000-01-03 to 2025-12-31, for the 1,130 permnos in membership spells that Prof. Bowen rebuilt from Key Dev and Compustat (the official `dsp500list` was not available, see the Drive folder's README). We use `ret_adj` (return including the delisting return), `ticker`, `comnam`, `vol`. | Pulled from WRDS by Prof. Bowen on 2026-11-04 and shared as the Google Drive folder `dao528_request`. Its `README.md` and `code/` folder document the pull. |
| `data/raw/wrds/outputs/keydev_sp500_events.parquet` (git-ignored) | Capital IQ Key Developments, S&P 500 adds and drops (event types 95 and 75), linked to permno, with a volume check of the date (`trading_days_to_peak`) | same Drive folder |
| `data/raw/wrds/outputs/market_daily.parquet` (git-ignored) | CRSP market returns. We only use its dates, as the trading calendar in step 3b. | same Drive folder |
| `data/raw/wrds/outputs/crsp_daily.parquet` (git-ignored, optional) | The same CRSP daily file for every security (1.5 GB). Step 4 reads it only for older permnos that were never in the S&P 500 (`PREDECESSORS` in `code/config.py`). | same Drive folder |

## One row of the final dataset

`data/clean/event_panel.csv`, key (`event_id`, `anchor`, `event_day`): one S&P 500 addition × one anchor (`announce` or `effective`) × one trading day from −10 to +10. History additions (`sample == "keydev_history"`) only have the effective anchor.

| event_id | sample | era | announce_et | effective_date | anchor | day0 | event_day | ret | mkt_ret | beta | ar | car_to_date | ret_source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| COIN_2025 | releases_2022on | 2022-2026 | 2025-05-12 18:00 | 2025-05-19 | announce | 2025-05-13 | 0 | 0.2397 | 0.0066 | 3.44 | 0.2178 | 0.0404 | crsp |
| COIN_2025 | releases_2022on | 2022-2026 | 2025-05-12 18:00 | 2025-05-19 | effective | 2025-05-16 | 0 | 0.0901 | 0.0063 | 3.44 | 0.0690 | 0.1076 | crsp |
| HLT_2017 | keydev_history | 2015-2021 | | 2017-06-19 | effective | 2017-06-16 | 0 | -0.0066 | 0.0002 | 1.30 | -0.0072 | -0.0088 | crsp |

Day 0 rules and the market model are documented at the top of [`code/05_build_event_panel.py`](code/05_build_event_panel.py).

## Magnitudes

For the five recent 2022+ additions, the dollar jumps look huge at an average +7.7% ($3.9 billion) two day post announcement spike compared to just -4.5% to +4.9% for smaller 2001–2021 additions, though Coinbase alone drives a +24% ($10.5 billion) spike and the average drops to +3.6% without it. Even though bid ask spreads are tiny at around 0.03%, traders mostly can’t capture this move because S&P announces after market close, meaning the +8.4% day 0 jump happens off news that were before the closing price you can’t buy at. Buying after the news and holding until the close only gets you an average extra return of +0.2% (positive for 3 of the 5), so the price fixes itself almost immediately and index fund investors would pay basically for the increase while the hedge funds would have very little to trade. These five additions are just early examples rather than reliable results, and the market values are approximate since CRSP leaves out Coinbase’s Class B shares and uses end of 2025 share counts for 2026 additions. (All numbers: `outputs/magnitudes.csv`.)

## Threats to validity (so far)

- **Two dates.** Wikipedia only has effective dates. Announcement dates come from S&P's releases, and all releases since 2022 came out after the close.
- **Fake additions.** 5 Wikipedia "additions" since 2022 are ticker changes or a merger (CPAY, DAY, EG, WTW, WBD). We drop them; `code/03_build_additions.py` asserts that every Wikipedia-only row is one of these.
- **Batches.** 51 of 84 additions share a release with at least one other addition (`outputs/sample_counts.csv`), so they are not fully independent. Per Prof. Bowen's Checkpoint 1 feedback we keep the tests simple (plain means and t-tests over short windows) and just note this.
- **Overlapping windows.** For every 2022+ addition the announcement day 0 is inside the effective [-10,+10] window (the gap is at most 10 trading days). For 29 of 84 it is also inside the effective CAR[-1,+1], and for 4 inside CAR[0,+1] (`outputs/announce_effective_gap.csv`). So the effective-date CARs partly measure the announcement jump. COIN's effective CAR[-10,+10] (+4.9%) includes its +21.8% announcement-day AR. We still have to decide how to handle this in v1 (only events with a longer gap, or effective windows that start after announcement day +1).
- **Releases after the fact.** VYLR's release (2026-10-01) reports an addition that already happened (a Corteva spin-off). Its rebalance day is before the announcement day 0, so there was no index-fund trade to anticipate. Step 5 drops events like this and lists them in `outputs/dropped_short_history.csv`.
- **Confounding news.** Earnings inside the window (COIN, MRVL in the proof of concept). Not yet flagged in the data.
- **Spin-offs** with no return history before the announcement (e.g. GE Vernova, Solventum, Kenvue) cannot get a market model. Events with fewer than 200 estimation days (`MIN_EST_DAYS`) are dropped and counted (approved by Prof. Bowen at Checkpoint 1).
- **Survivorship.** Additions are taken from S&P's own announcements (and Key Dev before 2022), not from today's constituent list, so firms deleted later are still in the sample. Returns come from CRSP, which keeps delisted firms and includes delisting returns. yfinance is only used where CRSP has no row: event windows that end after 2025, and spin-offs that were not trading yet at the announcement (`outputs/yfinance_fallback.csv`, 30 of the 84 2022+ additions, each with its reason).
- **Key Dev dates before 2022 are effective dates.** For 2001-2021 we only study the effective date. Key Dev has 555 additions in those years. 36 are not additions: a Key Dev backfill dated Saturday 2005-01-29 (AT&T, Fannie Mae and other long-time members, no matching drops). 5 repeat a firm within 10 trading days (Moderna on 2021-07-20 and 2021-07-22), and we keep one row per firm (`SAME_FIRM_WINDOW`). 16 are not new members. Either the permno was already in the index (Google's second share class in 2014, Fox and News Corp in 2015, Regions 2004), or Key Dev drops it again within 10 trading days (Alcoa/Arconic 2016, Coca-Cola Enterprises 2010, spin-offs like DT Midstream that S&P held for a day). No index fund buys these. Step 3b finds them from Key Dev's own add and drop rows. That leaves 498 additions (`outputs/history_date_check.csv`; every dropped row, with its name, is in `outputs/history_dropped.csv`).
- **Spin-offs and mergers before 2022.** 77 of the 498 have no CRSP row on the rebalance day because the stock started trading 1 to 7 trading days later (`trading_days_to_first_crsp` in `outputs/history_dropped.csv`). They are spin-offs or firms created by a merger (Zimmer, PayPal, AbbVie, Kraft Heinz), and `code/03b_build_history_additions.py` asserts that each one starts trading after the rebalance day. When an S&P 500 member spins off a firm, index funds get the new shares through the spin-off without buying them. 2015-2021 has more of these (41, against 20 and 16), which changes the mix of firms across eras a little.
- **Effective dates without volume data.** Up to Checkpoint 2 we kept a history addition only if its CRSP volume peak was on our rebalance day. That filter used volume after day 0, so it is off now (`HISTORY_VOLUME_FILTER`). Instead, step 3b checks every Key Dev date against Wikipedia's changes table (same ticker, at most 10 trading days apart; the ticker is CRSP's on the trading day before the Key Dev date, so 5 firms that changed ticker on that day, such as Evergy and Alphabet, go unmatched, all with the same date in both sources) and records a rule per addition (`outputs/history_dates.csv`, counts by era in `outputs/history_date_rules.csv`):
  - 169 dates agree.
  - Where Key Dev lists the firm twice around Wikipedia's date (Moderna) or Wikipedia's date is later (14 additions, where Key Dev looks like the announcement), we use Wikipedia's date.
  - Where Wikipedia is one trading day earlier (70, mostly 2008-2014), S&P's own releases decide. Up to 2020 Wikipedia gives the "after the close of" day and Key Dev the effective date (Helmerich & Payne 2010, WellCare 2018, Ingersoll Rand 2020), so we keep Key Dev. In 2021 Key Dev is a day late (Trimble, Monolithic Power, PTC, SolarEdge), so the 4 cases from 2021 use Wikipedia (`AMBIGUOUS_WIKIPEDIA_FROM`). `code/06_hand_check.py` checks all eight against the releases. The volume peak agrees: Key Dev's rebalance day for 58 of the 70, Wikipedia's for the 4 from 2021 (`volume_peak_on` in `outputs/history_dates.csv`). We only report it and never use it to pick a date.
  - Where Wikipedia is 2 to 10 trading days earlier (7), we keep Key Dev as well.
  - 237 additions have no Wikipedia match, 152 of them before 2008, when the table has almost no rows. They keep Key Dev's date.
  
  `outputs/car_summary_history_dates.csv` repeats the history CARs for four groups: all additions, only those that pass the old volume filter, all without the one-day disagreements (62 of the 70 are in the CAR sample), and only those where both sources agree.
- **The 2001-2007 jump rests on dates nobody has checked.** Only 2001-2007 has a significant effective-date CAR[0,+1] (+0.81%, t = 2.59, `outputs/car_summary.csv`). But 152 of its 167 additions have no Wikipedia match, and the README of the WRDS folder says that in 2005-2007, 5-22% of Key Dev dates look like announcement dates. Where Key Dev gives the announcement, our "effective" CAR holds the announcement jump. With the old volume filter, which keeps only additions whose volume peak is on our rebalance day, the mean is +0.31% (t = 0.93, `outputs/car_summary_history_dates.csv`). So we don't read the 2001-2007 number as an effective-date effect until the old S&P releases date these additions (planned for the final).
- **The announcement is inside the effective window before 2022 too.** Back then S&P often announced about a week before the effective date, so the effective-date CAR over [-10,+10] includes the announcement jump. We can't measure the gap yet because we have no announcement dates for 2001-2021.
- **Two return sources.** CRSP up to 2025, yfinance for 2026 additions, never mixed within one event (`ret_source`). Where both exist they agree (`code/06_hand_check.py`).
- **New permnos.** Some firms got a new CRSP permno when they moved abroad or back, so they seemed to have no return history. Ensco has three: Ensco International Inc, then the Ensco plc ADS after the move to the UK in 2009, then Ensco plc class A shares in 2012. `PREDECESSORS` in `code/config.py` maps each new permno to the old one, and step 4 fills the estimation window with the old permno's returns (`outputs/history_predecessors.csv`). The old permno's last return runs to the first close of the new shares (CRSP's delisting return), so on that one day a two-day stock return meets a one-day market return. `code/06_hand_check.py` recomputes Ensco's 2012 CAR across its three permnos. Invesco (the AMVESCAP ADR before its 2007 move to the NYSE) and News Corp (the Australian ADR before its 2004 move to the US) need the same, but their old permnos were never in the S&P 500, so their returns are only in the full CRSP file (`crsp_daily.parquet`, same Drive folder), and they are not in `PREDECESSORS` yet. Until then IVZ_2008 and NWS_2004 are dropped for short history. The other short-history drops are IPOs and spin-offs (`outputs/dropped_short_history.csv`).
- **Index-fund ownership** is not in the data yet. The WRDS account could not read the mutual fund tables.
