"""
ICMP Ping Service
-----------------
Provides asynchronous ping capabilities to monitor host availability 
and network latency using the ICMP protocol.
"""

import aioping
import asyncio
from typing import Tuple

async def ping(host: str, timeout: float = 1.0) -> Tuple[bool, float | None]:
    """
    Ping a single host once and return its availability and latency.
    
    :param host: The IP address or hostname to ping.
    :param timeout: Maximum time to wait for a response in seconds.
    :return: A tuple of (Success: bool, Delay: float in ms or None).
    """
    try:
        # aioping performs the low-level ICMP ECHO request.
        delay = await aioping.ping(host, timeout=timeout)  # returns delay in seconds
        # Return success and delay converted to milliseconds.
        return True, float(delay) * 1000.0
    except TimeoutError:
        # Host is unreachable or request timed out.
        return False, None
    except Exception:
        # Catch other errors like DNS resolution failures or network issues.
        return False, None

async def ping_many(hosts: list[str], timeout: float = 1.0, concurrency: int = 50):
    """
    Ping multiple hosts concurrently using a semaphore to limit overhead.
    
    :param hosts: A list of hostnames or IP addresses.
    :param timeout: The ping timeout for each individual host.
    :param concurrency: Max number of concurrent ping requests to allow.
    :return: A dictionary mapping hostnames to their (ok, latency) result.
    """
    # Use a semaphore to prevent overwhelming the system's network stack.
    sem = asyncio.Semaphore(concurrency)
    results = {}

    async def _one(h):
        # Acquire semaphore before pinging.
        async with sem:
            ok, ms = await ping(h, timeout=timeout)
            results[h] = (ok, ms)

    # Launch all pings and wait for completion.
    await asyncio.gather(*[_one(h) for h in hosts])
    return results
