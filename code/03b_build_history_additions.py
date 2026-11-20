"""Step 3b: S&P 500 additions before our release sample (2001-2021), from Capital IQ Key Developments.

Before about 2021 the Key Dev "announcedate" behaves like the effective date, not the announcement
(volume check in data/raw/wrds/README.md). So these additions get the effective anchor only.
Their announcement dates would have to come from the old S&P releases (planned for the final version).

1. Same firm twice (audit A3). Key Dev rows of one permno at most SAME_FIRM_WINDOW trading days apart
   are one addition (Moderna 2021-07-20 and 2021-07-22). The last row is kept, the others are dropped
   as "duplicate Key Dev row". The group's first and last Key Dev dates are used in rule 2.
2. Effective date (audit A1). No volume data is used to pick it.
   k = first trading day on or after the Key Dev date (16% of Key Dev dates are weekends).
   w = Wikipedia's date for the same ticker, at most WIKI_MATCH_DAYS trading days from k, from the
       pinned "Selected changes" table (step 01). Wikipedia has almost no rows before 2007.
   Offsets are in trading days on the CRSP calendar.
     date_rule                            when                                       effective date
     agree                                w == k                                     k
     keydev duplicate, wikipedia inside   the rule-1 group's Key Dev dates surround w  w  (MRNA 2021)
     keydev early                         w is 1 or more days after k. Key Dev looks   w
                                          like the announcement (9 of 14 in 2001-2007)
     ambiguous                            w is one day before k                      k, but w from
                                                                                     AMBIGUOUS_WIKIPEDIA_FROM
       S&P's own releases decide (code/06_hand_check.py): up to 2020 Wikipedia gives the rebalance
       close (HP 2010, WellCare 2018, Ingersoll Rand 2020); in 2021 Key Dev is a day late (Trimble,
       Monolithic Power, PTC, SolarEdge). Step 07 also reports the CARs without the ambiguous ones.
     wikipedia earlier                    w is 2 or more days before k               k
     keydev only                          no Wikipedia match                         k
   rebalance_day = the trading day before the effective date, the close where index funds trade
   (effective day 0). HISTORY_DATE_SOURCE = "keydev" uses k for every addition (the v0 rule).
3. Drop rules (later ones win; every dropped row is in outputs/history_dropped.csv with its name):
   - Volume filter, only if HISTORY_VOLUME_FILTER (the v0 rule, off since the Checkpoint 2 audit):
     keep an addition only if its CRSP volume peak within 15 trading days of the Key Dev date is on
     the trading day before the Key Dev date. It uses volume after day 0, so it selects events on
     the data around the event. passes_volume_filter keeps the result for a robustness test in 07.
   - Not a new member, from Key Dev's own add and drop rows (no returns or volume): the permno is
     already in the index (its last Key Dev event before this firm's first row is an add: a second
     share class like GOOG 2014, or Regions 2004), or Key Dev drops the same permno within
     SAME_FIRM_WINDOW trading days (Alcoa/Arconic 2016, Coca-Cola Enterprises 2010, spin-offs held
     for a day like DT Midstream 2021). No index fund buys these.
   - New listing: no CRSP row on the rebalance day, because the stock started trading after it.
     These are spin-offs and firms created by a merger (Zimmer, PayPal, AbbVie, Kraft Heinz).
     The assert below checks that each one starts trading after the rebalance day, so none is a
     firm with an older price history under the same permno.
   - Key Dev backfill: a date with BACKFILL_MIN_ADDS or more adds and no drops is not an index change.
     2005-01-29 (a Saturday) has 36 "additions" of long-time members like AT&T and Fannie Mae, all from
     source "Index Website". Real changes come in add/drop pairs.
   - Duplicate Key Dev row (rule 1).

Outputs:
  data/clean/history_additions.csv   one row = one kept addition (key: event_id; permno + effective_date unique)
  outputs/history_dates.csv          one row = one real addition (none of NOT_ADDITIONS): Key Dev
                                     and Wikipedia dates, the chosen date and rule, and where the volume
                                     peak is (reported only, never used to pick a date)
  outputs/history_date_rules.csv     one row = one era: how many real additions each date rule dated
  outputs/history_date_check.csv     one row = one era: how many Key Dev rows each drop rule removed
  outputs/history_dropped.csv        one row = one dropped Key Dev row, with its name and the reason
"""
import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from config import (AMBIGUOUS_WIKIPEDIA_FROM, CLEAN, CRSP_DAILY, CRSP_MARKET, HISTORY_DATE_SOURCE, HISTORY_END,
                    HISTORY_PEAK_DAY, HISTORY_PER_ERA, HISTORY_SEED, HISTORY_START, HISTORY_VOLUME_FILTER,
                    KEYDEV_EVENTS, OUTPUTS, RAW, SAME_FIRM_WINDOW, WIKI_MATCH_DAYS, era_of)

