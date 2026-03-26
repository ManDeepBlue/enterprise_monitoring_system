# Enterprise Network & Productivity Monitor

This is my Final Year Project—a full-stack system designed to give a 360-degree view of an office network. It doesn't just track if a server is up; it monitors PC performance, scans for security risks on network devices, and even analyzes employee productivity based on browser activity.

### What it actually does:
* **Live PC Monitoring**: Tracks CPU, RAM, Disk, and Network usage in real-time from any computer running the agent.
* **Network Health**: Pings routers, switches, and APs to make sure the backbone of the network is stable.
* **Security Scans**: Includes a built-in port scanner that checks for open ports and gives a risk rating with suggestions on how to close them.
* **Productivity Tracking**: The agent reads local browser history (Chrome/Edge) and categorizes sites into "Productive," "Social," or "Streaming" so you can see where the time is going.
* **Smart Alerts**: Sends email notifications if a PC hits 90% CPU or if a critical device goes offline.

---

### Tech Stack
* **Backend**: FastAPI (Python) — chosen for its speed and native WebSocket support.
* **Database**: PostgreSQL — handles all the logs, metrics, and audit trails.
* **Frontend**: Vanilla HTML/CSS/JS — kept it light and fast without heavy frameworks.
* **Agent**: A lightweight Python script that runs on target machines using `psutil`.

---

### Getting Started (The Server)

The easiest way to run the whole backend is using Docker.

1. **Fire up the containers**:
   
   docker compose up --build -d
   
2. **Open the Dashboard**:
   Go to `http://localhost:8000/login.html` and log in.

---

### Setting up the Monitoring Agent

To monitor a PC, you need to run the agent on it.

1. **Get the Agent folder**: Copy the `agent/` directory to the target PC.
2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure it**:
   Rename `config.example.json` to `config.json`.
   * Set `server_url` to your server's IP (e.g., `http://192.168.1.50:8000`).
   * Get the `client_id` and `agent_key` from the "Add Client" section in the Dashboard.
4. **Run it**:
   ```bash
   python agent.py
   ```

---

### A Note on Privacy & Security
This tool is built for internal office monitoring. In a real-world setting, you should always inform users that the agent is running. 

**Pro-Tip for Testing**: If you're testing on a real network, make sure the server's firewall allows traffic on port 8000, otherwise the agents won't be able to "check in."

