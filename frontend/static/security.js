/**
 * Security Assessment Logic
 * -------------------------
 * Orchestrates network port scanning, vulnerability analysis, 
 * and the display of security findings and recommendations.
 */

mountLayout("Security Assessment", "Port scanning, vulnerability scoring, risk classification and recommended actions.");

const content = document.getElementById("content");
content.className = "grid cols-2";

/**
 * Initialize the Security UI: Scan controls, Recent Scans list, and Detailed Findings table.
 */
content.innerHTML = `
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Start Port Scan</div>
    <div class="row">
      <div>
        <div class="small">Client</div>
        <select id="client"></select>
      </div>
      <div>
        <div class="small">Target (IP/Host)</div>
        <input class="input" id="target" placeholder="192.168.1.10" />
      </div>
    </div>
    <div style="height:12px"></div>
    <button class="btn" id="run">Run scan</button>
    <div class="small" id="msg" style="margin-top:10px"></div>
  </div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Recent Scans</div>
    <table class="table">
      <thead><tr><th>ID</th><th>Client</th><th>Target</th><th>Status</th><th>Open</th><th></th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>

  <div class="card" style="grid-column:1/-1">
    <div style="font-weight:700;margin-bottom:8px">Findings</div>
    <table class="table">
      <thead><tr><th>Port</th><th>State</th><th>Risk</th><th>Score</th><th>Recommendation</th></tr></thead>
      <tbody id="findings"></tbody>
    </table>
  </div>
`;

let clients = [];

/**
 * Fetch available clients and populate the selection dropdown.
 */
async function loadClients(){
  try {
    clients = await apiFetch("/api/clients");
    const sel = document.getElementById("client");
    sel.innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
  } catch(err) {
    console.error("Failed to load clients:", err);
  }
}

/**
 * Returns a CSS class name for the badge based on risk level.
 * @param {string} level - Risk level ('high', 'medium', 'low').
 * @returns {string} HTML string for the badge.
 */
function riskBadge(level){
  const cls = level==="high"?"danger":(level==="medium"?"warn":"ok");
  return `<span class="badge ${cls}">${level}</span>`;
}

/**
 * Fetch and list the most recent security scans.
 */
async function loadScans(){
  try {
    const scans = await apiFetch("/api/scans?limit=20");
    const rows = document.getElementById("rows");
    rows.innerHTML = scans.map(s=>{
      const cn = (clients.find(c=>c.id===s.client_id)||{}).name || s.client_id;
      const open = (s.summary && s.summary.count_open!=null) ? s.summary.count_open : "—";
      return `<tr>
        <td>${s.id}</td><td>${cn}</td><td>${s.target}</td><td>${s.status}</td><td>${open}</td>
        <td><button class="btn secondary" onclick="loadFindings(${s.id})">View</button></td>
      </tr>`;
    }).join("");
  } catch(err) {
    console.error("Failed to load scans:", err);
  }
}

/**
 * Fetch and display detailed findings for a specific scan.
 * @param {number} scanId - The ID of the scan to load findings for.
 */
async function loadFindings(scanId){
  try {
    const f = await apiFetch(`/api/scans/${scanId}/findings`);
    const body = document.getElementById("findings");
    body.innerHTML = f.map(x=>`<tr>
      <td>${x.port}/${x.proto}</td>
      <td>${x.state}</td>
      <td>${riskBadge(x.risk_level)}</td>
      <td>${x.risk_score.toFixed(1)}</td>
      <td>${x.recommendation}</td>
    </tr>`).join("");
  } catch(err) {
    console.error("Failed to load findings:", err);
  }
}

/**
 * Start a new security scan for the selected client and target.
 */
document.getElementById("run").onclick = async ()=>{
  const client_id = parseInt(document.getElementById("client").value,10);
  const target = document.getElementById("target").value.trim();
  const msg = document.getElementById("msg");
  
  if(!target) {
    msg.textContent = "Please specify a target IP or hostname.";
    return;
  }

  msg.textContent = "Starting…";
  try{
    const run = await apiFetch("/api/scans", {
      method:"POST", 
      body: JSON.stringify({client_id, target})
    });
    msg.textContent = `Scan started (ID ${run.id}). Refreshing…`;
    await loadScans();
    
    // Poll for status update after a brief delay
    setTimeout(()=>loadScans(), 3000);
  }catch(e){
    msg.textContent = "Failed: " + e.message;
  }
};

/**
 * Initialization: Auth check, client load, scan load.
 */
(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await loadScans();
  setStatus(true, "Ready");
})();
