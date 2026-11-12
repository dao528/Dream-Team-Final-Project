# The Disappearing Index Effect
Dream Team: Karthik Sekhar, Daniel Outkou, Manuel Casanova Jr, Tom Sickert

## Question and who would pay for the answer

**Question:** Our project seed idea that we picked in class is pretty much when a stock gets added to the S&P 500, what we want to know is if the price jump between when the S&P says a company is joining, and when index funds actually buy the stock, has shrunk over time.

**Who would pay for the answer?:** Index funds are forced to buy every new company that joins at the closing price(because S&P make the index), so if the stock price goes up after the announcement, the investors will end up overpaying. Then we see hedge funds used to make money by buying right after the announcement and selling to index funds later, but if that price jump disappears, that trade and the hedge fund would no longer make money. So index funds and hedge funds would probably pay for that answer.

**Background(research)+why this is interesting:** I saw that back in the late 1970s, researcher Andrei Shleifer found stocks jumped about 3% when added and in the 1990s, research from researchers Greenwood and Sammon show that jump grew to around 7%. Today that price rising has faded to under 1%. I think it is very interesting to watch a financial gap that can make you money disappear as the market gets smarter and adjusts to it and knows that it is happening. That just means that people have to find new shortcuts and gaps to make money.

## Data

One row of the data is a S&P 500 addition, an anchor (announcement date / effective date) and a trading day from -10 to 10 around this anchor. So the key is event_id and anchor and event_day. From 2001 to 2021, the 377 additions only have the effective anchor. We have 555 of them from Capital IQ Key Dev and keep 377. CRSP starts in January 2000 but our market model need around 250 trading days before day 0, which is why our sample starts in 2001. Then from 2022 we use S&P’s own press releases, because they have the announcement date, the release time and effective date, which are 84 additions from 53 releases. Until end of 2025 the returns come from CRSP and after that we use Yahoo Finance.

In the data, there are 36 fake additions because of Key Dev backfills which get dropped, and 80 that were not trading on the rebalance day yet (spin-offs, new listings). 4 are with no volume tests. There are also 58 with the volume peak on a different day, which we drop too. All events also need at least 200 days, so we drop spin-offs and firms that have a new permno. We also drop 5 Wikipedia additions, because they are merger or ticker changes.

The data must-have variables are both dates, daily returns including delisting returns, SPY return and a permno link. For index-fund ownership we plan to use Sammons’s passive ownership file or the Coles, Heath and Ringgenberg data (v1). Nice-to-have are the announcement dates for 2012 to 2021, market cap (for a size comparison), earnings dates and deletions.

From the S&P newsroom releases we get the raw inputs scraped for the announcement time and effective date.The Wikipedia changes table is then a cross check and pinned to a revision. From WRDS we got CRSP daily from 2000 to 2025 and the Capital IQ Key Dev events (They are licensed, so they stay out of our public repo). From Yahoo Finance we get SPY from 1999-11-08 to 2026-11-09 plus the 2026 additions pulled on 2026-11-10.

## Method

In the pipeline we use one file per step. Python run_all.py runs it all. With 01 and 02 we get the Wikipedia changes as well as the S&P’s releases. Then 03 and 03b build the additions and 04 gets the returns. Furthermore 05 runs the market model, 06 checks some numbers by hand and with 07 we make t-tests and a figure.

Because S&P announces after the close, the next trading day is the announcement day 0. The last trading day before the effective day is then the effective day 0, which is the closing auction where index funds buy. For example Tesla’s record auction on 2020-12-18 matches our rule.

For the market model we use SPY, and estimate it on trading days -250 to -30 before the announcement day 0, with its CARs over [0, +1] , [-1, 1] and the [-10, 10]. Then we test the mean CAR per anchor as well as era with t-tests. When we compare 2 dates, we see which one matters and by comparing eras we see whether the effect is disappearing.

There is one problem: for 29 of the 84 additions (since 2022), the announcement falls inside the effective [-1, 1] window.

