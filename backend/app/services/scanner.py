"""
Network Port Scanner Service
----------------------------
Provides high-performance, asynchronous TCP port scanning capabilities
to identify open, closed, and filtered ports across targets.
"""

from __future__ import annotations
import asyncio
import errno
from typing import Iterable


async def tcp_check(host: str, port: int, timeout: float = 1.0) -> str:
    """
    Perform a TCP connect check to determine the port state.
    
    This function uses a non-blocking TCP connection to distinguish between:
    - 'open':     The connection was successfully established (SYN-ACK received).
    - 'closed':   The connection was actively refused (RST received).
    - 'filtered': No response was received within the timeout (dropped by firewall).
    
    :param host: Target hostname or IP address.
    :param port: The target port number.
    :param timeout: Time in seconds to wait for a response.
    :return: A string indicating the port state ('open', 'closed', or 'filtered').
    """
    loop = asyncio.get_running_loop()
    try:
        # Create a connection attempt without sending any actual protocol data.
        fut = loop.create_connection(lambda: asyncio.Protocol(), host=host, port=port)
        tr, _ = await asyncio.wait_for(fut, timeout=timeout)
        # Successfully connected, so the port is open.
        tr.close()
        return "open"

    except asyncio.TimeoutError:
        # No response received at all; the packet is likely being dropped.
        return "filtered"

    except ConnectionRefusedError:
        # Connection was actively reset by the target; the port is closed.
        return "closed"

    except OSError as e:
        # Certain OS errors (like Unreachable or Access Denied) indicate filtering.
        if e.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EACCES):
            return "filtered"
        return "filtered"

    except Exception:
        # Catch-all for other runtime errors during connection.
        return "filtered"


async def scan_ports(
    host: str,
    ports: Iterable[int],
    timeout: float = 1.0,
    concurrency: int = 200,
) -> dict[int, str]:
    """
    Scan a collection of ports on a host concurrently.
    
    Uses a semaphore to manage concurrent connections and prevent 
    system resource exhaustion or triggering IDS.
    
    :param host: Target host IP or hostname.
    :param ports: An iterable of port numbers to check.
    :param timeout: Timeout per port check.
    :param concurrency: Max concurrent connection attempts.
    :return: A dictionary mapping port numbers to their scanned state.
    """
    sem = asyncio.Semaphore(concurrency)
    results: dict[int, str] = {}

    async def _one(p: int):
        async with sem:
            # Execute the port check within the semaphore's scope.
            results[p] = await tcp_check(host, p, timeout=timeout)

    # Launch and wait for all concurrent checks to finish.
    await asyncio.gather(*[_one(p) for p in ports])
    return results

# A default list of well-known and commonly exploited ports for routine scans.
TOP_PORTS = [
    20, 21, 22, 23, 25, 53, 67, 68, 69, 80, 110, 111, 119, 123,
    135, 137, 138, 139, 143, 161, 389, 443, 445, 465, 514, 587,
    631, 636, 993, 995, 1433, 1521, 2049, 3306, 3389, 5432, 5900,
    6379, 8080, 8443
]