/**
 * Performance Monitoring Logic
 * ----------------------------
 * Handles fetching, displaying, and charting of client performance data.
 * Supports real-time updates via WebSockets and historical trend analysis via Chart.js.
 */

mountLayout("Performance Monitoring", "Real-time CPU, RAM, bandwidth and connections with historical trends.");

const content = document.getElementById("content");
content.className = "grid cols-2";

/**
 * Initialize the dashboard UI components including selection controls,
 * KPI cards, and trend chart canvases.
 */
content.innerHTML = `
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Select Client</div>
    <div class="row">
      <select id="client"></select>
      <select id="range">
        <option value="60">Last 1 hour</option>
        <option value="240">Last 4 hours</option>
        <option value="1440">Last 24 hours</option>
      </select>
      <button class="btn secondary" id="refresh">Refresh</button>
    </div>
    <div class="small" id="meta" style="margin-top:10px"></div>
  </div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Real-time Snapshot</div>
    <div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr));gap:10px" id="kpis"></div>
  </div>

  <div class="card" style="grid-column:1/-1">
    <div style="font-weight:700;margin-bottom:8px">System Health Trends</div>
    <canvas id="chartSystem" height="80"></canvas>
  </div>

  <div class="card" style="grid-column:1/-1">
    <div style="font-weight:700;margin-bottom:8px">Network & Traffic Trends</div>
    <canvas id="chartNetwork" height="80"></canvas>
  </div>
`;

let chartSystem, chartNetwork;

/**
 * Creates and updates Chart.js instances for system and network metrics.
 * @param {Array<string>} labels - Time labels for the x-axis.
 * @param {Object} series - Data series for CPU, RAM, Network, etc.
 */
function makeCharts(labels, series){
  const ctxS = document.getElementById("chartSystem");
  
  // Clean up existing chart instance before creating a new one
  if(chartSystem) chartSystem.destroy();
  
  chartSystem = new Chart(ctxS, {
    type:"line",
    data:{ labels, datasets: [
      {
        label:"CPU %", 
        data: series.cpu, 
        tension:.4, 
        borderColor: "#3498db", 
        backgroundColor: "rgba(52, 152, 219, 0.2)", 
        fill: true,
        pointRadius: 2
      },
      {
        label:"RAM %", 
        data: series.ram, 
        tension:.4, 
        borderColor: "#9b59b6", 
        backgroundColor: "rgba(155, 89, 182, 0.2)", 
        fill: true,
        pointRadius: 2
      },
    ]},
    options:{ 
      responsive:true, 
      interaction:{mode:"index", intersect:false}, 
      plugins: { legend: { display: true, position: 'top', align: 'end' } },
      scales:{ 
        x:{ticks:{maxTicksLimit:8}, grid: { display: false }}, 
        y:{beginAtZero:true, max:100, grid: { color: "rgba(255,255,255,0.05)" }} 
      } 
    }
  });

  const ctxN = document.getElementById("chartNetwork");
  if(chartNetwork) chartNetwork.destroy();
  chartNetwork = new Chart(ctxN, {
    type:"line",
    data:{ labels, datasets: [
      {label:"RX kbps", data: series.rx, tension:.4, borderColor: "#2ecc71", backgroundColor: "rgba(46, 204, 113, 0.1)", fill: true},
      {label:"TX kbps", data: series.tx, tension:.4, borderColor: "#e67e22", backgroundColor: "rgba(230, 126, 34, 0.1)", fill: true},
      {label:"Connections", data: series.conn, tension:.4, borderColor: "#f1c40f", yAxisID: 'y1', pointStyle: 'rectRot', radius: 4},
    ]},
    options:{ 
      responsive:true, 
      interaction:{mode:"index", intersect:false}, 
      plugins: { legend: { display: true, position: 'top', align: 'end' } },
      scales:{ 
        x:{ticks:{maxTicksLimit:8}, grid: { display: false }}, 
        y:{title:{display:true, text:"kbps"}, beginAtZero:true, grid: { color: "rgba(255,255,255,0.05)" }},
        y1:{type:"linear", display:true, position:"right", title:{display:true, text:"Count"}, grid:{drawOnChartArea:false}}
      } 
    }
  });
}

