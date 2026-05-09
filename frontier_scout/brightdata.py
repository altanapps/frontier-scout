"""Bright Data Web Unlocker wrapper.

Bright Data's Web Unlocker bypasses bot-protection (Cloudflare, captchas,
LinkedIn login walls) at scale via their residential proxy network. They
won the hiQ Labs v. LinkedIn case, so scraping public LinkedIn profiles
through their service is legally sanctioned.

Set BRIGHTDATA_API_KEY in your environment to enable. If unset, all
helpers in this module return empty / fall through silently — the rest
of the pipeline keeps working without Bright Data.

API docs: https://docs.brightdata.com/api-reference/web-unlocker
Cost: ~$4 per 1000 requests (Web Unlocker), ~$0.20-0.50 per LinkedIn
profile lookup (Datasets API).
"""

import os
import re
import urllib.parse
from typing import Optional

import httpx

API_URL = "https://api.brightdata.com/request"
ZONE = os.getenv("BRIGHTDATA_ZONE", "web_unlocker1")
API_KEY = os.getenv("BRIGHTDATA_API_KEY")


def is_configured() -> bool:
    return bool(API_KEY)


def _fetch(url: str, render: bool = True, timeout: float = 45.0) -> Optional[str]:
    """Fetch a URL via Bright Data Web Unlocker. Returns HTML or None."""
    if not API_KEY:
        return None
    payload = {
        "zone": ZONE,
        "url": url,
        "format": "raw",
    }
    if render:
        payload["data_format"] = "html"
    try:
        r = httpx.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        r.raise_for_status()
        return r.text
    except httpx.RequestError:
        return None


def google_search(query: str, num: int = 5) -> list[str]:
    """Run a Google search via Bright Data, return result URLs."""
    if not API_KEY:
        return []
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&num={num}"
    html = _fetch(url, render=False)
    if not html:
        return []
    # Extract result URLs from Google SERP HTML.
    urls = re.findall(r'href="(https?://[^"]+)"', html)
    seen: set[str] = set()
    out = []
    for u in urls:
        if "google." in u or "youtube.com" in u or "support.google" in u:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out[:num]


def _name_tokens(name: str) -> list[str]:
    """Lowercase, accent-stripped, split-on-whitespace name tokens.

    Handles characters NFKD doesn't decompose well (ø, æ, å, ß) by
    pre-substituting their ASCII equivalents — matches what URL slugs
    typically use.
    """
    import unicodedata
    n = name.lower()
    for src, dst in [("ø", "o"), ("æ", "ae"), ("å", "a"), ("ß", "ss"),
                     ("ł", "l"), ("đ", "d"), ("þ", "th")]:
        n = n.replace(src, dst)
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    n = n.replace(".", " ").replace("-", " ").replace("'", " ")
    return [t for t in n.split() if len(t) >= 2]


def _slug_matches_name(linkedin_url: str, name: str) -> bool:
    """True if the URL's slug plausibly matches the researcher's name.

    Accepts when:
    - both first and last name appear (handles short last names like Fu, Ge)
    - just the last name appears, if it's 4+ chars (handles "yarin-gal-...")
    - first + first-4-chars of last appear (handles diacritics: Paternò → patern)

    Rejects garbage like 'camille-guillaume' for 'Auke Ijspeert' or
    'wenlin-chen' for 'Hernández-Lobato'.
    """
    if "/in/" not in linkedin_url:
        return False
    # Strip query, fragment (#:~:text=... from Google), and trailing slashes
    slug = linkedin_url.split("/in/")[-1].split("?")[0].split("#")[0].split("/")[0].lower()
    tokens = _name_tokens(name)
    if not tokens:
        return False
    first = tokens[0]
    last = tokens[-1]
    if first in slug and last in slug:
        return True
    if len(last) >= 4 and last in slug:
        return True
    if first in slug and len(last) >= 4 and last[:4] in slug:
        return True
    return False


def find_linkedin_url(name: str, lab_keyword: str = "") -> str:
    """Search for the researcher's LinkedIn URL with name-slug verification.

    Returns a URL only if the slug plausibly matches the person's name.
    Rejects Google's first-hit-no-matter-what behavior — better blank
    than a wrong handle that triggers a misdirected cold email.
    """
    query = f'"{name}" {lab_keyword} site:linkedin.com/in'
    urls = google_search(query, num=8)
    for u in urls:
        if "linkedin.com/in/" not in u:
            continue
        cleaned = u.split("?")[0].rstrip("/")
        if _slug_matches_name(cleaned, name):
            return cleaned
    return ""


def fetch_linkedin_profile_text(profile_url: str) -> str:
    """Fetch LinkedIn profile HTML and return visible text. Empty on fail."""
    html = _fetch(profile_url, render=True)
    if not html:
        return ""
    # crude tag strip — good enough for matching
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:8000]
