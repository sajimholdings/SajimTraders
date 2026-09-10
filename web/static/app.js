// =============================================================================
// SAJIM TRADERS — WEB APPLICATION ENTRY POINT (app.js)
// Modular Architecture: All logic separated into web/static/js/
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  // Check if an account was previously connected
  if (window.clientAccount && window.clientAccount.account_id) {
    window.showCockpit();
  } else {
    window.showGate();
  }

  // Connect form submission hook
  const connForm = document.getElementById("form-account-connect");
  if (connForm) {
    connForm.addEventListener("submit", window.handleAccountConnect);
  }

  // Polling intervals for real-time responsiveness
  setInterval(() => {
    const cockpit = document.getElementById("screen-cockpit");
    if (cockpit && cockpit.style.display !== "none") {
      if (window.fetchAccount) window.fetchAccount();
      if (window.fetchActiveTrades) window.fetchActiveTrades();
      if (window.fetchSignals) window.fetchSignals();
    }
  }, 3500);
});
