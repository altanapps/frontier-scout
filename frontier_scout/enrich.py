from anthropic import Anthropic

PROMPT = """\
You are looking up public profile info for a research-lab member.

Use the web_search tool to find:
- github_handle (just the username; "" if not found)
- twitter_handle (without @; "" if not found; PERSONAL handle, not a lab account)
- personal_site (full URL; "" if not found)
- email (only if publicly listed on the lab page or personal site; "" otherwise)

Be conservative on identity. If you can't disambiguate a profile from common-named
people via lab affiliation or research area, leave the field blank. Do not guess.
A lab's account (e.g. @BIOROB_EPFL) is NOT a personal handle — leave twitter_handle
blank in that case.

After your searches, you MUST call the report_handles tool exactly once with your
findings. That is your final action — no prose afterward.
"""

REPORT_TOOL = {
    "name": "report_handles",
    "description": "Report the public profile handles found for this researcher. Call this exactly once as your final action.",
    "input_schema": {
        "type": "object",
        "properties": {
            "github_handle": {"type": "string"},
            "twitter_handle": {"type": "string"},
            "personal_site": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["github_handle", "twitter_handle", "personal_site", "email"],
    },
}

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
        max_tokens=2048,
        system=[{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[
            {"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches},
            REPORT_TOOL,
        ],
        messages=[{
            "role": "user",
            "content": (
                f"Name: {name}\n"
                f"Lab: {lab}\n"
                f"Research area: {research_area or '(unknown)'}"
            ),
        }],
    )

    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "report_handles":
            return dict(block.input)
    return {}
