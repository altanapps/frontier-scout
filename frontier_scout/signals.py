import os
from datetime import datetime

import httpx

GITHUB_API = "https://api.github.com"


def fetch_events(handle: str, since: datetime, timeout: float = 15.0) -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "frontier-scout/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    r = httpx.get(
        f"{GITHUB_API}/users/{handle}/events/public",
        headers=headers,
        timeout=timeout,
    )
    if r.status_code in (404, 403):
        return []
    r.raise_for_status()

    out: list[dict] = []
    for e in r.json():
        ts = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
        if ts < since:
            break
        sig = _classify(e)
        if sig:
            sig["observed_at"] = ts.isoformat()
            out.append(sig)
    return out


def _classify(event: dict) -> dict | None:
    t = event.get("type")
    repo = event.get("repo", {}).get("name", "")
    payload = event.get("payload") or {}

    if t == "CreateEvent" and payload.get("ref_type") == "repository":
        return {
            "kind": "new_repo",
            "detail": f"Created repository {repo}",
            "url": f"https://github.com/{repo}",
        }
    if t == "PublicEvent":
        return {
            "kind": "made_public",
            "detail": f"Made repository public: {repo}",
            "url": f"https://github.com/{repo}",
        }
    if t == "CreateEvent" and payload.get("ref_type") == "tag":
        ref = payload.get("ref", "")
        return {
            "kind": "new_release_tag",
            "detail": f"Tagged {ref} in {repo}",
            "url": f"https://github.com/{repo}/releases/tag/{ref}",
        }
    return None
