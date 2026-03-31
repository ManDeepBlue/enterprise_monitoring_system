from __future__ import annotations
import asyncio
import errno
from typing import Iterable


async def tcp_check(host: str, port: int, timeout: float = 1.0) -> str:
    """
    Returns:
      "open"     — TCP connection succeeded (SYN-ACK received)
      "closed"   — Connection actively refused (RST received), errno ECONNREFUSED
      "filtered" — No response within timeout, or ICMP unreachable (firewall/drop)
    """
    loop = asyncio.get_running_loop()
    try:
        fut = loop.create_connection(lambda: asyncio.Protocol(), host=host, port=port)
        tr, _ = await asyncio.wait_for(fut, timeout=timeout)
        tr.close()
        return "open"

    except asyncio.TimeoutError:
        # No response at all — port is being silently dropped (filtered)
        return "filtered"

    except ConnectionRefusedError:
        # RST received — port is actively closed
        return "closed"

    except OSError as e:
        # EHOSTUNREACH / ENETUNREACH — ICMP unreachable, treated as filtered
        if e.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EACCES):
            return "filtered"
        # Anything else (bad hostname, etc.) — treat as filtered
        return "filtered"

    except Exception:
        return "filtered"


async def scan_ports(
    host: str,
    ports: Iterable[int],
    timeout: float = 1.0,
    concurrency: int = 200,
) -> dict[int, str]:
    sem = asyncio.Semaphore(concurrency)
    results: dict[int, str] = {}

    async def _one(p: int):
        async with sem:
            results[p] = await tcp_check(host, p, timeout=timeout)

    await asyncio.gather(*[_one(p) for p in ports])
    return results


TOP_PORTS = [
    20, 21, 22, 23, 25, 53, 67, 68, 69, 80, 110, 111, 119, 123,
    135, 137, 138, 139, 143, 161, 389, 443, 445, 465, 514, 587,
    631, 636, 993, 995, 1433, 1521, 2049, 3306, 3389, 5432, 5900,
    6379, 8080, 8443
]