"""Natural-language search over the roster + papers, via Claude.

The user types a thesis-shaped question — "find me a quantum researcher
with recent papers on photonic systems" — and Claude returns a ranked
list of matches with one-line reasons.

V0: send Claude a compact DB digest + the question, parse the JSON answer.
At ~150 papers + ~1000 people, the digest is ~20-40K tokens — fine for
Sonnet 4.6. ~$0.05 per query, ~3-5 second response.

V1 upgrade: pre-compute embeddings, retrieve top-50 candidates, then
let Claude rank. Saves cost as DB grows.
"""

import json
import sqlite3
from pathlib import Path

from anthropic import Anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are a research-scout assistant for a European deep-tech VC. Given a
question and a compact database of EU/UK research labs, researchers, and
recent papers, return a ranked list of the most relevant researchers.

Rules:
- Output JSON only, no prose. Schema: {"matches": [{"person_id": int, "reason": str, "relevant_paper_id": int or null}]}
- "reason" must be ≤ 25 words, concrete, ground-truth from the data (mention a paper title, a research area, or a lab if relevant).
- Return at most 8 matches, sorted by relevance.
- Never invent people or papers — only use IDs from the database. If nothing matches the query, return {"matches": []} and don't fabricate.
- Prefer matches with a directly-relevant recent paper. If none, fall back to lab/research-area match.
"""


def _build_db_digest(con: sqlite3.Connection) -> str:
    """Compact text digest of papers + researchers for the prompt."""
    parts = ["# RESEARCHERS"]
    for r in con.execute(
        "SELECT id, name, lab, role, research_area FROM people ORDER BY lab, name"
    ):
        bits = [f"[{r['id']}] {r['name']}"]
        if r["role"]: bits.append(f"({r['role']})")
        bits.append(f"— {r['lab']}")
        if r["research_area"]: bits.append(f"· {r['research_area']}")
        parts.append(" ".join(bits))

    parts.append("\n# PAPERS (last 16 months)")
    for p in con.execute(
        "SELECT id, title, matched_person, matched_lab, why_it_matters, published FROM papers ORDER BY published DESC"
    ):
        line = f"[{p['id']}] {p['title']}"
        if p["matched_person"]: line += f" — {p['matched_person']}"
        if p["matched_lab"]: line += f" ({p['matched_lab']})"
        if p["why_it_matters"]: line += f" :: {p['why_it_matters']}"
        parts.append(line)

    return "\n".join(parts)


def search(query: str, db_path: Path, model: str = DEFAULT_MODEL) -> dict:
    """Run a natural-language search. Returns the raw JSON payload from Claude."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    digest = _build_db_digest(con)

    client = Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": (
                f"DATABASE:\n\n{digest}\n\n"
                f"---\n\nQUESTION: {query}\n\n"
                "Return JSON only."
            ),
        }],
    )

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text = block.text.strip()
            break
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"matches": [], "error": "could not parse model output", "raw": text[:400]}


def hydrate_matches(matches: list[dict], db_path: Path) -> list[dict]:
    """Fetch full person + paper rows for each match ID returned by Claude."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    out = []
    for m in matches:
        pid = m.get("person_id")
        if not pid:
            continue
        person = con.execute("SELECT * FROM people WHERE id = ?", (pid,)).fetchone()
        if not person:
            continue
        paper = None
        rid = m.get("relevant_paper_id")
        if rid:
            row = con.execute("SELECT * FROM papers WHERE id = ?", (rid,)).fetchone()
            if row:
                paper = dict(row)
        out.append({
            "person": dict(person),
            "paper": paper,
            "reason": m.get("reason", ""),
        })
    return out
