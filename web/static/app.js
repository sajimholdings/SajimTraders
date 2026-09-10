/**
 * ========================================================================================
 *              SAJIM TRADERS — 1-TAP CLIENT PORTAL & COPY ENGINE (app.js)
 * ========================================================================================
 * Chief Quantitative Architect: Jimmy Mathu
 * Brand: Sajim Traders (@sajimtraders)
 * Features:
 *   - Live Account Balance & Telemetry Synchronization
 *   - 1-Tap Direct MT5 Order Execution
 *   - Hands-Free Auto-Pilot Copy Trading Toggle
 *   - Real-Time Open Position Management & Close Triggers
 * ========================================================================================
 */

let clientAccount = {
  account_id: "17537803",
  account_name: "Jimmy Muema",
  broker_server: "Headway-Real",
  autopilot_enabled: false,
  balance: 20.98,
  equity: 20.98,
  free_margin: 20.98,
  floating_pnl: 0.0,
  currency: "USD",
  terminal_connected: true
};

let cachedSignals = [];
let activeCategoryFilter = "ALL";
let pollInterval = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  // Initial Loads
  fetchAccount();
  fetchSignals();
  fetchActiveTrades();

  // 3-second live polling
  startLivePolling();
});

// -----------------------------------------------------------------------------
// LIVE POLLING
// -----------------------------------------------------------------------------
function startLivePolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(() => {
    fetchAccount();
    fetchSignals();
    fetchActiveTrades();
  }, 3000);
}

// -----------------------------------------------------------------------------
// ACCOUNT TELEMETRY
// -----------------------------------------------------------------------------
async function fetchAccount() {
  try {
    const res = await fetch("/api/client/account");
    if (!res.ok) return;
    const data = await res.json();
    clientAccount = data;

    // Update Top Hero Card
    const heroBalance = document.getElementById("hero-balance");
    if (heroBalance) {
      heroBalance.innerHTML = `$${data.balance.toFixed(2)} <span class="currency">${data.currency || 'USD'}</span>`;
    }

    const heroEquity = document.getElementById("hero-equity");
    if (heroEquity) heroEquity.textContent = `$${data.equity.toFixed(2)}`;

    const heroFreeMargin = document.getElementById("hero-free-margin");
    if (heroFreeMargin) heroFreeMargin.textContent = `$${data.free_margin.toFixed(2)}`;

    const heroBroker = document.getElementById("hero-broker-server");
    if (heroBroker) heroBroker.textContent = data.broker_server || "Headway-Real";

    const heroName = document.getElementById("hero-acc-name");
    if (heroName) heroName.textContent = data.account_name || `#${data.account_id}`;

    // Floating PnL
    const heroPnl = document.getElementById("hero-floating-pnl");
    const floatingPnl = data.floating_pnl || 0.0;
    if (heroPnl) {
      const sign = floatingPnl > 0 ? "+" : "";
      heroPnl.textContent = `${sign}$${floatingPnl.toFixed(2)}`;
      heroPnl.className = "pnl-value " + (floatingPnl > 0 ? "positive" : (floatingPnl < 0 ? "negative" : "zero"));
    }

    // Active trades count in hero
    const openCount = (data.open_positions || []).length;
    const heroCount = document.getElementById("hero-active-count");
    if (heroCount) heroCount.textContent = `${openCount} / 3 Max`;

    const btnTradesCount = document.getElementById("btn-trades-count");
    if (btnTradesCount) btnTradesCount.textContent = openCount;

    const badgeTradesCount = document.getElementById("badge-trades-count");
    if (badgeTradesCount) badgeTradesCount.textContent = openCount;

    // Header Chip
    const chipText = document.getElementById("chip-acc-text");
    if (chipText) chipText.textContent = `MT5: #${data.account_id}`;

    const chipDot = document.getElementById("chip-dot");
    if (chipDot) {
      chipDot.className = "chip-status-dot " + (data.terminal_connected ? "connected" : "");
    }

    // Sync Auto-Pilot Toggle State
    syncAutoPilotUI(data.autopilot_enabled);

  } catch (err) {
    console.warn("Account polling offline or server restarting:", err);
  }
}

