# Which day is the "effective day"?

Research notes after Checkpoint 1 (Nov 4, 2026). Prof. Bowen asked us to work out when index funds actually trade and to define the effective-day event around that.

## Short answer

When S&P says an addition is "effective prior to the open of trading on Monday, December 22", it means the change is put in **at the close of the last trading day before that date** (Friday, December 19, in that example). Index funds buy in that day's closing auction, at the official closing price, because that is the price the index uses for the new member.

So the event is the **rebalance close**. Since spec #2 (`specs_tried.md`), we define:

| Day | Date | What happens |
|---|---|---|
| effective day 0 | last trading day before S&P's effective date | index funds buy at this day's close |
| day 0 return | close(−1) → close(0) | ends at the price index funds pay |
| day +1 | S&P's stated effective date | first day the stock trades as a member |

Our Checkpoint 1 code called the first member day "day 0". Under that convention the rebalance close was day −1. Bowen's comment ("either what you're currently calling day −1 is the first day, or the returns are from close of day −1 to day 0") was right. The first reading is the one the S&P documents support.

## Evidence

1. **S&P's own rules.** The *Equity Indices Policies & Practices* methodology, in its section on unexpected exchange closures, says adds and drops "remain unchanged, as trading was completed at the close of the day before the effective date". It also says that if the exchange is closed on the day before the effective date, the changes "are moved to after the close of the next trading date". The *Index Mathematics* methodology explains that divisor changes are made "after the close", using closing prices.
2. **S&P's press releases** all use the same wording. For example, the Dec 5, 2025 release says "effective prior to the open of trading on Monday, December 22, to coincide with the quarterly rebalance." 54 of our 76 cached releases contain "prior to the open(ing)".
3. **Volume.** Lynch & Mendenhall (1997) say "most funds rebalance their portfolios on the day before the change," and "the largest abnormal volume is on the day before" the change day. Kappou, Brooks & Ward (2010) find about 35% of the day's volume in the 4pm closing auction on the rebalance day. Greenwood & Sammon report that the effective-date share of volume rose from about 15% in earlier decades to almost 30% in the 2010s. State Street (SSGA, 2026) says index funds and ETFs are "structurally incentivized to execute trades at the closing auction."
4. **Tesla, Dec 2020.** Tesla was "effective prior to the open of trading on Monday, December 21, 2020." Its record closing auction was on **Friday Dec 18**. *(We saw this in news summaries, not the full article.)*

## How papers label it (not all the same, so we state ours)

- **First member day as the change date** (our old convention): Lynch & Mendenhall (1997) and Vijh & Wang ("ED is the first date when the added stock trades as part of the index").
- **Rebalance day as the event date** (our new convention): Kappou, Brooks & Ward (2010) and Kappou (2018) ("the change becomes effective at the close of business of the event date").
- **Greenwood & Sammon** measure the effective-date return from the day before to the day after the change, so their window covers both days either way.

## Details we handle

- **Holidays.** We take the previous day on the SPY trading calendar, never "calendar date minus one". In June 2026 the effective date was Monday June 22. Friday June 19 was Juneteenth, a market holiday, so FLEX and MRVL have rebalance day 0 on **Thursday June 18**.
- **Quarterly rebalances** take effect on a Monday, so funds trade the Friday close. That Friday is usually the third-Friday options and futures expiration, so day 0 also picks up expiration-day trading.
- **What changed in our numbers.** For the five proof-of-concept additions, effective day 0 moved one trading day earlier. FLEX's +6.0% abnormal return is on the first member day, which is now day +1. On the rebalance day itself FLEX is +0.7%. The announcement-day results don't change.

## Sources

- S&P DJI, *Equity Indices Policies & Practices* methodology (2014 copy): https://www.spice-indices.com/idpfiles/spice-assets/resources/public/documents/methodology-sp-equity-indices-policies-practices.pdf. The current copy on spglobal.com blocked our download, so the wording should be checked against the latest version.
- S&P DJI, *Index Mathematics* methodology: https://www.spice-indices.com/idpfiles/spice-assets/resources/public/documents/methodology-index-math.pdf
- S&P press release, Dec 5, 2025: https://press.spglobal.com/2025-12-05-CRH,-Carvana-and-Comfort-Systems-USA-Set-to-Join-S-P-500-Others-to-Join-S-P-MidCap-400-and-S-P-SmallCap-600
- S&P press release on Tesla, Nov 30, 2020: https://press.spglobal.com/2020-11-30-S-P-Dow-Jones-Indices-Announces-Implementation-of-Teslas-Addition-to-S-P-500
- Lynch & Mendenhall (1997), *Journal of Business*: https://pages.stern.nyu.edu/~alynch/pdfs/jb97lm.pdf
- Kappou, Brooks & Ward (2010), *Journal of Banking & Finance*: https://centaur.reading.ac.uk/18666/1/18666.pdf
- Kappou (2018), *Journal of Asset Management*: https://centaur.reading.ac.uk/76714/1/Diminished%20effect%20of%20index%20rebalances_kkappou.pdf
- Vijh & Wang, *Financial Management*: https://www.biz.uiowa.edu/faculty/avijh/SP_1.pdf
- Greenwood & Sammon, "The Disappearing Index Effect", *Journal of Finance* 80(2), 2025 (NBER w30748): https://www.nber.org/papers/w30748
- SSGA, "Closing time" (2026): https://www.ssga.com/us/en/intermediary/insights/how-passive-investing-reshaping-microstructure
- ThinkAdvisor/Bloomberg on Tesla's closing auction (Dec 18, 2020): https://www.thinkadvisor.com/2020/12/18/hungry-index-funds-cram-tesla-into-sp-500-at-record-high/
