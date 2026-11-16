# Instructor audit: Dream Team, Checkpoint 2

**Repo:** dao528/Dream-Team-Final-Project · **Audited commit:** `f212ecc` (2026-11-11, merge of PR #7 into `main`) · **Seed:** 3, the disappearing index effect

> Note from your human teacher: This review is generated with minimal supervision from Opus 5.5-high. It is thorough, but can be too generous at times and doesn't know my taste for what is "good". Grades it and I would assign are correlated, but noisy, ok? If you want additional feedback from _me_, you need to find me before/after/during class or during office hours for a guaranteed speedy reply. I will try to respond to emails and issues, but can not respond to student inquiries around the clock across the final weeks of class. Response times will be unpredictable, though during Thanksgiving week, I will do my best to respond quickly virtually, as in person options will be nil.

## Summary

The 2022+ half of the pipeline holds up. I rebuilt the additions table from the pinned Wikipedia revision and your committed release parse and got the same table. I also wrote my own event-study code, with my own trading calendar and regression, and it reproduces every CAR for the five v0 additions to four decimals. That holds on your `prices.csv` and on a fresh yfinance pull. I could not rerun steps 03b to 06 because they need the licensed WRDS files, which are not in the repo, so the history sample (2001–2021) was audited from your committed outputs. Before v1, the things that matter most are in the history sample: (1) the event dates come from a volume filter that drops real additions, and your planned replacement uses a different date convention in some years (A1); (2) 15% of the real Key Dev additions are dropped as "not trading" with no names attached, and renamed firms are dropped rather than recovered (A2); (3) batches and same-firm duplicates make events overlap, which the t-tests ignore (A3).

| Check | Result |
|---|---|
| Reruns from scratch | ⚠️ Steps 01, 03 and 07 reproduce exactly. 02 couldn't run here (the newsroom host is blocked in the audit environment, not your bug). 03b–06 need WRDS files the auditor doesn't have. An independent recomputation of the 2022+ CARs matches |
| Inputs have provenance | ✅ pinned Wikipedia revision, pull dates for the newsroom list and yfinance, WRDS pull documented. Gap: the release HTML isn't committed (A5) |
| Keys unique, merges validated | ✅ `assert`s on every key, `validate=` on the merges. Rechecked on the regenerated `additions.csv` and the committed `event_panel.csv` |
| No look-ahead / survivorship | ⚠️ Volume-filter look-ahead (disclosed, A1). Renamed or re-listed firms are dropped (A2) |
| LLM leakage handled | n/a, no LLM in the pipeline |
| `specs_tried.md` complete | ✅ matches `code/config.py` (windows, `MIN_EST_DAYS`, eras, seed 331), including the redraw that flipped 2008–2014 |
| Magnitudes discussed | ⚠️ not yet (your self-audit says so too, A7) |
| Hand checks | ✅ `code/06_hand_check.py` (COIN, CRSP vs. yfinance, Tesla) is well designed. I couldn't rerun it (WRDS), but my independent recomputation matches |
| Threats to validity | ✅ unusually thorough. A1–A4 add evidence and two items |
| Every number traces to `outputs/` | ⚠️ a few counts live only in `data/clean/` or console output (A6) |

## What holds up

- **Day 0 logic.** With my own code and the XNYS exchange calendar (not your SPY dates), I recomputed announcement day 0, rebalance day 0 and the gap for all 84 additions in `data/clean/additions.csv`. 0 of 84 rows differ from `outputs/announce_effective_gap.csv`. Your counts check out: 29 with the announcement inside effective CAR[−1,+1], 4 inside CAR[0,+1], VYLR the only release after the rebalance day, max gap 10, and 51 of 84 sharing a release (53 releases). Every release is stamped 17:00–19:59 ET (12 / 58 / 14 by hour), so the after-close rule applies to all of them. The Juneteenth case (FLEX/MRVL, effective 2026-06-22, rebalance 2026-06-18) and the Juneteenth mismatch with Wikipedia (PANW) are handled correctly.
- **Headline numbers recomputed independently.** I wrote a separate script (XNYS calendar, `np.linalg.lstsq`, estimation days [−250, −30] before announcement day 0). Inputs were your raw `data/raw/prices.csv`, and again a fresh yfinance pull made 2026-11-15. Results:

  | 2022–2026, n = 5 | Your `outputs/car_summary.csv` | Auditor |
  |---|---|---|
  | announce CAR[0,+1] | +0.07699 | +0.07699 |
  | effective CAR[0,+1] | +0.03082 | +0.03082 |
  | effective CAR[−10,+10] | −0.06099 | −0.06099 |

  All 10 event × anchor rows of `outputs/car_windows.csv` match to four decimals, betas included. For COIN and DASH I used yfinance where you used CRSP, and the betas still agree (3.4441 and 1.0472), which supports your CRSP-vs-yfinance check. The fresh yfinance pull differs from your `prices.csv` by at most 0.02 bp in daily returns.
- **Reproducible steps reproduce exactly.** Step 01 rebuilt `data/raw/wiki_sp500_changes.csv` from revision 1368675864: 407 × 7, identical. Step 03 rebuilt `data/clean/additions.csv`: 84 × 11, identical. Its assert that every Wikipedia-only row is a rename or merger passed (CPAY, DAY, EG, WBD, WTW). Step 07 rebuilt `outputs/car_summary.csv` from your `car_windows.csv` identically. The figure plots the same data; only the font differs on my machine.
- **README example rows** (COIN announce/effective, HLT_2017) match `data/clean/event_panel.csv` to the digits shown.
- **Survivorship by design.** The sample comes from S&P's own releases and Key Dev, not today's constituent list. Returns come from CRSP `ret_adj`. Firms deleted or acquired later stay in (MOH, deleted 2026-03-23, and FDO and PDCO in the history draw).
- **Honest reporting.** You record the redraw that moved 2008–2014 from +3.3% to −2.4%. You list every dropped event with a reason. You flag your own look-ahead. This is the standard we want.

## Findings

### A1 · Major · History dates come from a volume filter that drops real additions; the planned replacement (Wikipedia) dates some events differently

**Evidence:**
- `code/config.py:53` (`HISTORY_PEAK_DAY = -1`) and `code/03b_build_history_additions.py:143` keep a Key Dev addition only if its CRSP volume peak is on the rebalance day. `outputs/history_date_check.csv`: 58 real additions are dropped as "volume peak elsewhere", 26 of them with the peak one day off (20 at 0, 6 at −2; counted from `outputs/history_dropped.csv`).
- Concrete case from your own file: Moderna (permno 18312) has two Key Dev rows, 2021-07-20 (`trading_days_to_peak` 0) and 2021-07-22 (−2). Both point to a volume peak on 2021-07-20, yet neither row passes, so a real addition disappears. PTC (2021-04-21, −2) is another.
- Your README (line 83) proposes Wikipedia dates from 2007 on for v1. I matched the 12 sampled history events to `data/raw/wiki_sp500_changes.csv` (same ticker, within 400 days). 7 are in the table. 5 have Wikipedia's date equal to your `effective_date`. 2 do not, and in both Wikipedia's date equals your **rebalance day**: RRC (Key Dev 2007-12-21, Wikipedia 2007-12-20) and HP (Key Dev 2010-03-01, Wikipedia 2010-02-26). For 2022+ Wikipedia follows the effective-date convention (77 of 78 agree). So its convention is not uniform across years.

**Why it matters:** The research question is the change across eras. Which history events survive depends on post-event volume and on one-day offsets in Key Dev. Switching to Wikipedia without a convention check would move day 0 by one trading day for some events, which is the whole effect at CAR[0,+1].

**Fix:** For v1, build history dates that don't use post-event volume. Use Wikipedia (2007+) or the archived S&P releases. Before switching, classify each Wikipedia date as "effective date" or "rebalance close" by comparing it with Key Dev and the calendar, and document the rule. Report the history CARs with and without the volume filter, as you planned. Collapse duplicate Key Dev rows for the same permno (see A3) before applying any date rule.

**How to show it's fixed:** A table in `outputs/` with, for each history addition, the Key Dev date, the Wikipedia date, the chosen effective date and the rule used, plus counts by era. Also the CAR summary with and without the volume filter. The auditor will recount the Wikipedia matches and check RRC, HP and MRNA.

### A2 · Major · 80 history additions are dropped as "not trading" with no names, and renamed or re-listed firms are dropped instead of recovered

**Evidence:**
- `code/03b_build_history_additions.py:138-145`: an addition with no CRSP row for its permno on the rebalance day is dropped as "not trading on rebalance day". Ticker and company come from that same CRSP merge, so in `outputs/history_dropped.csv` all 80 such rows have blank `ticker` and `company` (checked: 80 of 80 blank). Nobody can tell from the outputs which are spin-offs and which are permno mismatches.
- The drop rate is not flat across eras (from `outputs/history_date_check.csv`, real additions = total minus backfill): 2001–2007 21/172 = 12.2%, 2008–2014 16/153 = 10.5%, 2015–2021 43/194 = 22.2%.
- Your README (line 86) already finds two renamed or re-listed firms, Ensco and Invesco. IVZ_2008 is dropped in `outputs/dropped_short_history.csv` with `n_est` = 149, which leaves the 2008–2014 era at n = 3 in `outputs/car_summary.csv`.
- For v1, 21 of the 84 2022+ additions have effective windows ending after 2025-12-31 (my count from `outputs/announce_effective_gap.csv`), so they will use yfinance by ticker. `code/04_download_returns.py:79-82` prints, but does not save or check, which additions failed the CRSP link.

**Why it matters:** This is the survivorship item for this seed. Renamed, re-listed or later-delisted firms need their returns found another way, not dropped. If the 2015–2021 drops include permno changes and not only spin-offs, the eras differ in sample composition.

**Fix:**
1. Write Key Dev's company name or headline into `history_dropped.csv` (they come from Key Dev, not CRSP, so they exist for every row).
2. For each "not trading" and short-history drop, look for a predecessor permno (CRSP stock names by CUSIP or company name, or the CCM link history by gvkey). Where it is the same economic firm (IVZ, ESV), splice the predecessor's returns into the estimation window.
3. Report how many drops were recovered, and the remaining reasons by era.
4. In step 04, save the list of 2022+ additions that fall back to yfinance and why. Assert that every 2022–2025 addition with pre-announcement trading links to CRSP.

**How to show it's fixed:** The auditor will open `history_dropped.csv` and expect a name on every row. The auditor will also check that IVZ_2008 is either back in the sample or dropped for a stated reason other than a new permno, and that a saved yfinance-fallback list exists.

### A3 · Minor · Overlapping events: batches share dates, and the same firm can appear twice

**Evidence:**
- My count from `data/clean/additions.csv`: the 84 2022+ additions have only 53 distinct announcement day 0s and 56 distinct rebalance days.
- In v0, FLEX and MRVL come from the same release and share both day 0s. On 2026-06-02 (announce day −4) their ARs in `data/clean/event_panel.csv` are +7.2% and +32.0% on the same calendar day.
- `code/07_summarize.py:113-118` runs a one-sample t-test over events as if they were independent.
- In the history sample, Key Dev has the same permno on two nearby dates: Moderna (18312, 2021-07-20 and 2021-07-22) and permno 90435 (2004-12-02 and 2004-12-03), both in `outputs/history_dropped.csv`. `03b` only asserts uniqueness of (permno, keydev_date) and (permno, effective_date), at lines 115 and 165. Today the volume filter happens to drop both pairs, but once you drop the filter in v1 (A1), these firms enter twice with overlapping windows.

**Why it matters:** This seed's auditors check overlapping events. Events on the same dates share market-wide and sector shocks, so the effective sample size is closer to the number of dates than the number of additions. Duplicated firms double-count.

**Fix:** Keep the plain t-tests you agreed on, and add two things. (1) Report `n_dates` (distinct day 0s) next to `n` in `car_summary.csv`. (2) Report a second plain t-test on one average CAR per release date. Also add a rule that collapses same-permno Key Dev additions within, say, 10 trading days into one event, with an `assert`.

**How to show it's fixed:** `car_summary.csv` has `n_dates` and the by-date version. A re-run of 03b without the volume filter produces no permno with two events within 10 trading days.

### A4 · Minor · The [−10,+10] windows mix in other news and, for every 2022+ addition, the announcement

**Evidence:**
- MRVL rose 32.5% on 2026-06-02, announce day −4 (AR +0.3195 in `data/clean/event_panel.csv`). That one day causes most of the jump around day −4 in the right panel of `outputs/fig_mean_car_by_era.png`.
- It also drives the 2022–2026 announce CAR[−10,+10] mean: +0.1187 with MRVL, +0.0376 without (auditor's recomputation).
- Every one of the 84 2022+ additions has its announcement day 0 inside the effective [−10,+10] window (max gap 10, auditor's recount). So the effective CAR[−10,+10] of −6.1% is not an effective-date effect.
- You disclose both points (README lines 74 and 76), but the figure and `car_summary.csv` present the long windows without a flag.

**Why it matters:** A reader of the dashboard will read the long-window lines as the index effect.

**Fix:** Flag confounded events in the data (earnings or other large news inside the window, with a source for the date), and report the long window with and without them. For the effective anchor, report a window that starts after announcement day +1, as you proposed, or drop [−10,+10] from the headline.

**How to show it's fixed:** A `confound` column in `events.csv`, with a source per flag, and `car_summary.csv` rows with and without the flagged events.

### A5 · Minor · The press-release pages behind the announcement times aren't committed

**Evidence:** `.gitignore:8` ignores `data/raw/spdji_releases/`. As a result, `code/02_download_announcements.py:85-90` re-downloads every release page on every fresh clone, even without `--fresh`. Announcement times come from each page's `ITEMDATE` comment (line 119), and the live newsroom is not pinned. In the audit environment, step 02 stopped at the first page download (the host is blocked here, which is not your bug). So the timestamps could not be re-derived, and that `ITEMDATE` is US Eastern publication time is **not verified** by the auditor. Your self-audit lists the timestamp check as still open.

**Why it matters:** Announcement day 0 for all 84 additions rests on these timestamps. If a page changes or disappears, a rerun silently changes or fails.

**Fix:** Commit the cache (about 5 MB is fine for GitHub), or commit a manifest with url, sha256 of the page, and the extracted `ITEMDATE`. Add a hand check of three timestamps against an independent source, such as a news story giving the release time, in `06_hand_check.py`.

**How to show it's fixed:** Step 02 runs offline from a fresh clone, and the hand check prints the three comparisons.

### A6 · Minor · A few reported numbers don't trace to a file in `outputs/`

**Evidence:** I verified every number below, but each lives only in `data/clean/` or in console output:
- "51 of 84 additions share a release" (README line 73). Derivable only from `data/clean/additions.csv`.
- "84 additions from 53 releases" (`PROPOSAL.md`, `STATUS.md`). Printed by step 03, not saved.
- "77 of the 78 … agree" (`STATUS.md`). From `additions.csv`.
- COIN's "+21.8% announcement-day AR" and "+23.97%" (README line 74, `STATUS.md`). In `data/clean/event_panel.csv`.

**Fix:** Have step 03 write its printed counts to `outputs/sample_counts.csv`, and cite that file and `car_windows.csv` next to each number.

**How to show it's fixed:** Each number in README, PROPOSAL and the dashboard text points to a file in `outputs/` that contains it.

### A7 · Minor · Magnitudes not yet discussed, and `STATUS.md` is still the Checkpoint 1 memo

**Evidence:** `audits/01_self_audit.md:30` ("Magnitudes: not yet"). `STATUS.md:1` ("Status memo: Checkpoint 1 (Oct 23)").

**Fix:** Put the CARs in economic terms. For example, CAR[0,+1] times market value at day −1 gives dollars per addition. Or compare with the magnitudes in Greenwood & Sammon for the same windows, and say what transaction costs a trader would face. Update `STATUS.md` for Checkpoint 2.

**How to show it's fixed:** A magnitudes paragraph in the README with numbers traceable to `outputs/`, and a current `STATUS.md`.

## How to respond

This audit is `audits/02_instructor_audit.md` in your repo. Fix what you can, then add `audits/03_audit_response.md`, replying to each finding ID: fixed (the commit), disputed (why), or disclosed as a limitation (where).

**Deadline: Saturday, November 21, 2026.**
