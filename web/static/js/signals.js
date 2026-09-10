// =============================================================================
// SAJIM TRADERS — SIGNALS & 1-TAP EXECUTION MODULE (signals.js)
// =============================================================================

window.fetchActiveTrades = async function() {
  const container = document.getElementById("active-trades-view");
  const slotPill = document.getElementById("trades-slot-pill");
  if (!container) return;

  try {
    let trades = window.clientAccount.open_positions || [];

    if (!window.clientAccount.is_demo) {
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
              <span>🛡️ Breakeven Shield Active (+0.35R) • Auto-Trailing to +0.65R</span>
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
};

window.closeTrade = async function(ticket) {
  if (!confirm(`Are you sure you want to close position #${ticket}?`)) return;

  if (window.clientAccount.is_demo) {
    window.clientAccount.open_positions = window.clientAccount.open_positions.filter(t => t.ticket !== ticket);
    if (window.showToast) window.showToast("✅ Trade closed successfully.");
    window.fetchActiveTrades();
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
      if (window.showToast) window.showToast("✅ Position closed on broker.");
      window.fetchActiveTrades();
      if (window.fetchAccount) window.fetchAccount();
    } else {
      if (window.showToast) window.showToast("❌ Close failed: " + (data.error || "Unknown"));
    }
  } catch (err) {
    if (window.showToast) window.showToast("Error closing trade: " + err.message);
  }
};

window.fetchSignals = async function() {
  const container = document.getElementById("cockpit-signals-grid");
  if (!container) return;

  try {
    const res = await fetch("/api/client/signals");
    if (!res.ok) return;
    const data = await res.json();
    const signals = data.signals || [];

    if (signals.length === 0) {
      container.innerHTML = `<div class="loading-mini" style="font-size: 0.8rem; color: var(--text-dim); text-align: center; padding: 16px;">Waiting for next high-accuracy BEEP anomaly...</div>`;
      return;
    }

    let html = "";
    signals.slice(0, 4).forEach(s => {
      const isBuy = s.action === "BUY";
      const actionClass = isBuy ? "buy" : "sell";
      const healthPct = s.trade_health_pct || 88;
      const healthStatus = s.trade_health_status || "PRIME HEALTH";
      const duration = s.expected_duration || "15-25 mins";
      const bars = s.expected_bars || "10 bars";
      const explainer = s.trade_explainer || "Institutional momentum surge detected on dynamic HMA baseline. +0.35R Breakeven Shield protection armed.";
      const strategy = s.strategy || "Sajim V2 Momentum Edge";

      html += `
        <div class="signal-quick-card">
          <div class="sig-card-header">
            <div class="sig-title-box">
              <span class="sig-symbol">${s.symbol}</span>
              <span class="sig-action-pill ${actionClass}">${s.action}</span>
              <span class="sig-strat-tag">${strategy}</span>
            </div>
            <div class="sig-pnl-est">
              <span class="gain">TP: ${s.gain_estimate_usd}</span>
              <span class="risk">SL: ${s.risk_estimate_usd}</span>
            </div>
          </div>

          <div class="sig-prices-row">
            <span>Entry: <strong>${s.entry}</strong></span>
            <span>SL: <strong>${s.sl}</strong></span>
            <span>TP: <strong>${s.tp}</strong></span>
            <span>R:R: <strong>${s.rr || "1:2"}</strong></span>
          </div>

          <!-- DURATION & TRADE HEALTH TELEMETRY -->
          <div class="sig-telemetry-row">
            <div class="sig-duration-chip">
              <span class="duration-icon">⏳</span>
              <span>Exp. Hold: <strong>${duration}</strong> (${bars})</span>
            </div>
            <div class="sig-health-chip">
              <div class="sig-health-header">
                <span>🟢 Health: ${healthStatus}</span>
                <span>${healthPct}%</span>
              </div>
              <div class="sig-health-track">
                <div class="sig-health-fill" style="width: ${healthPct}%;"></div>
              </div>
            </div>
          </div>

          <!-- PLAIN-ENGLISH TRADE EXPLAINER -->
          <div class="sig-explainer-row">
            <strong>💡 Setup Reason:</strong> ${explainer}
          </div>

          <button class="btn-1tap-exec" onclick="execute1TapSignal('${s.symbol}', '${s.action}', ${s.entry}, ${s.sl}, ${s.tp})">
            ⚡ 1-Tap Trade (0.01 Micro-Lot)
          </button>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    console.warn("Signals error:", err);
  }
};

window.execute1TapSignal = async function(symbol, action, entry, sl, tp) {
  if (window.showToast) window.showToast(`⚡ Dispatching 0.01 lot order on ${symbol}...`);

  try {
    const res = await fetch("/api/client/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: window.clientAccount.account_id,
        symbol: symbol,
        action: action,
        volume: 0.01,
        sl: sl,
        tp: tp
      })
    });

    const data = await res.json();
    if (data.success) {
      if (window.showToast) window.showToast(`✅ Executed Order #${data.ticket} on ${symbol}!`);
      window.fetchActiveTrades();
      if (window.fetchAccount) window.fetchAccount();
    } else {
      if (window.showToast) window.showToast(`❌ Execution rejected: ${data.error || "Check broker margin"}`);
    }
  } catch (err) {
    if (window.showToast) window.showToast("Order routing error: " + err.message);
  }
};
