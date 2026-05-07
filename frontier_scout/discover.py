from anthropic import Anthropic

PROMPT = """\
You help a VC build a list of leading research labs in a given area.

Use web search to find labs in Europe and the UK working on the topic.
For each lab return:
- name (string, format: "University — Lab name", e.g. "ETH Zurich — Robotic Systems Lab")
- people_url (full URL to a public lab page that lists faculty + students)
- arxiv_categories (array of relevant arXiv category codes, e.g. cs.RO, q-bio.NC, cond-mat.supr-con)

Aim for 8–15 labs. Skip any lab that doesn't have a public people page you
verified via search. Prefer university labs over corporate research where there
is overlap.

Output valid YAML only — no prose, no fence — in this exact shape:

labs:
  - name: ...
    people_url: ...
    arxiv_categories: [...]
"""

DEFAULT_MODEL = "claude-sonnet-4-6"


def find_labs(topic: str, model: str = DEFAULT_MODEL, max_searches: int = 8) -> str:
    client = Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": max_searches,
        }],
        messages=[{"role": "user", "content": f"Topic: {topic}"}],
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
    return text.strip()
