/**
 * SNMP Monitoring Module.
 * 
 * Provides functionality to query networking devices for their interface status
 * using the SNMP protocol. Supports both manual queries and real-time updates 
 * via WebSockets.
 */

// Initialize the dashboard layout for the SNMP page
mountLayout("SNMP Link Status", "Monitor interface status and port details for networking devices.");

const content = document.getElementById("content");

/**
 * Define the SNMP query form and results table structure.
 */
content.className = "grid cols-1";
content.innerHTML = `
  <!-- Card: SNMP Query Configuration -->
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Select or Query Device</div>
    <div class="row" style="display:flex; gap:10px; align-items:flex-end;">
      <div style="flex:1"><div class="small">Known Device</div><select id="deviceSelect" class="input"><option value="">Custom Host...</option></select></div>
      <div style="flex:1"><div class="small">Host/IP</div><input class="input" id="host" placeholder="192.168.1.1"/></div>
      <div style="flex:1"><div class="small">Community</div><input class="input" id="community" value="public"/></div>
      <div style="flex:0.5"><div class="small">Port</div><input class="input" id="port" value="161" type="number"/></div>
      <div style="flex:0.5"><button class="btn" id="queryBtn" style="width:100%">Query</button></div>
    </div>
    <div class="small" id="msg" style="margin-top:10px"></div>
  </div>

  <!-- Card: SNMP Query Results (Initially Hidden) -->
  <div class="card" id="resultsCard" style="display:none">
    <div style="font-weight:700;margin-bottom:12px">Interface Status for <span id="targetHost"></span></div>
    <table class="table">
      <thead>
        <tr>
          <th>Index</th>
          <th>Description</th>
          <th>Alias</th>
          <th>Admin Status</th>
          <th>Oper Status</th>
          <th>Health / Reason</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
`;

// Element references
const deviceSelect = document.getElementById("deviceSelect");
const hostInput = document.getElementById("host");
const commInput = document.getElementById("community");
const portInput = document.getElementById("port");
const queryBtn = document.getElementById("queryBtn");
const msg = document.getElementById("msg");
const rows = document.getElementById("rows");
const resultsCard = document.getElementById("resultsCard");
const targetHost = document.getElementById("targetHost");

let currentDeviceId = null;

/**
 * Loads the list of registered devices from the backend to populate the select dropdown.
 * Also handles initial routing if a device ID is provided in the URL hash.
 */
async function loadDevices(){
  try {
    const devices = await apiFetch("/api/devices");
    devices.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.host;
      opt.dataset.id = d.id;
      opt.dataset.community = d.snmp_community;
      opt.dataset.port = d.snmp_port;
      opt.textContent = `${d.name} (${d.host})`;
      deviceSelect.appendChild(opt);
    });

    const hash = location.hash.replace("#device=", "");
    if (hash) {
        deviceSelect.value = Array.from(deviceSelect.options).find(o => o.dataset.id === hash)?.value || "";
        onDeviceChange();
    }
  } catch (e) {
    console.error("Failed to load devices", e);
  }
}

/**
 * Fetches the most recent cached SNMP status for a known device.
 * @param {number} deviceId - The unique ID of the device.
 * @param {string} host - The hostname or IP address (for display).
 */
async function loadLatestStatus(deviceId, host) {
  try {
    const data = await apiFetch(`/api/snmp/latest/${deviceId}`);
    if (data.length > 0) {
      targetHost.textContent = host;
      renderInterfaces(data.map(d => ({
        index: d.interface_index,
        description: d.description,
        alias: d.alias,
        admin_status: d.admin_status,
        oper_status: d.oper_status,
        admin_status_name: d.admin_status === 1 ? "up" : (d.admin_status === 2 ? "down" : "unknown"),
        oper_status_name: d.oper_status === 1 ? "up" : (d.oper_status === 2 ? "down" : "unknown"),
        reason: d.reason
      })));
      resultsCard.style.display = "block";
      msg.textContent = "";
    } else {
      msg.textContent = "No data found for this device.";
      resultsCard.style.display = "none";
    }
  } catch (e) {
    msg.textContent = "Error: " + e.message;
  }
}

/**
 * Renders the interface data into the results table.
 * @param {Array<Object>} interfaces - List of interface status objects.
 */
function renderInterfaces(interfaces) {
  /**
   * Helper to style status text based on RFC 1213 states.
   * 1 = up (Green), 2 = down (Red), Others = warn (Yellow).
   */
  const getStatusStyle = (status) => {
    if (status === 1) return "color: #2ecc71; font-weight: bold;";
    if (status === 2) return "color: #e74c3c; font-weight: bold;";
    return "color: #f1c40f; font-weight: bold;";
  };

  rows.innerHTML = interfaces.map(iface => `
    <tr>
      <td>${iface.index}</td>
      <td>${iface.description}</td>
      <td>${iface.alias || "—"}</td>
      <td style="${getStatusStyle(iface.admin_status)}">${iface.admin_status_name}</td>
      <td style="${getStatusStyle(iface.oper_status)}">${iface.oper_status_name}</td>
      <td>
        <div style="display:flex; align-items:center; gap:8px">
          <!-- Small dot indicator for quick visual health check -->
          <div style="width:10px; height:10px; border-radius:50%; background-color:${iface.oper_status === 1 ? '#2ecc71' : '#e74c3c'}"></div>
          <span>${iface.reason}</span>
        </div>
      </td>
    </tr>
  `).join("");
}

/**
 * Handler for when a device is selected from the dropdown.
 * Synchronizes inputs and triggers a status load.
 */
function onDeviceChange() {
  const opt = deviceSelect.options[deviceSelect.selectedIndex];
  if (opt.value) {
    hostInput.value = opt.value;
    commInput.value = opt.dataset.community || "public";
    portInput.value = opt.dataset.port || "161";
    currentDeviceId = opt.dataset.id;
    location.hash = `device=${currentDeviceId}`;
    
    if (currentDeviceId) {
        loadLatestStatus(currentDeviceId, opt.value);
    }
  } else {
    currentDeviceId = null;
    location.hash = "";
    resultsCard.style.display = "none";
    msg.textContent = "";
  }
}

deviceSelect.onchange = onDeviceChange;

/**
 * Performs a real-time SNMP query against the specified host.
 * This bypasses cached data and triggers a direct network probe.
 */
queryBtn.onclick = async () => {
  const host = hostInput.value.trim();
  const community = commInput.value.trim();
  const port = parseInt(portInput.value, 10);
  
  if (!host) {
    msg.textContent = "Please enter a host.";
    return;
  }
  
  msg.textContent = "Querying...";
  msg.style.color = "inherit";
  
  try {
    const data = await apiFetch(`/api/snmp/query?host=${encodeURIComponent(host)}&community=${encodeURIComponent(community)}&port=${port}`);
    targetHost.textContent = data.host;
    renderInterfaces(data.interfaces);
    resultsCard.style.display = "block";
    msg.textContent = "";
  } catch (e) {
    msg.textContent = "Query failed: " + e.message;
    msg.style.color = "#e24b4a";
  }
};

/**
 * WebSocket setup for real-time interface updates.
 * If the current viewing device is updated by the background scanner, 
 * refresh the interface list immediately.
 */
const ws = new WebSocket(`${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/realtime`);
ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "snmp_updated" && data.device_id == currentDeviceId) {
        loadLatestStatus(currentDeviceId, hostInput.value);
    }
};

/**
 * Initialization IIFE: Auth check and initial device load.
 */
(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadDevices();
  setStatus(true,"Ready");
})();
