import json, time, hashlib, os, shutil, sqlite3
from datetime import datetime, timezone
import psutil
import httpx

def utcnow_iso():
    return datetime.now().astimezone().isoformat()

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()

def get_disk_percent():
    try:
        return float(psutil.disk_usage("/").percent)
    except Exception:
        # Windows fallback
        return float(psutil.disk_usage(os.getenv("SystemDrive","C:") + "\\").percent)

class NetRate:
    def __init__(self):
        self.prev = psutil.net_io_counters()
        self.prev_t = time.time()

    def kbps(self):
        now = time.time()
        cur = psutil.net_io_counters()
        dt = max(now - self.prev_t, 0.001)
        rx = (cur.bytes_recv - self.prev.bytes_recv) * 8 / 1000.0 / dt
        tx = (cur.bytes_sent - self.prev.bytes_sent) * 8 / 1000.0 / dt
        self.prev, self.prev_t = cur, now
        return float(rx), float(tx)

def count_connections():
    try:
        return len(psutil.net_connections(kind="inet"))
    except Exception:
        return 0

def find_chrome_history_paths():
    paths = []
    home = os.path.expanduser("~")

    # Windows Chrome/Edge
    paths += [
        os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "History"),
        os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "History"),
    ]

    # Linux Chrome/Chromium
    paths += [
        os.path.join(home, ".config", "google-chrome", "Default", "History"),
        os.path.join(home, ".config", "chromium", "Default", "History"),
    ]

    return [p for p in paths if os.path.exists(p)]

def read_recent_domains(seconds_back=120):
    domains = []
    for p in find_chrome_history_paths():
        tmp = p + ".tmp_copy"
        try:
            shutil.copy2(p, tmp)
            con = sqlite3.connect(tmp)
            cur = con.cursor()

            cur.execute("""
                SELECT url, last_visit_time
                FROM urls
                ORDER BY last_visit_time DESC
                LIMIT 50
            """)

            for url, _ in cur.fetchall():
                if not url:
                    continue
                try:
                    from urllib.parse import urlparse
                    d = urlparse(url).netloc.lower()
                    if d:
                        domains.append((d, sha256(url)))
                except Exception:
                    continue

            con.close()

        except Exception:
            pass
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    # remove duplicates
    seen=set()
    out=[]
    for d,h in domains:
        if (d,h) in seen:
            continue
        seen.add((d,h))
        out.append((d,h))

    return out[:25]

def main():
    cfg_path = os.environ.get("AGENT_CONFIG", "config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    server = cfg["server_url"].rstrip("/")
    client_id = int(cfg["client_id"])
    agent_key = cfg["agent_key"]
    interval = int(cfg.get("interval_sec", 5))
    user_label = cfg.get("user_label", "default")
    enable_web = bool(cfg.get("enable_web_activity", True))

    headers = {"X-Agent-Key": agent_key}
    net = NetRate()

    print("Agent started. Sending to", server, "client_id", client_id)

    with httpx.Client(timeout=10.0) as http:
        while True:
            try:
                cpu = float(psutil.cpu_percent(interval=None))
                ram = float(psutil.virtual_memory().percent)
                disk = get_disk_percent()
                rx, tx = net.kbps()
                conns = int(count_connections())

                metric = {
                    "cpu": cpu, "ram": ram, "disk": disk,
                    "rx_kbps": rx, "tx_kbps": tx,
                    "connections": conns,
                    "ts": utcnow_iso()
                }

                http.post(f"{server}/api/ingest/{client_id}/metrics", headers=headers, json=metric)

                if enable_web:
                    for domain, url_hash in read_recent_domains():
                        web = {
                            "user_label": user_label,
                            "ts": utcnow_iso(),
                            "domain": domain,
                            "url_hash": url_hash,
                            "category": "",
                            "duration_seconds": 30
                        }
                        http.post(f"{server}/api/ingest/{client_id}/web", headers=headers, json=web)

            except Exception as e:
                print("Agent error:", e)

            time.sleep(interval)

if __name__ == "__main__":
    main()