## Threats and checks, plus the raw-input table with sources

The biggest threat is separating the market's reaction to the firm being added to the index, versus when the company actually gets added. For many of the additions the two dates are only a few trading days apart, so a wider event window overlaps. We report short CAR windows and measure the trading day gap between the two events.In the next version, we plan to test specifications that exclude overlapping portions of the event windows

The second biggest threat is unrelated firm news. Earnings announcements, or any other big announcements relating to the firm may affect the stock price during the same event window. We have already found this issue in the example with COIN and MRVL. These events will be flagged so we test whether results are sensitive to unrelated firm specific news.

The third biggest threat is that historical additions create additional data quality issues. Some firms lack the return history needed to estimate a market model, so our solution for this was that we require at least 200 estimation days and record every dropped observation. Our historical Key Development sample also currently uses a volume-based date check that looks around the event date, which creates potential look-ahead bias. We treat this as a v0 limitation and plan to compare results using dates that do not depend on future volume.

The fourth biggest threat is survivorship bias. If we only looked at companies that are still in the S&P 500 today, we could miss firms that were added and later removed or delisted. We avoid this by using S&P’s own historical addition announcements instead of today’s constituent list. For historical returns, CRSP also keeps data for firms that were later delisted.

The fifth biggest threat is that we also have to consider that many additions are announced in batches. 51 of the 84 additions since 2022 share a release with at least one other company, so those events are not fully independent from each other. We keep the analysis simple and report this as a limitation instead of treating every observation as completely independent.

The sixth biggest threat is p-hacking, where we could keep trying different event windows or specifications until we find a result that looks good. To prevent this, every specification we test is recorded in specs_tried.md, including the ones that do not work or are later dropped.

The final threat was also to avoid LLM leakage in the analysis. The actual event-study calculations and results come from the project code and the underlying financial data, not from an LLM generating or changing the results.

We also check reproducibility and source consistency. The estimation window ends 30 trading days before the announcement, trading days are defined using the market calendar. COIN’s result is independently recomputed with separate code. Where CRSP and Yahoo Finance overlap, we compare returns directly.

| Raw Inputs | Source | What we use it for | Where it lives in the repo | How we reproduce it |
|---|---|---|---|---|
| S&P DJI press releases | S&P Global newsroom | 2022+ announcement dates, times, and additions | data/raw/spdji_release_list.csv and data/raw/spdji_releases/ | code/02_download_announcements.py |
| S&P 500 changes table | Pinned Wikipedia revision | Effective-date cross check | data/raw/wiki_sp500_changes.csv | code/01_download_index_changes.py |
| CRSP daily stock data | WRDS/CRSP | Daily stock returns through 2025 | data/raw/wrds/outputs/crsp_daily_sp500_ever.parquet | WRDS files provided by Prof.Bowen |
| Capital IQ Key Developments | WRDS/ Capital IQ | Historical 2001-2021 additions | data/raw/wrds/outputs/keydev_sp500_events.parquet | WRDS files provided by Prof. Bowen |
| CRSP market calendar | WRDS/CRSP | Trading-day dates for historical events | data/raw/wrds/outputs/market_daily.parquet | WRDS files provided by Prof. Bowen |
| Yahoo Finance prices | yfinance | SPY and 2026 returns, plus return source cross-checks | data/raw/prices.csv | code/04_download_returns.py |

## Dashboard mockup

Live site: https://dream-team-index-effect.streamlit.app/

![Dashboard mockup](dashboard_mockup.png)

### Finished dashboard 
- The Finished dashboard will have all companies instead of just 5
- It will also have real text in the place of placeholders
- Intro: Answers the main question at hand: Does a stock jump when it joins the S&P 500?
- Methodology: 5 steps: List the additions, get returns, set 2 day 0's, compute abnormal returns, avg them
- Results: Shows average jump by era
- Explore: Shows the stock's return vs the market return, 10 days before and after being added to S&P 500