OUT = CLEAN / "history_additions.csv"
DATES_OUT = OUTPUTS / "history_dates.csv"
RULES_OUT = OUTPUTS / "history_date_rules.csv"
CHECK_OUT = OUTPUTS / "history_date_check.csv"
DROPPED_OUT = OUTPUTS / "history_dropped.csv"
BACKFILL_MIN_ADDS = 10  # the largest real batch of 2001-2021 additions on one date is 7 (2002-07-22)
NEW_LISTING = "new listing: first CRSP day after the rebalance day (spin-off or merger)"
NOT_NEW_MEMBER_ALREADY = "not a new member: already in the index (earlier Key Dev add, no drop since)"
NOT_NEW_MEMBER_DROPPED = f"not a new member: Key Dev drops the same permno within {SAME_FIRM_WINDOW} trading days"
NOT_ADDITIONS = ["Key Dev backfill", "duplicate Key Dev row", NOT_NEW_MEMBER_ALREADY, NOT_NEW_MEMBER_DROPPED]
USE_WIKIPEDIA = ["keydev duplicate, wikipedia inside", "keydev early"]
assert HISTORY_DATE_SOURCE in ("keydev", "keydev+wikipedia")

trading_days = pd.DatetimeIndex(pd.read_parquet(CRSP_MARKET, columns=["date"])["date"]).sort_values()

# The sample is defined by the rebalance day (effective day 0), which can be a few days before
# the Key Dev date, so read a week before HISTORY_START and filter on the rebalance day below.
first_keydev_date = HISTORY_START - pd.Timedelta(days=7)
keydev_adds = (pd.read_parquet(KEYDEV_EVENTS)
               .query("action == 'add' and @first_keydev_date <= announcedate <= @HISTORY_END")
               .rename(columns={"announcedate": "keydev_date"}))
assert not keydev_adds.duplicated(subset=["permno", "keydev_date"]).any()
assert keydev_adds.index.is_unique

changes_per_date = (pd.read_parquet(KEYDEV_EVENTS, columns=["announcedate", "action"])
                    .groupby(["announcedate", "action"]).size().unstack(fill_value=0))
backfill_dates = changes_per_date.query("add >= @BACKFILL_MIN_ADDS and drop == 0").index
print("Key Dev backfill dates (adds without drops):", [d.date() for d in backfill_dates])

keydev_pos = trading_days.searchsorted(keydev_adds["keydev_date"])  # first trading day on or after
assert (keydev_pos > 0).all()  # every addition has a trading day before it in CRSP
keydev_adds = keydev_adds.assign(keydev_pos=keydev_pos, keydev_effective=trading_days[keydev_pos])

# 1. Same firm twice: rows of one permno at most SAME_FIRM_WINDOW trading days apart are one event
# (audit A3). Keep the last row; the earlier rows are listed as duplicates. (Sorted only for this
# step. The row order stays as before, because the seed-331 draw below depends on it.)
by_firm = keydev_adds.sort_values(["permno", "keydev_pos"])
days_since_previous = by_firm.groupby("permno")["keydev_pos"].diff()
keydev_adds["firm_event"] = (days_since_previous.isna() | (days_since_previous > SAME_FIRM_WINDOW)).cumsum()
keydev_adds["duplicate"] = keydev_adds.loc[by_firm.index, "firm_event"].duplicated(keep="last")
one_per_event = by_firm[~keydev_adds.loc[by_firm.index, "duplicate"]]
assert not (one_per_event.groupby("permno")["keydev_pos"].diff() <= SAME_FIRM_WINDOW).any()
firm_event = keydev_adds.groupby("firm_event")
keydev_adds = keydev_adds.assign(
    n_keydev_rows=firm_event["keydev_pos"].transform("size"),
    group_first_pos=firm_event["keydev_pos"].transform("min"),
    group_last_pos=firm_event["keydev_pos"].transform("max"),
    keydev_dates=firm_event["keydev_date"].transform(lambda d: ", ".join(sorted(d.dt.strftime("%Y-%m-%d")))))
