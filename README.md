# frontier-scout

Track research labs. Watch new papers. Find handles. Draft outreach. Catch when someone starts a new repo.

A small CLI for systematically scouting frontier-tech research — robotics, BCI, fusion, biotech, anything that publishes on arXiv. Built for VCs, recruiters, journalists, and operators who want a steady signal from the labs they care about without doomscrolling Twitter.

## What it does

| Command | Purpose |
|---|---|
| `init` | Write a starter `labs.yaml` |
| `find-labs <topic>` | Auto-discover EU/UK labs by topic via Claude web search |
| `verify` | HEAD every people_url in parallel; optionally write an alive-only YAML |
| `roster` | Scrape lab people-pages → researchers in SQLite (Claude extracts) |
| `enrich` | Find each researcher's GitHub / Twitter / site / email via web search |
| `papers` | Pull new arXiv preprints from everyone in the roster |
| `signals` | Poll GitHub for new repos / public-makes / tags |
| `digest` | Markdown report of papers + signals, with one-line "why it matters" |
| `draft <arxiv_id>` | Draft a short outreach email anchored on a specific paper |
| `people` | List the roster (filter by lab, or only show people with resolved handles) |

One config file (`labs.yaml`), one SQLite file, a handful of cron-friendly commands.

**See it in action:** [`examples/sample-digest.md`](examples/sample-digest.md) — real output from a 3-lab, 60-day run.

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
export FRONTIER_SCOUT_INTRO="Investor at MoreMarkets, previously built NEAR DA."

frontier-scout find-labs "humanoid robotics" >> labs.yaml   # optional: discover labs
frontier-scout init                                          # or just start with the example
$EDITOR labs.yaml

frontier-scout roster                       # extract people
frontier-scout enrich --limit 30            # resolve GitHub/Twitter/sites
frontier-scout papers --since 7d            # arXiv lookups
frontier-scout signals --since 7d           # GitHub event polling
frontier-scout digest --since 7d            # the actual report you read

# When a paper looks interesting:
frontier-scout draft 2401.12345
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
```

Optional env vars:

| Var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for `roster`, `enrich`, `digest --explain`, `draft`, `find-labs` |
| `FRONTIER_SCOUT_INTRO` | Used by `draft` — one sentence about you |
| `GITHUB_TOKEN` | Optional, raises GitHub rate limit from 60→5000/h |

## Daily digest via GitHub Actions

A starter workflow lives at `.github/workflows/daily-digest.yml.example`. Copy to `.yml`, add `ANTHROPIC_API_KEY` (and optional `SLACK_WEBHOOK_URL`, `GITHUB_TOKEN`) as repo secrets. Roster + enrich are expensive one-shots — re-run them manually when `labs.yaml` changes. The daily workflow only refreshes papers + signals + digest.

## What it costs

- `roster`: ~$0.005 per lab page (Haiku)
- `enrich`: ~$0.01 per person (Sonnet + web search)
- `papers`: free (arXiv API)
- `signals`: free (GitHub public API; set `GITHUB_TOKEN` for higher rate limit)
- `digest --explain`: ~$0.001 per new paper (Haiku)
- `draft`: ~$0.001 per email (Haiku)
- `find-labs`: ~$0.05 per topic (Sonnet + web search)

For a typical setup (15 labs, ~600 people, ~30 new papers/week) total monthly spend lands under $5.

## What's deliberately out of scope (for now)

- **Twitter signal-tracking.** Twitter API costs $200/mo for basic; scraping is fragile. If you have a paid API key, open an issue.
- **LinkedIn.** ToS minefield. Don't.
- **Web frontend.** The digest *is* the frontend.
- **Multi-user, auth, hosted version.** This is a single-user CLI.

## URL decay is real

Lab pages move. In live testing, **5 of 10** URLs in the original starter list returned 404 within months of being curated, and **6 of 58** in the larger reference list (`examples/eu-uk-frontier-labs.yaml`) are dead today. Always `verify` before a roster run:

```bash
frontier-scout verify --write labs.alive.yaml
mv labs.alive.yaml labs.yaml
frontier-scout roster
```

## Status

V0.3. Tested against ~10 robotics labs end-to-end (roster → papers → digest). Lab pages with heavy JS will need a Playwright fallback (open an issue or PR). Roster extraction quality depends on the lab page format — patchy on departmental pages with hundreds of names mixed across roles.

## License

MIT.
