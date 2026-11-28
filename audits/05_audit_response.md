**B1 – Fixed**

The issue with B1 was that our analysis only included five of the recent S&P 500 additions. We expanded our sample to all 84 additions, with 69 meeting the requirements for our analysis. Our updated results show an average two-day CAR (day 0 and day +1) of +4.46% around the announcement date compared to -1.02% around the rebalance date. This issue was addressed and fixed in PR #18 (commit `8b3b016`).

**B2 – Pending**

The issue with B2 is that our dashboard still contains placeholder text and references to our original sample size. Karthik is currently responsible for updating the dashboard to reflect our full sample and updated findings. This issue will remain open until his changes are completed and merged into main.

**A7 – Fixed**

To address A7, we expanded our discussion of the results by showing the dollar value of the abnormal returns and how much of those returns a trader could realistically capture after the announcement. We also updated the README to reflect our full sample of 69 recent additions and updated STATUS.md to reflect our current progress. These changes were made through PRs #11 (`2d6fbfa`), #12 (`545a282`), #19 (`a6ac82f` and `dde2558`), and #20 (`fd7775f`).
