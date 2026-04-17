/**
 * Logs & Database Status Logic
 * ----------------------------
 * Manages the display of database health, table statistics, 
 * network connectivity check history, and the administrative audit trail.
 */

mountLayout("Logs & Database", "Live row counts, database health, and audit trail.");

const content = document.getElementById("content");

/**
 * Initialize the page layout with several cards for different data types.
 */
content.innerHTML = `
  <div style="display:flex;flex-direction:column;gap:20px">

    <!-- Top row: DB Health + Table Stats -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">

      <!-- DB Health & Row Counts -->
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
          <div style="font-weight:700;font-size:15px">Database health</div>
          <button class="btn secondary" id="refresh-btn" style="padding:4px 14px;font-size:13px">Refresh</button>
        </div>
        <div id="health-status" style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
          <span id="health-dot" style="width:10px;height:10px;border-radius:50%;background:#555;display:inline-block"></span>
          <span id="health-text" class="small" style="color:var(--muted)">Not checked yet</span>
        </div>
        <div id="table-stats" style="display:flex;flex-direction:column;gap:6px"></div>
      </div>

      <!-- Audit Log Summary -->
      <div class="card">
        <div style="font-weight:700;font-size:15px;margin-bottom:14px">Audit log summary</div>
        <div id="audit-summary" style="color:var(--muted);font-size:13px">Loading…</div>
      </div>
    </div>

    <!-- Recent Device Connectivity History -->
    <div class="card">
      <div style="font-weight:700;font-size:15px;margin-bottom:14px">Recent connectivity checks</div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="border-bottom:1px solid rgba(255,255,255,.1);text-align:left">
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Time</th>
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Device</th>
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Status</th>
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Latency</th>
            </tr>
          </thead>
          <tbody id="checks-body">
            <tr><td colspan="4" style="padding:16px 10px;color:var(--muted)">Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Full interactive audit log table -->
    <div class="card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div style="font-weight:700;font-size:15px">Recent activity</div>
        <input id="log-filter" type="text" placeholder="Filter by user or action…"
          style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:6px;color:inherit;padding:4px 10px;font-size:13px;width:220px;outline:none"/>
      </div>
      <div id="log-table-wrap" style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="border-bottom:1px solid rgba(255,255,255,.1);text-align:left">
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Time</th>
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">User</th>
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Action</th>
              <th style="padding:6px 10px;color:var(--muted);font-weight:500">Detail</th>
            </tr>
          </thead>
          <tbody id="log-body">
            <tr><td colspan="4" style="padding:16px 10px;color:var(--muted)">Loading…</td></tr>
          </tbody>
        </table>
      </div>
      <div id="log-empty" style="display:none;padding:20px 0;text-align:center;color:var(--muted);font-size:13px">No log entries found</div>
    </div>

  </div>
`;

let allLogs = [];

/**
 * Escapes HTML to prevent XSS.
 * @param {string} str - The string to escape.
 * @returns {string} - Escaped HTML string.
 */
