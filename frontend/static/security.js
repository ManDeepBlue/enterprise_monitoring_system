
mountLayout("Security Assessment", "Port scanning, vulnerability scoring, risk classification and recommended actions.");
const content = document.getElementById("content");
content.className = "grid cols-2";

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
async function loadClients(){
  clients = await apiFetch("/api/clients");
  const sel = document.getElementById("client");
  sel.innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
}

function riskBadge(level){
  const cls = level==="high"?"danger":(level==="medium"?"warn":"ok");
  return `<span class="badge ${cls}">${level}</span>`;
}

async function loadScans(){
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
}

async function loadFindings(scanId){
  const f = await apiFetch(`/api/scans/${scanId}/findings`);
  const body = document.getElementById("findings");
  body.innerHTML = f.map(x=>`<tr>
    <td>${x.port}/${x.proto}</td>
    <td>${x.state}</td>
    <td>${riskBadge(x.risk_level)}</td>
    <td>${x.risk_score.toFixed(1)}</td>
    <td>${x.recommendation}</td>
  </tr>`).join("");
}

document.getElementById("run").onclick = async ()=>{
  const client_id = parseInt(document.getElementById("client").value,10);
  const target = document.getElementById("target").value.trim();
  const msg = document.getElementById("msg");
  msg.textContent = "Starting…";
  try{
    const run = await apiFetch("/api/scans", {method:"POST", body: JSON.stringify({client_id, target})});
    msg.textContent = `Scan started (ID ${run.id}). Refreshing…`;
    await loadScans();
    setTimeout(()=>loadScans(), 2000);
  }catch(e){
    msg.textContent = "Failed: " + e.message;
  }
};

(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await loadScans();
  setStatus(true, "Ready");
})();
