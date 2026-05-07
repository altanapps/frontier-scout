import unicodedata
from datetime import datetime

import arxiv


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def author_matches_roster(author_name: str, roster_name: str) -> bool:
    """True if an arXiv author entry plausibly matches a roster name.

    Match rule: last names equal AND first names equal, with initial-vs-full
    fallback only when one side is genuinely a single-letter initial. Avoids
    false positives like "Yu Chen" ↔ "Yixin Chen" while still matching
    "A. Crespi" ↔ "Alessandro Crespi".
    """
    a = _normalize(author_name).replace(".", " ").split()
    r = _normalize(roster_name).replace(".", " ").split()
    if len(a) < 2 or len(r) < 2:
        return False
    if a[-1] != r[-1]:
        return False
    a_first, r_first = a[0], r[0]
    if a_first == r_first:
        return True
    if len(a_first) == 1 or len(r_first) == 1:
        return a_first[0] == r_first[0]
    return False


def search_categories(
    categories: list[str],
    since: datetime,
    max_results: int = 2000,
) -> list[dict]:
    """Fetch all recent papers across a set of arXiv categories.

    Returns one dict per paper with full author list, so callers can
    match against their roster client-side. This is the rate-limit-safe
    path: 1 query per lab instead of N queries per researcher.
    """
    if not categories:
        return []
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    client = arxiv.Client(page_size=100, delay_seconds=5, num_retries=5)
    search = arxiv.Search(
        query=cat_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    out: list[dict] = []
    for r in client.results(search):
        if r.published < since:
            break
        out.append({
            "arxiv_id": r.entry_id.rsplit("/", 1)[-1],
            "title": " ".join(r.title.split()),
            "authors": [a.name for a in r.authors],
            "summary": " ".join(r.summary.split()),
            "published": r.published.isoformat(),
            "pdf_url": r.pdf_url,
        })
    return out


def search_author(
    author_name: str,
    categories: list[str],
    since: datetime,
    max_results: int = 50,
) -> list[dict]:
    """Per-author query. Kept for one-off lookups; do not call in a loop."""
    name_query = f'au:"{author_name}"'
    if categories:
        cat_query = " OR ".join(f"cat:{c}" for c in categories)
        query = f"({name_query}) AND ({cat_query})"
    else:
        query = name_query

    client = arxiv.Client(page_size=50, delay_seconds=5, num_retries=5)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    out: list[dict] = []
    for r in client.results(search):
        if r.published < since:
            break
        out.append({
            "arxiv_id": r.entry_id.rsplit("/", 1)[-1],
            "title": " ".join(r.title.split()),
            "authors": ", ".join(a.name for a in r.authors),
            "summary": " ".join(r.summary.split()),
            "published": r.published.isoformat(),
            "pdf_url": r.pdf_url,
        })
    return out
