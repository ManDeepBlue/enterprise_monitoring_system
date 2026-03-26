const API = location.origin; // same origin
function getToken(){ return localStorage.getItem("token"); }
function setToken(t){ localStorage.setItem("token", t); }
function logout(){ localStorage.removeItem("token"); location.href="/login.html"; }

async function apiFetch(path, opts={}){
  opts.headers = opts.headers || {};
  opts.headers["Content-Type"] = opts.headers["Content-Type"] || "application/json";
  const token = getToken();
  if(token) opts.headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(API + path, opts);
  if(res.status === 401){ logout(); }
  if(!res.ok){
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

function setActiveNav(){
  const path = location.pathname;
  document.querySelectorAll(".nav a").forEach(a=>{
    if(a.getAttribute("href") === path) a.classList.add("active");
  });
}

function mountLayout(pageTitle, pageSubtitle){
  const root = document.getElementById("app");
  root.innerHTML = `
  <div class="container">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo" aria-hidden="true"></div>
        <div>
          <h1>Enterprise Monitoring</h1>
          <div class="small">Admin Console</div>
        </div>
      </div>
      <nav class="nav" aria-label="Primary">
        <a href="/index.html">Dashboard</a>
        <a href="/security.html">Security Assessment</a>
        <a href="/performance.html">Performance Monitoring</a>
        <a href="/productivity.html">Employee Productivity</a>
        <a href="/alerts.html">Alerts & Notifications</a>
        <a href="/devices.html">Network Device Monitoring</a>
        <a href="/analytics.html">Visual Analytics</a>
        <a href="/logs.html">Logs & Database</a>
        <a href="/settings.html">System Settings</a>
      </nav>
      <div class="footer">
        <button class="btn secondary" onclick="logout()">Sign out</button>
      </div>
    </aside>
    <main class="main">
      <div class="topbar">
        <div class="title">
          <h2>${pageTitle}</h2>
          <p>${pageSubtitle || ""}</p>
        </div>
        <div class="badge" id="statusBadge">Connecting…</div>
      </div>
      <div id="content" class="grid"></div>
    </main>
  </div>`;
  setActiveNav();
}

// Always parse server timestamps as UTC (appends Z if missing) and display in local time
function fmtTime(ts){
  if(!ts) return "—";
  return new Date(ts.endsWith("Z") ? ts : ts + "Z").toLocaleString();
}
function fmtTimeShort(ts){
  if(!ts) return "—";
  return new Date(ts.endsWith("Z") ? ts : ts + "Z").toLocaleTimeString();
}

function setStatus(ok, text){
  const el = document.getElementById("statusBadge");
  if(!el) return;
  el.className = "badge " + (ok ? "ok":"danger");
  el.textContent = text;
}