print(f"same permno within {SAME_FIRM_WINDOW} trading days, collapsed into one event (earlier rows): "
      f"{[(p, str(d.date())) for p, d in keydev_adds.loc[keydev_adds['duplicate'], ['permno', 'keydev_date']].values]}")

# Not a new member. Uses only Key Dev's own add and drop rows (all years), no returns or volume.
# (a) The permno's last Key Dev event before this firm's first row is an add: it is already in the
#     index, and Key Dev lists a second share class or a renamed firm (GOOG 2014, FOX 2015, Regions 2004).
#     A same-day add and drop counts as a drop ("add" sorts before "drop").
# (b) Key Dev drops the same permno within SAME_FIRM_WINDOW trading days: a restructuring on an existing
#     permno (Alcoa/Arconic 2016, Coca-Cola Enterprises 2010) or a spin-off held for a day or two.
keydev_events = (pd.read_parquet(KEYDEV_EVENTS, columns=["permno", "announcedate", "action"])
                 .sort_values(["announcedate", "action"]))
keydev_adds["group_first_date"] = firm_event["keydev_date"].transform("min")
before_first = pd.merge_asof(keydev_adds[["permno", "group_first_date"]].reset_index().sort_values("group_first_date"),
                             keydev_events.rename(columns={"announcedate": "group_first_date", "action": "action_before"}),
                             on="group_first_date", by="permno", allow_exact_matches=False)
keydev_adds["already_member"] = before_first.set_index("index")["action_before"].eq("add")
keydev_drops = (keydev_events.query("action == 'drop'")
                .assign(drop_pos=lambda d: trading_days.searchsorted(d["announcedate"]))
                [["permno", "drop_pos"]].sort_values("drop_pos"))
nearest_drop = pd.merge_asof(keydev_adds[["permno", "keydev_pos"]].reset_index().sort_values("keydev_pos"), keydev_drops,
                             left_on="keydev_pos", right_on="drop_pos", by="permno", direction="nearest",
                             tolerance=SAME_FIRM_WINDOW)
keydev_adds["dropped_soon"] = nearest_drop.set_index("index")["drop_pos"].notna()
assert len(keydev_adds) == len(before_first) == len(nearest_drop)

# Ticker and name as of the Key Dev date, from CRSP (Key Dev often has today's name): the first CRSP
# row on or after the trading day before k. For a new listing that is its first trading day.
crsp_names = (ds.dataset(CRSP_DAILY)
              .to_table(columns=["permno", "date", "ticker", "comnam"],
                        filter=ds.field("permno").isin(keydev_adds["permno"].unique().tolist()))
              .to_pandas()
              .astype({"ticker": str, "comnam": str, "date": "datetime64[ns]"})
              .rename(columns={"comnam": "company"}))
assert not crsp_names.duplicated(subset=["permno", "date"]).any()
keydev_adds = (pd.merge_asof(keydev_adds.assign(name_date=trading_days[keydev_adds["keydev_pos"] - 1])
                             .reset_index()
                             .sort_values("name_date"),
                             crsp_names.rename(columns={"date": "name_date"}).sort_values("name_date"),
                             on="name_date", by="permno", direction="forward")
               .set_index("index")
               .sort_index())
assert keydev_adds["company"].notna().all(), "a Key Dev addition with no CRSP row on or after its date"

# 2. Effective date: Key Dev, checked against Wikipedia (audit A1).
wiki_adds = (pd.read_csv(RAW / "wiki_sp500_changes.csv", parse_dates=["effective_date"])
             .query("add_ticker.notna() and effective_date <= @trading_days[-1]")
             .rename(columns={"add_ticker": "ticker", "effective_date": "wiki_date"})
             [["ticker", "wiki_date"]])
