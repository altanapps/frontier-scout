import json

from anthropic import Anthropic

PROMPT = """\
You are looking up public profile info for a research-lab member.

Use web search to find:
- github_handle (string, just the username; "" if not found)
- twitter_handle (string, without @; "" if not found)
- personal_site (full URL; "" if not found)
- email (only if publicly listed on the lab page or personal site; "" otherwise)

Be conservative: if you're not confident a profile is the same person, leave it
blank. Disambiguate using lab name and research area. Many academics have
common names — do not guess.

Output JSON only, no prose, no code fence:
{"github_handle": "...", "twitter_handle": "...", "personal_site": "...", "email": ""}
"""

DEFAULT_MODEL = "claude-sonnet-4-6"


def enrich_person(
    name: str,
    lab: str,
    research_area: str = "",
    model: str = DEFAULT_MODEL,
    max_searches: int = 5,
) -> dict:
    client = Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=[{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": max_searches,
        }],
        messages=[{
            "role": "user",
            "content": (
                f"Name: {name}\n"
                f"Lab: {lab}\n"
                f"Research area: {research_area or '(unknown)'}"
            ),
        }],
    )

    text = ""
    for block in reversed(msg.content):
        if getattr(block, "type", None) == "text":
            text = block.text.strip()
            break

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()

    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
