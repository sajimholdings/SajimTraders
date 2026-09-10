// =============================================================================
// SAJIM TRADERS — ACCOUNT CONNECTOR & MULTI-ACCOUNT MANAGER (accounts.js)
// =============================================================================

window.launchDemoCockpit = function() {
  window.clientAccount = {
    account_id: "1200442972",
    account_name: "Free Demo Trader",
    broker_server: "Headway-Demo",
    autopilot_enabled: true,
    balance: 50.00,
    equity: 52.60,
    free_margin: 49.80,
    today_pnl: 15.20,
    today_pnl_percent: 30.4,
    currency: "USD",
    open_positions: [
      {
        ticket: 8840291,
        symbol: "XAUUSD",
        type: "BUY",
        volume: 0.01,
        open_price: 2315.20,
        current_price: 2317.80,
        sl: 2315.50,
        tp: 2325.00,
        pnl: 2.60,
        comment: "Sajim_V2_Demo"
      }
    ],
    floating_pnl: 2.60,
    terminal_connected: true,
    is_demo: true
  };

  if (window.saveClientAccountState) window.saveClientAccountState(window.clientAccount);
  if (window.updateCockpitUI) window.updateCockpitUI(window.clientAccount);
  if (window.showCockpit) window.showCockpit();
  if (window.showToast) window.showToast("🚀 Free Demo Activated! Live V2 Auto-Pilot is armed.");
};

window.openConnectModal = function(defaultTab = "DEMO") {
  const modal = document.getElementById("modal-account-connector");
  if (!modal) return;
  modal.style.display = "flex";
  window.switchConnectorTab(defaultTab);
  loadAllClientAccounts();
};

window.closeConnectModal = function() {
  const modal = document.getElementById("modal-account-connector");
  if (modal) modal.style.display = "none";
};

window.closeModalOnOverlay = function(event) {
  if (event.target.id === "modal-account-connector") {
    window.closeConnectModal();
  }
};

window.switchConnectorTab = function(tab) {
  window.currentConnectorTab = tab;
  const tabDemo = document.getElementById("tab-opt-demo");
  const tabReal = document.getElementById("tab-opt-real");
  const serverSelect = document.getElementById("conn-server");
  const loginInput = document.getElementById("conn-login");
  const passInput = document.getElementById("conn-password");

  if (tab === "DEMO") {
    if (tabDemo) tabDemo.classList.add("active");
    if (tabReal) tabReal.classList.remove("active");
    if (serverSelect) serverSelect.value = "Headway-Demo";
    if (loginInput) loginInput.value = "1200442972";
    if (passInput) passInput.value = "demo1234";
  } else {
    if (tabReal) tabReal.classList.add("active");
    if (tabDemo) tabDemo.classList.remove("active");
    if (serverSelect) serverSelect.value = "Headway-Real";
    if (loginInput) loginInput.value = window.clientAccount.account_id || "";
    if (passInput) passInput.value = "";
  }
};

window.handleAccountConnect = async function(event) {
  event.preventDefault();
  const server = document.getElementById("conn-server").value;
  const login = document.getElementById("conn-login").value;
  const password = document.getElementById("conn-password").value;

  const btn = document.getElementById("btn-submit-connect");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Connecting to Broker...";
  }

  try {
    const res = await fetch("/api/client/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: login,
        broker_server: server,
        password: password,
        autopilot_enabled: true,
        risk_mode: "MICRO_FIXED"
      })
    });

    const data = await res.json();
    if (data.success) {
      if (window.showToast) window.showToast("✅ Account Connected Successfully!");
      window.closeConnectModal();
      if (window.fetchAccount) await window.fetchAccount();
      if (window.showCockpit) window.showCockpit();
    } else {
      if (window.showToast) window.showToast("❌ " + (data.error || "Login Failed. Check credentials."));
    }
  } catch (err) {
    if (window.showToast) window.showToast("Error connecting account: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "⚡ CONNECT & LAUNCH COCKPIT";
    }
  }
};

async function loadAllClientAccounts() {
  const container = document.getElementById("connected-accounts-list");
  if (!container) return;

  try {
    const res = await fetch("/api/client/accounts");
    if (!res.ok) return;
    const data = await res.json();
    const accounts = data.accounts || [];

    if (accounts.length === 0) {
      container.innerHTML = `<p style="font-size: 0.75rem; color: var(--text-dim);">No accounts linked yet.</p>`;
      return;
    }

    let html = `<h5 style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">Active Linked Accounts:</h5>`;
    accounts.forEach(acc => {
      const isCurrent = String(acc.account_id) === String(window.clientAccount.account_id);
      const activeBadge = isCurrent ? `<span style="color: var(--emerald); font-size: 0.7rem; font-weight: 800;">ACTIVE NOW</span>` : "";
      html += `
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 8px 10px; border-radius: 6px; margin-bottom: 6px; border: 1px solid ${isCurrent ? 'var(--border-emerald)' : 'var(--border-subtle)'};">
          <div>
            <strong style="font-size: 0.82rem;">#${acc.account_id}</strong>
            <span style="font-size: 0.72rem; color: var(--text-dim); margin-left: 6px;">(${acc.broker_server || 'Headway'})</span>
            ${activeBadge}
          </div>
          <div style="display: flex; gap: 6px;">
            ${!isCurrent ? `<button style="background: var(--cyan); color: #000; border: none; padding: 3px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; cursor: pointer;" onclick="switchAccount('${acc.account_id}')">Switch</button>` : ''}
            <button style="background: rgba(244,63,94,0.2); color: var(--rose); border: 1px solid rgba(244,63,94,0.4); padding: 3px 6px; border-radius: 4px; font-size: 0.68rem; cursor: pointer;" onclick="deleteAccount('${acc.account_id}')">✕</button>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (e) {
    console.warn("Could not load account list:", e);
  }
}

window.switchAccount = async function(accountId) {
  try {
    const res = await fetch("/api/client/switch-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id: accountId })
    });
    const data = await res.json();
    if (data.success) {
      if (window.showToast) window.showToast(`Switched active account to #${accountId}`);
      window.closeConnectModal();
      if (window.fetchAccount) await window.fetchAccount();
    }
  } catch (err) {
    if (window.showToast) window.showToast("Switch failed: " + err.message);
  }
};

window.deleteAccount = async function(accountId) {
  if (!confirm(`Unlink account #${accountId}?`)) return;
  try {
    await fetch("/api/client/delete-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id: accountId })
    });
    loadAllClientAccounts();
  } catch (e) {
    console.warn("Delete error:", e);
  }
};