wiki_adds["wiki_pos"] = trading_days.searchsorted(wiki_adds["wiki_date"])
keydev_adds = (pd.merge_asof(keydev_adds.reset_index().sort_values("keydev_pos"),
                             wiki_adds.sort_values("wiki_pos"),
                             left_on="keydev_pos", right_on="wiki_pos", by="ticker",
                             direction="nearest", tolerance=WIKI_MATCH_DAYS)
               .set_index("index")
               .sort_index())
wiki_offset = keydev_adds["wiki_pos"] - keydev_adds["keydev_pos"]
in_duplicate_group = ((keydev_adds["n_keydev_rows"] > 1)
                      & keydev_adds["wiki_pos"].between(keydev_adds["group_first_pos"], keydev_adds["group_last_pos"]))
keydev_adds["wiki_offset"] = wiki_offset
keydev_adds["date_rule"] = np.select(
    [keydev_adds["wiki_pos"].isna(), wiki_offset == 0, in_duplicate_group, wiki_offset >= 1, wiki_offset == -1],
    ["keydev only", "agree", "keydev duplicate, wikipedia inside", "keydev early", "ambiguous"],
    default="wikipedia earlier")
ambiguous_late_keydev = (keydev_adds["date_rule"].eq("ambiguous")
                         & (keydev_adds["keydev_effective"].dt.year >= AMBIGUOUS_WIKIPEDIA_FROM))
use_wiki = ((keydev_adds["date_rule"].isin(USE_WIKIPEDIA) | ambiguous_late_keydev)
            & (HISTORY_DATE_SOURCE == "keydev+wikipedia"))
keydev_adds["date_source"] = np.where(use_wiki, "wikipedia", "keydev")
chosen_pos = keydev_adds["wiki_pos"].where(use_wiki, keydev_adds["keydev_pos"]).astype(int)
keydev_adds = keydev_adds.assign(effective_date=trading_days[chosen_pos], rebalance_day=trading_days[chosen_pos - 1])

# Where the volume peak is. Reported only (history_dates.csv), never used to pick a date or an event.
keydev_rebalance = trading_days[keydev_adds["keydev_pos"] - 1]
wiki_rebalance = pd.Series(pd.NaT, index=keydev_adds.index)
matched = keydev_adds["wiki_pos"].notna()
wiki_rebalance[matched] = trading_days[keydev_adds.loc[matched, "wiki_pos"].astype(int) - 1]
peak = keydev_adds["peak_volume_date"]
keydev_adds["volume_peak_on"] = np.select(
    [peak.isna(), (peak == keydev_rebalance) & (peak == wiki_rebalance), peak == keydev_rebalance,
     peak == wiki_rebalance],
    ["no volume test", "both rebalance days", "keydev rebalance day", "wikipedia rebalance day"],
    default="neither")
keydev_adds["passes_volume_filter"] = keydev_adds["trading_days_to_peak"] == HISTORY_PEAK_DAY

keydev_adds = keydev_adds.query("rebalance_day >= @HISTORY_START").copy()
keydev_adds["era"] = keydev_adds["rebalance_day"].dt.year.map(era_of)
print(f"Key Dev additions {HISTORY_START.year}-{HISTORY_END.year}: {len(keydev_adds)} "
      f"({keydev_adds['permno'].nunique()} permnos)")

# Trading on the rebalance day? And the first CRSP day, to show that the ones that weren't are new listings.
crsp_days = crsp_names[["permno", "date"]].rename(columns={"date": "rebalance_day"})
keydev_adds = keydev_adds.merge(crsp_days, on=["permno", "rebalance_day"], how="left",
                                validate="many_to_one", indicator=True)
keydev_adds["trading_on_rebalance_day"] = keydev_adds.pop("_merge") == "both"
first_crsp_day = crsp_names.groupby("permno")["date"].min().rename("first_crsp_day")
keydev_adds = keydev_adds.merge(first_crsp_day, left_on="permno", right_index=True, how="left",
                                validate="many_to_one")
keydev_adds["trading_days_to_first_crsp"] = (trading_days.searchsorted(keydev_adds["first_crsp_day"])
                                             - trading_days.searchsorted(keydev_adds["rebalance_day"]))

