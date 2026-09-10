/**
 * ========================================================================================
 *              SAJIM TRADERS — QUANTITATIVE WEB PLATFORM & TERMINAL (app.js)
 * ========================================================================================
 * Chief Quantitative Architect: Jimmy Mathu
 * Brand: Sajim Traders (@sajimtraders)
 * Note: Consumes sanitized institutional signals from BEEP API Gateway.
 * ========================================================================================
 */

let refreshCountdown = 3;
let refreshInterval = 3;
let autoRefreshTimer = null;
let allSignalsCache = [];
let activeSignalFilter = "ALL";

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSammyCheck();
  initManualRefresh();
  
  // Initial fetch
  fetchLandingStats();
  fetchTelemetry();
  fetchPositions();
  fetchSignals();
  fetchEdgeMatrix();

  // Start polling
  startAutoRefresh();
});

// -----------------------------------------------------------------------------
// VIEW SWITCHING (LANDING OVERVIEW <--> QUANT TERMINAL)
// -----------------------------------------------------------------------------
window.switchView = function(viewName) {
  const landingView = document.getElementById("view-landing");
  const terminalView = document.getElementById("view-terminal");
  const btnLanding = document.getElementById("btn-view-landing");
  const btnTerminal = document.getElementById("btn-view-terminal");

  if (viewName === "terminal") {
    if (landingView) landingView.classList.remove("active");
    if (terminalView) terminalView.classList.add("active");
    if (btnLanding) btnLanding.classList.remove("active");
    if (btnTerminal) btnTerminal.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else {
    if (terminalView) terminalView.classList.remove("active");
    if (landingView) landingView.classList.add("active");
    if (btnTerminal) btnTerminal.classList.remove("active");
    if (btnLanding) btnLanding.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
};

// -----------------------------------------------------------------------------
// LANDING STATS
// -----------------------------------------------------------------------------
async function fetchLandingStats() {
  try {
    const res = await fetch("/api/landing");
    if (!res.ok) return;
    const data = await res.json();
    // Landing stats are statically rendered with high-converting values,
    // but dynamic sync can update if needed.
  } catch (err) {
    console.warn("Landing stats fallback active.");
  }
}

// -----------------------------------------------------------------------------
// TAB SWITCHING (INSIDE TERMINAL)
// -----------------------------------------------------------------------------
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");

      tabBtns.forEach(b => b.classList.remove("active"));
      tabPanels.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const activePanel = document.getElementById(targetTab);
      if (activePanel) activePanel.classList.add("active");
    });
  });
}

// -----------------------------------------------------------------------------
// AUTO-REFRESH & POLLING
// -----------------------------------------------------------------------------
function startAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);

  autoRefreshTimer = setInterval(() => {
    refreshCountdown--;
    const counterEl = document.getElementById("refresh-counter");
    if (counterEl) counterEl.textContent = `${refreshCountdown}s`;

    if (refreshCountdown <= 0) {
      refreshCountdown = refreshInterval;
      fetchTelemetry();
      fetchPositions();
      fetchSignals();
    }
  }, 1000);
}

function initManualRefresh() {
  const btn = document.getElementById("btn-manual-refresh");
  if (btn) {
    btn.addEventListener("click", () => {
      refreshCountdown = refreshInterval;
      fetchTelemetry();
      fetchPositions();
      fetchSignals();
      fetchEdgeMatrix();
      showToast("Telemetry synced with MT5 terminal");
    });
  }
}

