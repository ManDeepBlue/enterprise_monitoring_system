
mountLayout("Network Device Monitoring", "ICMP-based connectivity checks for routers, switches, and access points.");
const content = document.getElementById("content");
content.className = "grid cols-2";
content.innerHTML = `
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Add Device</div>
    <div class="row">
      <div><div class="small">Client</div><select id="client"></select></div>
      <div><div class="small">Type</div>
        <select id="type">
          <option value="router">Router</option>
          <option value="switch">Switch</option>
          <option value="ap">Access Point</option>
          <option value="other">Other</option>
        </select>
      </div>
    </div>
    <div style="height:10px"></div>
    <div class="row">
      <div><div class="small">Name</div><input class="input" id="name" placeholder="Core Switch"/></div>
      <div><div class="small">Host/IP</div><input class="input" id="host" placeholder="192.168.1.1"/></div>
    </div>
    <div style="height:12px"></div>
    <div style="font-weight:700;margin-bottom:8px">SNMP Settings</div>
    <div class="row">
      <div><div class="small">Enable SNMP</div><input type="checkbox" id="snmp_enabled"/></div>
      <div><div class="small">Community</div><input class="input" id="snmp_community" value="public"/></div>
      <div><div class="small">Port</div><input class="input" id="snmp_port" value="161" type="number"/></div>
    </div>
    <div style="height:12px"></div>
    <button class="btn" id="add">Add</button>
    <div class="small" id="msg" style="margin-top:10px"></div>
  </div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Devices</div>
    <table class="table">
      <thead><tr><th>Name</th><th>Type</th><th>Host</th><th></th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
`;

let clients = [];
async function loadClients(){
  clients = await apiFetch("/api/clients");
  document.getElementById("client").innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
}

async function loadDevices(){
  const devices = await apiFetch("/api/devices");
  document.getElementById("rows").innerHTML = devices.map(d=>`<tr>
    <td>${d.name}</td><td>${d.device_type}</td><td>${d.host}</td>
    <td style="text-align:right;white-space:nowrap">
      <a class="btn secondary" href="/analytics.html#device=${d.id}" style="padding:4px 10px;font-size:12px">Status</a>
      <button class="btn" onclick="deleteDevice(${d.id}, '${d.name.replace(/'/g, "\\'")}')" 
        style="padding:4px 10px;font-size:12px;background:rgba(226,75,74,0.1);color:#e24b4a;border:1px solid rgba(226,75,74,0.2);margin-left:4px">
        Delete
      </button>
    </td>
  </tr>`).join("");
}

window.deleteDevice = async (id, name) => {
  if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
  try {
    await apiFetch(`/api/devices/${id}`, { method: "DELETE" });
    await loadDevices();
    const msg = document.getElementById("msg");
    msg.textContent = "Deleted.";
    setTimeout(() => { if (msg.textContent === "Deleted.") msg.textContent = ""; }, 3000);
  } catch (e) {
    alert("Delete failed: " + e.message);
  }
};

document.getElementById("add").onclick = async ()=>{
  const client_id = parseInt(document.getElementById("client").value,10);
  const device_type = document.getElementById("type").value;
  const name = document.getElementById("name").value.trim();
  const host = document.getElementById("host").value.trim();
  const snmp_enabled = document.getElementById("snmp_enabled").checked;
  const snmp_community = document.getElementById("snmp_community").value.trim() || "public";
  const snmp_port = parseInt(document.getElementById("snmp_port").value, 10) || 161;
  const msg = document.getElementById("msg");
  msg.textContent = "Saving…";
  try{
    await apiFetch("/api/devices", {method:"POST", body: JSON.stringify({
      client_id, name, host, device_type, is_enabled:true,
      snmp_enabled, snmp_community, snmp_port
    })});
    msg.textContent = "Added.";
    await loadDevices();
  }catch(e){ msg.textContent = "Failed: " + e.message; }
};

(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await loadDevices();
  setStatus(true,"Ready");
})();
