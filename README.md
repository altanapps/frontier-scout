# frontier-scout

Track research labs. Watch new papers. Get a daily digest.

A small CLI for systematically scouting frontier-tech research — robotics, BCI, fusion, biotech, anything that publishes on arXiv. Built for VCs, recruiters, journalists, and curious operators who want a steady signal from the labs they care about without doomscrolling Twitter.

## What it does

1. **Roster** — point it at a list of lab websites; it uses Claude to extract the faculty, postdocs, and PhDs into a structured database.
2. **Papers** — watches arXiv for new preprints by everyone in the roster.
3. **Digest** — markdown report grouped by lab, with a one-line "why it matters" per paper.

That's it. No frontend, no AI agent, no graph database. One config file, one SQLite file, one cron job.

## Install

```bash
pip install frontier-scout
```

Or from source:

```bash
git clone https://github.com/altanapps/frontier-scout
cd frontier-scout
pip install -e .
```

## Quickstart

```bash
export ANTHROPIC_API_KEY=sk-ant-...

frontier-scout init                    # writes labs.yaml in cwd
$EDITOR labs.yaml                       # add the labs you care about
frontier-scout roster                   # scrape lab pages → frontier.db
frontier-scout papers --since 7d        # poll arXiv for everyone
frontier-scout digest --since 7d        # markdown digest to stdout
```

## Configuration

```yaml
# labs.yaml
labs:
  - name: ETH Zurich — Robotic Systems Lab
    people_url: https://rsl.ethz.ch/people.html
    arxiv_categories: [cs.RO, cs.LG]

  - name: Imperial College — Hamlyn Centre
    people_url: https://www.imperial.ac.uk/hamlyn-centre/people/
    arxiv_categories: [cs.RO]

  - name: Oxford Robotics Institute
    people_url: https://ori.ox.ac.uk/people/
    arxiv_categories: [cs.RO]
```

`arxiv_categories` is optional — if set, paper search is restricted to those arXiv categories. See [arxiv.org/category_taxonomy](https://arxiv.org/category_taxonomy) for the full list.

## Daily digest via GitHub Actions

A starter workflow lives at `.github/workflows/daily-digest.yml.example`. Copy it into your fork as `.yml`, add `ANTHROPIC_API_KEY` as a repo secret. Roster runs are expensive; the workflow only refreshes papers + digest daily — re-run roster manually when you change `labs.yaml`.

## What it costs

Roster extraction calls Claude Haiku once per lab page (~$0.01 each). The "why it matters" line is one Haiku call per new paper. Real money kicks in if you point it at hundreds of labs and run digest with `--explain` daily — for a typical setup of 10–20 labs and ~30 new papers/week, expect under $1/month of API spend.

## Status

V0. Single user, single machine, SQLite. Tested against ~10 robotics labs. Lab pages with heavy JS will need a Playwright fallback (open an issue or PR). LinkedIn / Twitter signal-detection is intentionally out of scope for V0 — start with what people publish.

## License

MIT.
