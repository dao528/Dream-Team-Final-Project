# Specifications tried

Every specification we run goes here, including the ones we drop. Newest at the bottom.

| # | Date | Sample | Day 0 rule | Estimation window | Model | Outcome windows | Result / note |
|---|---|---|---|---|---|---|---|
| 0 | 2026-10-15 | FLEX only (`poc/seed3_index_effect_poc.py`) | effective date, calendar days | 250 days ending 30 calendar days before | market model vs SPY, `np.polyfit` | AR by day | effective-day AR +6.07%, beta 2.48. Superseded by #1 (calendar-day windows). |
| 1 | 2026-10-16 | 5 additions: COIN, DASH, FLEX, MRVL, VEEV (`run_all.py`) | announce: next trading day after the release (all releases after the close). effective: first trading day on or after the effective date | trading days [-250, -30] relative to the announcement day 0, for both anchors | market model vs SPY | CAR[-1,+1], CAR[0,+1], CAR[-10,+10] | COIN announce CAR[0,+1] +24.0%; FLEX effective-day AR +6.0%. Proof of concept only, no averages or tests yet. |