# 3. Drop rules. Later lines win, so the rules are written from the last to the first.
keydev_adds["date_check"] = "kept"
if HISTORY_VOLUME_FILTER:
    keydev_adds.loc[~keydev_adds["passes_volume_filter"], "date_check"] = "volume peak elsewhere"
    keydev_adds.loc[keydev_adds["trading_days_to_peak"].isna(), "date_check"] = "no volume test"
keydev_adds.loc[keydev_adds["dropped_soon"], "date_check"] = NOT_NEW_MEMBER_DROPPED
keydev_adds.loc[keydev_adds["already_member"], "date_check"] = NOT_NEW_MEMBER_ALREADY
keydev_adds.loc[~keydev_adds["trading_on_rebalance_day"], "date_check"] = NEW_LISTING
keydev_adds.loc[keydev_adds["keydev_date"].isin(backfill_dates), "date_check"] = "Key Dev backfill"
keydev_adds.loc[keydev_adds["duplicate"], "date_check"] = "duplicate Key Dev row"

new_listings = keydev_adds.query("date_check == @NEW_LISTING")
assert (new_listings["first_crsp_day"] > new_listings["rebalance_day"]).all(), "a gap in CRSP, not a new listing"

(keydev_adds
 .query("date_check != 'kept'")
 [["permno", "gvkey", "ticker", "company", "headline", "era", "keydev_date", "keydev_dates", "effective_date",
   "rebalance_day", "first_crsp_day", "trading_days_to_first_crsp", "trading_days_to_peak", "date_check"]]
 .sort_values(["date_check", "keydev_date"])
 .to_csv(DROPPED_OUT, index=False))

date_check = keydev_adds.pivot_table(index="era", columns="date_check", values="permno", aggfunc="size",
                                     fill_value=0)
# Share of the real additions (backfill rows are not additions, duplicate rows repeat an addition).
date_check["share_kept"] = (date_check["kept"]
                            / date_check.drop(columns=[c for c in NOT_ADDITIONS if c in date_check]).sum(axis=1)).round(3)
date_check.to_csv(CHECK_OUT)
print(date_check.to_string())

# One row per real addition: the dates, the rule, and the volume peak (audit A1).
real_additions = keydev_adds.query("date_check not in @NOT_ADDITIONS")
(real_additions
 [["permno", "ticker", "company", "era", "keydev_dates", "keydev_effective", "wiki_date", "wiki_offset", "date_rule", "date_source",
   "effective_date", "rebalance_day", "passes_volume_filter", "volume_peak_on", "date_check"]]
 .sort_values("effective_date")
 .to_csv(DATES_OUT, index=False))
date_rules = pd.crosstab(real_additions["era"], real_additions["date_rule"], margins=True, margins_name="all")
date_rules.to_csv(RULES_OUT)
print(date_rules.to_string())
print(pd.crosstab(real_additions["date_rule"], real_additions["volume_peak_on"]).to_string())

history_adds = (keydev_adds
                .query("date_check == 'kept'")
                .assign(event_id=lambda d: d["ticker"] + "_" + d["effective_date"].dt.year.astype(str)))
assert not history_adds.duplicated(subset="event_id").any()
assert not history_adds.duplicated(subset=["permno", "effective_date"]).any()

if HISTORY_PER_ERA is not None:
    assert history_adds["era"].value_counts().min() >= HISTORY_PER_ERA
    history_adds = history_adds.groupby("era").sample(n=HISTORY_PER_ERA, random_state=HISTORY_SEED)

history_adds = (history_adds
                [["event_id", "permno", "gvkey", "ticker", "company", "era", "keydev_date", "wiki_date", "date_rule",
                  "effective_date", "rebalance_day", "passes_volume_filter", "peak_volume_date",
                  "trading_days_to_peak", "link_source", "headline"]]
                .sort_values("effective_date")
                .reset_index(drop=True))
history_adds.to_csv(OUT, index=False)
print(f"saved {OUT.name}: {len(history_adds)} additions")
print(history_adds.groupby(["era", "date_rule"]).size().unstack(fill_value=0).to_string())
