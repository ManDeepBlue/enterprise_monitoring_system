/**
 * Core Application Configuration & Global Utilities
 * ------------------------------------------------
 * This file contains global constants, authentication helpers, and
 * UI layout management used across the entire monitoring dashboard.
 */

const API = location.origin; // Base API URL (assumed same-origin)

/**
 * Retrieve the current JWT authentication token from local storage.
 * @returns {string|null} The token string or null if not logged in.
 */
function getToken(){ return localStorage.getItem("token"); }

/**
 * Save the JWT authentication token to local storage.
 * @param {string} t - The token string to save.
 */
function setToken(t){ localStorage.setItem("token", t); }

/**
 * Determine the user's role by checking local storage or decoding the JWT.
 * Defaults to 'guest' if no role can be identified.
 * @returns {string} The role (e.g., 'admin', 'readonly', 'guest').
 */
function getRole(){ 
  const role = localStorage.getItem("role");
  if(role) return role;
  
  // Fallback: Try to decode the role from the JWT token if it exists.
  // This is useful for initial loads or if the role wasn't explicitly saved.
  const token = getToken();
  if(token){
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(window.atob(base64));
      if(payload.role) {
        localStorage.setItem("role", payload.role);
        return payload.role;
      }
    } catch (e) { console.error("Token decode failed", e); }
  }
  return "guest"; 
}

/**
 * Clear authentication data and redirect the user to the login page.
 */
function logout(){ 
  localStorage.removeItem("token"); 
  localStorage.removeItem("role"); 
  location.href="/login.html"; 
}

/**
 * Enhanced fetch wrapper that handles authentication headers,
 * JSON parsing, and global error handling (e.g., 401 redirects).
 * 
 * @param {string} path - The relative API path.
 * @param {RequestInit} opts - Standard fetch options.
 * @returns {Promise<any>} The parsed JSON or text response.
 * @throws {Error} If the response is not OK or permission is denied.
 */
async function apiFetch(path, opts={}){
  opts.headers = opts.headers || {};
  opts.headers["Content-Type"] = opts.headers["Content-Type"] || "application/json";
  
  const token = getToken();
  if(token) opts.headers["Authorization"] = `Bearer ${token}`;
  
  const res = await fetch(API + path, opts);
  
  // If the server returns Unauthorized, force a logout.
  if(res.status === 401){ logout(); }
  
  if(!res.ok){
    if(res.status === 403) throw new Error("Access Denied: You do not have permission for this action.");
    let text = await res.text();
    try {
      const json = JSON.parse(text);
      if(json.detail) text = json.detail; // Extract FastAPI error detail if present.
    } catch(e) {}
    throw new Error(text || res.statusText);
  }
  
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

/**
 * Highlight the active navigation link based on the current URL path.
 */
function setActiveNav(){
  const path = location.pathname;
  document.querySelectorAll(".nav a").forEach(a=>{
    if(a.getAttribute("href") === path) a.classList.add("active");
  });
}

/**
 * Mount the standard application layout (sidebar, topbar, and main content area).
 * This dynamically adjusts based on the user's role.
 * 
 * @param {string} pageTitle - The title to display in the topbar.
 * @param {string} pageSubtitle - Optional subtitle description for the page.
 */
function mountLayout(pageTitle, pageSubtitle){
  const root = document.getElementById("app");
  const role = getRole();
  const roleLabel = role.charAt(0).toUpperCase() + role.slice(1);
  
  root.innerHTML = `
  <div class="container">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo" aria-hidden="true"></div>
        <div>
          <h1>Enterprise Monitoring</h1>
          <div class="small">${roleLabel} Console</div>
        </div>
      </div>
      <nav class="nav" aria-label="Primary">
        <a href="/index.html">Dashboard</a>
        ${role !== 'readonly' ? '<a href="/security.html">Security Assessment</a>' : ''}
        <a href="/performance.html">Performance Monitoring</a>
        <a href="/productivity.html">Employee Productivity</a>
        <a href="/alerts.html">Alerts & Notifications</a>
        <a href="/devices.html">Network Device Monitoring</a>
        <a href="/snmp.html">SNMP Link Status</a>
        <a href="/analytics.html">Visual Analytics</a>
        ${role === 'admin' ? '<a href="/logs.html">Logs & Database</a>' : ''}
        ${role === 'admin' ? '<a href="/settings.html">System Settings</a>' : ''}
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

/**
 * Parse a server timestamp ensuring it's treated as UTC.
 * @param {string|number} ts - The timestamp from the server.
 * @returns {Date} A valid Date object or Invalid Date.
 */
function parseDate(ts){
  if(!ts) return new Date(NaN);
  const s = ts.toString();
  // Only append Z if it doesn't already have a timezone offset or Z.
  // This ensures the browser doesn't interpret it as local time.
  const hasTZ = /(Z|[+-]\d{2}(:?\d{2})?)$/.test(s);
  return new Date(hasTZ ? s : s + "Z");
}

/**
 * Format a timestamp into a human-readable locale string.
 * @param {string} ts - The timestamp to format.
 */
function fmtTime(ts){
  const d = parseDate(ts);
  return isNaN(d) ? "—" : d.toLocaleString();
}

/**
 * Format a timestamp into a human-readable local time string (ignoring date).
 * @param {string} ts - The timestamp to format.
 */
function fmtTimeShort(ts){
  const d = parseDate(ts);
  return isNaN(d) ? "—" : d.toLocaleTimeString();
}

/**
 * Update the global connection status badge in the topbar.
 * @param {boolean} ok - Whether the connection is healthy.
 * @param {string} text - Status text to display.
 */
function setStatus(ok, text){
  const el = document.getElementById("statusBadge");
  if(!el) return;
  el.className = "badge " + (ok ? "ok":"danger");
  el.textContent = text;
}