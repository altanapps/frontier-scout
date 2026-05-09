from anthropic import Anthropic

from frontier_scout import brightdata

PROMPT = """\
You are looking up public profile info for a research-lab member.

Use the web_search tool to find:
- github_handle (just the username; "" if not found)
- twitter_handle (without @; "" if not found; PERSONAL handle, not a lab account)
- linkedin_url (full URL like https://www.linkedin.com/in/firstname-lastname-xxxxx; "" if not found or uncertain)
- personal_site (full URL; "" if not found)
- email (only if publicly listed on the lab page or personal site; "" otherwise)

Verification approach:
- Always verify a candidate profile by checking it lists the researcher's lab,
  research area, or co-authors. If the affiliation doesn't match, leave the
  field blank.
- For LinkedIn: search "<full name> <lab keyword> linkedin". The right profile
  almost always lists the lab in current/past experience.
- For Twitter: ignore lab accounts and accounts with no profile bio matching
  the researcher.
- For email: only use what's published on the lab page or personal site. Never
  pattern-guess emails.

Be conservative. Blank > wrong. A confidently-wrong handle is worse than a
missing one because the user might cold-email the wrong person.

After your searches, you MUST call the report_handles tool exactly once with
your findings. That is your final action — no prose afterward.
"""

REPORT_TOOL = {
    "name": "report_handles",
    "description": "Report the public profile handles found for this researcher. Call this exactly once as your final action.",
    "input_schema": {
        "type": "object",
        "properties": {
            "github_handle": {"type": "string"},
            "twitter_handle": {"type": "string"},
            "linkedin_url": {"type": "string"},
            "personal_site": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["github_handle", "twitter_handle", "linkedin_url", "personal_site", "email"],
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
    # Step 1 — if Bright Data is configured, pre-resolve a LinkedIn URL via
    # their Web Unlocker. LinkedIn frequently blocks Anthropic's web search
    # endpoint, so this delivers ~90% LinkedIn coverage where Claude alone
    # gets ~30-50%.
    bd_linkedin = ""
    if brightdata.is_configured():
        lab_keyword = lab.split("—")[0].split("·")[0].strip()
        bd_linkedin = brightdata.find_linkedin_url(name, lab_keyword)

    user_msg = (
        f"Name: {name}\n"
        f"Lab: {lab}\n"
        f"Research area: {research_area or '(unknown)'}"
    )
    if bd_linkedin:
        user_msg += (
            f"\n\nBright Data pre-resolved a candidate LinkedIn URL: {bd_linkedin}\n"
            f"Verify it matches this researcher (lab/affiliation/research area). "
            f"If it doesn't match, leave linkedin_url blank."
        )

    client = Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        system=[{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[
            {"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches},
            REPORT_TOOL,
        ],
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "report_handles":
            return dict(block.input)
    return {}