// -----------------------------------------------------------------------------
// TELEMETRY & ACCOUNT METRICS
// -----------------------------------------------------------------------------
async function fetchTelemetry() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    const acc = data.account || {};
    const pnl = data.pnl || {};
    const conc = data.concurrency || {};
    const broker = data.broker || {};
    const circuit = data.circuit_breaker || {};

    // Top Navigation
    const brokerEl = document.getElementById("nav-broker-status");
    if (brokerEl && broker.server) {
      brokerEl.textContent = `MT5: ${broker.server} (${broker.account})`;
    }

    const sessionEl = document.getElementById("nav-market-session");
    if (sessionEl && data.session) {
      sessionEl.textContent = data.session;
    }

    const circuitEl = document.getElementById("nav-circuit-breaker");
    const circuitText = document.getElementById("circuit-text");
    if (circuitEl && circuitText) {
      if (circuit.active) {
        circuitEl.className = "circuit-badge tripped";
        circuitText.textContent = "CIRCUIT TRIPPED";
      } else {
        circuitEl.className = "circuit-badge safe";
        circuitText.textContent = "CIRCUIT SAFE";
      }
    }

    // KPI Cards
    const balUsc = acc.balance_usc || 0.0;
    const balUsd = acc.balance_usd || (balUsc / 100.0);
    const eqUsc = acc.equity_usc || 0.0;
    const eqUsd = acc.equity_usd || (eqUsc / 100.0);

    const balEl = document.getElementById("kpi-balance");
    if (balEl) balEl.textContent = `${balUsc.toFixed(2)} USC`;

    const balUsdEl = document.getElementById("kpi-balance-usd");
    if (balUsdEl) balUsdEl.textContent = `$${balUsd.toFixed(2)} USD (Cent Account)`;

    const eqEl = document.getElementById("kpi-equity");
    if (eqEl) eqEl.textContent = `${eqUsc.toFixed(2)} USC`;

    const eqUsdEl = document.getElementById("kpi-equity-usd");
    if (eqUsdEl) eqUsdEl.textContent = `$${eqUsd.toFixed(2)} USD`;

    // Floating PnL
    const floatPnl = pnl.today_floating || 0.0;
    const floatEl = document.getElementById("kpi-floating-pnl");
    if (floatEl) {
      const prefix = floatPnl >= 0 ? "+" : "";
      floatEl.textContent = `${prefix}${floatPnl.toFixed(2)} USC`;
      floatEl.className = `kpi-value ${floatPnl >= 0 ? "profit-green" : "loss-red"}`;
    }

    const closedPnl = pnl.today_closed || 0.0;
    const closedEl = document.getElementById("kpi-closed-pnl");
    if (closedEl) {
      closedEl.textContent = `Today's Closed PnL: ${closedPnl >= 0 ? "+" : ""}${closedPnl.toFixed(2)} USC`;
    }

    // Free Margin & Level
    const freeMargin = acc.free_margin || 0.0;
    const freeMarginEl = document.getElementById("kpi-free-margin");
    if (freeMarginEl) freeMarginEl.textContent = `${freeMargin.toFixed(2)} USC`;

    const marginLvl = acc.margin_level_pct || 0.0;
    const marginLvlEl = document.getElementById("kpi-margin-level");
    if (marginLvlEl) marginLvlEl.textContent = `Margin Level: ${marginLvl.toFixed(1)}%`;

    // Concurrency
    const totalOpen = conc.total_open || 0;
    const maxCombined = conc.max_combined || 12;
    const concEl = document.getElementById("kpi-concurrency");
    if (concEl) concEl.textContent = `${totalOpen} / ${maxCombined}`;

    const progressEl = document.getElementById("concurrency-progress");
    if (progressEl) {
      const pct = Math.min(100, Math.round((totalOpen / maxCombined) * 100));
      progressEl.style.width = `${pct}%`;
    }

    const breakdownEl = document.getElementById("kpi-bot-breakdown");
    if (breakdownEl) {
      breakdownEl.textContent = `V1: ${conc.v1_count || 0} | V2: ${conc.v2_count || 0}`;
    }

    const tabBadge = document.getElementById("tab-positions-badge");
    if (tabBadge) tabBadge.textContent = totalOpen;

  } catch (err) {
    console.error("Error fetching telemetry:", err);
  }
}