function esc(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Renders the table statistics (row counts) into the UI.
 * @param {Array} tables - Array of table objects with 'name' and 'rows'.
 */
function renderTableStats(tables) {
  const el = document.getElementById("table-stats");
  if (!tables || !tables.length) { 
    el.innerHTML = '<span class="small" style="color:var(--muted)">No data</span>'; 
    return; 
  }
  el.innerHTML = tables.map(t => `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)">
      <span style="font-size:13px;color:var(--muted)">${esc(t.name)}</span>
      <span style="font-size:13px;font-weight:600;font-variant-numeric:tabular-nums">${t.rows.toLocaleString()} rows</span>
    </div>
  `).join("");
}

/**
 * Renders the audit log entries into the table.
 * @param {Array} logs - Array of audit log entry objects.
 */
function renderLogs(logs) {
  const tbody = document.getElementById("log-body");
  const empty = document.getElementById("log-empty");
  if (!logs || !logs.length) {
    tbody.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  tbody.innerHTML = logs.map((l, i) => `
    <tr style="border-bottom:1px solid rgba(255,255,255,.04);${i % 2 === 0 ? "" : "background:rgba(255,255,255,.02)"}">
      <td style="padding:7px 10px;white-space:nowrap;color:var(--muted)">${esc(fmtTime(l.ts))}</td>
      <td style="padding:7px 10px;font-weight:500">${esc(l.user || "—")}</td>
      <td style="padding:7px 10px">
        <span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;background:rgba(99,153,34,.15);color:#97c459">${esc(l.action || "—")}</span>
      </td>
      <td style="padding:7px 10px;color:var(--muted);max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          title="${esc(l.detail || "")}">
        ${esc(l.detail || "—")}
      </td>
    </tr>
  `).join("");
}

/**
 * Calculates and renders a summary of the audit logs.
 * @param {Array} logs - Array of audit log entry objects.
 */
function renderAuditSummary(logs) {
  const el = document.getElementById("audit-summary");
  if (!logs || !logs.length) {
    el.innerHTML = '<span style="color:var(--muted)">No audit entries recorded yet.</span>';
    return;
  }
  const users = [...new Set(logs.map(l => l.user).filter(Boolean))];
  const actions = [...new Set(logs.map(l => l.action).filter(Boolean))];
  const latest = logs[0];
  el.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;justify-content:space-between">
        <span style="color:var(--muted)">Entries shown</span>
        <span style="font-weight:600">${logs.length}</span>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span style="color:var(--muted)">Unique users</span>
        <span style="font-weight:600">${users.length}</span>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span style="color:var(--muted)">Action types</span>
        <span style="font-weight:600">${actions.length}</span>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,.08);padding-top:10px">
        <div style="color:var(--muted);margin-bottom:4px;font-size:12px">Latest entry</div>
        <div style="font-size:13px">${fmtTime(latest.ts)}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:2px">${latest.user || "system"} — ${latest.action || ""}</div>
      </div>
    </div>
  `;
}

/**
 * Renders the recent device connectivity checks.
 * @param {Array} checks - Array of check objects from the ICMP scanner.
 */
function renderChecks(checks) {
  const tbody = document.getElementById("checks-body");
  if (!checks || !checks.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="padding:16px 10px;color:var(--muted)">No check data available</td></tr>';
    return;
  }
  tbody.innerHTML = checks.map((c, i) => `
    <tr style="border-bottom:1px solid rgba(255,255,255,.04);${i % 2 === 0 ? "" : "background:rgba(255,255,255,.02)"}">
      <td style="padding:7px 10px;white-space:nowrap;color:var(--muted)">${esc(fmtTime(c.ts))}</td>
      <td style="padding:7px 10px;font-weight:500">${esc(c.device_name || "—")}</td>
      <td style="padding:7px 10px">
        <span class="badge ${c.reachable ? 'ok' : 'danger'}" style="padding:2px 8px;font-size:11px">
          ${c.reachable ? 'online' : 'offline'}
        </span>
      </td>
      <td style="padding:7px 10px;color:var(--muted)">${c.latency_ms ? c.latency_ms.toFixed(1) + ' ms' : '—'}</td>
    </tr>
  `).join("");
}

/**
 * Primary data loading function. Fetches DB stats and check history in parallel.
 */
async function load() {
  const dot = document.getElementById("health-dot");
  const txt = document.getElementById("health-text");
  
  // Update status to indicate loading
  dot.style.background = "#888";
  txt.textContent = "Checking…";
  
  try {
    const [data, checks] = await Promise.all([
      apiFetch("/api/db-stats"),
      apiFetch("/api/devices/all-checks?limit=20")
    ]);
    
    // Update UI with health status
    dot.style.background = "#4caf50";
    txt.textContent = "Connected — " + fmtTime(data.checked_at);
    
    // Render the various data sections
    renderTableStats(data.tables);
    renderChecks(checks);
    
    allLogs = data.recent_logs || [];
    renderLogs(allLogs);
    renderAuditSummary(allLogs);
    
    setStatus(true, "Ready");
  } catch (e) {
    // Handle loading errors
    dot.style.background = "#e24b4a";
    txt.textContent = "Failed: " + e.message;
    document.getElementById("table-stats").innerHTML = '<span class="small" style="color:var(--muted)">Could not load stats</span>';
    setStatus(false, "Error");
  }
}

// Bind refresh button click
document.getElementById("refresh-btn").onclick = load;

/**
 * Real-time filtering logic for the audit log table.
 */
document.getElementById("log-filter").oninput = function() {
  const q = this.value.toLowerCase();
  renderLogs(q
    ? allLogs.filter(l =>
        (l.user||"").toLowerCase().includes(q) ||
        (l.action||"").toLowerCase().includes(q) ||
        (l.detail||"").toLowerCase().includes(q))
    : allLogs);
};

/**
 * Initialization: Auth check and initial data load.
 */
(async () => {
  if (!getToken()) { location.href = "/login.html"; return; }
  await load();
})();
