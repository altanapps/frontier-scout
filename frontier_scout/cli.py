import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from frontier_scout import (
    arxiv_search,
    config,
    db,
    digest,
    discover,
    enrich as enrich_mod,
    extract,
    scrape,
    signals as signals_mod,
)


@click.group()
@click.version_option()
def main() -> None:
    """Scout frontier-tech research labs. Watch papers. Get a daily digest."""


@main.command()
@click.option("--path", default="labs.yaml", type=click.Path(path_type=Path))
def init(path: Path) -> None:
    """Write an example labs.yaml in the current directory."""
    if path.exists():
        click.echo(f"{path} already exists. Edit it directly.", err=True)
        sys.exit(1)
    config.write_example(path)
    click.echo(f"Wrote {path}. Edit it, then run `frontier-scout roster`.")


@main.command()
@click.option("--config-path", "config_path", default="labs.yaml",
              type=click.Path(exists=True, path_type=Path))
@click.option("--db-path", default="frontier.db", type=click.Path(path_type=Path))
def roster(config_path: Path, db_path: Path) -> None:
    """Scrape lab people-pages → researchers in the database."""
    labs = config.load(config_path)
    with db.connect(db_path) as con:
        for lab in labs:
            click.echo(f"→ {lab.name}")
            try:
                html = scrape.fetch(lab.people_url)
            except Exception as e:
                click.echo(f"  fetch failed: {e}", err=True)
                continue
            try:
                people = extract.extract_roster(scrape.to_text(html), lab.people_url)
            except Exception as e:
                click.echo(f"  extract failed: {e}", err=True)
                continue
            for p in people:
                con.execute(
                    """INSERT OR IGNORE INTO people
                       (lab, name, role, profile_url, research_area)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        lab.name,
                        p.get("name", "").strip(),
                        p.get("role", "").strip(),
                        p.get("profile_url", "").strip(),
                        p.get("research_area", "").strip(),
                    ),
                )
            click.echo(f"  +{len(people)} people")


@main.command()
@click.option("--config-path", "config_path", default="labs.yaml",
              type=click.Path(exists=True, path_type=Path))
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--since", default="7d", help="Lookback window, e.g. 7d, 24h.")
def papers(config_path: Path, db_path: Path, since: str) -> None:
    """Fetch new arXiv papers for everyone in the roster."""
    cutoff = _parse_since(since)
    labs = {lab.name: lab for lab in config.load(config_path)}

    with db.connect(db_path) as con:
        roster_rows = con.execute("SELECT lab, name FROM people").fetchall()
        click.echo(f"Searching arXiv for {len(roster_rows)} researchers since {cutoff:%Y-%m-%d}.")
        for r in roster_rows:
            lab = labs.get(r["lab"])
            cats = lab.arxiv_categories if lab else []
            try:
                hits = arxiv_search.search_author(r["name"], cats, cutoff)
            except Exception as e:
                click.echo(f"  arxiv failed for {r['name']}: {e}", err=True)
                continue
            if not hits:
                continue
            for h in hits:
                con.execute(
                    """INSERT OR IGNORE INTO papers
                       (arxiv_id, title, authors, summary, published, pdf_url,
                        matched_person, matched_lab)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (h["arxiv_id"], h["title"], h["authors"], h["summary"],
                     h["published"], h["pdf_url"], r["name"], r["lab"]),
                )
            click.echo(f"  {r['name']}: +{len(hits)}")


@main.command()
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--limit", default=20, type=int,
              help="Max people to enrich this run. Web search costs ~$0.01/person.")
@click.option("--force", is_flag=True,
              help="Re-enrich people who already have an enriched_at timestamp.")
def enrich(db_path: Path, limit: int, force: bool) -> None:
    """Find GitHub/Twitter/personal-site/email for the roster (uses Claude web search)."""
    with db.connect(db_path) as con:
        if force:
            rows = con.execute("SELECT * FROM people LIMIT ?", (limit,)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM people WHERE enriched_at IS NULL OR enriched_at = '' LIMIT ?",
                (limit,),
            ).fetchall()

        click.echo(f"Enriching {len(rows)} people...")
        for r in rows:
            click.echo(f"→ {r['name']} ({r['lab']})")
            try:
                data = enrich_mod.enrich_person(
                    r["name"], r["lab"], r["research_area"] or ""
                )
            except Exception as e:
                click.echo(f"  enrich failed: {e}", err=True)
                continue
            con.execute(
                """UPDATE people
                   SET github_handle = ?, twitter_handle = ?, personal_site = ?,
                       email = ?, enriched_at = ?
                   WHERE id = ?""",
                (
                    (data.get("github_handle") or "").strip(),
                    (data.get("twitter_handle") or "").strip().lstrip("@"),
                    (data.get("personal_site") or "").strip(),
                    (data.get("email") or "").strip(),
                    datetime.now(timezone.utc).isoformat(),
                    r["id"],
                ),
            )
            found = [
                f"{k}={data[k]}"
                for k in ("github_handle", "twitter_handle", "personal_site", "email")
                if data.get(k)
            ]
            click.echo(f"  {', '.join(found) if found else '(no public profiles found)'}")


