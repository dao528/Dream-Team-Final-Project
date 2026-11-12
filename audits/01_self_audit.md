# Self-audit 1 (Checkpoint 2)

Source: the auditor agent's skeptical review (Nov 10) & what we fixed (commits `cefcad2`, `bb16d62`).
Not covered yet: `dashboard/app.py` and `PROPOSAL.md` (added after the review).

## 1. Reproduces: OK

We ran the `run_all.py` file multiple times and got the same results. Only the file `STATUS.md` is out of date, because it is still the Checkpoint 1 memo.

## 2. Provenance: OK

Because `prices.csv` had no pull date and it came from an old config, a new download could give different numbers. We fixed the end date in `config.py` and wrote in the README that we pulled it on 2026-11-10.

## 3. Unit and keys: OK

We found out that there were 36 fake additions, which were e.g. long-term firms stated as added. We dropped them, so in total 377 are kept. Because VYLR's release came after its rebalance day and we had no check that S&P's release comes before the rebalance day, we now drop events like that and list them.

## 4. No look-ahead: problem

Because the date check for 2001 to 2021 looks at trading volume up to 15 days after day 0, we pick events using data from after the event, but this is still open. In v1 we want dates that do not need the volume and also we will show results without the filter.

## 5. LLM leakage: OK

We do not use an LLM on the data, so there is no leakage.

## 6. No p-hacking: OK

We chose the eras before we saw the results, and every specification is in `specs_tried.md`. Fixing the fake additions changed our random sample, such as 2008-14 went from +3.3% to -2.4%.

## 7. Magnitudes: not yet

We have our results in percent in the README and the figure. For `car_summary.csv` we use decimals, which is also written in the code now.

## 8. Hand checks: OK

By hand we recomputed COIN's beta as well as the CAR from the raw CRSP, where we got the same numbers. Additionally we checked that CRSP and Yahoo agree, also for MRVL because it pays dividends. Still open is the check of the announcement times.

## 9. Honest limits: problem

Since 2022, for 29 of 84 additions the announcement falls inside the effective [-1,+1] window. So the effective CAR is partly really the announcement.

## 10. Explainable: not yet

The README is updated so the drop reasons match the related code.

## Still open for v1

- 4. volume filter look-ahead
- how to handle the window overlap
- the old parser of S&P releases
- v0 small n: e.g. 2015-21 t-stats at n=4 mean nothing, should not be starred in the dashboard
- `STATUS.md` update
