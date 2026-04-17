/**
 * Alerts & Notifications View
 * --------------------------
 * Displays a sortable/filterable table of system events and alerts, 
 * categorized by severity (Critical, High, Medium, Info).
 */

mountLayout("Alerts & Notifications", "Threshold-based alerts with multi-level severity and full event history.");

const content = document.getElementById("content");
content.className = "grid cols-3"; // 2/3 for the event table, 1/3 for the summary sidebar

// Static page structure
content.innerHTML = `
  <div class="card" style="grid-column: span 2">
    <div class="row">
      <div style="font-weight:700">Recent Events</div>
      <button class="btn secondary" id="refresh" style="margin-left:auto">Refresh</button>
    </div>
    <div style="height:10px"></div>
    <table class="table">
      <thead><tr><th>Time</th><th>Client</th><th>Severity</th><th>Type</th><th>Message</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div class="small" id="meta" style="margin-top:10px;color:var(--text-muted)"></div>
  </div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:15px">Alert Summary</div>
    <div id="summary-content">
      <div class="notice">Loading stats...</div>
    </div>
    <hr style="margin:15px 0;border:0;border-top:1px solid var(--border)">
    <div class="small" style="color:var(--text-muted)">
      Alerts are triggered based on thresholds set in <b>System Settings</b>.
    </div>
  </div>
`;

/**
 * Convert a timestamp into a relative "time ago" string (e.g., "5m ago").
 * @param {string} ts - The timestamp string.
 */
function timeAgo(ts) {
  const d = parseDate(ts);
  if(isNaN(d)) return "—";
  const ms = new Date() - d;
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return min + "m ago";
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return hrs + "h ago";
  return Math.floor(hrs / 24) + "d ago";
}

let clients = [];

/**
 * Helper to generate a styled badge based on alert severity.
 * @param {string} sev - The severity level.
 */
function sevBadge(sev){
  const cls = sev==="critical"||sev==="high" ? "danger" : (sev==="medium" ? "warn" : "ok");
  return `<span class="badge ${cls}">${sev}</span>`;
}

/**
 * Fetch and render the latest alerts and their aggregate statistics.
 */
async function load(){
  // Fetch clients to map client_id to names.
  clients = await apiFetch("/api/clients");
  const alerts = await apiFetch("/api/alerts?limit=200");
  
  // Render the alert rows in the table.
  document.getElementById("rows").innerHTML = alerts.map(a=>{
    const cn = (clients.find(c=>c.id===a.client_id)||{}).name || a.client_id;
    return `<tr>
      <td>${fmtTimeShort(a.ts)}</td>
      <td>${cn}</td>
      <td>${sevBadge(a.severity)}</td>
      <td>${a.alert_type}</td>
      <td title="${timeAgo(a.ts)}">${a.message}</td>
    </tr>`;
  }).join("");

  document.getElementById("meta").textContent = `Showing ${alerts.length} most recent events`;

  // Calculate summary statistics for the sidebar.
  const stats = { critical:0, high:0, medium:0, info:0 };
  alerts.forEach(a => { if(stats[a.severity] !== undefined) stats[a.severity]++; });

  document.getElementById("summary-content").innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px">
      <div class="row" style="justify-content:space-between">
        <span>Critical</span>
        <span class="badge danger">${stats.critical}</span>
      </div>
      <div class="row" style="justify-content:space-between">
        <span>High Severity</span>
        <span class="badge danger" style="opacity:0.8">${stats.high}</span>
      </div>
      <div class="row" style="justify-content:space-between">
        <span>Medium Severity</span>
        <span class="badge warn">${stats.medium}</span>
      </div>
      <div class="row" style="justify-content:space-between">
        <span>Information</span>
        <span class="badge ok">${stats.info}</span>
      </div>
    </div>
  `;
}

/**
 * Update the status of a specific alert (e.g., 'resolved').
 */
async function setStatusAlert(id, status){
  await apiFetch(`/api/alerts/${id}`, {method:"PATCH", body: JSON.stringify({status})});
  await load();
}

document.getElementById("refresh").onclick = load;

let ws;
/**
 * WebSocket connection for real-time alert event listener.
 */
function connectWS(){
  ws = new WebSocket((location.protocol==="https:"?"wss://":"ws://") + location.host + "/ws/realtime");
  ws.onopen = ()=>{ setStatus(true,"Live"); ws.send("ping"); };
  ws.onmessage = (ev)=>{ try{
    const msg = JSON.parse(ev.data);
    // Reload the list if the server announces an alert update.
    if(msg.type === "alerts_updated") load();
  }catch{} };
  ws.onclose = ()=>{ setStatus(false,"Disconnected"); setTimeout(connectWS, 1500); };
}

// Initialization
(async ()=>{
  if(!getToken()) location.href="/login.html";
  await load();
  connectWS();
})();