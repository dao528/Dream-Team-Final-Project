# Self-audit 1 (Checkpoint 2)

We ran a skeptical review of branch `checkpoint2-v0` on Nov 10 (the `auditor` agent in `.claude/agents/`, based on the course's Skeptical review prompt) and fixed what it found in commits `cefcad2` and `bb16d62`. Below is the result for each point of the course's 10-point list. The dashboard (`dashboard/app.py`) and `PROPOSAL.md` were added after the review and are not covered yet.

## 1. Reproduces

We ran `run_all.py` twice and got exactly the same files both times. Only `STATUS.md` is out of date, because it is still the Checkpoint 1 memo.

## 2. Provenance

Because `data/raw/prices.csv` had no pull date and came from an old config, a new download could give slightly different numbers. Now the end date is fixed in `code/config.py` (`PRICES_END`), and the README says we pulled it on 2026-11-10. The README also said CRSP has every firm that was ever in the S&P 500. That was too strong: it has the 1,130 permnos from the membership spells Prof. Bowen rebuilt, because the official `dsp500list` was not available.

## 3. Unit and keys

Every merge has `validate=` and the keys are checked with asserts. We found out that there were 36 fake additions in Key Dev, all on Saturday 2005-01-29. They are long-term members like AT&T and Fannie Mae listed as "added", and 4 of them passed our date check. We drop them now, so 377 of 555 additions are kept. We also had no check that S&P's release comes before the rebalance day. VYLR's release came after it, so now we drop events like that and list them in `outputs/dropped_short_history.csv`.

## 4. No look-ahead

The estimation window ends 30 trading days before the announcement, so it never contains the news. But our date check for 2001-2021 looks at trading volume up to 15 days after day 0, so we pick events with data from after the event. This is still open. In v1 we want dates that don't need volume (old S&P releases, or Wikipedia from 2007 on), and we will also show results without the filter.

## 5. LLM leakage

No LLM is used on the data, so there is no leakage.

## 6. No p-hacking

Every specification is in `specs_tried.md`, and we chose the eras before we saw results. Fixing the fake additions changed our random v0 sample, and the 2008-2014 mean CAR[0,+1] went from +3.3% to -2.4% (spec #5). This shows how noisy 4 events per era are. One weak spot: our commits have the same timestamp, so git can't show in which order we did things.

## 7. Magnitudes

Our results are in percent in the README and the figure. `outputs/car_summary.csv` uses decimals (0.01 = 1%), which is now written in `code/07_summarize.py`. We also added CAR[-10,+10] to the summary.

## 8. Hand checks

We recomputed COIN's beta and CAR by hand from raw CRSP and got the same numbers (`code/06_hand_check.py`). We also check that CRSP and Yahoo agree, now with MRVL too because it pays dividends (max gap 0.8bp), and that our effective day 0 rule gives Tesla's record closing auction on 2020-12-18. Still open: an independent check of the announcement times.

## 9. Honest limits

For 29 of the 84 additions since 2022, the announcement falls inside the effective [-1,+1] window, so part of the effective CAR is really the announcement (`outputs/announce_effective_gap.csv`). The README now says this and also counts the drop reasons correctly: 36 backfill, 80 not trading on the rebalance day, 4 without a volume test, 58 with the volume peak on another day.

## 10. Explainable

The README now explains the drop rules exactly like the code does them.

## Still open for v1

- the look-ahead in the volume filter (point 4)
- how to handle the window overlap: only events with a longer gap, or effective windows that start after announcement day +1
- the parser for old S&P releases: they say "effective after the close of X", so our day 0 rule would be one day off there
- small n in v0: the t-stats at n = 4 mean nothing, and the dashboard should not mark them as significant
- update `STATUS.md`
