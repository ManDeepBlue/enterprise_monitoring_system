
from __future__ import annotations
import socket
import asyncio
from typing import Iterable

async def tcp_check(host: str, port: int, timeout: float = 1.0) -> str:
    loop = asyncio.get_running_loop()
    try:
        fut = loop.create_connection(lambda: asyncio.Protocol(), host=host, port=port)
        tr, pr = await asyncio.wait_for(fut, timeout=timeout)
        tr.close()
        return "open"
    except Exception:
        return "closed"

async def scan_ports(host: str, ports: Iterable[int], timeout: float = 1.0, concurrency: int = 200) -> dict[int, str]:
    sem = asyncio.Semaphore(concurrency)
    results: dict[int, str] = {}

    async def _one(p: int):
        async with sem:
            results[p] = await tcp_check(host, p, timeout=timeout)

    await asyncio.gather(*[_one(p) for p in ports])
    return results

TOP_PORTS = [
    20,21,22,23,25,53,67,68,69,80,110,111,119,123,135,137,138,139,143,161,389,443,445,465,514,587,631,636,993,995,1433,1521,2049,3306,3389,5432,5900,6379,8080,8443
]