// -----------------------------------------------------------------------------
// AUTOPILOT TOGGLING
// -----------------------------------------------------------------------------
window.toggleAutoPilot = async function(enabled) {
  try {
    const res = await fetch("/api/client/toggle-autopilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: clientAccount.account_id,
        enabled: enabled
      })
    });

    const data = await res.json();
    if (data.success) {
      clientAccount.autopilot_enabled = enabled;
      syncAutoPilotUI(enabled);
      const msg = enabled 
        ? "🤖 Auto-Pilot ACTIVATED! All V2 signals will mirror automatically." 
        : "⏸️ Auto-Pilot PAUSED. Switched to Manual 1-Tap execution.";
      showToast(msg);
    } else {
      showToast("Failed to update Auto-Pilot: " + (data.error || "Unknown error"));
    }
  } catch (err) {
    console.error("AutoPilot toggle error:", err);
    showToast("Error communicating with trading server");
  }
};

function syncAutoPilotUI(enabled) {
  // Header Toggle
  const headerToggle = document.getElementById("header-autopilot-toggle");
  if (headerToggle && headerToggle.checked !== enabled) {
    headerToggle.checked = enabled;
  }

  const headerText = document.getElementById("header-autopilot-text");
  if (headerText) {
    headerText.textContent = enabled ? "ON" : "OFF";
    headerText.className = "autopilot-status-text " + (enabled ? "active" : "");
  }

  // Main Hub Toggle
  const mainToggle = document.getElementById("main-autopilot-toggle");
  if (mainToggle && mainToggle.checked !== enabled) {
    mainToggle.checked = enabled;
  }

  const statusBox = document.getElementById("autopilot-status-box");
  const bannerText = document.getElementById("autopilot-banner-text");

  if (statusBox && bannerText) {
    if (enabled) {
      statusBox.className = "status-indicator-box active";
      bannerText.innerHTML = "<strong>Auto-Pilot is ACTIVE!</strong> 24/7 autonomous copy-trading enabled for account #" + clientAccount.account_id;
    } else {
      statusBox.className = "status-indicator-box inactive";
      bannerText.innerHTML = "Auto-Pilot is currently OFF. You are in manual 1-tap mode.";
    }
  }
}

// -----------------------------------------------------------------------------
// SIGNALS FEED & 1-TAP EXECUTION
// -----------------------------------------------------------------------------
async function fetchSignals() {
  try {
    const res = await fetch("/api/client/signals");
    if (!res.ok) return;
    const data = await res.json();
    cachedSignals = data.signals || [];

    const badgeCount = document.getElementById("badge-signal-count");
    if (badgeCount) badgeCount.textContent = cachedSignals.length;

    renderSignals();
  } catch (err) {
    console.warn("Signals fetch error:", err);
  }
}

window.filterSignalsCategory = function(cat) {
  activeCategoryFilter = cat;
  const chips = document.querySelectorAll(".filter-chip");
  chips.forEach(c => {
    c.classList.remove("active");
    if (c.textContent.toUpperCase().includes(cat) || (cat === "ALL" && c.textContent.includes("All"))) {
      c.classList.add("active");
    }
  });
  renderSignals();
};

