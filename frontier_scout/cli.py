import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from frontier_scout import arxiv_search, config, db, digest, extract, scrape


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


@main.command(name="digest")
@click.option("--db-path", default="frontier.db",
              type=click.Path(exists=True, path_type=Path))
@click.option("--since", default="7d", help="Lookback window, e.g. 7d, 24h.")
@click.option("--explain/--no-explain", "do_explain", default=True,
              help="Use Claude to write a one-line 'why it matters' per paper.")
def digest_cmd(db_path: Path, since: str, do_explain: bool) -> None:
    """Render a markdown digest of recent papers."""
    cutoff = _parse_since(since)
    with db.connect(db_path) as con:
        rows = con.execute(
            "SELECT * FROM papers WHERE published >= ? ORDER BY matched_lab, published DESC",
            (cutoff.isoformat(),),
        ).fetchall()
        items = [dict(r) for r in rows]
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
    click.echo(digest.render(items))


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
