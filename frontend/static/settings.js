
mountLayout("System Settings", "Monitoring intervals, alert thresholds, user and policy configuration.");
const content = document.getElementById("content");
content.className = "grid cols-2";
content.innerHTML = `
  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Alert Thresholds</div>
    <div class="row">
      <div><div class="small">CPU High %</div><input class="input" id="cpu" type="number" min="1" max="100"></div>
      <div><div class="small">RAM High %</div><input class="input" id="ram" type="number" min="1" max="100"></div>
    </div>
    <div style="height:10px"></div>
    <div class="row">
      <div><div class="small">Disk High %</div><input class="input" id="disk" type="number" min="1" max="100"></div>
      <div><div class="small">Connections High</div><input class="input" id="conn" type="number" min="1"></div>
    </div>
    <div style="height:12px"></div>
    <button class="btn" id="save">Save</button>
    <div class="small" id="msg" style="margin-top:10px"></div>
  </div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:8px">Privacy & Retention Policy</div>
    <div class="notice">
      Configure how long to retain raw metrics and web activity logs. For compliance, consider anonymization and least-privilege access.
    </div>
    <div style="height:12px"></div>
    <div class="row">
      <div><div class="small">Metrics retention (days)</div><input class="input" id="mret" type="number" min="1" value="30"></div>
      <div><div class="small">Web retention (days)</div><input class="input" id="wret" type="number" min="1" value="30"></div>
    </div>
    <div style="height:12px"></div>
    <button class="btn secondary" id="saveRet">Save policy</button>
    <div class="small" id="msg2" style="margin-top:10px"></div>
  </div>
`;

async function load(){
  const all = await apiFetch("/api/settings");
  const th = (all.find(x=>x.key==="alert_thresholds")||{}).value || {cpu_high:85,ram_high:85,disk_high:90,connections_high:1000};
  document.getElementById("cpu").value = th.cpu_high;
  document.getElementById("ram").value = th.ram_high;
  document.getElementById("disk").value = th.disk_high;
  document.getElementById("conn").value = th.connections_high;

  const pol = (all.find(x=>x.key==="retention")||{}).value || {metrics_days:30, web_days:30};
  document.getElementById("mret").value = pol.metrics_days;
  document.getElementById("wret").value = pol.web_days;
}

document.getElementById("save").onclick = async ()=>{
  const msg = document.getElementById("msg");
  msg.textContent = "Saving…";
  try{
    await apiFetch("/api/settings/alert_thresholds", {method:"PUT", body: JSON.stringify({value:{
      cpu_high: parseFloat(document.getElementById("cpu").value),
      ram_high: parseFloat(document.getElementById("ram").value),
      disk_high: parseFloat(document.getElementById("disk").value),
      connections_high: parseInt(document.getElementById("conn").value,10),
    }})});
    msg.textContent = "Saved.";
  }catch(e){ msg.textContent = "Failed: " + e.message; }
};

document.getElementById("saveRet").onclick = async ()=>{
  const msg = document.getElementById("msg2");
  msg.textContent = "Saving…";
  try{
    await apiFetch("/api/settings/retention", {method:"PUT", body: JSON.stringify({value:{
      metrics_days: parseInt(document.getElementById("mret").value,10),
      web_days: parseInt(document.getElementById("wret").value,10),
    }})});
    msg.textContent = "Saved.";
  }catch(e){ msg.textContent = "Failed: " + e.message; }
};

(async ()=>{
  if(!getToken()) location.href="/login.html";
  await load();
  setStatus(true,"Ready");
})();
