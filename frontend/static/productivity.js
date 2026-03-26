mountLayout("Employee Productivity Monitoring", "Web activity logging, website categorization, and time-based productivity insights.");
const content = document.getElementById("content");
content.className = "grid cols-2";
content.innerHTML = `
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Client & Range</div>
    <div class="row">
      <select id="client"></select>
      <select id="range">
        <option value="120">Last 2 hours</option>
        <option value="480">Last 8 hours</option>
        <option value="1440">Last 24 hours</option>
      </select>
      <button class="btn secondary" id="refresh">Refresh</button>
    </div>
    <div class="notice" style="margin-top:10px">
      Privacy: the system stores domain + hashed URL, and supports retention controls in Settings.
    </div>
  </div>
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Category Breakdown</div>
    <canvas id="pie" height="160"></canvas>
  </div>
  <div class="card" style="grid-column:1/-1">
    <div style="font-weight:700;margin-bottom:8px">Recent Activity</div>
    <table class="table">
      <thead><tr><th>Time</th><th>Domain</th><th>Category</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
`;

let pie;
function buildPie(labels, values){
  const ctx = document.getElementById("pie");
  if(pie) pie.destroy();
  pie = new Chart(ctx, {
    type:"doughnut",
    data:{ labels, datasets:[{data:values}] },
    options:{ responsive:true }
  });
}

async function loadClients(){
  const clients = await apiFetch("/api/clients");
  document.getElementById("client").innerHTML = clients.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
}

async function refresh(){
  const clientId = parseInt(document.getElementById("client").value,10);
  const minutes = parseInt(document.getElementById("range").value,10);
  const summary = await apiFetch(`/api/productivity/${clientId}/summary?minutes=${minutes}`);
  const recent = await apiFetch(`/api/productivity/${clientId}/recent?minutes=${minutes}`);

  const labels = summary.by_category.map(x=>x.category);
  const values = summary.by_category.map(x=>x.seconds);
  buildPie(labels, values);

  document.getElementById("rows").innerHTML = recent.map(r=>`<tr>
    <td>${fmtTime(r.ts)}</td>
    <td>${r.domain}</td>
    <td><span class="badge">${r.category}</span></td>
  </tr>`).join("");
}

document.getElementById("refresh").onclick = refresh;

(async ()=>{
  if(!getToken()) location.href="/login.html";
  await loadClients();
  await refresh();
  setStatus(true,"Ready");
})();