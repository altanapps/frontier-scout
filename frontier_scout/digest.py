from collections import defaultdict
from datetime import datetime, timezone


def render(papers: list[dict]) -> str:
    by_lab: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        by_lab[p.get("matched_lab") or "Unattributed"].append(p)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Frontier Scout — Digest {today}", ""]

    if not papers:
        lines.append("_No new papers in the lookback window._")
        return "\n".join(lines)

    lines.append(f"**{len(papers)} new papers across {len(by_lab)} labs.**")
    lines.append("")

    for lab in sorted(by_lab):
        lines.append(f"## {lab}")
        lines.append("")
        for p in by_lab[lab]:
            published = (p.get("published") or "")[:10]
            person = p.get("matched_person") or "?"
            lines.append(f"- **{p['title']}** — _{person}_ ({published})")
            lines.append(f"  https://arxiv.org/abs/{p['arxiv_id']}")
            why = p.get("why_it_matters")
            if why:
                lines.append(f"  → {why}")
            lines.append("")

    return "\n".join(lines)
