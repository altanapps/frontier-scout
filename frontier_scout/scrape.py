import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "frontier-scout/0.1 (+https://github.com/altanapps/frontier-scout)"
}


def fetch(url: str, timeout: float = 30.0) -> str:
    r = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.text


def to_text(html: str, max_chars: int = 60000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return text[:max_chars]
