# Pipeline walkthrough

For the four of us, so each of us can explain any step on Dec 1. All numbers come from `outputs/` (or `data/clean/`) on `main` after PR #20. If a number here and a file disagree, the file wins.

## The question in five sentences

When S&P adds a company to the S&P 500, two dates matter. The announcement: S&P publishes a press release, always after the 4pm close since 2022, so the first trading day after it is the announcement day 0. The effective date: the change takes effect "prior to the open" on that date, so index funds buy in the closing auction the trading day before, and that close is the effective day 0 (we call it the rebalance close). Shleifer (1986) found a big jump at additions; Greenwood and Sammon find the jump has mostly disappeared. We measure the jump at both day 0s for every addition since 2022, and at the effective day 0 back to 2001, to see how it changed.

```
release after 4pm  ->  announcement day 0  ->  ...  ->  rebalance close (effective day 0)  ->  effective date (first day in the index)
                       first close after                index funds buy here
                       the news
```

The gap between the two day 0s is usually short: 1 trading day for 25 of the 84 additions (a member is acquired and S&P replaces it fast) and 8 or 9 trading days for 40 (the quarterly rebalance). Median 4, max 10 (`outputs/announce_effective_gap.csv`).

## Results to remember

Mean CAR[0,+1] (abnormal return on day 0 and day +1, added up), from `outputs/car_summary.csv`:

| Sample | Day 0 | n | Mean | t |
|---|---|---|---|---|
| 2022-2026 | announcement | 69 | +4.46% | 6.13 |
| 2022-2026 | effective (rebalance close) | 69 | -1.02% | -1.90 |
| 2001-2007 | effective | 142 | +0.81% | 2.59 |
| 2008-2014 | effective | 127 | -0.56% | -1.78 |
| 2015-2021 | effective | 140 | -0.10% | -0.50 |

How to read it:

