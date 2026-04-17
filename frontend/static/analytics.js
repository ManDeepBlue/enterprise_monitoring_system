/**
 * Visual Analytics & Forecasting Logic
 * ------------------------------------
 * Handles interactive metric forecasting using linear regression models
 * and displays historical reachability logs for network devices.
 */

mountLayout("Visual Analytics", "Interactive charts, trend analysis, and forecasting views.");

const content = document.getElementById("content");
content.className = "grid cols-2";

// Static UI for selection and charting.
content.innerHTML = `
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Forecast (Simple)</div>
    <div class="row">
      <select id="client"></select>
      <select id="metric">
        <option value="cpu">CPU</option>
        <option value="ram">RAM</option>
        <option value="rx_kbps">RX</option>
        <option value="tx_kbps">TX</option>
        <option value="connections">Connections</option>
      </select>
      <button class="btn secondary" id="run">Generate</button>
    </div>
    <div class="small" id="note" style="margin-top:10px"></div>
    <div style="height:10px"></div>
    <canvas id="fc" height="140"></canvas>
  </div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Device Status (Last 2h): <span id="deviceName"></span></div>
    <div class="small">Select from Devices page to jump here for a specific device.</div>
    <div style="height:10px"></div>
    <table class="table">
      <thead><tr><th>Time</th><th>Reachable</th><th>Latency</th></tr></thead>
      <tbody id="drows"></tbody>
    </table>
  </div>
`;

let clients = [];
let fc;

/**
 * Build or update the forecast Chart.js instance.
 * @param {number[]} values - Predicted data points.
 */
function buildForecast(values){
  const ctx = document.getElementById("fc");
  // Destroy previous chart instance to prevent memory leaks or overlay bugs.
  if(fc) fc.destroy();
  fc = new Chart(ctx, {
    type:"line",
    data:{ 
      labels: values.map((_,i)=>`+${i+1}`), 
      datasets:[{
        label:"Forecasted Trend", 
        data:values, 
        tension:.25,
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        fill: true
      }] 
    },
    options:{ 
      responsive:true,
      scales: { y: { beginAtZero: true } }
    }
  });
}

/**
 * Load all available clients to populate the dropdown.
 */
async function loadClients(){
  clients = await apiFetch("/api/clients");
  document.getElementById("client").innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
}

/**
 * Check the URL hash for a device ID and load its recent connectivity logs.
 */
async function loadDeviceFromHash(){
  const hash = new URLSearchParams(location.hash.replace("#",""));
  const deviceId = hash.get("device");
  if(!deviceId) return;

  const checks = await apiFetch(`/api/devices/${deviceId}/checks?minutes=120`);
  if(checks.length > 0) {
    document.getElementById("deviceName").textContent = checks[0].device_name || `Device #${deviceId}`;
  }

  // Render the reachability log table.
  document.getElementById("drows").innerHTML = checks.map(c=>`<tr>
    <td>${fmtTime(c.ts)}</td>
    <td>${c.reachable ? '<span class="badge ok">online</span>' : '<span class="badge danger">offline</span>'}</td>
    <td>${c.latency_ms ? c.latency_ms.toFixed(1)+' ms' : '—'}</td>
  </tr>`).join("");
}

/**
 * Handle the Forecast 'Generate' button click.
 */
document.getElementById("run").onclick = async ()=>{
  const clientId = parseInt(document.getElementById("client").value,10);
  const metric = document.getElementById("metric").value;
  
  // Request a simple linear forecast from the backend analytics engine.
  const res = await apiFetch(`/api/analytics/forecast/simple?client_id=${clientId}&metric=${metric}&minutes=240&horizon_points=12`);
  
  document.getElementById("note").textContent = res.note || `Model slope: ${res.model.slope.toFixed(3)}`;
  buildForecast(res.forecast || []);
};

// Initialization
(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await loadDeviceFromHash();
  setStatus(true,"Ready");
})();