# Dream-Team-Final-Project

**Checkpoint 0: candidate ideas.** We're choosing between two project seeds: **#3, The disappearing index effect** and **#7, Do analyst upgrades move prices, and does the broker matter?** Each idea below is "read backwards," starting from the final dataset and chart, and ends with what our first proof of concept found.

---

## Idea A (Seed 3): The disappearing index effect

### 1. The question
When a company is added to the S&P 500, does its stock still jump? And is the jump on the day the addition is **announced** or the day it **takes effect**?

### 2. One row of the final dataset
One row = **one S&P 500 addition × one event day** (relative to either the announcement date or the effective date).

| ticker | announce_date | effective_date | anchor | event_day | ret | mkt_ret | ar | car_to_date | mktcap_bn | batch_size |
|---|---|---|---|---|---|---|---|---|---|---|
| FLEX | 2026-06-05 | 2026-06-22 | announce | +1 | 0.041 | 0.003 | 0.035 | 0.038 | 22.1 | 2 |
| FLEX | 2026-06-05 | 2026-06-22 | effective | 0 | 0.068 | 0.003 | 0.061 | 0.061 | 22.1 | 2 |
| DASH | 2025-03-07 | 2025-03-24 | announce | 0 | 0.022 | -0.004 | 0.031 | 0.031 | 85.0 | 4 |

_(The rows are fake except FLEX's effective-day AR, which our proof of concept computed. FLEX's announcement date is a guess, not yet checked against the press release.)_

### 3. Raw inputs, and whether we can get them
| Input | Source | Do we know we can get it? |
|---|---|---|
| Additions + **effective** dates | Wikipedia "List of S&P 500 companies" changes table | **Yes, with a catch.** The current page dropped the changes table in Aug 2026. An archived revision (`oldid=1368675864`, 2026-08-10) still has it: 96 change rows since 2022, 83 of them additions. We pin that revision. |
| **Announcement** dates | S&P Dow Jones Indices press releases | **Not yet.** We'd need an agent to collect them, about 80–100 releases. This is the riskiest input. |
| Daily returns | yfinance (stock + SPY) | **Yes.** Worked for FLEX. |
| Returns for deleted / delisted firms | yfinance has gaps for delisted tickers | **Unknown.** Only matters if we add deletions (stretch goal). |
| Size, index-fund ownership | yfinance market cap; ownership TBD | Market cap yes. Index-fund float share is not checked yet. |

### 4. The chart that answers the question
Two average-CAR lines on one plot, from day −10 to day +10: one anchored on the announcement date and one on the effective date, with a 95% confidence band. Small multiples by year (2022 … 2026) show whether the jump is shrinking. A second dashboard page shows a scatter of CAR against market cap.

### 5. The first thing an auditor would attack
**Mixing up the two dates, and overlapping events.** Wikipedia gives the effective date, not the announcement date, so an event study "at day 0" from Wikipedia alone measures the wrong thing. Additions are also announced in batches on the same day (FLEX and MRVL were both effective 2026-06-22), so they aren't independent observations. Our t-stats need to cluster by announcement date.

### Proof of concept (Oct 15) — what we learned
- **Got:** a real event row for **FLEX** (added effective **2026-06-22**). Market-model beta 2.48, estimated on 250 days ending a month before the event. **AR on the effective day: +6.07%.** Code: [`poc/seed3_index_effect_poc.py`](poc/seed3_index_effect_poc.py).
- **What broke:** the Wikipedia changes table **is gone from the live page**, so a naive scraper silently gets only the current constituents. We fixed this by pinning an old revision ID.
- **Worries:** FLEX's ARs swing ±6–7% on nearby days, so one firm is very noisy. The beta of 2.48 looks high and needs a hand check. June 19 is missing from the data (Juneteenth), so "event day" must count trading days, not calendar days. **The announcement dates are still missing.** They decide whether this project works.
- **Time to build the full dataset:** effective dates and returns take about an hour. Announcement dates are unknown and depend on how easily the press releases can be scraped.

---

## Idea B (Seed 7): Do analyst upgrades move prices, and does the broker matter?

### 1. The question
When a Wall Street broker upgrades or downgrades a stock, does the price move, and are some brokers' calls worth more than others?

### 2. One row of the final dataset
One row = **one rating change × one event day.**

| ticker | broker | grade_timestamp | day0 | action | from_grade | to_grade | event_day | ar | car_0_1 | near_earnings |
|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | Rothschild & Co | 2026-08-17 20:20 | 2026-08-18 | up | Neutral | Buy | 0 | 0.0192 | 0.0383 | False |
| AAPL | Jefferies | 2026-08-10 12:38 | 2026-08-10 | down | Hold | Underperform | 0 | -0.011 | -0.015 | False |
| MSFT | Morgan Stanley | 2025-01-29 21:05 | 2025-01-30 | down | Overweight | Equal-Weight | 0 | -0.024 | -0.031 | **True** |

