"""Step 3b: S&P 500 additions before our release sample (2001-2021), from Capital IQ Key Developments.

Before about 2021 the Key Dev "announcedate" behaves like the effective date, not the announcement
(volume check in data/raw/wrds/README.md). So these additions get the effective anchor only.
Their announcement dates would have to come from the old S&P releases (planned for v1).

Date rule, the same as for the 2022+ sample:
  effective_date = first trading day on or after the Key Dev date (16% of Key Dev dates are weekends)
  rebalance_day  = the trading day before that, the close where index funds trade (effective day 0)
Drop rules, in this order (each dropped addition is listed in outputs/history_dropped.csv):
  1. Key Dev backfill: a date with BACKFILL_MIN_ADDS or more adds and no drops is not an index change.
     2005-01-29 (a Saturday) has 36 "additions" of long-time members like AT&T and Fannie Mae, all from
     source "Index Website". Real changes come in add/drop pairs.
  2. Not trading on the rebalance day: no CRSP row that day (spin-offs and new listings).
  3. No volume test in the WRDS pull.
  4. Volume peak elsewhere: keep an addition only if its CRSP volume peak within 15 trading days of the
     Key Dev date is on the rebalance day (trading_days_to_peak == HISTORY_PEAK_DAY). This uses volume
     after day 0 too, so it is a selection on the data around the event (README, threats).

Outputs:
  data/clean/history_additions.csv     one row = one addition (key: event_id; permno + effective_date unique)
  outputs/history_date_check.csv       one row = one era: how many Key Dev additions each drop rule removed
  outputs/history_dropped.csv          one row = one dropped addition, with the reason
"""
import pandas as pd
import pyarrow.dataset as ds

from config import (CLEAN, CRSP_DAILY, CRSP_MARKET, HISTORY_END, HISTORY_PEAK_DAY, HISTORY_PER_ERA,
                    HISTORY_SEED, HISTORY_START, KEYDEV_EVENTS, OUTPUTS, era_of)

OUT = CLEAN / "history_additions.csv"
CHECK_OUT = OUTPUTS / "history_date_check.csv"
DROPPED_OUT = OUTPUTS / "history_dropped.csv"
BACKFILL_MIN_ADDS = 10  # the largest real batch of 2001-2021 additions on one date is 7 (2002-07-22)

trading_days = pd.DatetimeIndex(pd.read_parquet(CRSP_MARKET, columns=["date"])["date"]).sort_values()

# The sample is defined by the rebalance day (effective day 0), which can be a few days before
# the Key Dev date, so read a week before HISTORY_START and filter on the rebalance day below.
first_keydev_date = HISTORY_START - pd.Timedelta(days=7)
keydev_adds = (pd.read_parquet(KEYDEV_EVENTS)
               .query("action == 'add' and @first_keydev_date <= announcedate <= @HISTORY_END")
               .rename(columns={"announcedate": "keydev_date"}))
assert not keydev_adds.duplicated(subset=["permno", "keydev_date"]).any()

changes_per_date = (pd.read_parquet(KEYDEV_EVENTS, columns=["announcedate", "action"])
                    .groupby(["announcedate", "action"]).size().unstack(fill_value=0))
backfill_dates = changes_per_date.query("add >= @BACKFILL_MIN_ADDS and drop == 0").index
print("Key Dev backfill dates (adds without drops):", [d.date() for d in backfill_dates])

positions = trading_days.searchsorted(keydev_adds["keydev_date"])  # first trading day on or after
assert (positions > 0).all()  # every addition has a trading day before it in CRSP
keydev_adds = (keydev_adds
               .assign(effective_date=trading_days[positions], rebalance_day=trading_days[positions - 1])
               .query("rebalance_day >= @HISTORY_START"))
keydev_adds["era"] = keydev_adds["rebalance_day"].dt.year.map(era_of)
print(f"Key Dev additions {HISTORY_START.year}-{HISTORY_END.year}: {len(keydev_adds)} "
      f"({keydev_adds['permno'].nunique()} permnos)")

# Ticker and name as of the rebalance day, from CRSP (Key Dev often has today's name).
crsp_names = (ds.dataset(CRSP_DAILY)
              .to_table(columns=["permno", "date", "ticker", "comnam"],
                        filter=ds.field("permno").isin(keydev_adds["permno"].unique().tolist()))
              .to_pandas()
              .astype({"ticker": str, "comnam": str, "date": "datetime64[ns]"})
              .rename(columns={"date": "rebalance_day", "comnam": "company"}))
keydev_adds = keydev_adds.merge(crsp_names, on=["permno", "rebalance_day"], how="left",
                                validate="one_to_one", indicator=True)

# Later lines win, so the rules are written from the last to the first.
keydev_adds["date_check"] = "kept"
keydev_adds.loc[keydev_adds["trading_days_to_peak"] != HISTORY_PEAK_DAY, "date_check"] = "volume peak elsewhere"
keydev_adds.loc[keydev_adds["trading_days_to_peak"].isna(), "date_check"] = "no volume test"
keydev_adds.loc[keydev_adds["_merge"] == "left_only", "date_check"] = "not trading on rebalance day"
keydev_adds.loc[keydev_adds["keydev_date"].isin(backfill_dates), "date_check"] = "Key Dev backfill"

(keydev_adds
 .query("date_check != 'kept'")
 [["permno", "ticker", "company", "era", "keydev_date", "rebalance_day", "trading_days_to_peak", "date_check"]]
 .sort_values(["date_check", "keydev_date"])
 .to_csv(DROPPED_OUT, index=False))

date_check = keydev_adds.pivot_table(index="era", columns="date_check", values="permno", aggfunc="size",
                                     fill_value=0)
# Share of the real additions (backfill rows are not additions).
date_check["share_kept"] = (date_check["kept"] / date_check.drop(columns="Key Dev backfill").sum(axis=1)).round(3)
date_check.to_csv(CHECK_OUT)
print(date_check.to_string())

history_adds = (keydev_adds
                .query("date_check == 'kept'")
                .assign(event_id=lambda d: d["ticker"] + "_" + d["effective_date"].dt.year.astype(str)))
assert not history_adds.duplicated(subset="event_id").any()
assert not history_adds.duplicated(subset=["permno", "effective_date"]).any()

if HISTORY_PER_ERA is not None:
    assert history_adds["era"].value_counts().min() >= HISTORY_PER_ERA
    history_adds = history_adds.groupby("era").sample(n=HISTORY_PER_ERA, random_state=HISTORY_SEED)

history_adds = (history_adds
                [["event_id", "permno", "ticker", "company", "era", "keydev_date", "effective_date",
                  "rebalance_day", "peak_volume_date", "trading_days_to_peak", "link_source", "headline"]]
                .sort_values("effective_date")
                .reset_index(drop=True))
history_adds.to_csv(OUT, index=False)
print(f"saved {OUT.name}: {len(history_adds)} additions")
print(history_adds[["event_id", "company", "era", "keydev_date", "rebalance_day"]].to_string())
