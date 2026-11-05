Read and follow `AGENTS.md` in this folder. It has the rules for this repo.

## Claude Code specifics

Three subagents live in `.claude/agents/`. Use them when they save work, not by default.

- `researcher`: questions about papers, methodology or data sources. It returns a short report with links and quotes and doesn't touch the repo.
- `auditor`: the skeptical review before a checkpoint or a pull request. It reruns the pipeline on the cached data, checks the course's audit list and reports problems with file and line. It doesn't fix anything.
- `explainer`: walks a teammate through a script in plain language and lists the questions Prof. Bowen might ask about it.

Text for Prof. Bowen is only ever a draft for a teammate to rewrite (see "Using AI" in `AGENTS.md`).

Personal notes for whoever is working locally go in `CLAUDE.local.md`, which git ignores.