function renderSignals() {
  const container = document.getElementById("signals-feed-container");
  if (!container) return;

  const filtered = cachedSignals.filter(s => {
    if (activeCategoryFilter === "ALL") return true;
    if (activeCategoryFilter === "GOLD") return s.symbol.includes("XAU") || s.symbol.includes("GOLD");
    if (activeCategoryFilter === "INDICES") return s.symbol.includes("100") || s.symbol.includes("30") || s.symbol.includes("US") || s.symbol.includes("NAS");
    if (activeCategoryFilter === "FOREX") return !s.symbol.includes("XAU") && !s.symbol.includes("100") && !s.symbol.includes("30");
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-trades-state">
        <p>Scanning markets for high-probability ${activeCategoryFilter} setups...</p>
      </div>
    `;
    return;
  }

  let html = "";
  filtered.forEach(s => {
    const isBuy = (s.action || "").toUpperCase() === "BUY";
    const actionClass = isBuy ? "buy" : "sell";
    const actionPill = isBuy ? "🟢 BUY" : "🔴 SELL";

    html += `
      <div class="signal-card">
        <div class="sig-card-head">
          <div class="sig-asset-group">
            <span class="sig-symbol">${s.symbol}</span>
            <span class="sig-tf">${s.timeframe}</span>
          </div>
          <div class="sig-badges">
            <span class="badge-win-prob">🎯 ${s.win_probability || '89% Win Rate'}</span>
            <span class="badge-action-pill ${actionClass}">${actionPill}</span>
          </div>
        </div>

        <div class="sig-metrics-grid">
          <div class="sig-metric-box">
            <span class="sig-m-lbl">Entry Level</span>
            <span class="sig-m-val">${s.entry}</span>
          </div>
          <div class="sig-metric-box">
            <span class="sig-m-lbl">Target (TP)</span>
            <span class="sig-m-val target">${s.tp}</span>
          </div>
          <div class="sig-metric-box">
            <span class="sig-m-lbl">Stop Loss (SL)</span>
            <span class="sig-m-val stop">${s.sl}</span>
          </div>
        </div>

        <div class="sig-payoff-strip">
          <div class="payoff-item">
            <span>Target Gain:</span>
            <span class="payoff-gain">${s.gain_estimate_usd || '+$12.50'}</span>
          </div>
          <div class="payoff-item">
            <span>Max Risk:</span>
            <span class="payoff-risk">${s.risk_estimate_usd || '-$4.20'}</span>
          </div>
          <div class="payoff-item">
            <span>Reward:</span>
            <span class="payoff-rr">${s.rr || '1:2.5'}</span>
          </div>
        </div>

        <button 
          class="btn-1tap-execute ${actionClass}" 
          id="btn-exec-${s.id}" 
          onclick='handle1TapExecute(${JSON.stringify(s)})'>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          ⚡ 1-TAP EXECUTE ON MT5 (${actionPill})
        </button>
      </div>
    `;
  });

  container.innerHTML = html;
}

// -----------------------------------------------------------------------------
// 1-TAP EXECUTE ACTION
// -----------------------------------------------------------------------------
window.handle1TapExecute = async function(sig) {
  const btn = document.getElementById(`btn-exec-${sig.id}`);
  const originalText = btn ? btn.innerHTML : "";

  if (btn) {
    btn.disabled = true;
    btn.className = "btn-1tap-execute executing";
    btn.innerHTML = `<div class="spinner" style="width: 20px; height: 20px; margin: 0;"></div> Submitting order to MT5...`;
  }

  try {
    const payload = {
      account_id: clientAccount.account_id,
      symbol: sig.symbol,
      action: sig.action,
      volume: 0.01,
      sl: sig.sl,
      tp: sig.tp,
      comment: "Sajim_1Tap"
    };

    const res = await fetch("/api/client/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (res.ok && data.success) {
      if (btn) {
        btn.className = "btn-1tap-execute success";
        btn.innerHTML = `✓ PLACED ORDER ON MT5 (Ticket #${data.ticket})`;
      }
      showToast(`⚡ TRADE EXECUTED! #${data.ticket}: ${sig.action} 0.01 ${sig.symbol}`);

      // Refresh account and trades
      fetchAccount();
      fetchActiveTrades();

      // Reset button after 3 seconds
      setTimeout(() => {
        if (btn) {
          btn.disabled = false;
          btn.className = `btn-1tap-execute ${sig.action.toLowerCase()}`;
          btn.innerHTML = originalText;
        }
      }, 3000);

    } else {
      if (btn) {
        btn.disabled = false;
        btn.className = `btn-1tap-execute ${sig.action.toLowerCase()}`;
        btn.innerHTML = originalText;
      }
      showToast(`Execution Failed: ${data.error || "Broker rejected order"}`);
    }

  } catch (err) {
    console.error("1-Tap execution error:", err);
    if (btn) {
      btn.disabled = false;
      btn.className = `btn-1tap-execute ${sig.action.toLowerCase()}`;
      btn.innerHTML = originalText;
    }
    showToast("Network error executing trade.");
  }
};