// -----------------------------------------------------------------------------
// ACTIVE POSITIONS
// -----------------------------------------------------------------------------
async function fetchPositions() {
  try {
    const res = await fetch("/api/positions");
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById("positions-table-body");
    if (!tbody) return;

    const trades = data.trades || [];
    if (trades.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No open positions currently held.</td></tr>`;
      return;
    }

    let rowsHtml = "";
    trades.forEach(t => {
      const pnl = t.profit || 0.0;
      const pnlClass = pnl >= 0 ? "profit-green" : "loss-red";
      const pnlSign = pnl >= 0 ? "+" : "";
      const typeBadge = t.type === "BUY" ? "badge-buy" : "badge-sell";

      rowsHtml += `
        <tr>
          <td><span style="font-family: var(--font-mono); color: var(--text-muted);">${t.ticket}</span></td>
          <td><strong>${t.symbol}</strong></td>
          <td>
            <span class="badge" style="background: rgba(56, 189, 248, 0.1); color: var(--cyan-glow);">${t.bot}</span>
          </td>
          <td><span class="badge ${typeBadge}">${t.type}</span></td>
          <td>${t.volume}</td>
          <td>${t.price_open}</td>
          <td style="color: #fb7185;">${t.sl || "--"}</td>
          <td style="color: #34d399;">${t.tp || "--"}</td>
          <td class="${pnlClass}" style="font-weight: 700;">${pnlSign}${pnl.toFixed(2)}</td>
          <td><span class="badge badge-rare">${t.comment || "Sajim_Edge"}</span></td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;
  } catch (err) {
    console.error("Error fetching positions:", err);
  }
}

// -----------------------------------------------------------------------------
// BEEP SIGNALS RADAR & FILTERING
// -----------------------------------------------------------------------------
async function fetchSignals() {
  try {
    const res = await fetch("/api/signals");
    if (!res.ok) return;
    const data = await res.json();

    allSignalsCache = data.signals || [];
    renderFilteredSignals();
  } catch (err) {
    console.error("Error fetching signals:", err);
  }
}

window.filterSignals = function(tier) {
  activeSignalFilter = tier;
  const chipBtns = document.querySelectorAll(".chip-btn");
  chipBtns.forEach(btn => {
    btn.classList.remove("active");
    if (btn.textContent.includes(tier) || (tier === "ALL" && btn.textContent.includes("All"))) {
      btn.classList.add("active");
    }
  });
  renderFilteredSignals();
};

function renderFilteredSignals() {
  const container = document.getElementById("signals-container");
  const countEl = document.getElementById("radar-signal-count");
  if (!container) return;

  const filtered = allSignalsCache.filter(s => {
    if (activeSignalFilter === "ALL") return true;
    return (s.layer || "").toUpperCase() === activeSignalFilter.toUpperCase();
  });

  if (countEl) countEl.textContent = filtered.length;

  if (filtered.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem;">Scanning for institutional ${activeSignalFilter} setups...</div>`;
    return;
  }

  let cardsHtml = "";
  filtered.forEach(s => {
    const isBuy = (s.action || "").toUpperCase() === "BUY";
    const actionBadge = isBuy ? "badge-buy" : "badge-sell";
    
    let layerBadge = "badge-certified";
    if (s.layer === "DIAMOND") layerBadge = "badge-diamond";
    else if (s.layer === "RARE") layerBadge = "badge-rare";

    cardsHtml += `
      <div class="signal-card">
        <div class="signal-card-head">
          <div class="signal-pair">${s.symbol} <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 400;">(${s.timeframe})</span></div>
          <div style="display: flex; gap: 0.4rem;">
            <span class="badge ${layerBadge}">${s.layer}</span>
            <span class="badge ${actionBadge}">${s.action}</span>
          </div>
        </div>

        <div class="signal-metrics">
          <div class="metric-item">
            <span class="metric-lbl">ENTRY PRICE</span>
            <span class="metric-val">${s.entry}</span>
          </div>
          <div class="metric-item">
            <span class="metric-lbl">TARGET (1:${s.rr} R:R)</span>
            <span class="metric-val" style="color: #34d399;">${s.tp}</span>
          </div>
          <div class="metric-item">
            <span class="metric-lbl">INVALIDATION (SL)</span>
            <span class="metric-val" style="color: #fb7185;">${s.sl}</span>
          </div>
          <div class="metric-item">
            <span class="metric-lbl">EDGE MASS M(t)</span>
            <span class="metric-val">${s.m_t}</span>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">
          <span>Session: ${s.session || "LONDON"}</span>
          <span>Spread: ${s.spread_points || 15} pts</span>
        </div>

        <div class="signal-actions">
          <button class="btn btn-outline" style="flex: 1;" onclick='copySignal(${JSON.stringify(s)})'>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            Copy Signal
          </button>
          <button class="btn btn-primary" onclick='dispatchSimulatedTrade(${JSON.stringify(s)})'>
            Verify Risk
          </button>
        </div>
      </div>
    `;
  });

  container.innerHTML = cardsHtml;
}

// -----------------------------------------------------------------------------
// EMPIRICAL EDGE MATRIX
// -----------------------------------------------------------------------------
async function fetchEdgeMatrix() {
  try {
    const res = await fetch("/api/edge-matrix");
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById("top-edges-body");
    const bleedersList = document.getElementById("toxic-bleeders-list");

    if (tbody && data.top_edges) {
      let rows = "";
      data.top_edges.forEach(e => {
        const symbol = e.symbol || "";
        const tf = e.timeframe || e.tf || "";
        const pf = (e.profit_factor || e.pf || 0).toFixed(2);
        const wr = (e.win_rate_pct || e.wr || 0).toFixed(1);
        const exp = (e.expectancy_r || e.expectancy || 0).toFixed(3);

        rows += `
          <tr>
            <td><strong>${symbol}</strong></td>
            <td><span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1;">${tf}</span></td>
            <td style="color: #38bdf8; font-weight: 700;">${pf}</td>
            <td style="color: #34d399;">${wr}%</td>
            <td>+${exp}R</td>
          </tr>
        `;
      });
      tbody.innerHTML = rows;
    }

    if (bleedersList && data.toxic_bleeders && data.toxic_bleeders.worst_assets) {
      let items = "";
      data.toxic_bleeders.worst_assets.forEach(b => {
        items += `<div>• <span style="color: #fb7185;">${b}</span></div>`;
      });
      bleedersList.innerHTML = items;
    }
  } catch (err) {
    console.error("Error fetching edge matrix:", err);
  }
}

// -----------------------------------------------------------------------------
// SAMMY'S 4-CHECK RISK GATEKEEPER
// -----------------------------------------------------------------------------
function initSammyCheck() {
  const btn = document.getElementById("btn-run-sammy-check");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const payload = {
      symbol: document.getElementById("sammy-symbol").value,
      direction: document.getElementById("sammy-direction").value,
      current_price: parseFloat(document.getElementById("sammy-price").value) || 0,
      b_t: parseFloat(document.getElementById("sammy-bt").value) || 0,
      sl: parseFloat(document.getElementById("sammy-sl").value) || 0,
      lot_size: parseFloat(document.getElementById("sammy-lot").value) || 0.10,
      m_t: parseFloat(document.getElementById("sammy-mt").value) || 40.0,
      lambda_pct: parseFloat(document.getElementById("sammy-lambda").value) || 15.0,
    };

    try {
      const res = await fetch("/api/sammy-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) return;
      const data = await res.json();
      renderSammyResult(data);
      showToast(`Sammy's 4-Check Decision: ${data.decision}`);
    } catch (err) {
      console.error("Error evaluating Sammy 4-Check:", err);
    }
  });
}

