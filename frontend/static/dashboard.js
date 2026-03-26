mountLayout("Dashboard", "Centralized multi-client overview with real-time system health.");
const content = document.getElementById("content");
content.className = "grid cols-3";

// Static shell — written once, never overwritten by refresh()
content.innerHTML = `
  <div class="card" style="grid-column:1/-1;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end">
    <div style="flex:1;min-width:180px">
      <div class="small" style="margin-bottom:4px">Client name</div>
      <input id="clientName" class="input" placeholder="e.g. Acme Corp" style="width:100%;box-sizing:border-box"/>
    </div>
    <button class="btn" onclick="createClient()">Add Client</button>
  </div>
  <div id="keyBox" class="card" style="grid-column:1/-1;display:none;flex-direction:column;gap:12px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-weight:600">Client created</span>
      <span class="badge ok">Ready</span>
    </div>
    <div style="border:1px solid var(--border);border-radius:10px;overflow:hidden">
      <div style="display:flex;align-items:center;padding:10px 14px;border-bottom:1px solid var(--border);gap:12px">
        <span class="small" style="width:80px;flex-shrink:0">Client ID</span>
        <code id="clientId" style="flex:1;font-size:13px;color:var(--text)"></code>
      </div>
      <div style="display:flex;align-items:center;padding:10px 14px;gap:12px">
        <span class="small" style="width:80px;flex-shrink:0">Agent Key</span>
        <code id="agentKey" style="flex:1;font-size:13px;color:var(--text);word-break:break-all"></code>
        <button class="btn secondary" style="flex-shrink:0;padding:6px 12px;font-size:12px" onclick="copyKey()">Copy key</button>
      </div>
    </div>
    <div class="small" style="color:var(--warn)">⚠ Save the agent key now — it won't be shown again.</div>
  </div>
  <div id="clientList" style="display:contents"></div>
`;

function clientCard(c){
  const statusClass = c.status === "online" ? "ok" : (c.status === "offline" ? "danger" : "warn");
  return `
  <div class="card">
    <div class="kpi">
      <div>
        <div style="font-weight:700">${escHtml(c.name)}</div>
        <div class="small">${c.last_seen ? "Last seen: " + fmtTime(c.last_seen) : "No data yet"}</div>
      </div>
      <span class="badge ${statusClass}">${c.status || "unknown"}</span>
    </div>
    <div style="height:10px"></div>
    <div class="grid" style="grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
      <div class="card" style="padding:10px">
        <div class="small">CPU</div>
        <div class="value">${c.cpu ?? "—"}${c.cpu != null ? "%" : ""}</div>
      </div>
      <div class="card" style="padding:10px">
        <div class="small">RAM</div>
        <div class="value">${c.ram ?? "—"}${c.ram != null ? "%" : ""}</div>
      </div>
      <div class="card" style="padding:10px">
        <div class="small">RX</div>
        <div class="value">${c.rx_kbps ?? "—"}</div>
        <div class="small">kbps</div>
      </div>
      <div class="card" style="padding:10px">
        <div class="small">TX</div>
        <div class="value">${c.tx_kbps ?? "—"}</div>
        <div class="small">kbps</div>
      </div>
    </div>
    <div style="height:10px"></div>
    <div style="display:flex;gap:8px">
      <a class="btn secondary" style="flex:1;text-align:center" href="/performance.html#client=${c.id}">Open monitoring</a>
      <button class="btn" style="border-color:rgba(255,91,111,.4);color:var(--danger);padding:10px 14px" onclick="deleteClient(${c.id}, this)">Delete</button>
    </div>
  </div>`;
}

function escHtml(str){
  return String(str).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

// Only touches #clientList — the Add Client card and key box are never wiped
async function refresh(){
  try {
    const clients = await apiFetch("/api/analytics/clients/health");
    document.getElementById("clientList").innerHTML = clients.map(clientCard).join("");
  } catch(err) {
    console.error("Failed to refresh clients:", err);
  }
}

async function createClient(){
  const nameEl = document.getElementById("clientName");
  const name = nameEl.value.trim();
  if(!name){ nameEl.focus(); return; }

  try {
    const result = await apiFetch("/api/clients", {
      method: "POST",
      body: JSON.stringify({ name })
    });

    document.getElementById("clientId").textContent = result.id;
    document.getElementById("agentKey").textContent = result.agent_key;
    document.getElementById("keyBox").style.display = "flex";
    nameEl.value = "";

    await refresh();
  } catch(err) {
    alert("Failed to create client: " + err.message);
  }
}

async function deleteClient(id, btn){
  if(!confirm("Delete this client? All associated data will be removed.")) return;
  btn.disabled = true;
  btn.textContent = "Deleting…";
  try {
    await apiFetch(`/api/clients/${id}`, { method: "DELETE" });
    await refresh();
  } catch(err) {
    alert("Failed to delete client: " + err.message);
    btn.disabled = false;
    btn.textContent = "Delete";
  }
}

function copyKey(){
  const key = document.getElementById("agentKey").textContent;
  navigator.clipboard.writeText(key).then(() => {
    const btn = document.querySelector("#keyBox .btn");
    btn.textContent = "Copied!";
    setTimeout(() => btn.textContent = "Copy", 2000);
  });
}

let ws;
let retryDelay = 1500;

function connectWS(){
  ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws/realtime");
  ws.onopen = () => { retryDelay = 1500; setStatus(true, "Live"); ws.send("ping"); };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if(msg.type === "metric" || msg.type === "alerts_updated"){ refresh(); }
    } catch {}
  };
  ws.onclose = () => {
    setStatus(false, "Disconnected");
    setTimeout(connectWS, retryDelay);
    retryDelay = Math.min(retryDelay * 2, 30000);
  };
  ws.onerror = () => { setStatus(false, "Error"); };
}

(async () => {
  if(!getToken()) location.href = "/login.html";
  await refresh();
  connectWS();
})();
// deleteClient is defined inline via onclick — append here is a no-op placeholder