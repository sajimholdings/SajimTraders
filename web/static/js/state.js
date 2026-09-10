// =============================================================================
// SAJIM TRADERS — CLIENT STATE & STORAGE MODULE (state.js)
// =============================================================================

window.clientAccount = {
  account_id: "",
  account_name: "Trader",
  broker_server: "Headway-Real",
  autopilot_enabled: false,
  balance: 0.00,
  equity: 0.00,
  free_margin: 0.00,
  today_pnl: 0.00,
  today_pnl_percent: 0.0,
  currency: "USD",
  open_positions: [],
  floating_pnl: 0.0,
  terminal_connected: false,
  is_demo: false
};

window.currentConnectorTab = "DEMO";

// Restore stored account from localStorage if present
(function initStoredState() {
  const savedAcc = localStorage.getItem("sajim_client_account");
  if (savedAcc) {
    try {
      const parsed = JSON.parse(savedAcc);
      window.clientAccount = { ...window.clientAccount, ...parsed };
    } catch (e) {
      console.warn("Could not parse saved account:", e);
    }
  }
})();

window.saveClientAccountState = function(acc) {
  window.clientAccount = acc;
  localStorage.setItem("sajim_client_account", JSON.stringify(acc));
};
