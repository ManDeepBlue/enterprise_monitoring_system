import json, time, hashlib, os, shutil, sqlite3
from datetime import datetime, timezone
import psutil
import httpx

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()

def get_disk_percent():
    try:
        return float(psutil.disk_usage("/").percent)
    except Exception:
        # Windows fallback
        return float(psutil.disk_usage(os.getenv("SystemDrive","C:") + "\\").percent)

# --- PERFORMANCE TRACKING ---
# This class calculates how much data is being sent/received per second.
class NetRate:
    def __init__(self):
        self.prev = psutil.net_io_counters()
        self.prev_t = time.time()

    def kbps(self):
        now = time.time()
        cur = psutil.net_io_counters()
        dt = max(now - self.prev_t, 0.001)
        # We compare current bytes vs previous bytes to find the "speed"
        rx = (cur.bytes_recv - self.prev.bytes_recv) * 8 / 1000.0 / dt
        tx = (cur.bytes_sent - self.prev.bytes_sent) * 8 / 1000.0 / dt
        self.prev, self.prev_t = cur, now
        return float(rx), float(tx)

# --- BROWSER HISTORY TRACKER ---
# This looks for where Chrome and Edge store their history files on your computer.
def find_chrome_history_paths():
    paths = []
    home = os.path.expanduser("~")
    # Windows paths
    paths += [
        os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "History"),
        os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "History"),
    ]
    return [p for p in paths if os.path.exists(p)]

# Chrome saves time in a weird format (microseconds since year 1601). 
# This converts it to a normal date and time we can read.
def webkit_to_iso(ct):
    if not ct or ct == 0:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ct)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

# This function opens the browser's database and reads the most recent website visits.
def read_recent_domains(limit=50):
    visits = []
    for p in find_chrome_history_paths():
        tmp = p + ".tmp_copy" # We make a copy so we don't lock the browser's file
        try:
            shutil.copy2(p, tmp)
            con = sqlite3.connect(tmp)
            cur = con.cursor()
            # Grab the URL and the exact time it was visited
            cur.execute("""
                SELECT url, last_visit_time
                FROM urls
                WHERE last_visit_time > 0
                ORDER BY last_visit_time DESC
                LIMIT ?
            """, (limit,))
...
            con.close()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except: pass

    # Remove any duplicates from the list before returning
    seen = set()
    unique_visits = []
    for v in visits:
        key = (v["domain"], v["url_hash"], v["ts_raw"])
        if key not in seen:
            seen.add(key)
            unique_visits.append(v)
    return sorted(unique_visits, key=lambda x: x["ts_raw"], reverse=True)

# --- MAIN LOOP ---
# This is the part that runs forever while the agent is active.
def main():
    # Load our config (Server URL, Client ID, etc.)
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
    
    # We keep track of the last time we sent data so we don't send the same history twice.
    last_sent_max_ts = 0

    print("Agent started. Sending to", server, "client_id", client_id)

    with httpx.Client(timeout=10.0) as http:
        while True:
            try:
                # 1. Grab PC performance (CPU, RAM, Disk)
                cpu = float(psutil.cpu_percent(interval=None))
                ram = float(psutil.virtual_memory().percent)
                disk = get_disk_percent()
                rx, tx = net.kbps()
                conns = int(count_connections())

                # 2. Package it into a JSON "metric"
                metric = {
                    "cpu": cpu, "ram": ram, "disk": disk,
                    "rx_kbps": rx, "tx_kbps": tx,
                    "connections": conns,
                    "ts": utcnow_iso()
                }

                # 3. Send it to our FastAPI server
                http.post(f"{server}/api/ingest/{client_id}/metrics", headers=headers, json=metric)

                # 4. If web activity is on, check browser history and send NEW visits
                if enable_web:
                    current_batch = read_recent_domains()
                    new_max_ts = last_sent_max_ts
                    for v in current_batch:
                        if v["ts_raw"] > last_sent_max_ts:
                            web = {
                                "user_label": user_label,
                                "ts": v["ts"],
                                "domain": v["domain"],
                                "url_hash": v["url_hash"],
                                "category": "",
                                "duration_seconds": 30
                            }
                            try:
                                resp = http.post(f"{server}/api/ingest/{client_id}/web", headers=headers, json=web)
                                if resp.status_code == 200:
                                    if v["ts_raw"] > new_max_ts:
                                        new_max_ts = v["ts_raw"]
                            except Exception as ex:
                                print(f"Failed to send web activity: {ex}")
                    last_sent_max_ts = new_max_ts

            except Exception as e:
                print("Agent error:", e)

            # Wait for 5 seconds (or whatever interval is set) before doing it again
            time.sleep(interval)

            except Exception as e:
                print("Agent error:", e)

            time.sleep(interval)

if __name__ == "__main__":
    main()