@main.command()
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--since", default="7d", help="Lookback window, e.g. 7d, 24h.")
def signals(db_path: Path, since: str) -> None:
    """Poll GitHub for new repos / public-makes / tags from people in the roster."""
    cutoff = _parse_since(since)
    with db.connect(db_path) as con:
        rows = con.execute(
            "SELECT id, name, lab, github_handle FROM people "
            "WHERE github_handle IS NOT NULL AND github_handle <> ''"
        ).fetchall()
        click.echo(f"Polling GitHub for {len(rows)} researchers since {cutoff:%Y-%m-%d}.")
        total = 0
        for r in rows:
            try:
                events = signals_mod.fetch_events(r["github_handle"], cutoff)
            except Exception as e:
                click.echo(f"  github failed for {r['name']}: {e}", err=True)
                continue
            for s in events:
                con.execute(
                    """INSERT OR IGNORE INTO signals
                       (person_name, lab, source, kind, detail, url, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (r["name"], r["lab"], "github", s["kind"], s["detail"],
                     s["url"], s["observed_at"]),
                )
            if events:
                total += len(events)
                click.echo(f"  {r['name']} (@{r['github_handle']}): +{len(events)}")
        click.echo(f"Done. {total} new signals.")


@main.command(name="digest")
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--since", default="7d", help="Lookback window, e.g. 7d, 24h.")
@click.option("--explain/--no-explain", "do_explain", default=True,
              help="Use Claude to write a one-line 'why it matters' per paper.")
def digest_cmd(db_path: Path, since: str, do_explain: bool) -> None:
    """Render a markdown digest of recent papers and signals."""
    cutoff = _parse_since(since)
    with db.connect(db_path) as con:
        paper_rows = con.execute(
            "SELECT * FROM papers WHERE published >= ? ORDER BY matched_lab, published DESC",
            (cutoff.isoformat(),),
        ).fetchall()
        items = [dict(r) for r in paper_rows]
        if do_explain:
            for p in items:
                if p.get("why_it_matters"):
                    continue
                try:
                    why = extract.explain(p["title"], p["summary"] or "")
                except Exception:
                    continue
                con.execute(
                    "UPDATE papers SET why_it_matters = ? WHERE id = ?",
                    (why, p["id"]),
                )
                p["why_it_matters"] = why

        sig_rows = con.execute(
            "SELECT * FROM signals WHERE observed_at >= ? ORDER BY observed_at DESC",
            (cutoff.isoformat(),),
        ).fetchall()
        sig_items = [dict(r) for r in sig_rows]

    click.echo(digest.render(items, sig_items))


@main.command()
@click.argument("arxiv_id")
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--intro", envvar="FRONTIER_SCOUT_INTRO",
              help="One-sentence intro about you. Or set FRONTIER_SCOUT_INTRO.")
def draft(arxiv_id: str, db_path: Path, intro: str) -> None:
    """Draft an outreach email anchored on a specific arXiv paper."""
    if not intro:
        click.echo(
            "Set --intro or FRONTIER_SCOUT_INTRO env var. Example:\n"
            "  export FRONTIER_SCOUT_INTRO='Investor at MoreMarkets, previously built NEAR DA.'",
            err=True,
        )
        sys.exit(1)
    with db.connect(db_path) as con:
        row = con.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
    if not row:
        click.echo(f"No paper with arxiv_id {arxiv_id} in DB.", err=True)
        sys.exit(1)
    text = extract.draft_outreach(
        person_name=row["matched_person"] or "there",
        paper_title=row["title"],
        paper_summary=row["summary"] or "",
        sender_intro=intro,
    )
    click.echo(text)


@main.command(name="find-labs")
@click.argument("topic")
def find_labs_cmd(topic: str) -> None:
    """Discover EU/UK labs working on a topic via Claude web search. Outputs YAML."""
    yaml_text = discover.find_labs(topic)
    if not yaml_text:
        click.echo("No results.", err=True)
        sys.exit(1)
    click.echo(yaml_text)


@main.command(name="people")
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--lab", help="Filter by lab name substring.")
@click.option("--enriched/--all", default=False,
              help="Show only people with at least one public profile resolved.")
def people_cmd(db_path: Path, lab: str | None, enriched: bool) -> None:
    """List people in the roster (optionally filtered)."""
    sql = "SELECT * FROM people WHERE 1=1"
    args: list = []
    if lab:
        sql += " AND lab LIKE ?"
        args.append(f"%{lab}%")
    if enriched:
        sql += (" AND ((github_handle IS NOT NULL AND github_handle <> '')"
                " OR (twitter_handle IS NOT NULL AND twitter_handle <> '')"
                " OR (personal_site IS NOT NULL AND personal_site <> ''))")
    sql += " ORDER BY lab, name"
    with db.connect(db_path) as con:
        rows = con.execute(sql, args).fetchall()
    for r in rows:
        bits = [f"{r['name']} ({r['role'] or '?'})"]
        if r["github_handle"]: bits.append(f"gh:{r['github_handle']}")
        if r["twitter_handle"]: bits.append(f"tw:@{r['twitter_handle']}")
        if r["personal_site"]: bits.append(r["personal_site"])
        if r["email"]: bits.append(r["email"])
        click.echo(f"[{r['lab']}] " + " | ".join(bits))


def _parse_since(s: str) -> datetime:
    s = s.strip().lower()
    if not s or not s[-1].isalpha():
        raise click.BadParameter("--since must be like 7d or 24h")
    n = int(s[:-1])
    unit = s[-1]
    if unit == "d":
        delta = timedelta(days=n)
    elif unit == "h":
        delta = timedelta(hours=n)
    else:
        raise click.BadParameter("--since must be like 7d or 24h")
    return datetime.now(timezone.utc) - delta
