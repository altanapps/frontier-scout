from collections import defaultdict
from datetime import datetime, timezone


def render(papers: list[dict], signals: list[dict] | None = None) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Frontier Scout — Digest {today}", ""]

    if not papers and not signals:
        lines.append("_Nothing new in the lookback window._")
        return "\n".join(lines)

    if signals:
        lines.append(f"## Signals ({len(signals)})")
        lines.append("")
        for s in signals:
            ts = (s.get("observed_at") or "")[:10]
            who = s["person_name"]
            lab = s.get("lab") or ""
            lab_suffix = f" — _{lab}_" if lab else ""
            lines.append(f"- **{who}**{lab_suffix}: {s['detail']} ({ts})")
            if s.get("url"):
                lines.append(f"  {s['url']}")
            lines.append("")

    if papers:
        by_lab: dict[str, list[dict]] = defaultdict(list)
        for p in papers:
            by_lab[p.get("matched_lab") or "Unattributed"].append(p)

        lines.append(f"## Papers ({len(papers)} across {len(by_lab)} labs)")
        lines.append("")

        for lab in sorted(by_lab):
            lines.append(f"### {lab}")
            lines.append("")
            for p in by_lab[lab]:
                published = (p.get("published") or "")[:10]
                person = p.get("matched_person") or "?"
                lines.append(f"- **{p['title']}** — _{person}_ ({published})")
                lines.append(f"  https://arxiv.org/abs/{p['arxiv_id']}")
                why = p.get("why_it_matters")
                if why:
                    lines.append(f"  → {why}")
                lines.append(f"  _Draft outreach: `frontier-scout draft {p['arxiv_id']}`_")
                lines.append("")

    return "\n".join(lines)