_(The first row's ARs are real, from our proof of concept. The other rows are fake.)_

### 3. Raw inputs, and whether we can get them
| Input | Source | Do we know we can get it? |
|---|---|---|
| Rating changes (broker, timestamp, from/to grade, action) | `yf.Ticker(t).upgrades_downgrades` | **Yes.** AAPL has 969 rows from 2012-09 to 2026-10. But only **73 are true up/down changes**: 708 are "main" (reiterations), 170 "reit", and 18 "init". |
| Daily returns | yfinance | **Yes.** |
| Earnings dates (to flag confounded events) | `yf.Ticker(t).earnings_dates` (used in HW6) | **Yes**, from HW6. |
| Firm universe | A fixed list of large firms, chosen as of the start date to avoid survivorship | Needs a point-in-time list. We could reuse Idea A's Wikipedia data. |

### 4. The chart that answers the question
A **broker leaderboard**: the average CAR[0,1] for upgrades (and, separately, downgrades) for each broker, with 95% confidence intervals. Brokers are sorted by mean, and the number of calls is shown next to each bar. Brokers with fewer than about 30 calls are greyed out, so noise doesn't top the ranking.

### 5. The first thing an auditor would attack
**Timestamps and confounds.** Is `GradeDate` in UTC or Eastern time, and was the call made before the open or after the close? Getting this wrong shifts day 0 by a day. Calls issued right after earnings pick up the earnings reaction, so they need to be flagged or dropped. Ranking 40+ brokers also invites picking the winner by chance, so we need a multiple-testing adjustment and a `specs_tried.md` log.

### Proof of concept (Oct 15) — what we learned
- **Got:** a real event row for the **AAPL upgrade by Rothschild & Co (Neutral → Buy)**, stamped 2026-08-17 20:20:47. Beta 0.85. **AR +1.92% on Aug 18 and +1.91% on Aug 19.** Code: [`poc/seed7_ratings_poc.py`](poc/seed7_ratings_poc.py).
- **What the timing problem looks like in real numbers:** if the stamp is UTC (4:20pm ET, after the close), day 0 is Aug 18 and **CAR[0,1] = +3.83%**. If we take the date at face value, day 0 is Aug 17 and **CAR[0,1] = +2.10%**. The same event nearly halves depending on a time-zone assumption. We need to confirm yfinance's time zone, for example against a call with a known press time.
- **Worries:** most rows are reiterations, not changes, so the number of real events per firm is small (~5 per year for AAPL, probably fewer for smaller firms). Broker names may be inconsistent ("B of A Securities" vs. "BofA"). yfinance's history may also only show brokers that still exist, which is a kind of survivorship.
- **Time to build the full dataset:** fast. The ratings and returns for 50 firms take a few minutes to pull, so the work is in cleaning and the earnings-date merge.

---

## Our lean, and the one data question we need answered first
Idea B's data is easier to get. Idea A is a cleaner research question, but it depends on one open question: **can we reliably collect S&P DJI announcement dates for every addition since 2022?**

**Answer (Oct 16): yes.** S&P DJI's newsroom (`press.spglobal.com`, section `s=2429`) can be searched by keyword and paged through with plain `requests`, no agent needed.
- Every "Set to Join S&P 500" release since 2022 has a **summary table** (effective date, index, action, company, ticker), so `pd.read_html` gives us additions and deletions directly. Each page also carries a publication timestamp in Eastern time (`<!-- ITEMDATE: 2026-06-05 19:25:00 EDT -->`).
- **84 additions from 53 releases**, 2022-01 to 2026-10. All 78 Wikipedia additions with a release match on ticker, and the effective dates agree for 77 (PANW: the release says Jun 19, 2023, a market holiday, and Wikipedia says Jun 20; both are the same first trading day).
- **Wikipedia's "83 additions" includes 5 that aren't additions**: CPAY, DAY, EG, and WTW are ticker changes, and WBD is the Discovery/WarnerMedia merger. A Wikipedia-only event study would include them as fake events.
- **Every release came out between 17:00 and 19:59 ET**, after the close, so the announcement day 0 is always the next trading day. FLEX's announcement is confirmed as **2026-06-05**, so its day 0 is 2026-06-08.
- The 6 additions after the pinned Wikipedia revision (RDDT, BE, P, ILMN, TWLO, VYLR) come from the releases alone. **The releases are the primary source, and Wikipedia is now only a cross-check.**

Idea B's open question has an answer too: yfinance builds `GradeDate` with `pd.to_datetime(epochGradeDate, unit='s')` (`yfinance/scrapers/quote.py`), so the timestamps are **UTC** epoch seconds. That supports the "day 0 = Aug 18" reading for the Rothschild call.

**Our lean: Idea A (Seed 3).** Its riskiest input is solved, and the question is cleaner. Proof of concept for 5 additions: branch `checkpoint1-seed3-poc`.
