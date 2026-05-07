from datetime import datetime

import arxiv


def search_author(
    author_name: str,
    categories: list[str],
    since: datetime,
    max_results: int = 50,
) -> list[dict]:
    name_query = f'au:"{author_name}"'
    if categories:
        cat_query = " OR ".join(f"cat:{c}" for c in categories)
        query = f"({name_query}) AND ({cat_query})"
    else:
        query = name_query

    client = arxiv.Client(page_size=50, delay_seconds=3, num_retries=3)
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
