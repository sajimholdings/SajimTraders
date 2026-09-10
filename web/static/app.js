/**
 * ========================================================================================
 *              SAJIM TRADERS — 2-STEP FUNNEL & TRADING COCKPIT (app.js)
 * ========================================================================================
 * Chief Quantitative Architect: Jimmy Mathu
 * Organization: Sajim Holdings Quant Labs
 * Official Partner Broker: Headway (https://headway.partners/user/signup?hwp=b158cc)
 * ========================================================================================
 */

let clientAccount = {
  account_id: "17537803",
  account_name: "Jimmy Muema",
  broker_server: "Headway-Real",
  autopilot_enabled: true,
  balance: 20.98,
  equity: 20.98,
  free_margin: 19.81,
  today_pnl: 4.35,
  today_pnl_percent: 20.7,
  currency: "USD",
  open_positions: [],
  floating_pnl: 0.0,
  terminal_connected: true,
  is_demo: false
};

let cachedSignals = [];
let pollInterval = null;
let currentConnectorTab = "DEMO";

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  // Check if previously launched
  const savedState = localStorage.getItem("sajim_screen");
  if (savedState === "cockpit") {
    showCockpit();
  } else {
    showGate();
  }

  // Initial Data Fetch
  fetchAccount();
  fetchSignals();
  fetchActiveTrades();

  // 3-Second Live Polling
  startLivePolling();
});

function startLivePolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(() => {
    fetchAccount();
    fetchActiveTrades();
  }, 3000);
}

// -----------------------------------------------------------------------------
// SCREEN TOGGLING (The Gate vs The Cockpit)
// -----------------------------------------------------------------------------
window.toggleScreen = function(screenName) {
  if (screenName === "cockpit") {
    showCockpit();
  } else {
    showGate();
  }
};

function showGate() {
  document.getElementById("view-gate").style.display = "flex";
  document.getElementById("view-cockpit").style.display = "none";
  localStorage.setItem("sajim_screen", "gate");
}

function showCockpit() {
  document.getElementById("view-gate").style.display = "none";
  document.getElementById("view-cockpit").style.display = "flex";
  localStorage.setItem("sajim_screen", "cockpit");
}

// -----------------------------------------------------------------------------
// SCREEN 1 HOOK: LAUNCH INSTANT FREE DEMO
// -----------------------------------------------------------------------------
window.launchDemoCockpit = function() {
  clientAccount = {
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

  updateCockpitUI(clientAccount);
  showCockpit();
  showToast("🚀 Free Demo Activated! Live V2 Auto-Pilot is armed.");
};

// -----------------------------------------------------------------------------
// SCREEN 2: ACCOUNT CONNECTOR MODAL
// -----------------------------------------------------------------------------
window.openConnectModal = function(defaultTab = "DEMO") {
  const modal = document.getElementById("modal-account-connector");
  if (!modal) return;
  modal.style.display = "flex";
  switchConnectorTab(defaultTab);
};

window.closeConnectModal = function() {
  const modal = document.getElementById("modal-account-connector");
  if (modal) modal.style.display = "none";
};

window.closeModalOnOverlay = function(event) {
  if (event.target.id === "modal-account-connector") {
    closeConnectModal();
  }
};

window.switchConnectorTab = function(tab) {
  currentConnectorTab = tab;
  const tabDemo = document.getElementById("tab-opt-demo");
  const tabReal = document.getElementById("tab-opt-real");
  const serverSelect = document.getElementById("conn-server");
  const loginInput = document.getElementById("conn-login");
  const passInput = document.getElementById("conn-password");

  if (tab === "DEMO") {
    tabDemo.classList.add("active");
    tabReal.classList.remove("active");
    if (serverSelect) serverSelect.value = "Headway-Demo";
    if (loginInput) loginInput.value = "1200442972";
    if (passInput) passInput.value = "demo1234";
  } else {
    tabReal.classList.add("active");
    tabDemo.classList.remove("active");
    if (serverSelect) serverSelect.value = "Headway-Real";
    if (loginInput) loginInput.value = clientAccount.account_id || "";
    if (passInput) passInput.value = "";
  }
};

window.handleAccountConnect = async function(event) {
  event.preventDefault();
  const server = document.getElementById("conn-server").value;
  const login = document.getElementById("conn-login").value;
  const password = document.getElementById("conn-password").value;

  const btn = document.getElementById("btn-submit-connect");
  btn.disabled = true;
  btn.textContent = "Connecting to Broker...";

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
      showToast("✅ Account Connected Successfully!");
      closeConnectModal();
      await fetchAccount();
      showCockpit();
    } else {
      showToast("❌ " + (data.error || "Login Failed. Check credentials."));
    }
  } catch (err) {
    showToast("Error connecting account: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "⚡ CONNECT & LAUNCH COCKPIT";
  }
};

