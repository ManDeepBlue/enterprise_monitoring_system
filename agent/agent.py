"""
Enterprise Monitoring Agent
---------------------------
This script runs on client machines to collect system metrics (CPU, RAM, Disk, Network)
and optional web activity (browser history) to send to the central monitoring server.
"""

import json, time, hashlib, os, shutil, sqlite3
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import psutil
import httpx


def utcnow_iso():
    """Returns the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def sha256(s: str) -> str:
    """Computes the SHA-256 hash of a string, ignoring encoding errors."""
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()


def get_disk_percent():
    """
    Returns the percentage of disk usage for the root directory.
    Attempts to handle both Unix-like and Windows path styles.
    """
    try:
        return float(psutil.disk_usage("/").percent)
    except Exception:
        # Fallback for Windows if "/" fails
        return float(psutil.disk_usage(os.getenv("SystemDrive", "C:") + "\\").percent)


def webkit_to_iso(ct):
    """
    Converts a WebKit timestamp (microseconds since Jan 1, 1601) to ISO 8601 format.
    Used for parsing Chrome and Edge history timestamps.
    """
    if not ct or ct == 0:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ct)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


class NetRate:
    """
    Helper class to calculate network transmission rates (kbps) 
    by comparing snapshots of network I/O counters over time.
    """
    def __init__(self):
        self.prev = psutil.net_io_counters()
        self.prev_t = time.time()

    def kbps(self):
        """
        Calculates and returns the current (receive, transmit) rates in kbps 
        since the last call.
        """
        now = time.time()
        cur = psutil.net_io_counters()
        # Ensure dt is at least 1ms to avoid division by zero
        dt = max(now - self.prev_t, 0.001)
        rx = (cur.bytes_recv - self.prev.bytes_recv) * 8 / 1000.0 / dt
        tx = (cur.bytes_sent - self.prev.bytes_sent) * 8 / 1000.0 / dt
        self.prev, self.prev_t = cur, now
        return float(rx), float(tx)


def count_connections():
    """Returns the number of active IPv4/IPv6 network connections."""
    try:
        return len(psutil.net_connections(kind="inet"))
    except Exception:
        return 0


def find_chrome_history_paths():
    """
    Scans common default installation paths for Chrome and Edge browser 
    history files on Windows and Linux.
    """
    paths = []
    home = os.path.expanduser("~")

    # Windows Chrome/Edge default profile paths
    paths += [
        os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "History"),
        os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "History"),
    ]

    # Linux Chrome/Chromium default profile paths
    paths += [
        os.path.join(home, ".config", "google-chrome", "Default", "History"),
        os.path.join(home, ".config", "chromium", "Default", "History"),
    ]

    return [p for p in paths if os.path.exists(p)]


def read_recent_domains(limit=50):
    """
    Reads the most recent browser history entries.
    Copies the SQLite database to a temporary file to avoid 'database is locked' errors.
    Returns a list of unique domain visits.
    """
    visits = []

    for p in find_chrome_history_paths():
        tmp = p + f".tmp_{int(time.time())}"
        try:
            # Copy file to avoid locks from active browser sessions
            shutil.copy2(p, tmp)
            # Open as read-only
            con = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
            cur = con.cursor()
            
            # Fetch recent URLs ordered by last visit time
            cur.execute("""
                SELECT url, last_visit_time
                FROM urls
                WHERE last_visit_time > 0
                ORDER BY last_visit_time DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            con.close()

            for url, ts_raw in rows:
                if not url: continue
                try:
                    domain = urlparse(url).netloc.lower()
                    if domain:
                        visits.append({
                            "domain": domain,
                            "url_hash": sha256(url),
                            "ts_raw": ts_raw,
                            "ts": webkit_to_iso(ts_raw)
                        })
                except Exception: continue
        except Exception as e:
            print(f"Error reading history from {p}: {e}")
        finally:
            # Cleanup temporary file
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass

    # Remove duplicates within the current batch
    seen = set()
    unique_visits = []
    for v in visits:
        key = (v["domain"], v["url_hash"], v["ts_raw"])
        if key not in seen:
            seen.add(key)
            unique_visits.append(v)

    # Return sorted by raw timestamp descending
    return sorted(unique_visits, key=lambda x: x["ts_raw"], reverse=True)


def main():
    """
    Main loop: Loads configuration, initializes counters, and periodically 
    collects and posts metrics and web activity to the server.
    """
    # Load configuration from JSON file
    cfg_path = os.environ.get("AGENT_CONFIG", "config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    server     = cfg["server_url"].rstrip("/")
    client_id  = int(cfg["client_id"])
    agent_key  = cfg["agent_key"]
    interval   = int(cfg.get("interval_sec", 5))
    user_label = cfg.get("user_label", "default")
    enable_web = bool(cfg.get("enable_web_activity", True))

    headers = {"X-Agent-Key": agent_key}
    net = NetRate()
    last_sent_max_ts = 0

    print("Agent started. Sending to", server, "client_id", client_id)

    # Use a persistent HTTP client for efficiency
    with httpx.Client(timeout=10.0) as http:
        while True:
            try:
                # 1. Collect System Metrics
                cpu  = float(psutil.cpu_percent(interval=None))
                ram  = float(psutil.virtual_memory().percent)
                disk = get_disk_percent()
                rx, tx = net.kbps()
                conns  = int(count_connections())

                metric = {
                    "cpu": cpu, "ram": ram, "disk": disk,
                    "rx_kbps": rx, "tx_kbps": tx,
                    "connections": conns,
                    "ts": utcnow_iso()
                }

                # Ingest metrics
                http.post(
                    f"{server}/api/ingest/{client_id}/metrics",
                    headers=headers,
                    json=metric
                )

                # 2. Collect Web Activity (if enabled)
                if enable_web:
                    current_batch = read_recent_domains()
                    new_max_ts = last_sent_max_ts

                    for v in current_batch:
                        # Only send visits newer than the last one successfully sent
                        if v["ts_raw"] > last_sent_max_ts:
                            web = {
                                "user_label": user_label,
                                "ts": v["ts"],
                                "domain": v["domain"],
                                "url_hash": v["url_hash"],
                                "category": "" # Server-side categorization target
                                }                            
                            try:
                                resp = http.post(
                                    f"{server}/api/ingest/{client_id}/web",
                                    headers=headers,
                                    json=web
                                )
                                if resp.status_code == 200:
                                    # Update track of latest successfully sent visit
                                    if v["ts_raw"] > new_max_ts:
                                        new_max_ts = v["ts_raw"]
                            except Exception as ex:
                                print(f"Failed to send web activity: {ex}")

                    last_sent_max_ts = new_max_ts

            except Exception as e:
                print("Agent error:", e)

            # Wait for next collection cycle
            time.sleep(interval)


if __name__ == "__main__":
    main()
