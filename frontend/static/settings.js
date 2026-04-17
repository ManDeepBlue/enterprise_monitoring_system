/**
 * System Settings & User Management module.
 * 
 * Handles the configuration of monitoring thresholds, data retention policies,
 * and user account management including roles and status.
 */

// Initialize the common layout with page-specific title and description
mountLayout("System Settings", "Monitoring intervals, alert thresholds, user and policy configuration.");

const content = document.getElementById("content");

/**
 * Define the main grid layout for the settings page.
 * Uses a 2-column grid to organize different setting cards.
 */
content.className = "grid cols-2";
content.innerHTML = `
  <!-- Card: Alert Thresholds -->
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

  <!-- Card: Privacy & Retention Policy -->
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

  <!-- Card: User Management (Full width) -->
  <div class="card" style="grid-column: 1 / -1">
    <div style="font-weight:700;margin-bottom:8px">User Management</div>
    <div class="row" style="align-items:flex-end">
      <div>
        <div class="small">Email</div>
        <input class="input" id="newEmail" type="email" placeholder="user@example.com">
      </div>
      <div>
        <div class="small">Password</div>
        <input class="input" id="newPass" type="password" placeholder="******">
      </div>
      <div>
        <div class="small">Role</div>
        <select class="input" id="newRole">
          <option value="admin">Admin</option>
          <option value="analyst">Analyst</option>
          <option value="readonly" selected>Read Only</option>
        </select>
      </div>
      <button class="btn" id="addUser">Add User</button>
    </div>
    <div class="small" id="msgUser" style="margin-top:10px;margin-bottom:10px;color:var(--danger)"></div>
    <div style="overflow-x:auto;">
      <table class="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th>Created At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="userTableBody">
          <tr><td colspan="5" class="small">Loading users...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
`;

/**
 * Fetches the list of all registered users and renders them in the table.
 * Includes inline editing for roles and active status.
 */
async function loadUsers() {
  const tbody = document.getElementById("userTableBody");
  try {
    const users = await apiFetch("/api/users");
    tbody.innerHTML = users.map(u => `
      <tr>
        <td>${u.email}</td>
        <td>
          <select class="input" onchange="updateUser(${u.id}, 'role', this.value)" style="padding:4px">
            <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
            <option value="analyst" ${u.role === 'analyst' ? 'selected' : ''}>Analyst</option>
            <option value="readonly" ${u.role === 'readonly' ? 'selected' : ''}>Read Only</option>
          </select>
        </td>
        <td>
          <input type="checkbox" ${u.is_active ? 'checked' : ''} onchange="updateUser(${u.id}, 'is_active', this.checked)">
        </td>
        <td class="small">${fmtTime(u.created_at)}</td>
        <td>
          <button class="btn" style="padding:4px 8px;font-size:12px;background:var(--danger);color:#fff" onclick="deleteUser(${u.id})">Delete</button>
        </td>
      </tr>
    `).join("") || '<tr><td colspan="5" class="small">No users found.</td></tr>';
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="small" style="color:var(--danger)">Failed to load users: ${e.message}</td></tr>`;
  }
}

/**
 * Updates a specific field for a user.
 * @param {number} id - User ID.
 * @param {string} field - Field name to update ('role', 'is_active', etc.).
 * @param {any} value - New value for the field.
 */
window.updateUser = async (id, field, value) => {
  try {
    const payload = {};
    payload[field] = value;
    await apiFetch("/api/users/" + id, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    // No reload needed for simple toggles/selects, but can be added if UI needs sync
  } catch (e) {
    alert("Failed to update user: " + e.message);
    loadUsers(); // Revert local state by reloading from server
  }
};

/**
 * Deletes a user account after confirmation.
 * @param {number} id - User ID to delete.
 */
window.deleteUser = async (id) => {
  if(!confirm("Are you sure you want to delete this user?")) return;
  try {
    await apiFetch("/api/users/" + id, { method: "DELETE" });
    loadUsers();
  } catch (e) {
    alert("Failed to delete user: " + e.message);
  }
};

/**
 * Initializes settings by fetching existing threshold and retention configurations.
 * Populates form inputs with current server values.
 */
async function load(){
  const all = await apiFetch("/api/settings");
  
  // Load alert thresholds
  const th = (all.find(x=>x.key==="alert_thresholds")||{}).value || {cpu_high:85,ram_high:85,disk_high:90,connections_high:1000};
  document.getElementById("cpu").value = th.cpu_high;
  document.getElementById("ram").value = th.ram_high;
  document.getElementById("disk").value = th.disk_high;
  document.getElementById("conn").value = th.connections_high;

  // Load retention policy
  const pol = (all.find(x=>x.key==="retention")||{}).value || {metrics_days:30, web_days:30};
  document.getElementById("mret").value = pol.metrics_days;
  document.getElementById("wret").value = pol.web_days;
  
  await loadUsers();
}

/**
 * Save handler for Alert Thresholds.
 * Updates global system triggers for alerts across all devices.
 */
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

/**
 * Save handler for Retention Policy.
 * Sets the duration for automated data cleanup tasks in the backend.
 */
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

/**
 * Event handler for adding a new user.
 * Validates inputs and resets form upon successful creation.
 */
document.getElementById("addUser").onclick = async ()=>{
  const msgUser = document.getElementById("msgUser");
  const email = document.getElementById("newEmail").value.trim();
  const password = document.getElementById("newPass").value;
  const role = document.getElementById("newRole").value;
  
  if(!email || !password) {
    msgUser.textContent = "Email and password are required.";
    return;
  }
  
  msgUser.style.color = "var(--text)";
  msgUser.textContent = "Adding...";
  try {
    await apiFetch("/api/users", {
      method: "POST",
      body: JSON.stringify({ email, password, role })
    });
    msgUser.textContent = "";
    document.getElementById("newEmail").value = "";
    document.getElementById("newPass").value = "";
    loadUsers();
  } catch (e) {
    msgUser.style.color = "var(--danger)";
    msgUser.textContent = "Failed: " + e.message;
  }
};

/**
 * Initialization IIFE: Check authentication, load data, and set page status.
 */
(async ()=>{
  if(!getToken()) location.href="/login.html";
  await load();
  setStatus(true,"Ready");
})();
