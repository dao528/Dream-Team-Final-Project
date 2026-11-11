"""Step 2: ANNOUNCEMENT dates and times, from S&P Dow Jones Indices press releases.

1. Search the S&P newsroom for index-change releases and keep those about the S&P 500
   published since SAMPLE_START. Release URLs start with the publication date.
2. Download each release once (cached in data/raw/spdji_releases/).
3. Parse the release's publication time (the page's ITEMDATE comment, US Eastern) and its
   summary table (Effective Date | Index Name | Action | Company Name | Ticker | GICS Sector).

Outputs:
  data/raw/spdji_release_list.csv    one row per release (url, publication date)
  data/clean/spdji_sp500_actions.csv one row per release x S&P 500 action (addition/deletion)
"""
import io
import re
import time

import pandas as pd
import requests

from config import (CLEAN, HEADERS, NEWSROOM_SEARCH, NEWSROOM_SECTION, RAW, RELEASE_CACHE,
                    SAMPLE_START, SEARCH_KEYWORDS)

LIST_OUT = RAW / "spdji_release_list.csv"
ACTIONS_OUT = CLEAN / "spdji_sp500_actions.csv"
PAGE_SIZE = 100
LINK_PATTERN = re.compile(r'href="(https://press\.spglobal\.com/(\d{4}-\d{2}-\d{2})-[^"?]+)"')


def search_release_links(keyword):
    """Page through the newsroom search until results are older than SAMPLE_START."""
    links = {}
    for offset in range(0, 5000, PAGE_SIZE):
        html = requests.get(
            NEWSROOM_SEARCH,
            params={"s": NEWSROOM_SECTION, "l": PAGE_SIZE, "o": offset, "keywords": keyword},
            headers=HEADERS,
            timeout=30,
        ).text
        page_links = dict(LINK_PATTERN.findall(html))
        if not page_links:
            break
        links.update(page_links)
        if min(pd.to_datetime(list(page_links.values()))) < SAMPLE_START:
            break
        time.sleep(1)
    return links


def get_release_html(url):
    cache_file = RELEASE_CACHE / (url.rsplit("/", 1)[1][:150] + ".html")
    if not cache_file.exists():
        cache_file.write_text(requests.get(url, headers=HEADERS, timeout=30).text)
        time.sleep(1)
    return cache_file.read_text()


SUMMARY_COLUMNS = {"Effective Date": "effective_date", "Index Name": "index_name", "Action": "action",
                   "Company Name": "company", "Ticker": "ticker", "GICS Sector": "gics_sector"}
ACTION_WORDS = {"Addition", "Deletion"}


def tidy_summary_table(table):
    """The summary tables use merged cells, so read_html repeats some headers and values
    (e.g. two "Index Name" columns, the second holding the action). For each header, keep
    the column whose content fits it, and fill merged effective-date cells downward."""
    headers = table.iloc[0].astype(str).str.replace("\xa0", " ").str.strip()
    body = table.iloc[1:].reset_index(drop=True)
    tidy = {}
    for header, name in SUMMARY_COLUMNS.items():
        positions = [i for i, h in enumerate(headers) if h == header]
        if not positions:
            continue
        is_action_col = [body.iloc[:, i].isin(ACTION_WORDS).all() for i in positions]
        wanted = [p for p, a in zip(positions, is_action_col) if a == (name == "action")]
        tidy[name] = body.iloc[:, (wanted or positions)[0]]
    tidy = pd.DataFrame(tidy)
    tidy["effective_date"] = tidy["effective_date"].ffill()
    return tidy


def parse_release(url, html):
    """Return the release's S&P 500 rows from its summary table, with the publication time."""
    itemdate = re.search(r"ITEMDATE: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", html)
    published_et = itemdate.group(1) if itemdate else None
    tables = pd.read_html(io.StringIO(html)) if "<table" in html else []
    summary = [t for t in tables if (t.iloc[0].astype(str) == "Effective Date").any()]
    if not summary:
        return pd.DataFrame({"url": [url], "published_et": [published_et], "parsed": [False]})
    return (tidy_summary_table(summary[0])
            .query('index_name == "S&P 500"')
            .assign(url=url, published_et=published_et, parsed=True))


if LIST_OUT.exists():
    print(f"{LIST_OUT.name} exists, skipping newsroom search")
else:
    all_links = {}
    for keyword in SEARCH_KEYWORDS:
        all_links.update(search_release_links(keyword))
    release_list = (pd.DataFrame(list(all_links.items()), columns=["url", "url_date"])
                    .assign(url_date=lambda d: pd.to_datetime(d["url_date"]))
                    .query("url_date >= @SAMPLE_START")
                    .loc[lambda d: d["url"].str.contains("S-P-500")]
                    .sort_values("url_date")
                    .assign(pulled_on=pd.Timestamp.today().normalize()))
    release_list.to_csv(LIST_OUT, index=False)
    print(f"saved {LIST_OUT.name}: {len(release_list)} releases")

release_list = pd.read_csv(LIST_OUT, parse_dates=["url_date"])
sp500_actions = pd.concat(
    [parse_release(url, get_release_html(url)) for url in release_list["url"]],
    ignore_index=True,
).assign(
    published_et=lambda d: pd.to_datetime(d["published_et"]),
    effective_date=lambda d: pd.to_datetime(d["effective_date"], format="mixed", errors="coerce"),
)
sp500_actions.to_csv(ACTIONS_OUT, index=False)

unparsed_slugs = sp500_actions.query("not parsed")["url"].str.rsplit("/", n=1).str[1]
print(f"releases: {len(release_list)}, without a summary table: {len(unparsed_slugs)}")
# Releases without a table should be buyback reports and other news, never index changes.
index_change_words = "Join|Added|Replace|Remov"
assert not unparsed_slugs.str.contains(index_change_words, case=False).any(), "an index-change release did not parse"
print(sp500_actions.query("parsed")["action"].value_counts())
print("publication hour (ET) of releases with an S&P 500 addition:")
print(sp500_actions.query('action == "Addition"')["published_et"].dt.hour.value_counts().sort_index())
