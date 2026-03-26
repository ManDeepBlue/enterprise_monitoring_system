
import aioping
import asyncio
from typing import Tuple

async def ping(host: str, timeout: float = 1.0) -> Tuple[bool, float | None]:
    try:
        delay = await aioping.ping(host, timeout=timeout)  # seconds
        return True, float(delay) * 1000.0
    except TimeoutError:
        return False, None
    except Exception:
        return False, None

async def ping_many(hosts: list[str], timeout: float = 1.0, concurrency: int = 50):
    sem = asyncio.Semaphore(concurrency)
    results = {}
    async def _one(h):
        async with sem:
            ok, ms = await ping(h, timeout=timeout)
            results[h] = (ok, ms)
    await asyncio.gather(*[_one(h) for h in hosts])
    return results
