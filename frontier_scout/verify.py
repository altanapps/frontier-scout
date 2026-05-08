import asyncio

import httpx

from frontier_scout.config import Lab

HEADERS = {
    "User-Agent": "frontier-scout/0.1 verify (+https://github.com/altanapps/frontier-scout)"
}


async def _check_one(client: httpx.AsyncClient, lab: Lab) -> tuple[Lab, bool, str]:
    try:
        r = await client.head(lab.people_url, follow_redirects=True)
        if r.status_code < 400:
            return lab, True, f"HTTP {r.status_code}"
        if r.status_code in (405, 501):
            r = await client.get(lab.people_url, follow_redirects=True)
            if r.status_code < 400:
                return lab, True, f"HTTP {r.status_code} (GET)"
        return lab, False, f"HTTP {r.status_code}"
    except httpx.RequestError as e:
        return lab, False, type(e).__name__


async def _check_all(labs: list[Lab], timeout: float, concurrency: int):
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=timeout, headers=HEADERS, limits=limits) as client:
        async def guarded(lab: Lab):
            async with sem:
                return await _check_one(client, lab)
        return await asyncio.gather(*[guarded(lab) for lab in labs])


def check_all(
    labs: list[Lab],
    timeout: float = 15.0,
    concurrency: int = 16,
) -> list[tuple[Lab, bool, str]]:
    return asyncio.run(_check_all(labs, timeout, concurrency))