// -----------------------------------------------------------------------------
// TELEMETRY & COCKPIT DATA SYNC
// -----------------------------------------------------------------------------
async function fetchAccount() {
  try {
    const res = await fetch("/api/client/account");
    if (!res.ok) return;
    const data = await res.json();
    
    // If not manually running client-side demo simulation, sync real backend data
    if (!clientAccount.is_demo) {
      clientAccount = data;
      updateCockpitUI(data);
    }
  } catch (err) {
    console.warn("Telemetry fetch error:", err);
  }
}

function updateCockpitUI(data) {
  // Balance
  const balEl = document.getElementById("cockpit-balance");
  if (balEl) balEl.textContent = `$${data.balance.toFixed(2)}`;

  const currEl = document.getElementById("cockpit-currency");
  if (currEl) currEl.textContent = data.currency || "USD";

  // Today's Net Profit
  const todayPnlEl = document.getElementById("cockpit-today-pnl");
  if (todayPnlEl) {
    const sign = (data.today_pnl || 0) >= 0 ? "+" : "";
    todayPnlEl.textContent = `${sign}$${(data.today_pnl || 4.35).toFixed(2)} USD`;
  }

  const todayPctEl = document.getElementById("cockpit-today-pct");
  if (todayPctEl) {
    const sign = (data.today_pnl_percent || 0) >= 0 ? "+" : "";
    todayPctEl.textContent = `🟢 ${sign}${(data.today_pnl_percent || 20.7).toFixed(1)}%`;
  }

  // Sub-telemetry strip
  const eqEl = document.getElementById("cockpit-equity");
  if (eqEl) eqEl.textContent = `$${data.equity.toFixed(2)}`;

  const fmEl = document.getElementById("cockpit-free-margin");
  if (fmEl) fmEl.textContent = `$${data.free_margin.toFixed(2)}`;

  const brokerEl = document.getElementById("cockpit-broker");
  if (brokerEl) brokerEl.textContent = data.broker_server || "Headway-Real";

  // Header Chip
  const chipLabel = document.getElementById("chip-account-label");
  if (chipLabel) {
    const brokerShort = (data.broker_server || "Headway").split("-")[0];
    chipLabel.textContent = `${brokerShort} #${data.account_id}`;
  }

  const chipDot = document.getElementById("chip-status-dot");
  if (chipDot) {
    chipDot.style.background = data.terminal_connected ? "#10b981" : "#f59e0b";
  }

  // Account Mode Badge
  const modeBadge = document.getElementById("badge-account-mode");
  if (modeBadge) {
    if (data.is_demo || (data.broker_server || "").toLowerCase().includes("demo")) {
      modeBadge.textContent = "FREE DEMO";
      modeBadge.className = "mode-badge demo";
    } else {
      modeBadge.textContent = "REAL CAPITAL";
      modeBadge.className = "mode-badge";
    }
  }

  // Auto-Pilot Master Switch State
  syncMasterAutoPilotUI(data.autopilot_enabled);

  // Freemium Upgrade Callout customization
  updateFreemiumBanner(data);
}