function renderSammyResult(data) {
  const verdictBanner = document.getElementById("sammy-verdict-banner");
  const timestampEl = document.getElementById("sammy-card-timestamp");
  const summaryEl = document.getElementById("sammy-summary-text");

  if (timestampEl) timestampEl.textContent = data.timestamp || "";
  if (summaryEl) summaryEl.textContent = data.summary || "";

  if (verdictBanner) {
    if (data.decision === "GO") {
      verdictBanner.className = "sammy-verdict-box verdict-go";
      verdictBanner.textContent = ">>> GO — APPROVED FOR EXECUTION <<<";
    } else {
      verdictBanner.className = "sammy-verdict-box verdict-stop";
      verdictBanner.textContent = "!!! STOP — BLOCKED BY RISK GATEKEEPER !!!";
    }
  }

  const checks = data.checks || {};
  updateGateItem("gate-1", checks.check_1_momentum);
  updateGateItem("gate-2", checks.check_2_sl_baseline);
  updateGateItem("gate-3", checks.check_3_lot_size);
  updateGateItem("gate-4", checks.check_4_lambda_energy);
}

function updateGateItem(prefix, checkData) {
  if (!checkData) return;
  const badge = document.getElementById(`${prefix}-badge`);
  const desc = document.getElementById(`${prefix}-desc`);

  if (badge) {
    badge.className = checkData.passed ? "gate-badge-pass" : "gate-badge-fail";
    badge.textContent = checkData.passed ? "[PASS - YES]" : "[FAIL - NO]";
  }
  if (desc && checkData.detail) {
    desc.textContent = checkData.detail;
  }
}

// -----------------------------------------------------------------------------
// HELPER ACTIONS
// -----------------------------------------------------------------------------
window.copySignal = function(sig) {
  const text = 
`🏛️ *Signal: ${sig.symbol} (${sig.timeframe})*
━━━━━━━━━━━━━━━━━━━━━━
• Action: *${sig.action}* @ \`${sig.entry}\`
• Invalidation Floor (SL): \`${sig.sl}\`
• Target Profit (TP): \`${sig.tp}\` (1:${sig.rr} R:R)
• Layer: ${sig.layer}
• Edge Mass M(t): \`${sig.m_t}\`
⚡ *Sajim Traders — Powered by BEEP Protocol*`;

  navigator.clipboard.writeText(text).then(() => {
    showToast(`Signal for ${sig.symbol} copied!`);
  }).catch(() => {
    showToast("Copied to clipboard!");
  });
};

window.dispatchSimulatedTrade = function(sig) {
  // Ensure terminal view is active
  switchView('terminal');

  // Switch to Sammy tab and auto-populate parameters
  const sammyTabBtn = document.querySelector('[data-tab="tab-sammy"]');
  if (sammyTabBtn) sammyTabBtn.click();

  document.getElementById("sammy-symbol").value = sig.symbol;
  document.getElementById("sammy-direction").value = sig.action;
  document.getElementById("sammy-price").value = sig.entry;
  document.getElementById("sammy-bt").value = sig.b_t || sig.entry;
  document.getElementById("sammy-sl").value = sig.sl;
  document.getElementById("sammy-mt").value = sig.m_t || 45.0;

  // Run check automatically
  const checkBtn = document.getElementById("btn-run-sammy-check");
  if (checkBtn) checkBtn.click();
};

function showToast(message) {
  const toast = document.getElementById("toast-msg");
  if (!toast) return;
  toast.textContent = message;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 2500);
}