// -----------------------------------------------------------------------------
// OPEN TRADES MANAGEMENT
// -----------------------------------------------------------------------------
async function fetchActiveTrades() {
  try {
    const res = await fetch("/api/client/active-trades");
    if (!res.ok) return;
    const data = await res.json();
    const trades = data.trades || [];

    const container = document.getElementById("open-trades-container");
    if (!container) return;

    if (trades.length === 0) {
      container.innerHTML = `
        <div class="empty-trades-state">
          <div class="empty-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <h3>No Open Positions</h3>
          <p>You have no active orders executing on your MT5 terminal right now. Tap a signal from the feed or turn on Auto-Pilot to mirror trades automatically.</p>
          <button class="btn-primary" onclick="switchNavTab('signals-tab')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            Explore 1-Tap Signals
          </button>
        </div>
      `;
      return;
    }

    let listHtml = `<div class="trades-list">`;
    trades.forEach(t => {
      const pnl = t.pnl || 0.0;
      const pnlSign = pnl >= 0 ? "+" : "";
      const pnlClass = pnl >= 0 ? "positive" : "negative";

      listHtml += `
        <div class="trade-item-card">
          <div class="trade-item-left">
            <div>
              <div class="trade-ticket">Ticket #${t.ticket} &bull; ${t.time || ''}</div>
              <div class="trade-item-symbol">${t.symbol} <span class="badge-action-pill ${t.type.toLowerCase()}" style="font-size: 0.68rem; padding: 0.15rem 0.45rem;">${t.type}</span></div>
              <div class="trade-item-volume">${t.volume} Lots @ ${t.open_price} &rarr; Now ${t.current_price}</div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div class="trade-item-pnl ${pnlClass}">${pnlSign}$${pnl.toFixed(2)}</div>
            <button class="btn-close-trade" onclick="handleCloseTrade(${t.ticket})">
              ✕ Close
            </button>
          </div>
        </div>
      `;
    });
    listHtml += `</div>`;

    container.innerHTML = listHtml;

  } catch (err) {
    console.warn("Error loading trades:", err);
  }
}

window.handleCloseTrade = async function(ticket) {
  if (!confirm(`Are you sure you want to close position #${ticket} at market price?`)) {
    return;
  }

  try {
    const res = await fetch("/api/client/close-trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket: ticket })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Position #${ticket} successfully closed!`);
      fetchAccount();
      fetchActiveTrades();
    } else {
      showToast(`Failed to close: ${data.error || "Error"}`);
    }
  } catch (err) {
    showToast("Error communicating with broker to close position.");
  }
};

// -----------------------------------------------------------------------------
// TAB SWITCHING
// -----------------------------------------------------------------------------
window.switchNavTab = function(tabId) {
  const tabs = document.querySelectorAll(".tab-content");
  const navBtns = document.querySelectorAll(".nav-tab");

  tabs.forEach(t => t.classList.remove("active"));
  navBtns.forEach(b => b.classList.remove("active"));

  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add("active");

  const activeBtn = document.querySelector(`[onclick="switchNavTab('${tabId}')"]`);
  if (activeBtn) activeBtn.classList.add("active");

  window.scrollTo({ top: 0, behavior: "smooth" });
};

// -----------------------------------------------------------------------------
// CONNECT MT5 MODAL & MULTI-ACCOUNT MANAGEMENT
// -----------------------------------------------------------------------------
window.openConnectModal = function() {
  const modal = document.getElementById("connect-modal");
  if (modal) modal.classList.add("active");
  fetchAccountsList();
};

window.closeConnectModal = function() {
  const modal = document.getElementById("connect-modal");
  if (modal) modal.classList.remove("active");
};

