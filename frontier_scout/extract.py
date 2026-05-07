import json

from anthropic import Anthropic

ROSTER_PROMPT = """\
You are extracting a research-lab roster from a webpage.
Return JSON with a single key "people", an array of objects with fields:
- name (string, required)
- role (string, e.g. "Professor", "PhD Student", "Postdoc"; "" if unclear)
- profile_url (string, absolute URL to the person's page; "" if not present)
- research_area (string, short topic; "" if unclear)

Only include current researchers (faculty, postdocs, PhD/Masters students).
Skip support staff, alumni, and visitors unless explicitly current.
Output valid JSON only, no prose, no code fence.
"""

WHY_PROMPT = """\
Given a paper title and abstract, write one tight sentence (max 25 words)
explaining why this matters for someone scouting frontier-tech research.
No hype, no marketing. Concrete claim or technique only.
Output the sentence only — no preamble, no quotes, no markdown.
"""

DRAFT_PROMPT = """\
You are drafting a short, warm email from a VC/operator to a researcher
who just published a paper. The goal is to start a real conversation —
not to pitch.

Constraints:
- Maximum 5 sentences. Aim for 3–4.
- Open with one specific, technical question about the paper. Reference a
  concrete claim, technique, or result from the abstract — not a generality.
- One sentence saying who the sender is. No pitching, no fund-name dropping.
- End with a low-cost ask: 15 minutes on a call, OR a reply pointing to a
  related paper they recommend. Sender's choice — pick the one that fits.
- Plain text. No subject line. Start with "Hi <first name>,". No "Dear Dr. X".
- Sound like a human who actually read the paper. Banned words: exciting,
  groundbreaking, fascinating, synergy, leverage, in the space of, at the
  intersection of, deeply impressed.

Output the email body only. No commentary, no signature block.
"""

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def _client() -> Anthropic:
    return Anthropic()


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def extract_roster(page_text: str, base_url: str, model: str = DEFAULT_MODEL) -> list[dict]:
    msg = _client().messages.create(
        model=model,
        max_tokens=4096,
        system=[{"type": "text", "text": ROSTER_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": (
                f"Base URL (resolve relative links against this): {base_url}\n\n"
                f"Page text:\n\n{page_text}"
            ),
        }],
    )
    raw = _strip_fence(msg.content[0].text)
    data = json.loads(raw)
    return data.get("people", [])


def explain(title: str, summary: str, model: str = DEFAULT_MODEL) -> str:
    msg = _client().messages.create(
        model=model,
        max_tokens=200,
        system=[{"type": "text", "text": WHY_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"Title: {title}\n\nAbstract: {summary}",
        }],
    )
    return msg.content[0].text.strip()


def draft_outreach(
    person_name: str,
    paper_title: str,
    paper_summary: str,
    sender_intro: str,
    model: str = DEFAULT_MODEL,
) -> str:
    msg = _client().messages.create(
        model=model,
        max_tokens=600,
        system=[{"type": "text", "text": DRAFT_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": (
                f"Recipient: {person_name}\n"
                f"Sender intro (rephrase or compress as needed): {sender_intro}\n\n"
                f"Paper title: {paper_title}\n"
                f"Paper abstract: {paper_summary}"
            ),
        }],
    )
    return msg.content[0].text.strip()
