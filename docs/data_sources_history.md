# Going back before 2022, and the index-fund ownership data

Research notes after Checkpoint 1 (Nov 4, 2026). Prof. Bowen asked for two things:
- extend the sample to 2010 or earlier, so we can see how the index effect changed over time;
- tell him which WRDS dataset has stock-level index-fund ownership.

We tested the free sources with small scripts (probe scripts not committed). WRDS table and field names come from documentation, not from logging in, so they still need checking.

## 1. Announcement dates before 2022

For every addition we need **both** dates: when S&P announced it (date and time) and when it took effect.

| Period | Source | What we found | Work needed |
|---|---|---|---|
| Jul 2012 – 2021 | **The S&P DJI newsroom we already scrape** (`press.spglobal.com`, s=2429). It starts when S&P Dow Jones Indices was formed. | Keyword search pages back to the first index-change release, 2012-07-26 (Ensco). About 105 S&P 500 release links before 2022 from one keyword (2012: 8 … 2021: 11), and more with our other keywords. | (a) Set `SAMPLE_START` earlier. (b) Add a second table parser: before 2020 the table is "S&P 500 INDEX – *date*" with COMPANY / ADDED / DELETED and no ticker column. Tickers are only in the text, e.g. "(NYSE: ESV)". (c) Fix the time stamps (below). |
| Jan 2010 – Jun 2012 | PR Newswire, old "Standard & Poor's" page: `prnewswire.com/news/standard-%26-poor%27s/?page=N&pagesize=25` (16 pages, back to 2010-01-04) | Releases titled "Standard & Poor's Announces Changes to U.S. Indices", with HTML tables. Example: Netflix and F5 added, released 2010-12-09. | New small scraper, same table logic as the pre-2020 newsroom format. |
| 2000 – 2009 | No free source that's complete | Copies exist on syndication sites (finanzen.at, marketscreener). Wayback has some old S&P PDFs from 2003–2009, but coverage is patchy and there are no times. | Ask for WRDS Capital IQ (below), or check whether Lehigh has Factiva, which carries PR Newswire with time stamps. |

**Time stamp problem before 2017.** The newsroom's `ITEMDATE` and PR Newswire's listing show pre-2017 times like 13:35 or "05:35 ET". These are 12-hour clock times with the AM/PM lost. We checked the Ensco release against StreetInsider ("05:18PM"), and they are really evening releases, after the close. Since January 2017 the stamps are correct (17:00–19:59 ET).

S&P's practice was to announce after the close, so the simple fix is to treat every release before 2017 as after-close: day 0 = next trading day. We'd hand-check a few against news stories.

**Researcher datasets.** We found no free file with announcement dates:
- Greenwood & Sammon took theirs from **Siblis Research**, which is a paid service.
- Patel & Welch (2017) did not post their dates.
- We found no replication package on GitHub, Kaggle or openICPSR.

**Effective dates alone are easy.** Wikipedia's changes table (our pinned revision) has 407 rows with effective dates only. It is dense from about 2007 and sparse before.

## 2. Index-fund ownership (Prof. Bowen's offer to pull it)

The papers on this topic build index-fund ownership from mutual fund holdings:
- **Greenwood & Sammon** use "the Thompson S12 data on the quarterly holdings of mutual funds and ETFs", split-adjusted with CRSP.
- **Appel, Gormley & Keim (2016)** merge S12 with the CRSP Mutual Fund database "using the MFLINKS table". They flag a fund as passive if its name says index or CRSP classifies it as an index fund.
- **Coles, Heath & Ringgenberg (2022)** use the CRSP index fund flag.

For 2010 and later, CRSP's own holdings data is the better choice. WRDS notes the CRSP holdings are "reliable only after June 2010". Thomson S12 misses many newer index funds and ETFs (Zhu, *Management Science* 2020).

**Simple construction.** For each addition:

> index-fund share = shares held by all funds CRSP flags as index funds or ETFs, at their last report before the announcement ÷ CRSP shares outstanding at the same date.

If the fund-level data is too heavy, there are two fallbacks:
- 13F institutional ownership (`tfn.s34`);
- Appel, Gormley & Keim's proxy: the 13F holdings of Vanguard + BlackRock + State Street.

## 3. What to ask Prof. Bowen for (WRDS)

1. **CRSP stock data:** daily returns (`crsp.dsf`, or `dsf_v2`), `stocknames`, and S&P 500 membership (`crsp.dsp500list`, or `dsp500list_v2`), 2000 to now. This also fixes our survivorship problem: yfinance has no prices for many firms that were later acquired or delisted, and CRSP permnos stop reused tickers from matching the wrong firm.
2. **Capital IQ Key Developments** (`ciq.wrds_keydev`), event type "Index Constituent Adds/Drops". We understand it has announcement dates from about 2001, which would give us 2000–2011 announcement dates. *(Event-type IDs and whether there is a time field are unverified.)*
3. **CRSP Mutual Fund holdings** for the ownership variable:
   - `crsp.holdings` + `crsp.holdings_co_info` (for permno);
   - `crsp.portnomap`;
   - fund header history (`crsp.fund_hdr_hist`) with `index_fund_flag` and `et_flag`;
   - 2010 to now.
   - If we go before 2010: Thomson S12 (`tfn.s12`) + MFLINKS.

## Risks we know about

- Pre-2017 release times need the after-close assumption above.
- PR Newswire listings skip some releases (e.g. Tractor Supply, Jan 2014), so the newsroom stays the main source and PR Newswire only fills 2010–2012.
- Before 2012, one release often covers several companies. Before 2020 the tables have no ticker column.
- S&P did not announce additions in advance before October 1989, so the two-date design only works after that.

## Sources

- S&P DJI newsroom search: https://press.spglobal.com/index.php?s=2429
- PR Newswire, S&P Dow Jones Indices: https://www.prnewswire.com/news/s%26p-dow-jones-indices/
- PR Newswire, Standard & Poor's (2010–2012): https://www.prnewswire.com/news/standard-%26-poor%27s/
- Greenwood & Sammon, "The Disappearing Index Effect" (NBER w30748): https://www.nber.org/papers/w30748
- Appel, Gormley & Keim (2016), "Passive investors, not passive owners": https://corpgov.law.harvard.edu/wp-content/uploads/2019/11/Appel-Todd-Gormley-Donald-Keim.pdf
- Coles, Heath & Ringgenberg (2022), index ownership: https://papers.ssrn.com/abstract=3055324
- Zhu (2020), *Management Science*, S12 coverage: https://pubsonline.informs.org/doi/10.1287/mnsc.2019.3454
- WRDS, "Ownership Data on WRDS": https://wrds-www.wharton.upenn.edu/documents/1414/WRDS_Ownership_Data.pdf
- CRSP Mutual Fund Database guide (index_fund_flag, et_flag): https://kkwoo.sdf.org/files/MFDB_Guide.pdf
- Siblis Research (paid): https://siblisresearch.com/data-services-pricing/
