"use client";

import { SESSION_EXPIRED_NOTICE, useCockpit } from "../hooks/useCockpit";
import { GateScreen } from "../components/GateScreen";
import { CockpitHeader } from "../components/CockpitHeader";
import { MetricHeroCard } from "../components/MetricHeroCard";
import { ActionButtonsRow } from "../components/ActionButtonsRow";
import { ActiveTradeCard } from "../components/ActiveTradeCard";
import { SignalsQuickGrid } from "../components/SignalsQuickGrid";
import { RiskModeSheet } from "../components/RiskModeSheet";
import { AccountConnectorModal } from "../components/AccountConnectorModal";
import { AuthModal } from "../components/AuthModal";
import { FreemiumBanner } from "../components/FreemiumBanner";
import { AFFILIATE_URL } from "../lib/constants";

export default function Home() {
  const cockpit = useCockpit();

  // Guard against SSR/hydration mismatch: local storage is only read client-side.
  if (!cockpit.isMounted) {
    return <div className="min-h-screen bg-black" />;
  }

  return (
    <div className="min-h-screen bg-black text-gray-50 flex flex-col font-sans selection:bg-green-500 selection:text-black">
      {cockpit.toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-sm w-[90%] bg-[#111111] border border-green-500/40 text-green-300 text-xs px-4 py-3 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-md animate-fadeUp text-center font-medium">
          {cockpit.toast}
        </div>
      )}

      {!cockpit.isAuthenticated && (cockpit.sessionExpired || cockpit.authConfigError) && (
        <div className="max-w-md w-full mx-auto px-4 pt-4 space-y-2">
          {cockpit.sessionExpired && (
            <div
              role="alert"
              className="flex items-center justify-between gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-medium"
            >
              <span>{SESSION_EXPIRED_NOTICE}</span>
              <button
                type="button"
                onClick={() => {
                  cockpit.dismissSessionExpired();
                  cockpit.openSignIn();
                }}
                className="shrink-0 px-3 py-1.5 rounded-lg bg-amber-500 text-black font-bold hover:bg-amber-400"
              >
                Sign in
              </button>
            </div>
          )}
          {cockpit.authConfigError && (
            <div
              role="alert"
              className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium"
            >
              {cockpit.authConfigError}
            </div>
          )}
        </div>
      )}

      {!cockpit.isAuthenticated ? (
        <GateScreen
          onLaunchDemo={cockpit.onLaunchDemo}
          onConnectReal={cockpit.openConnectorReal}
          onOpenAuth={cockpit.openAuth}
          liveStats={cockpit.gateStats}
          affiliateLink={AFFILIATE_URL}
        />
      ) : (
        <div className="flex-1 flex flex-col">
          <CockpitHeader
            telemetry={cockpit.telemetry}
            onOpenConnector={cockpit.openConnector}
            onExitToGate={cockpit.onExitToGate}
          />

          <main className="flex-1 max-w-xl w-full mx-auto px-4 py-5 space-y-6 animate-fadeUp">
            {cockpit.connectionError && (
              <div
                role="alert"
                className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium"
              >
                ⚠️ Live data unavailable — showing last known values. {cockpit.connectionError}
              </div>
            )}

            <MetricHeroCard telemetry={cockpit.telemetry} onOpenConnector={cockpit.openConnector} />

            <ActionButtonsRow
              autoPilotEnabled={cockpit.telemetry.autopilot_enabled}
              onToggleAutoPilot={cockpit.onToggleAutoPilot}
              onOpenRiskSheet={cockpit.openRiskSheet}
              onScrollToSignals={cockpit.onScrollToSignals}
              onRefresh={cockpit.onRefresh}
              isRefreshing={cockpit.isRefreshing}
            />

            <ActiveTradeCard
              trades={cockpit.telemetry.open_positions}
              onClosePosition={cockpit.onClosePosition}
              isClosing={cockpit.isClosingTrade}
            />

            <div ref={cockpit.signalsSectionRef}>
              <SignalsQuickGrid
                signals={cockpit.signals}
                onExecute={cockpit.onExecuteSignal}
                isExecuting={cockpit.isExecutingSignal}
                isDemo={cockpit.telemetry.is_demo}
              />
            </div>

            {cockpit.telemetry.is_demo && (
              <FreemiumBanner
                onSwitchToRealModal={cockpit.openConnectorReal}
                affiliateLink={AFFILIATE_URL}
              />
            )}
          </main>

          <footer className="py-6 border-t border-white/[0.06] text-center text-xs text-gray-500">
            <p className="font-semibold text-gray-400">Sajim Traders © 2026</p>
            <p className="mt-1 text-[11px] text-gray-600">
              Autonomous Quantitative Execution • Official Partner: Headway
            </p>
          </footer>
        </div>
      )}

      <AccountConnectorModal
        isOpen={cockpit.showConnectorModal}
        onClose={cockpit.closeConnector}
        onConnectSuccess={cockpit.onAccountConnected}
        initialTab={cockpit.connectorTab}
        currentAccountId={cockpit.telemetry.account_id}
        currentServer={cockpit.telemetry.broker_server}
        affiliateLink={AFFILIATE_URL}
      />

      <AuthModal
        isOpen={cockpit.showAuthModal}
        onClose={cockpit.closeAuth}
        onSuccess={cockpit.onAuthSuccess}
        initialMode={cockpit.authMode}
      />

      <RiskModeSheet
        isOpen={cockpit.showRiskSheet}
        onClose={cockpit.closeRiskSheet}
        currentMode={cockpit.telemetry.risk_mode}
        onSelectMode={cockpit.onRiskChange}
      />
    </div>
  );
}
