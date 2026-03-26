mountLayout("Alerts & Notifications", "Threshold-based alerts with multi-level severity and full event history.");
const content = document.getElementById("content");
content.className = "grid";

content.innerHTML = `
  <div class="card">
    <div class="row">
      <button class="btn secondary" id="refresh">Refresh</button>
      <div class="small" id="meta"></div>
    </div>
    <div style="height:10px"></div>
    <table class="table">
      <thead><tr><th>Time</th><th>Client</th><th>Severity</th><th>Type</th><th>Message</th><th>Status</th><th></th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
`;

let clients = [];
function sevBadge(sev){
  const cls = sev==="critical"||sev==="high" ? "danger" : (sev==="medium" ? "warn" : "ok");
  return `<span class="badge ${cls}">${sev}</span>`;
}

async function load(){
  clients = await apiFetch("/api/clients");
  const alerts = await apiFetch("/api/alerts?limit=200");
  document.getElementById("meta").textContent = `Showing ${alerts.length} most recent alerts`;

  document.getElementById("rows").innerHTML = alerts.map(a=>{
    const cn = (clients.find(c=>c.id===a.client_id)||{}).name || a.client_id;
    return `<tr>
      <td>${fmtTime(a.ts)}</td>
      <td>${cn}</td>
      <td>${sevBadge(a.severity)}</td>
      <td>${a.alert_type}</td>
      <td>${a.message}</td>
      <td>${a.status}</td>
      <td>
        <button class="btn secondary" onclick="setStatusAlert(${a.id},'ack')">Ack</button>
        <button class="btn secondary" onclick="setStatusAlert(${a.id},'closed')">Close</button>
      </td>
    </tr>`;
  }).join("");
}

async function setStatusAlert(id, status){
  await apiFetch(`/api/alerts/${id}`, {method:"PATCH", body: JSON.stringify({status})});
  await load();
}

document.getElementById("refresh").onclick = load;

let ws;
function connectWS(){
  ws = new WebSocket((location.protocol==="https:"?"wss://":"ws://") + location.host + "/ws/realtime");
  ws.onopen = ()=>{ setStatus(true,"Live"); ws.send("ping"); };
  ws.onmessage = (ev)=>{ try{
    const msg = JSON.parse(ev.data);
    if(msg.type === "alerts_updated") load();
  }catch{} };
  ws.onclose = ()=>{ setStatus(false,"Disconnected"); setTimeout(connectWS, 1500); };
}

(async ()=>{
  if(!getToken()) location.href="/login.html";
  await load();
  connectWS();
})();