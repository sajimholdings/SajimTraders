// =============================================================================
// SAJIM TRADERS — COCKPIT DASHBOARD & TELEMETRY MODULE (cockpit.js)
// =============================================================================

window.showGate = function() {
  const gate = document.getElementById("screen-gate");
  const cockpit = document.getElementById("screen-cockpit");
  if (gate) gate.style.display = "flex";
  if (cockpit) cockpit.style.display = "none";
};

window.showCockpit = function() {
  const gate = document.getElementById("screen-gate");
  const cockpit = document.getElementById("screen-cockpit");
  if (gate) gate.style.display = "none";
  if (cockpit) cockpit.style.display = "flex";

  if (window.fetchAccount) window.fetchAccount();
  if (window.fetchActiveTrades) window.fetchActiveTrades();
  if (window.fetchSignals) window.fetchSignals();
};

window.fetchAccount = async function() {
  try {
    const res = await fetch("/api/client/account");
    if (!res.ok) return;
    const data = await res.json();
    
    if (!window.clientAccount.is_demo) {
      window.clientAccount = data;
      window.updateCockpitUI(data);
    }
  } catch (err) {
    console.warn("Telemetry fetch error:", err);
  }
};

window.updateCockpitUI = function(data) {
  // Balance
  const balEl = document.getElementById("cockpit-balance");
  if (balEl) balEl.textContent = `$${(data.balance || 0).toFixed(2)}`;

  const currEl = document.getElementById("cockpit-currency");
  if (currEl) currEl.textContent = data.currency || "USD";

  // Today's Net Profit
  const todayPnlEl = document.getElementById("cockpit-today-pnl");
  if (todayPnlEl) {
    const sign = (data.today_pnl || 0) >= 0 ? "+" : "";
    todayPnlEl.textContent = `${sign}$${(data.today_pnl || 0).toFixed(2)} USD`;
  }

  const todayPctEl = document.getElementById("cockpit-today-pct");
  if (todayPctEl) {
    const sign = (data.today_pnl_percent || 0) >= 0 ? "+" : "";
    todayPctEl.textContent = `🟢 ${sign}${(data.today_pnl_percent || 0).toFixed(1)}%`;
  }

  // Sub-telemetry strip
  const eqEl = document.getElementById("cockpit-equity");
  if (eqEl) eqEl.textContent = `$${(data.equity || 0).toFixed(2)}`;

  const fmEl = document.getElementById("cockpit-free-margin");
  if (fmEl) fmEl.textContent = `$${(data.free_margin || 0).toFixed(2)}`;

  const brokerEl = document.getElementById("cockpit-broker");
  if (brokerEl) brokerEl.textContent = data.broker_server || "Headway-Real";

  // Header Chip
  const chipLabel = document.getElementById("chip-account-label");
  if (chipLabel) {
    const brokerShort = (data.broker_server || "Headway").split("-")[0];
    chipLabel.textContent = `${brokerShort} #${data.account_id}`;
  }

  // Auto-Pilot Master Switch
  window.syncMasterAutoPilotUI(data.autopilot_enabled);

  // Upgrade banner
  window.updateFreemiumBanner(data);
};

window.syncMasterAutoPilotUI = function(enabled) {
  const btn = document.getElementById("btn-master-autopilot");
  const indicator = document.getElementById("switch-indicator-text");
  const modeBadge = document.getElementById("cockpit-mode-badge");

  if (!btn || !indicator) return;

  if (enabled) {
    btn.className = "btn-master-autopilot active";
    indicator.textContent = "ALGO AUTO-PILOT: ACTIVE (COPYING V2)";
    if (modeBadge) {
      modeBadge.textContent = "AUTOPILOT ON";
      modeBadge.style.color = "var(--emerald)";
      modeBadge.style.borderColor = "var(--border-emerald)";
    }
  } else {
    btn.className = "btn-master-autopilot inactive";
    indicator.textContent = "ALGO AUTO-PILOT: OFF (MANUAL ONLY)";
    if (modeBadge) {
      modeBadge.textContent = "PAUSED";
      modeBadge.style.color = "var(--text-muted)";
      modeBadge.style.borderColor = "var(--border-subtle)";
    }
  }
};

window.toggleAutoPilotMaster = async function() {
  const newState = !window.clientAccount.autopilot_enabled;
  window.clientAccount.autopilot_enabled = newState;
  window.syncMasterAutoPilotUI(newState);

  try {
    const res = await fetch("/api/client/toggle-autopilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: window.clientAccount.account_id,
        enabled: newState
      })
    });
    const data = await res.json();
    if (data.success) {
      window.showToast(newState ? "🤖 Auto-Pilot Activated (24/7 Execution)" : "⏸️ Auto-Pilot Paused");
    }
  } catch (err) {
    console.error("AutoPilot toggle error:", err);
  }
};

window.updateFreemiumBanner = function(data) {
  const banner = document.getElementById("card-freemium-banner");
  const title = document.getElementById("upgrade-banner-title");
  const desc = document.getElementById("upgrade-banner-desc");
  if (!banner || !title || !desc) return;

  if (data.is_demo) {
    title.textContent = "Your Demo Test Made Profit Today!";
    desc.textContent = "Switch to a Real MT5 account on Headway to withdraw real cash.";
  } else {
    title.textContent = "Headway Official Partnership Active";
    desc.textContent = "Enjoy 1:2000 leverage, zero spreads, and instant M-Pesa transactions.";
  }
};

window.showToast = function(message) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
};