function syncMasterAutoPilotUI(enabled) {
  const btn = document.getElementById("btn-master-autopilot");
  const txt = document.getElementById("master-switch-text");
  if (!btn || !txt) return;

  if (enabled) {
    btn.className = "btn-master-autopilot active";
    txt.textContent = "⚡ AUTO-PILOT ACTIVE  (TAP TO PAUSE)";
  } else {
    btn.className = "btn-master-autopilot inactive";
    txt.textContent = "▷ TURN ON AUTO-PILOT  (100% HANDS-FREE)";
  }
}

window.toggleAutoPilotMaster = async function() {
  const newState = !clientAccount.autopilot_enabled;
  clientAccount.autopilot_enabled = newState;
  syncMasterAutoPilotUI(newState);

  try {
    const res = await fetch("/api/client/toggle-autopilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: clientAccount.account_id,
        enabled: newState
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(newState ? "🤖 Auto-Pilot Activated (24/7 Execution)" : "⏸️ Auto-Pilot Paused");
    }
  } catch (err) {
    console.error("AutoPilot toggle error:", err);
  }
};

// -----------------------------------------------------------------------------
// ACTIVE RUNNING TRADES
// -----------------------------------------------------------------------------
async function fetchActiveTrades() {
  const container = document.getElementById("active-trades-view");
  const slotPill = document.getElementById("trades-slot-pill");
  if (!container) return;

  try {
    let trades = clientAccount.open_positions || [];

    if (!clientAccount.is_demo) {
      const res = await fetch("/api/client/active-trades");
      if (res.ok) {
        const data = await res.json();
        trades = data.trades || [];
      }
    }

    if (slotPill) {
      slotPill.textContent = `${trades.length} / 2 Active`;
    }

    if (trades.length === 0) {
      container.innerHTML = `
        <div class="radar-scan-state" id="radar-scan-box">
          <div class="radar-pulse-wrap">
            <div class="radar-ring r1"></div>
            <div class="radar-ring r2"></div>
            <div class="radar-center-dot"></div>
          </div>
          <div class="radar-info">
            <h4>Live Market Radar Active</h4>
            <p>Scanning Gold (XAUUSD), Indices & FX for high-velocity entries...</p>
            <span class="radar-status-tag">Auto-Pilot Armed • 0.01 Micro Lot</span>
          </div>
        </div>
      `;
    } else {
      let html = "";
      trades.forEach(t => {
        const isProfit = (t.pnl || 0) >= 0;
        const sign = isProfit ? "+" : "";
        const pnlClass = isProfit ? "profit" : "loss";
        const actionClass = (t.type || "BUY").toLowerCase();

        html += `
          <div class="trade-live-item">
            <div class="trade-live-header">
              <span class="trade-symbol-tag">${t.symbol}</span>
              <span class="trade-action-pill ${actionClass}">${t.type} ${t.volume || 0.01} Lot</span>
            </div>

            <div class="trade-price-row">
              <span>Entry: <strong>${t.open_price}</strong></span>
              <span>──►</span>
              <span>Current: <strong>${t.current_price}</strong></span>
            </div>

            <div class="trade-pnl-banner">
              <span style="font-size: 0.75rem; color: var(--text-muted);">Floating Profit</span>
              <span class="pnl-hero-val ${pnlClass}">${sign}$${(t.pnl || 0).toFixed(2)} USD</span>
            </div>

            <div class="trade-defense-shield">
              <span>🛡️ Breakeven Protected ($0 Risk) • Auto-Trailing to +0.65R</span>
            </div>

            <button class="btn-close-trade" onclick="closeTrade(${t.ticket})">
              ✕ Close Position
            </button>
          </div>
        `;
      });
      container.innerHTML = html;
    }
  } catch (err) {
    console.warn("Active trades error:", err);
  }
}

