"""Step 3: one row per S&P 500 addition, with its announcement time and effective date.

The S&P press releases are the primary source (they give both dates). The pinned
Wikipedia table is a cross-check on the effective date. Wikipedia rows with no release
should only be ticker changes and mergers, which are not index additions.

Outputs:
  data/clean/additions.csv    key: ticker
  outputs/sample_counts.csv   one row = one count about the 2022+ sample that the README,
                              PROPOSAL.md or the dashboard quotes
"""
import pandas as pd

from config import CLEAN, OUTPUTS, RAW, SAMPLE_START

OUT = CLEAN / "additions.csv"
COUNTS_OUT = OUTPUTS / "sample_counts.csv"

sp500_actions = pd.read_csv(CLEAN / "spdji_sp500_actions.csv", parse_dates=["published_et", "effective_date"])
release_additions = (sp500_actions
                     .query('action == "Addition"')
                     .drop_duplicates(subset=["url", "ticker"])  # FERG is listed twice in one release
                     .sort_values("published_et"))

# Batch size = how many S&P 500 additions the same release announced.
release_additions["batch_size"] = release_additions.groupby("url")["ticker"].transform("size")

# A ticker can appear in more than one release when S&P revises a pending addition
# (KVUE: announced 2023-08-09 with no date, re-announced 2023-08-21 with one).
# The first release is when the news became public. The last one has the final effective date.
additions = (release_additions
             .groupby("ticker")
             .agg(company=("company", "first"),
                  gics_sector=("gics_sector", "first"),
                  announce_et=("published_et", "first"),
                  announce_url=("url", "first"),
                  batch_size=("batch_size", "first"),
                  effective_date=("effective_date", "last"),
                  n_releases=("url", "nunique"))
             .reset_index())
assert additions["ticker"].is_unique

wiki_changes = pd.read_csv(RAW / "wiki_sp500_changes.csv", parse_dates=["effective_date"])
wiki_additions = (wiki_changes
                  .query("effective_date >= @SAMPLE_START & add_ticker.notna()")
                  .rename(columns={"add_ticker": "ticker", "effective_date": "wiki_effective_date",
                                   "reason": "wiki_reason"})
                  [["ticker", "wiki_effective_date", "wiki_reason"]])

print(f"release additions: {len(additions)}, wiki additions: {len(wiki_additions)}")
additions = additions.merge(wiki_additions, on="ticker", how="outer", validate="one_to_one", indicator=True)
print(additions["_merge"].value_counts())

# Wikipedia-only rows must be renames or mergers. If one isn't, the newsroom search missed a release.
wiki_only = additions.query('_merge == "right_only"')
not_an_addition = wiki_only["wiki_reason"].str.contains("changed its|renamed|merge", case=False)
assert not_an_addition.all(), f"release missing for: {wiki_only.loc[~not_an_addition, 'ticker'].tolist()}"
print("dropped (wiki only, rename or merger):", wiki_only["ticker"].tolist())

additions = (additions
             .query('_merge != "right_only"')
             .assign(in_wiki=lambda d: d["_merge"] == "both",
                     effective_dates_agree=lambda d: (d["effective_date"] == d["wiki_effective_date"])
                                                     | ~d["in_wiki"])
             .drop(columns=["_merge", "wiki_reason"])
             .astype({"batch_size": int, "n_releases": int})  # the outer merge made them floats
             .sort_values("announce_et"))

mismatch = additions.query("not effective_dates_agree")
print(f"release vs wiki effective date disagree: {len(mismatch)}")
print(mismatch[["ticker", "announce_et", "effective_date", "wiki_effective_date"]].to_string())
print(f"after the pinned wiki revision (release only): {additions.query('not in_wiki')['ticker'].tolist()}")

additions.to_csv(OUT, index=False)
print(f"saved {OUT.name}: {len(additions)} additions, {additions['announce_url'].nunique()} announcement releases")

# Every count we quote in the docs, saved so it traces to a file in outputs/ (audit finding A6).
in_both = additions.query("in_wiki")
sample_counts = pd.DataFrame([
    ("additions_2022on", len(additions), "S&P 500 additions announced in an S&P DJI release since 2022"),
    ("announcement_releases", additions["announce_url"].nunique(), "distinct releases that first announced them"),
    ("additions_sharing_a_release", int((additions["batch_size"] > 1).sum()),
     "additions announced in the same release as at least one other addition"),
    ("distinct_effective_dates", additions["effective_date"].nunique(), "distinct S&P effective dates"),
    ("wiki_only_dropped", len(wiki_only), "Wikipedia 'additions' with no release: renames or mergers, dropped"),
    ("in_both_sources", len(in_both), "additions in both the releases and the pinned Wikipedia table"),
    ("effective_dates_agree", int(in_both["effective_dates_agree"].sum()),
     "of in_both_sources, release and Wikipedia effective dates are the same"),
    ("release_only", int((~additions["in_wiki"]).sum()), "additions after the pinned Wikipedia revision"),
], columns=["measure", "value", "description"])
assert sample_counts["measure"].is_unique
sample_counts.to_csv(COUNTS_OUT, index=False)
print(f"saved {COUNTS_OUT.name}")
print(sample_counts[["measure", "value"]].to_string(index=False))
