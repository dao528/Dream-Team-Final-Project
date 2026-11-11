# Rules for this repo (humans and coding agents)

Coding agents (Codex, Claude Code, Copilot) read this file before they work. Humans should too. It follows the course's team-repo template, adapted to this project.

## The project

`README.md` is the plan, so read it first. We measure the S&P 500 index effect around two dates for every addition: the day S&P announces it and the day index funds trade it.

One row of the final dataset is one addition × one anchor (`announce` or `effective`) × one trading day from −10 to +10, in `data/clean/event_panel.csv`. That file is the contract between the pipeline and the dashboard. Don't rename or drop its columns without telling the product manager first.

## Who does what

| Role | Name | GitHub | Owns |
|---|---|---|---|
| CEO | Daniel Outkou | dao528 | `main`, reviews and merges every pull request |
| Developer | Tom Sickert | TRock270 | `code/`, `run_all.py`, the data pipeline |
| Product manager | Karthik Sekhar | kartsekhar | the dashboard app |
| Analyst | Manuel Casanova Jr | macq28 | sources, provenance, `specs_tried.md` review |

Only edit the files your role owns. If you need a change in someone else's file, ask them or open an issue.

## Git

- Never commit directly to `main`. Work in your own branch and open a pull request.
- Never force-push and never rewrite shared history (`git reset --hard` on a pushed branch, rebasing a shared branch) without a human's OK. It can erase a teammate's work.
- Commit small steps, with messages that say what changed ("Set effective day 0 to the rebalance close", not "update").
- At the start of each session: `git switch main`, `git pull`, then `git switch <your-branch>` and `git merge main`.

## Pipeline

- Run everything from the repo root: `python run_all.py`. It runs `code/01` to `code/06` in order. `--fresh` deletes `data/raw/` and downloads everything again.
- Every setting (paths, sample, windows, pinned sources) lives in `code/config.py`. Don't hard-code a second copy in a script.
- Never edit files in `data/raw/` by hand. Every raw file has a row in the README's provenance table: where it came from, when we pulled it, and the code that gets it again.
- Relative paths only, never `/Users/...` or `C:/...`.
- Check keys with `assert` and merge with `validate=`. When a script makes a new table, say what one row is.
- Each pipeline step gets at least one number recomputed a different way, like `code/06_hand_check.py` does for COIN.
- Every specification we run goes into `specs_tried.md`, including the ones we drop.

## Event-study rules

- Announcement day 0: S&P publishes after the 4pm close, so day 0 is the next trading day.
- Effective day 0: the last trading day before S&P's effective date. That is the close where index funds trade (see `docs/effective_day_convention.md`). Day +1 is the first day as a member.
- Use the SPY trading calendar for day counts, never calendar days.
- The market-model estimation window is trading days −250 to −30 before the announcement, for both anchors, so it never contains the news.
- Additions with fewer than 200 estimation days (mostly spin-offs) are dropped and listed in `outputs/dropped_short_history.csv`.
- No look-ahead. Only use what was public at the time. Index-fund ownership is measured before the announcement, and the sample comes from S&P's own releases, not from today's constituent list.
- Keep the methods at the level of the class: average ARs and CARs over short windows, with plain t-tests. Prof. Bowen asked for this at Checkpoint 1. No clustered standard errors or calendar-time portfolios unless he asks.

## Using AI

The course policy is that every teammate can explain every step, including the parts an agent wrote. Agents may draft code and notes. A teammate runs it, reads it and can explain it before it goes into a pull request.

Anything addressed to Prof. Bowen (PR replies, status memos, the proposal) is written by a teammate in their own words. Agents can collect facts and numbers for it, but they don't write the final text and they don't post comments to him.

Before every checkpoint, run a skeptical review of the repo (the course's "Skeptical review" prompt, or the `auditor` agent in `.claude/agents/`), fix what it finds, and write up the result in `audits/NN_self_audit.md`.

## Secrets

Never commit an API key. Keys go in `.env`, which is already in `.gitignore`. This project doesn't need any so far.

## Course pages we lean on

The course textbook is at https://ledatascifi.github.io/ledatascifi-2025/. These pages cover what this project does:

- Golden rules for projects: https://ledatascifi.github.io/ledatascifi-2025/content/02/10_Golden_1.html (and the following pages)
- EDA: https://ledatascifi.github.io/ledatascifi-2025/content/03/02e_eda_golden.html
- Merging: https://ledatascifi.github.io/ledatascifi-2025/content/03/05b_merging.html
- Missing data and outliers: https://ledatascifi.github.io/ledatascifi-2025/content/03/05c_missingdata.html, https://ledatascifi.github.io/ledatascifi-2025/content/03/05d_outliers.html
- Scraping (the S&P newsroom): https://ledatascifi.github.io/ledatascifi-2025/content/04/01_Intro_to_scraping.html, https://ledatascifi.github.io/ledatascifi-2025/content/04/01a_openingAndParsing.html
- Regex (for the older release tables): https://ledatascifi.github.io/ledatascifi-2025/content/04/02b_regex.html
- CAPM and factor loadings (the market model): https://ledatascifi.github.io/ledatascifi-2025/content/05/05b_capm.html, https://ledatascifi.github.io/ledatascifi-2025/content/05/05c_factorloadings.html
- Dashboards: https://ledatascifi.github.io/ledatascifi-2025/content/05/06c_dashboards.html
- Use of AI in the course: https://ledatascifi.github.io/ledatascifi-2025/content/about/use_of_gpt.html