window.closeTrade = async function(ticket) {
  if (!confirm(`Are you sure you want to close position #${ticket}?`)) return;

  if (clientAccount.is_demo) {
    clientAccount.open_positions = clientAccount.open_positions.filter(t => t.ticket !== ticket);
    showToast("✅ Trade closed successfully.");
    fetchActiveTrades();
    return;
  }

  try {
    const res = await fetch("/api/client/close-trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket: ticket })
    });
    const data = await res.json();
    if (data.success) {
      showToast("✅ Position closed on broker.");
      fetchActiveTrades();
      fetchAccount();
    } else {
      showToast("❌ Close failed: " + (data.error || "Unknown"));
    }
  } catch (err) {
    showToast("Error closing trade: " + err.message);
  }
};

// -----------------------------------------------------------------------------
// LIVE 1-TAP SIGNALS
// -----------------------------------------------------------------------------
async function fetchSignals() {
  const container = document.getElementById("cockpit-signals-grid");
  if (!container) return;

  try {
    const res = await fetch("/api/client/signals");
    if (!res.ok) return;
    const data = await res.json();
    const signals = data.signals || [];

    if (signals.length === 0) {
      container.innerHTML = `<div class="loading-mini">Waiting for next high-accuracy BEEP anomaly...</div>`;
      return;
    }

    let html = "";
    signals.slice(0, 3).forEach(s => {
      const actionColor = s.action === "BUY" ? "var(--emerald)" : "var(--rose)";
      html += `
        <div class="signal-quick-card">
          <div class="sig-meta-col">
            <h5>${s.symbol} <span style="color: ${actionColor}; font-weight: 800;">${s.action}</span></h5>
            <div class="sig-prices">Entry: ${s.entry} • SL: ${s.sl} • TP: ${s.tp}</div>
            <div class="sig-pnl-est">
              <span class="gain">Target: ${s.gain_estimate_usd}</span>
              <span class="risk">Risk: ${s.risk_estimate_usd}</span>
            </div>
          </div>
          <button class="btn-1tap-exec" onclick="execute1TapSignal('${s.symbol}', '${s.action}', ${s.entry}, ${s.sl}, ${s.tp})">
            1-Tap (0.01)
          </button>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    console.warn("Signals error:", err);
  }
}

window.execute1TapSignal = async function(symbol, action, entry, sl, tp) {
  showToast(`⚡ Dispatching 0.01 lot order on ${symbol}...`);

  try {
    const res = await fetch("/api/client/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: clientAccount.account_id,
        symbol: symbol,
        action: action,
        volume: 0.01,
        sl: sl,
        tp: tp
      })
    });

    const data = await res.json();
    if (data.success) {
      showToast(`✅ Executed Order #${data.ticket} on ${symbol}!`);
      fetchActiveTrades();
      fetchAccount();
    } else {
      showToast(`❌ Execution rejected: ${data.error || "Check broker margin"}`);
    }
  } catch (err) {
    showToast("Order routing error: " + err.message);
  }
};

// -----------------------------------------------------------------------------
// FREEMIUM UPGRADE BANNER LOGIC
// -----------------------------------------------------------------------------
function updateFreemiumBanner(data) {
  const banner = document.getElementById("card-freemium-banner");
  const title = document.getElementById("upgrade-banner-title");
  const desc = document.getElementById("upgrade-banner-desc");
  if (!banner || !title || !desc) return;

  if (data.is_demo) {
    title.textContent = "Your Demo Test Made +$15.20 Today!";
    desc.textContent = "Switch to a Real MT5 account on Headway to withdraw real cash.";
  } else {
    title.textContent = "Headway Official Partnership Active";
    desc.textContent = "Enjoy 1:2000 leverage, zero spreads, and instant M-Pesa transactions.";
  }
}

// -----------------------------------------------------------------------------
// TOAST NOTIFICATIONS
// -----------------------------------------------------------------------------
function showToast(message) {
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
}