- Today the jump comes at the announcement (+4.5%, very significant). By the rebalance close it's priced in, and the stock gives a little back (-1.0%, not significant at 5%).
- On the effective date, the jump shrinks from +0.8% in 2001-2007 to about zero after 2008. That fits "the disappearing index effect", but see the caveat below on the 2001-2007 dates.
- Additions announced in the same release share their day 0, so they aren't independent. The `*_by_date` columns average them per day 0 first: 43 announcement dates, t = 5.49. Same conclusion.
- In money (`outputs/magnitudes.csv`, Daniel's Magnitudes paragraph in the README): the average 2022+ announcement jump is about $2.4 billion per firm (median $1.5 billion). A trader can't get most of it. The day 0 AR (+4.68% on average) starts from the close before the news, and buying after the news and holding to the rebalance close earns only +0.22% on average, positive for 36 of 69.

The 2001-2007 caveat: 152 of its 167 additions have no Wikipedia date to check Key Dev against, and Prof. Bowen's WRDS README says that in 2005-2007, 5-22% of Key Dev dates look like announcement dates. Where that happens, our "effective" CAR holds the announcement jump. With the old volume filter the 2001-2007 mean is only +0.31% (t = 0.93, `outputs/car_summary_history_dates.csv`). So we say "consistent with a disappearing effect", not "proof".

## The steps

`python run_all.py` runs all of them in order. Steps 03b, 04, 05, 06 and 08 need the WRDS files (CRSP and Capital IQ) in `data/raw/wrds/`, which are licensed and not in git.

### 01 Wikipedia changes table (`code/01_download_index_changes.py`)

- In: Wikipedia's "List of S&P 500 companies", pinned to revision 1368675864 so it can't change.
- Out: `data/raw/wiki_sp500_changes.csv`, one row per index change, all years.
- Used for: a cross-check on S&P's effective dates (step 03) and on Key Dev's dates (step 03b).

### 02 S&P press releases (`code/02_download_announcements.py`)

- In: the S&P DJI newsroom. Every release page is committed in `data/raw/spdji_releases/`, so the step runs offline and the times can't change.
- Out: `data/clean/spdji_sp500_actions.csv`, one row per release x addition or deletion.
- The announcement time is the page's `ITEMDATE` stamp, US Eastern. All 84 are between 17:00 and 19:59, after the close (`code/06_hand_check.py` checks every stamp).

### 03 One row per 2022+ addition (`code/03_build_additions.py`)

- In: the release actions (02) and Wikipedia (01).
- Out: `data/clean/additions.csv` (84 additions from 53 releases) and `outputs/sample_counts.csv`.
- Checks:
  - 77 of the 78 additions in both sources have the same effective date.
  - 5 Wikipedia "additions" are renames or a merger (CPAY, DAY, EG, WBD, WTW). The code asserts that these are the only Wikipedia rows without a release.

### 03b History additions 2001-2021 (`code/03b_build_history_additions.py`)

- In: Capital IQ Key Developments (S&P 500 adds and drops, linked to CRSP permno), CRSP, Wikipedia.
- Out: `data/clean/history_additions.csv` (421 kept), `outputs/history_dates.csv`, `outputs/history_date_rules.csv`, `outputs/history_date_check.csv`, `outputs/history_dropped.csv` (every dropped row with its name and reason).
- Before 2021, Key Dev's "announcedate" is really the effective date, so these additions only get the effective day 0.
- From 555 Key Dev rows to 421 additions (`outputs/history_date_check.csv`):

  | Dropped | Rows | Why |
  |---|---|---|
  | backfill | 36 | a Saturday in 2005 when Key Dev "added" AT&T, Fannie Mae and other old members; no real index change |
  | same firm twice | 5 | Key Dev rows of one firm within 10 trading days (Moderna) become one event |
  | not new members | 16 | 10 firms were already in the index (Google's second share class in 2014, Alcoa 2016), 6 are dropped again by Key Dev within days (Coca-Cola Enterprises 2010, Kyndryl 2021) |
  | new listings | 77 | spin-offs and merger-created firms with no CRSP price on the rebalance day (PayPal, AbbVie, Kraft Heinz) |

- Dates: no volume data is used to pick a date (the old volume filter was a look-ahead, audit A1). Each Key Dev date is compared with Wikipedia's (`outputs/history_date_rules.csv`, 498 real additions):
  - 169 agree.
  - 237 have no Wikipedia match, mostly before 2008, and keep Key Dev's date.
  - For 70, Wikipedia is one trading day earlier. S&P's own releases settle these: up to 2020 Key Dev is right, and in 2021 Wikipedia is (eight releases checked in `code/06_hand_check.py`).

### 04 Event list and daily returns (`code/04_download_returns.py`)

- In: the 84 additions (03), the 421 history additions (03b), CRSP, yfinance.
- Out: `data/clean/events.csv` (505 events), `data/clean/stock_returns.parquet` (not in git, it's CRSP data), `data/raw/prices.csv` (SPY and the 2022+ stocks from yfinance), `outputs/yfinance_fallback.csv`, `outputs/history_predecessors.csv`.
- Returns come from CRSP (`ret_adj`, which includes delisting returns, so no survivorship problem) wherever CRSP has them. CRSP ends 2025-12-31, so 30 of the 84 2022+ additions use yfinance (`outputs/yfinance_fallback.csv`):
  - 18 were announced after CRSP ends.
  - 3 have windows that run past it.
  - 9 are spin-offs that weren't trading yet.

  One event never mixes the two sources (`ret_source`).
- Ensco changed permno twice: when it moved to the UK in 2009 (ADS) and when its class A shares replaced the ADS in 2012. Its older permnos' returns fill the estimation window (`outputs/history_predecessors.csv`). Invesco and News Corp would need the full CRSP file, which we don't have, so IVZ_2008 and NWS_2004 are still dropped.

### 05 Abnormal returns (`code/05_build_event_panel.py`)

- In: events and returns (04), SPY returns.
- Out: `data/clean/event_panel.csv` (one row = event x day 0 type x day -10 to +10), `outputs/car_windows.csv` (one row per event and day 0), `outputs/dropped_short_history.csv`, `outputs/announce_effective_gap.csv`.
- Market model, as in class:
  - Estimate alpha and beta of the stock against SPY over trading days -250 to -30 before the announcement day 0, for both day 0s, so the estimation window never contains the news. History events have no announcement date, so they use the effective day 0.
  - Expected return = alpha + beta x SPY return. Abnormal return (AR) = actual - expected. CAR = sum of ARs over a window: [0,+1], [-1,+1], [-10,+10].
- Dropped: events with fewer than 200 estimation days. 14 are since 2022, all spin-offs or new listings (GE Vernova, Kenvue, Solventum). 12 are in the history: mostly IPOs and spin-offs, plus IVZ and NWS (step 04). Also dropped is VYLR 2026, a release that came after the rebalance day. That's how 84 becomes 69.

### 06 Hand checks (`code/06_hand_check.py`)

Different code, same answers:

- COIN's announcement CAR by hand from raw CRSP with `np.polyfit`. The pipeline gives +24% (news: "Coinbase soars 24%").
- CRSP vs yfinance give the same daily returns where both exist.
- Tesla's record volume was on 2020-12-18, our rebalance day.
- All 84 release time stamps are Eastern time and after the close.
- Eight history dates match S&P's own releases.
- Ensco's 2012 CAR by hand across its three permnos.

### 07 Averages and t-tests (`code/07_summarize.py`)

- Out: `outputs/car_summary.csv` (means, t-tests, and the by-date version), `outputs/car_summary_history_dates.csv` (the history with and without the old volume filter and the uncertain dates), `outputs/fig_mean_car_by_era.png` (the main figure).

### 08 Magnitudes (`code/08_magnitudes.py`)

- Out: `outputs/magnitudes.csv`.
- Dollar CAR = CAR[0,+1] x market value the day before day 0. Also the bid-ask spread and the part of the announcement jump a trader could still get after the news (`car_day1_to_rebalance`).

## Questions we should expect

### Why is day 0 the close before the effective date?

S&P changes take effect "prior to the open" on the effective date, so index funds have to own the stock at the close the day before. That closing auction is where they buy (Tesla traded its record volume there, `code/06_hand_check.py`). See `docs/effective_day_convention.md`.

### Why is the 2022+ effective CAR negative?

The jump happens at the announcement, and by the rebalance close it's priced in. In the effective window the mean AR is +1.50% on day -1, then -0.37% on day 0 and -0.64% on day +1 (`data/clean/event_panel.csv`). Day -1 often still holds announcement jumps (the 25 additions with a one-day gap). One reading of the rest is that some price pressure reverses once index funds are done buying, but that's our interpretation, not something we test. At -1.02% with t = -1.90 it's not significant at 5%, and by date it's t = -1.24 (42 dates). So we call it "no jump, maybe a small giveback".

### Isn't the announcement inside the effective window?

Yes, for all 84 the announcement day 0 is inside the effective [-10,+10], and for 29 it's inside the effective CAR[-1,+1] (`outputs/announce_effective_gap.csv`). That's why our headline windows are the short ones and why we read the effective [-10,+10] (+3.23%, t = 2.28) as both moves together. README "Overlapping windows".

### Why only the effective date before 2022?

Key Dev's date is the effective date in those years, and we have no announcement times. The old S&P releases would have them (not done).

### How do you know the history dates are right?

We don't use trading volume to pick them, because that would use information from after day 0. We check Key Dev against Wikipedia and, for the one-day disagreements, against S&P's own releases. The weak spot is 2001-2007, where most dates are Key Dev only.

### Why drop spin-offs and IPOs?

Without about a year of returns before the event, there's no market model to compute "normal". We drop events with fewer than 200 estimation days and list every one in `outputs/dropped_short_history.csv`. When the parent is already in the S&P 500, index funds get the spin-off's shares in the spin-off and don't have to buy them.

### What about firms that were later delisted?

They stay in. The additions come from S&P's releases and Key Dev, not from today's index list, and CRSP's returns include delisting returns.

### Many additions are announced together. Isn't the t-test too optimistic?

Yes, a bit. The by-date version averages per day 0 first. The announcement result holds (43 dates, t = 5.49). The effective one gets weaker (42 dates, t = -1.24). Prof. Bowen asked us to keep the tests simple, so we report both and note it.

### Why a market model against SPY?

It's the class standard (the event-study notebooks). Alpha and beta come from days -250 to -30, with a 30-day gap so the run-up to the news isn't in the estimate.

### Can a hedge fund make money on this?

Not much. Most of the jump is in the day 0 AR, which starts from the close before the news, and the news comes after the close. Buying at the day 0 close and selling at the rebalance close earns +0.22% on average (`outputs/magnitudes.csv`). Spreads are tiny (median 0.04%), but there's little left to capture.

### Why did 84 additions become 69?

14 had fewer than 200 estimation days (spin-offs like GE Vernova and Kenvue) and VYLR 2026 was announced after its rebalance day (`outputs/dropped_short_history.csv`).

### Are IVZ_2008 and NWS_2004 in the sample?

No. They changed CRSP permno when they moved their listing to the US, and their old returns are only in a CRSP file we didn't get. Step 03b keeps them (they're in `outputs/history_dates.csv`), and step 05 drops them for short history: IVZ has 149 estimation days, NWS none. Bowen's Checkpoint 3 audit says IVZ is in the sample, probably from the 03b file. In the CAR results it isn't.

### What about earnings or other news in the window?

Not flagged in the data. It's one reason we lean on the 2-day windows. Example: Marvell had a +32% AR on announcement day -4. With it, the 2022+ announcement CAR[-10,+10] mean is +3.6%; without it, +3.0% (`outputs/car_windows.csv`). README "Confounding news" still has the numbers from the 5-event sample (+3.8% to +11.9%) and needs updating.

## Who knows what best

- Tom: steps 02-06, the data (CRSP, Key Dev, dates), the history sample.
- Daniel: step 08 and the magnitudes, the full 2022+ run (B1), STATUS.md.
- Karthik: the dashboard, the overlap handling (A4) and the release-page fixes (A5).
- Manny: the audit responses, what was fixed and what is disclosed.
