# The disappearing index effect, 2022–2026

When a company is added to the S&P 500, does its stock still jump? And is the jump on the day the addition is **announced** or the day it **takes effect**? Shleifer (1986) found a large jump; Greenwood & Sammon (_The Disappearing Index Effect_) find it has mostly vanished. We measure it for every S&P 500 addition since 2022.

**Status: Checkpoint 1 (pick + proof of concept).** See [`STATUS.md`](STATUS.md). The candidate ideas from Checkpoint 0 are in [`docs/checkpoint0_candidates.md`](docs/checkpoint0_candidates.md).

## How to run

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py           # uses the raw files in data/raw/ where they exist
.venv/bin/python run_all.py --fresh   # deletes data/raw/ and downloads everything again
```

No API keys. The proof of concept runs returns for 5 additions (`POC_TICKERS` in [`code/config.py`](code/config.py)); set it to `None` to run all 84.

## Folder layout

```
run_all.py                         runs code/01 ... 06 in order
code/
  config.py                        paths, pinned sources, windows, sample
  01_download_index_changes.py     Wikipedia changes table (pinned revision) -> data/raw/wiki_sp500_changes.csv
  02_download_announcements.py     S&P DJI press releases -> data/raw/spdji_release_list.csv, data/clean/spdji_sp500_actions.csv
  03_build_additions.py            one row per addition, both dates -> data/clean/additions.csv
  04_download_returns.py           yfinance adjusted closes -> data/raw/prices.csv
  05_build_event_panel.py          market-model ARs -> data/clean/event_panel.csv, outputs/poc_car_windows.csv
  06_hand_check.py                 recomputes COIN's announcement CAR with different code
data/raw/                          downloads, never edited (release HTML cache is git-ignored)
data/clean/                        built by code/
outputs/                           tables and figures
poc/                               Checkpoint 0 one-event scripts (superseded by code/)
docs/                              Checkpoint 0 candidate ideas
specs_tried.md                     every specification we have run
```

## Data and provenance

| Raw file | Source | How we get it again |
|---|---|---|
| `data/raw/spdji_release_list.csv` | S&P DJI newsroom search, [press.spglobal.com](https://press.spglobal.com/index.php?s=2429), keywords "Join S&P 500", "Added to the S&P 500", "S&P 500". The `pulled_on` column has the date. | `code/02_download_announcements.py` |
| `data/raw/spdji_releases/*.html` (git-ignored) | Each release page. Announcement time = the page's `ITEMDATE` comment (ET). | same script, cached on first run |
| `data/raw/wiki_sp500_changes.csv` | Wikipedia "List of S&P 500 companies", revision [1368675864](https://en.wikipedia.org/w/index.php?oldid=1368675864) (2026-08-10), the last one with the changes table | `code/01_download_index_changes.py` |
| `data/raw/prices.csv` | yfinance 1.7.0, `auto_adjust=True` Close, additions + SPY | `code/04_download_returns.py` |

## One row of the final dataset

`data/clean/event_panel.csv`, key (`ticker`, `anchor`, `event_day`): one S&P 500 addition × one anchor (`announce` or `effective`) × one trading day from −10 to +10.

| ticker | announce_et | effective_date | anchor | day0 | event_day | ret | mkt_ret | beta | ar | car_to_date | batch_size | gap_trading_days |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| COIN | 2025-05-12 18:00 | 2025-05-19 | announce | 2025-05-13 | 0 | 0.2397 | 0.0066 | 3.44 | 0.2178 | 0.0404 | 1 | 4 |

Day 0 rules and the market model are documented at the top of [`code/05_build_event_panel.py`](code/05_build_event_panel.py).

## Threats to validity (so far)

- **Two dates.** Wikipedia only has effective dates. Announcement dates come from S&P's releases, and all releases since 2022 came out after the close.
- **Fake additions.** 5 Wikipedia "additions" since 2022 are ticker changes or a merger (CPAY, DAY, EG, WTW, WBD). We drop them; `code/03_build_additions.py` asserts that every Wikipedia-only row is one of these.
- **Batches.** 51 of 84 additions share a release with at least one other addition, so they are not independent. Tests will cluster by release.
- **Overlapping windows.** The announce and effective windows overlap when the gap is short (4 trading days for COIN and VEEV).
- **Confounding news.** Earnings inside the window (COIN, MRVL in the proof of concept). Not yet flagged in the data.
- **Spin-offs** with no return history before the announcement (e.g. GE Vernova, Solventum, Kenvue) cannot get a market model. They will be dropped and counted.
- **Survivorship.** Additions are taken from S&P's own announcements, not from today's constituent list, so firms deleted later are still in the sample. Their returns may be harder to get from yfinance.
