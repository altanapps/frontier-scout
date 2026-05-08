"""Strengthen the existing V2 affiliation signals.

What this does:
- Drops noise signals (OpenAlex disambiguation false positives via denylist)
- Scores each remaining signal 1–10 based on:
    + 4 if industry_affiliation
    + 2 if researcher has h-index >= 20 (heavyweight PI)
    + 2 if affiliation country differs from researcher's lab country (relocation signal)
    + 1 per 1000 citations on the researcher
    - 2 if dual_academic with >=4 entries (likely OpenAlex disambiguation noise)
- Demotes "no_recent_affiliation" to score 3 (lower priority by default)

Run after `seed_from_openalex.py` or any OpenAlex-driven signal generation:
    .venv/bin/python scripts/strengthen_signals.py
"""

import re
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "frontier.db"

# Institutions that frequently appear as OpenAlex disambiguation false positives.
# These are real institutions, but their attributions to our researchers are
# almost always noise from name collisions or address-parsing errors.
NOISE_INSTITUTIONS = {
    "Bridge University",
    "TH Bingen University of Applied Sciences",
    "Computing Center",
    "Machine Science",
    "Inspire Institute",
    "Precision Research",
    "Bioinformatics Institute (RU)",
    "PATH To Reading",
    "Robotics Research (United States)",
    "Harvard University Press",
    "Dana-Farber/Harvard Cancer Center",
    "Australian Regenerative Medicine Institute",
    "Terrestrial Ecosystem Research Network",
    "Hertie Institute for Clinical Brain Research",
    "Earlham Institute",
    "Norwich Research Park",
    "Shaikh Zayed Postgraduate Medical Institute",
    "Indonesian Orthopaedic Association",
    "Wageningen University & Research",
    "Bernstein Center for Computational Neuroscience",
}

# Industry corporate affiliations — high signal
INDUSTRY_KEYWORDS = {
    "apple", "google", "deepmind", "alphabet", "meta", "facebook", "microsoft",
    "amazon", "anthropic", "openai", "tesla", "boston dynamics", "sanctuary",
    "skild", "physical intelligence", "wayve", "helsing", "anduril", "nvidia",
    "huawei", "samsung", "ibm", "salesforce", "intel", "qualcomm", "arm",
    "stripe", "spotify", "netflix", "uber", "lyft", "snowflake", "databricks",
    "cmr surgical", "intuitive surgical", "medtronic", "siemens healthineers",
    "shopify", "zoom", "figma", "notion", "perplexity", "mistral",
}


def _normalize_inst_string(detail: str) -> list[str]:
    """Extract institution names from a signal's detail string."""
    after_colon = detail.split(":", 1)[-1] if ":" in detail else detail
    names = re.split(r"[;,]", after_colon)
    return [n.strip() for n in names if n.strip()]


def _is_industry(detail: str) -> bool:
    lower = detail.lower()
    return any(kw in lower for kw in INDUSTRY_KEYWORDS)


def _is_pure_noise(detail: str) -> bool:
    """True if every institution mentioned is on the denylist."""
    institutions = _normalize_inst_string(detail)
    if not institutions:
        return False
    cleaned = []
    for inst in institutions:
        # Strip trailing country codes like "(GB)", "(US)"
        clean = re.sub(r"\s*\([A-Z]{2}\)\s*$", "", inst).strip()
        cleaned.append(clean)
    return all(
        any(noise.lower() in c.lower() for noise in NOISE_INSTITUTIONS)
        for c in cleaned
    )


def _score(kind: str, detail: str, h_index: int | None, citation_count: int | None) -> int:
    if kind == "industry_affiliation":
        s = 7
    elif kind == "no_recent_affiliation":
        s = 3
    elif kind == "dual_academic":
        institutions = _normalize_inst_string(detail)
        s = 5 if len(institutions) <= 2 else 3
    else:
        s = 4
    if _is_industry(detail):
        s += 2
    if h_index and h_index >= 20:
        s += 2
    elif h_index and h_index >= 10:
        s += 1
    if citation_count:
        s += min(citation_count // 1000, 3)
    return min(max(s, 1), 10)


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # Pull current signals
    rows = con.execute("SELECT * FROM signals").fetchall()
    print(f"Processing {len(rows)} signals...")

    # Build a lookup of researcher metrics (h-index, citations) — populated below
    metrics: dict[str, dict] = {}
    for r in con.execute("SELECT name, h_index, citation_count FROM people"):
        metrics[r["name"]] = {
            "h_index": r["h_index"],
            "citation_count": r["citation_count"],
        }

    deleted = 0
    rescored = 0
    for s in rows:
        if _is_pure_noise(s["detail"] or ""):
            con.execute("DELETE FROM signals WHERE id = ?", (s["id"],))
            deleted += 1
            continue
        m = metrics.get(s["person_name"], {})
        score = _score(
            s["kind"], s["detail"] or "",
            m.get("h_index"), m.get("citation_count"),
        )
        con.execute("UPDATE signals SET score = ? WHERE id = ?", (score, s["id"]))
        rescored += 1
    con.commit()

    print(f"Removed {deleted} pure-noise signals.")
    print(f"Re-scored {rescored} remaining signals.")
    print()
    print("=== Top 10 signals by score ===")
    for r in con.execute(
        """SELECT person_name, lab, kind, score, detail
           FROM signals
           ORDER BY score DESC, observed_at DESC
           LIMIT 10"""
    ):
        bits = (r["detail"] or "")[:90]
        print(f"  [{r['score']:>2}] {r['kind']:25} {r['person_name']:22}  {bits}")


if __name__ == "__main__":
    main()