/**
 * Generates a KPI card HTML string.
 * @param {string} label - The KPI title.
 * @param {number|string} value - The KPI value.
 * @param {string} [suffix=""] - Optional unit suffix.
 * @returns {string} HTML string.
 */
function kpi(label, value, suffix=""){
  return `<div class="card" style="padding:10px">
    <div class="small">${label}</div>
    <div class="value">${value ?? "—"}${value!=null?suffix:""}</div>
  </div>`;
}

/**
 * Fetches clients and populates the selection dropdown.
 * Also handles initial client selection from the URL hash.
 */
async function loadClients(){
  try {
    const clients = await apiFetch("/api/clients");
    const sel = document.getElementById("client");
    sel.innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
    
    // Check if a client ID was provided in the URL hash (e.g. #client=5)
    const hash = new URLSearchParams(location.hash.replace("#",""));
    if(hash.get("client")) sel.value = hash.get("client");
  } catch(err) {
    console.error("Failed to load clients:", err);
  }
}

/**
 * Fetches and refreshes metrics for the currently selected client and time range.
 */
async function refresh(){
  const clientId = parseInt(document.getElementById("client").value,10);
  const minutes = parseInt(document.getElementById("range").value,10);

  if(isNaN(clientId)) return;

  try {
    // Fetch latest point and historical range in parallel
    const [latest, arr] = await Promise.all([
      apiFetch(`/api/metrics/${clientId}/latest`),
      apiFetch(`/api/metrics/${clientId}/range?minutes=${minutes}`)
    ]);

    // Update real-time snapshot
    document.getElementById("meta").textContent = latest?.ts ? "Latest: " + fmtTime(latest.ts) : "No data";
    document.getElementById("kpis").innerHTML = [
      kpi("CPU", latest?.cpu, "%"),
      kpi("RAM", latest?.ram, "%"),
      kpi("Disk", latest?.disk, "%"),
      kpi("RX", latest?.rx_kbps, " kbps"),
      kpi("TX", latest?.tx_kbps, " kbps"),
      kpi("Connections", latest?.connections, ""),
    ].join("");

    // Prepare labels and series for charting
    const labels = arr.map(x=>fmtTimeShort(x.ts));
    makeCharts(labels, {
      cpu: arr.map(x=>x.cpu),
      ram: arr.map(x=>x.ram),
      rx: arr.map(x=>x.rx_kbps),
      tx: arr.map(x=>x.tx_kbps),
      conn: arr.map(x=>x.connections),
    });
  } catch(err) {
    console.error("Failed to refresh metrics:", err);
  }
}

// Bind manual refresh button
document.getElementById("refresh").onclick = refresh;

let ws;
/**
 * Establishes a WebSocket connection for real-time metric updates.
 */
function connectWS(){
  ws = new WebSocket((location.protocol==="https:"?"wss://":"ws://") + location.host + "/ws/realtime");
  ws.onopen = ()=>{ 
    setStatus(true,"Live"); 
    ws.send("ping"); 
  };
  ws.onmessage = (ev)=>{ 
    try {
      const msg = JSON.parse(ev.data);
      if(msg.type === "metric"){
        const clientId = parseInt(document.getElementById("client").value,10);
        // Refresh only if the message is for the currently viewed client
        if(msg.client_id === clientId) refresh();
      }
    } catch {}
  };
  ws.onclose = ()=>{ 
    setStatus(false,"Disconnected"); 
    setTimeout(connectWS, 2000); // Reconnect after 2 seconds
  };
}

/**
 * Initialization: Auth check, load clients, fetch initial data, and start WS.
 */
(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await refresh();
  connectWS();
})();
