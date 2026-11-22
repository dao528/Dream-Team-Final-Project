# Instructor audit: Dream Team, Checkpoint 3

**Repo:** dao528/Dream-Team-Final-Project · **Audited commit:** `6a57ca2` (2026-11-20, `main`, merge of PR #13) · **Seed:** 3, the disappearing index effect · **CP2 audit:** `audits/02_instructor_audit.md` (commit `f212ecc`)

> Note from your human teacher: This review is generated with minimal supervision from Opus 5.5-high. It is thorough, but can be too generous at times and doesn't know my taste for what is "good". Grades it and I would assign are correlated, but noisy, ok? If you want additional feedback from _me_, you need to find me before/after/during class or during office hours for a guaranteed speedy reply. I will try to respond to emails and issues, but can not respond to student inquiries around the clock across the final weeks of class. Response times will be unpredictable, though during Thanksgiving week, I will do my best to respond quickly virtually, as in person options will be nil.

## Summary

The 2001–2021 history sample is now complete and careful, and most CP2 findings are fixed with real evidence.
- Every dropped event has a name.
- The date rules are tabulated, and the volume filter is reported as a robustness row.
- Batches are counted with by-date tests, and the release pages are committed.
- Steps 01–03 and 07 reproduce exactly from a fresh copy, offline.

But the question the seed is about, announcement vs effective date in 2022–2026, still runs on the 5 proof-of-concept additions (B1). Your README says so. A quick yfinance version I ran on 69 of the 84 additions suggests the full sample has a clear answer, so this is the most valuable thing to finish. The dashboard is still the v0 skeleton with placeholder text (B2).

## Follow-up on your Checkpoint 2 audit

Response file: not found. The statuses below come from the repo itself.

| CP2 finding | Status | Evidence |
|---|---|---|
| A1 · History dates from a volume filter | fixed | `outputs/history_dates.csv` (498 additions: Key Dev dates, Wikipedia date, rule, chosen date, `passes_volume_filter`) and `history_date_rules.csv` (counts by era, which I recounted from `history_dates.csv` exactly). `car_summary_history_dates.csv` has "all", "v0 volume filter", "without ambiguous dates" and "Key Dev and Wikipedia agree" rows. RRC and HP: `ambiguous`, Key Dev date kept. MRNA: Key Dev listed it twice, so the Wikipedia date (2021-07-21) is used, which matches the S&P release quoted in `06_hand_check.py` ("effective prior to the opening of trading on Wednesday, July 21") |
| A2 · Dropped events have no names; renamed firms dropped | fixed | `outputs/history_dropped.csv`: 134 rows, `company` filled for all 134, each with a `date_check` reason. IVZ_2008 is in the sample (`history_dates.csv`: "keydev only", kept). `history_predecessors.csv` splices ESV's earlier permnos, and `yfinance_fallback.csv` (30 rows) is the saved fallback list |
| A3 · Overlapping events | fixed | `car_summary.csv` has `n_dates`, `mean_by_date` and `t_stat_by_date`, and commit `97866e5` collapses same-permno Key Dev rows within 10 trading days. In `data/clean/events.csv`, the 4 permnos with two events are at least 2,353 calendar days apart |
| A4 · [−10,+10] mixes in other news | disclosed | `README.md:82`: "Confounding news. Earnings inside the window … Not yet flagged in the data." No `confound` column in `events.csv` |
| A5 · Release pages not committed | fixed | Commit `2714ebc`: 76 pages in `data/raw/spdji_releases/`. `python code/02_download_announcements.py` ran offline on a fresh copy (exit 0, 1.5 s), and `03` rebuilt `additions.csv` (84 × 11) identically. `06_hand_check.py` §5 compares 8 history rebalance days with S&P releases. It needs CRSP, so it wasn't rerun |
| A6 · Numbers that don't trace to `outputs/` | fixed | `outputs/sample_counts.csv` (8 × 3) is written by the pipeline, and it regenerated identically |
| A7 · Magnitudes; `STATUS.md` still the CP1 memo | unaddressed | Half fixed. Magnitudes: done (`README.md:71-73`, `outputs/magnitudes.csv`, `08_magnitudes.py`). `STATUS.md:1` still reads "Status memo: Checkpoint 1 (Oct 23)", with no later section (`git log -- STATUS.md`: last changed in `c5db587`) |

**5 of 7 fixed, 1 still open (1 disclosed).**

## Checkpoint 3 checks

| Check | Result |
|---|---|
| Reruns from scratch (full sample) | ⚠️ `01`, `02`, `03` and `07` reproduce exactly (07 from the committed `car_windows.csv`). `03b`–`06` and `08` need the WRDS files (see below). The 2022+ sample isn't full (B1) |
| Inputs have provenance | ✅ pinned Wikipedia revision, committed release pages, WRDS files documented, README provenance table |
| Keys unique, merges validated | ✅ `assert`s on event keys. My check of `events.csv` finds no near-duplicate permno events |
| No look-ahead / survivorship | ✅ the volume filter is now a robustness row, and additions come from S&P's own releases and Key Dev, not today's list |
| LLM leakage handled | n/a |
| `specs_tried.md` complete | ✅ matches `config.py`, including the date-rule switches |
| Magnitudes discussed | ⚠️ yes, but for the 5 v0 additions only (`README.md:73`) (B1) |
| Hand checks | ✅ `06_hand_check.py` (COIN by hand, CRSP vs yfinance, release stamps, 8 history dates vs releases). Not rerun here (CRSP) |
| Threats to validity | ✅ thorough, including overlapping windows, Key Dev date types and spin-offs |
| Every number traces to `outputs/` | ✅ `sample_counts.csv`, `car_summary*.csv`, `magnitudes.csv` |
| Dashboard matches `outputs/` | ⚠️ the numbers match ("Additions in this version 414" = `car_windows.csv` events; "Coinbase … +23.9%" = 0.2395), but the text is the v0 skeleton (B2) |

Steps not rerun by design: `03b_build_history_additions.py`, `04_download_returns.py`, `05_build_event_panel.py`, `06_hand_check.py` and `08_magnitudes.py` read instructor-provided WRDS/CRSP files. I started from your committed `history_additions.csv`, `event_panel.csv` and `car_windows.csv`. These are not counted against you.

## Getting ready for Dec 1

Presentations run only from URLs, with a hard cutoff at 9 minutes (10:45 section) or 10 minutes (12:10 section). Put your URL(s) in column G of the Team Projects sheet.

| Check | Result |
|---|---|
| Dashboard launches from a clean clone | ✅ in a venv from `dashboard/requirements.txt` (streamlit 1.67.0, pandas 3.1.1, altair 6.3.0): `streamlit run dashboard/app.py --server.headless true --server.port 8603` on a clean export of `6a57ca2`. `/_stcore/health` returned `ok` after 3 s. A headless browser clicked all 4 tabs, with no exceptions on the page or in the log |
| Dashboard shows the v1 numbers from `outputs/` | ⚠️ it reads `event_panel.csv`, `car_windows.csv` and `car_summary.csv` (`dashboard/app.py:30-32`). The text is stale (B2) |
| README links the live URL(s) | ✅ `README.md:2` links dream-team-index-effect.streamlit.app (the live site itself wasn't checked) |

**Core story for 9–10 minutes:** two day 0s; the 2022+ announcement-vs-effective comparison on the full sample (B1); the 2001–2021 effective-date CARs by era (a positive 2001–2007 effect that fades, `car_summary.csv`); and the magnitudes (who can trade it). The date-rule detail can be one backup slide.

## What holds up

- **Offline reproduction.** On a fresh copy, `01` (pinned revision) and `02` (committed pages) made no downloads. `03` rebuilt `additions.csv` and `spdji_sp500_actions.csv` identically. `07` rebuilt `car_summary.csv` (15 rows) and `car_summary_history_dates.csv` (36 rows) to within 5e-16. All the `history_*.csv`, `sample_counts.csv` and `yfinance_fallback.csv` files match.
- **Independent recomputation.** With my own market model (yfinance vs SPY, sessions −250 to −30 before the announcement, as in `config.py`), CAR[0,+1] for the 5 v0 additions matches `car_windows.csv` to 4 decimals on both anchors. For example, COIN is +0.2395 at the announcement and +0.0568 at the rebalance close, and FLEX is −0.0337 and +0.0676.
- **The history sample is now honest.** It has every Key Dev addition, named drops with reasons, the volume filter reported both ways, and spliced predecessors. The 2001–2007 effective-date CAR[0,+1] is +0.81% (t = 2.59, n = 142), and later eras are near zero. That's the disappearing effect, on the effective date.
- **The A5 fix is thorough.** It covers the committed pages, a check of every stamp, and 8 history dates checked against S&P's own release text.

## New findings

### B1 · Blocking · The 2022–2026 comparison still runs on the 5 proof-of-concept additions

**Evidence:** `code/config.py:34` `POC_TICKERS = ["FLEX", "MRVL", "VEEV", "DASH", "COIN"]`. `code/04_download_returns.py:45-46` keeps only those. `outputs/car_summary.csv`: `releases_2022on` rows all have n = 5. `README.md:21`: "The 2022+ sample is still the 5 v0 additions (… set it to `None` for all 84)."

**Why it matters:** "Does the **announcement** date or the **effective** date matter more?" is the seed's question, and it's answered only by the 2022+ sample, which has both dates. With n = 5, the README's magnitudes paragraph can't say anything general. An indicative run of my own shows the full sample is informative. It uses yfinance only, with your market model and both of your day-0 definitions, on the 69 of 84 additions with at least 200 estimation days (13 are new listings or spin-offs with no history, 1 isn't on Yahoo, 1 has 167 days):

| Anchor | n | Mean CAR[0,+1] | Median | t | p |
|---|---|---|---|---|---|
| Announcement | 69 | **+4.46%** | +3.61% | 6.13 | < 0.0001 |
| Effective (rebalance close) | 69 | −1.02% | −0.53% | −1.90 | 0.062 |

These are my numbers, not yours, and they use Yahoo rather than CRSP, so treat them as a target to check, not a result.

**Fix:** Set `POC_TICKERS = None`, rerun 04–08 with the CRSP files, and handle the 13 new listings as your history sample does (fallback list, or excluded with a reason). Log the run in `specs_tried.md`, then update the README results and the magnitudes paragraph.

**How to show it's fixed:** `car_summary.csv` has `releases_2022on` rows with n ≈ 70. I will recompute the announcement CAR[0,+1] from yfinance and compare.

### B2 · Major · The dashboard is still the v0 skeleton

**Evidence:** `dashboard/app.py:1` "Dashboard skeleton (Checkpoint 2, v0)". The rendered page shows "v0: small sample, placeholder text." (`app.py:39`), "PLACEHOLDER. One or two sentences on the question…" (Intro tab), "PLACEHOLDER. Plain-language version of the steps below." (Methodology tab), and "v0 has only 3 to 5 additions per era" (`app.py:98`), while `car_summary.csv` has 127–142 per history era.

**Why it matters:** Presentations run from this URL. Placeholder text on screen on Dec 1 would undercut a careful project.

**Fix:** Replace the placeholders, drop the v0 captions, and after B1, show the announcement-vs-effective comparison on the Results tab.

**How to show it's fixed:** No "PLACEHOLDER" or "v0" text in `dashboard/app.py`.

## How to respond

This audit is `audits/04_instructor_audit.md` in your repo. Fix what you can, then add `audits/05_audit_response.md`, replying to each **B** finding and to each CP2 finding still open (A7): fixed (the commit), disputed (why), or disclosed as a limitation (where).

There's no separate deadline for this response. Keep working through these until your final deliverables are due: the final repo is audited again then.
