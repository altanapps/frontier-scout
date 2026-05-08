"""Insert papers from /tmp/openalex_papers.json into frontier.db.

Run after the OpenAlex bulk-fetch agent finishes:
    .venv/bin/python scripts/seed_from_openalex.py
"""

import json
import sqlite3
import sys
from pathlib import Path

SRC = Path("/tmp/openalex_papers.json")
DB = Path(__file__).resolve().parent.parent / "frontier.db"


def main() -> None:
    if not SRC.exists():
        print(f"ERROR: {SRC} does not exist. Did the agent finish?", file=sys.stderr)
        sys.exit(1)

    data = json.loads(SRC.read_text())
    researchers = data.get("researchers", [])
    if not researchers:
        print("No researchers in payload.", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB)

    inserted = 0
    skipped = 0
    for r in researchers:
        name = r.get("name")
        lab = r.get("lab")
        if not (name and lab):
            continue
        for p in r.get("papers", []):
            arxiv_id = (p.get("arxiv_id") or "").strip()
            doi = (p.get("doi") or "").strip()
            unique_id = arxiv_id or doi
            if not unique_id:
                skipped += 1
                continue

            cur = con.execute(
                "INSERT OR IGNORE INTO papers "
                "(arxiv_id, title, authors, summary, published, pdf_url, "
                " matched_person, matched_lab, why_it_matters, doi, venue) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    arxiv_id or unique_id,
                    p.get("title", "").strip(),
                    p.get("authors", "").strip(),
                    "",
                    (p.get("published") or "1970-01-01") + "T00:00:00+00:00",
                    p.get("pdf_url") or doi or "",
                    name,
                    lab,
                    p.get("why_it_matters", "").strip(),
                    doi,
                    p.get("venue", "").strip(),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    by_lab = con.execute(
        "SELECT matched_lab, COUNT(*) FROM papers GROUP BY matched_lab ORDER BY COUNT(*) DESC"
    ).fetchall()
    con.close()

    print(f"Inserted {inserted} new papers (skipped {skipped} duplicates / missing IDs).")
    print(f"Total papers in DB: {total} across {len(by_lab)} labs.")
    print()
    print("Top labs by paper count:")
    for lab, n in by_lab[:15]:
        print(f"  {n:>3}  {lab}")


if __name__ == "__main__":
    main()