async function fetchAccountsList() {
  const listContainer = document.getElementById("modal-accounts-list");
  if (!listContainer) return;

  try {
    const res = await fetch("/api/client/accounts");
    if (!res.ok) return;
    const data = await res.json();
    const accounts = data.accounts || [];

    if (accounts.length === 0) {
      listContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted);">No accounts linked yet.</div>`;
      return;
    }

    let html = "";
    accounts.forEach(acc => {
      const isActive = String(acc.account_id) === String(clientAccount.account_id);
      html += `
        <div style="background: rgba(0,0,0,0.35); border: 1px solid ${isActive ? 'var(--cyan-accent)' : 'var(--border-subtle)'}; border-radius: 8px; padding: 0.75rem 0.9rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-weight: 700; font-size: 0.88rem; color: #fff; display: flex; align-items: center; gap: 0.45rem;">
              <span>${acc.account_name || 'Account'} (#${acc.account_id})</span>
              ${isActive ? '<span style="background: rgba(56, 189, 248, 0.2); color: var(--cyan-accent); font-size: 0.65rem; padding: 0.1rem 0.4rem; border-radius: 999px; font-weight: 800;">ACTIVE</span>' : ''}
            </div>
            <div style="font-size: 0.75rem; color: var(--text-dim); font-family: var(--font-mono); margin-top: 0.15rem;">
              ${acc.broker_server} &bull; Risk: ${acc.risk_mode || '0.01 Lot'}
            </div>
          </div>
          <div style="display: flex; gap: 0.4rem;">
            ${!isActive ? `
              <button style="background: rgba(56, 189, 248, 0.15); border: 1px solid var(--cyan-accent); color: var(--cyan-accent); font-size: 0.75rem; font-weight: 700; padding: 0.35rem 0.65rem; border-radius: 6px; cursor: pointer;" onclick="switchActiveAccount('${acc.account_id}')">
                Switch
              </button>
            ` : ''}
            ${accounts.length > 1 ? `
              <button style="background: transparent; border: none; color: #fb7185; cursor: pointer; padding: 0.2rem 0.4rem; font-size: 1.1rem; line-height: 1;" onclick="removeAccount('${acc.account_id}')" title="Remove Account">
                &times;
              </button>
            ` : ''}
          </div>
        </div>
      `;
    });

    listContainer.innerHTML = html;
  } catch (err) {
    console.warn("Could not load accounts list:", err);
  }
}

window.switchActiveAccount = async function(accountId) {
  try {
    const res = await fetch("/api/client/switch-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id: accountId })
    });

    const data = await res.json();
    if (data.success) {
      showToast(`Switched active MT5 account to #${accountId}!`);
      fetchAccount();
      fetchAccountsList();
    } else {
      showToast("Switch failed: " + (data.error || "Unknown"));
    }
  } catch (err) {
    showToast("Error switching account");
  }
};

window.removeAccount = async function(accountId) {
  if (!confirm(`Remove account #${accountId}?`)) return;
  try {
    const res = await fetch("/api/client/delete-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id: accountId })
    });

    const data = await res.json();
    if (data.success) {
      showToast(`Account #${accountId} removed.`);
      fetchAccount();
      fetchAccountsList();
    }
  } catch (err) {
    showToast("Error removing account");
  }
};

window.handleAccountConnect = async function(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-save-account");
  const originalText = btn ? btn.innerHTML : "";

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width: 18px; height: 18px; margin: 0;"></div> Authenticating with MT5...`;
  }

  const broker = document.getElementById("modal-broker-server").value;
  const login = document.getElementById("modal-login").value;
  const password = document.getElementById("modal-password").value;
  const riskMode = document.getElementById("modal-risk-mode").value;

  const payload = {
    account_id: login,
    broker_server: broker,
    password: password,
    risk_mode: riskMode,
    account_name: `Account #${login}`
  };

  try {
    const res = await fetch("/api/client/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`✓ Verified & Connected MT5 #${login}!`);
      closeConnectModal();
      fetchAccount();
    } else {
      showToast(`Connection Failed: ${data.error || "Invalid credentials or server"}`);
    }
  } catch (err) {
    showToast("Network error verifying MT5 connection");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
};

// -----------------------------------------------------------------------------
// RISK MODE UPDATE
// -----------------------------------------------------------------------------
window.updateRiskMode = async function(mode) {
  const cards = document.querySelectorAll(".risk-preset-card");
  cards.forEach(c => {
    c.classList.remove("active");
    if (c.querySelector(`input[value="${mode}"]`)) {
      c.classList.add("active");
    }
  });

  try {
    await fetch("/api/client/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: clientAccount.account_id,
        risk_mode: mode
      })
    });
    showToast(`Risk profile updated to ${mode}`);
  } catch (err) {
    console.warn("Could not save risk mode:", err);
  }
};

// -----------------------------------------------------------------------------
// TOAST NOTIFICATION
// -----------------------------------------------------------------------------
function showToast(msg) {
  const toast = document.getElementById("app-toast");
  if (!toast) return;
  toast.textContent = msg;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3500);
}
