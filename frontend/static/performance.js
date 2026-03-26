mountLayout("Performance Monitoring", "Real-time CPU, RAM, bandwidth and connections with historical trends.");
const content = document.getElementById("content");
content.className = "grid cols-2";

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
    <div style="font-weight:700;margin-bottom:8px">Trends</div>
    <canvas id="chart" height="110"></canvas>
  </div>
`;

let chart;
function makeChart(labels, series){
  const ctx = document.getElementById("chart");
  if(chart) chart.destroy();
  chart = new Chart(ctx, {
    type:"line",
    data:{ labels, datasets: [
      {label:"CPU %", data: series.cpu, tension:.25},
      {label:"RAM %", data: series.ram, tension:.25},
      {label:"RX kbps", data: series.rx, tension:.25},
      {label:"TX kbps", data: series.tx, tension:.25},
      {label:"Connections", data: series.conn, tension:.25},
    ]},
    options:{ responsive:true, interaction:{mode:"index", intersect:false}, scales:{ x:{ticks:{maxTicksLimit:10}} } }
  });
}

function kpi(label, value, suffix=""){
  return `<div class="card" style="padding:10px">
    <div class="small">${label}</div>
    <div class="value">${value ?? "—"}${value!=null?suffix:""}</div>
  </div>`;
}

async function loadClients(){
  const clients = await apiFetch("/api/clients");
  const sel = document.getElementById("client");
  sel.innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
  const hash = new URLSearchParams(location.hash.replace("#",""));
  if(hash.get("client")) sel.value = hash.get("client");
}

async function refresh(){
  const clientId = parseInt(document.getElementById("client").value,10);
  const minutes = parseInt(document.getElementById("range").value,10);

  const latest = await apiFetch(`/api/metrics/${clientId}/latest`);
  const arr = await apiFetch(`/api/metrics/${clientId}/range?minutes=${minutes}`);

  document.getElementById("meta").textContent = latest?.ts ? "Latest: " + fmtTime(latest.ts) : "No data";
  document.getElementById("kpis").innerHTML = [
    kpi("CPU", latest?.cpu, "%"),
    kpi("RAM", latest?.ram, "%"),
    kpi("Disk", latest?.disk, "%"),
    kpi("RX", latest?.rx_kbps, " kbps"),
    kpi("TX", latest?.tx_kbps, " kbps"),
    kpi("Connections", latest?.connections, ""),
  ].join("");

  const labels = arr.map(x=>fmtTimeShort(x.ts));
  makeChart(labels, {
    cpu: arr.map(x=>x.cpu),
    ram: arr.map(x=>x.ram),
    rx: arr.map(x=>x.rx_kbps),
    tx: arr.map(x=>x.tx_kbps),
    conn: arr.map(x=>x.connections),
  });
}

document.getElementById("refresh").onclick = refresh;

let ws;
function connectWS(){
  ws = new WebSocket((location.protocol==="https:"?"wss://":"ws://") + location.host + "/ws/realtime");
  ws.onopen = ()=>{ setStatus(true,"Live"); ws.send("ping"); };
  ws.onmessage = (ev)=>{ try{
      const msg = JSON.parse(ev.data);
      if(msg.type === "metric"){
        const clientId = parseInt(document.getElementById("client").value,10);
        if(msg.client_id === clientId) refresh();
      }
    }catch{}
  };
  ws.onclose = ()=>{ setStatus(false,"Disconnected"); setTimeout(connectWS, 1500); };
}

(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await refresh();
  connectWS();
})();