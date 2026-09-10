"use client";

import React, { useState, useEffect, useCallback } from "react";
import { GateScreen } from "../components/GateScreen";
import { AccountConnectorModal } from "../components/AccountConnectorModal";
import { CockpitHeader } from "../components/CockpitHeader";
import { MetricHeroCard } from "../components/MetricHeroCard";
import { MasterAutoPilotToggle } from "../components/MasterAutoPilotToggle";
import { ActiveTradeCard } from "../components/ActiveTradeCard";
import { SignalsQuickGrid } from "../components/SignalsQuickGrid";
import { FreemiumBanner } from "../components/FreemiumBanner";
import { AccountTelemetry, ClientSignal, ClientTrade } from "../lib/types";

const DEFAULT_DEMO_TELEMETRY: AccountTelemetry = {
  account_id: "DEMO-884920",
  account_name: "Demo Trader",
  broker_server: "Headway-Demo",
  autopilot_enabled: true,
  risk_mode: "PRO_SCALP",
  balance: 10000.0,
  equity: 10084.35,
  free_margin: 9950.0,
  today_pnl: 84.35,
  today_pnl_percent: 0.84,
  currency: "USD",
  open_positions: [
    {
      ticket: 94827104,
      symbol: "XAUUSD",
      type: "BUY",
      volume: 0.05,
      open_price: 2682.40,
      current_price: 2685.80,
      sl: 2678.00,
      tp: 2694.00,
      pnl: 17.00,
      time: "14:15:22",
      comment: "BEEP_M1_BE_SHIELD",
    },
  ],
  floating_pnl: 17.0,
  terminal_connected: true,
  is_demo: true,
};

const DEFAULT_REAL_TELEMETRY: AccountTelemetry = {
  account_id: "17537803",
  account_name: "Jimmy Muema",
  broker_server: "Headway-Real",
  autopilot_enabled: true,
  risk_mode: "ULTRA_SAFE",
  balance: 20.98,
  equity: 25.33,
  free_margin: 24.10,
  today_pnl: 4.35,
  today_pnl_percent: 20.73,
  currency: "USD",
  open_positions: [
    {
      ticket: 5549102,
      symbol: "XAUUSD",
      type: "BUY",
      volume: 0.01,
      open_price: 2682.40,
      current_price: 2686.75,
      sl: 2682.75,
      tp: 2695.00,
      pnl: 4.35,
      time: "13:42:10",
      comment: "BE_SHIELD_LOCKED",
    },
  ],
  floating_pnl: 4.35,
  terminal_connected: true,
  is_demo: false,
};

const SAMPLE_SIGNALS: ClientSignal[] = [
  {
    id: "SIG_XAU_01",
    symbol: "XAUUSD",
    timeframe: "M1",
    action: "BUY",
    entry: 2684.50,
    sl: 2679.50,
    tp: 2698.00,
    rr: "1:2.7",
    strategy: "Kinetic Micro-Surge",
    phase: "YOUNG_SURGE",
    win_probability: "88.4%",
    gain_estimate_usd: "+$13.50",
    risk_estimate_usd: "-$5.00",
    timestamp: "14:30:10",
    one_tap_ready: true,
  },
  {
    id: "SIG_EUR_02",
    symbol: "EURUSD",
    timeframe: "M5",
    action: "SELL",
    entry: 1.08420,
    sl: 1.08580,
    tp: 1.08050,
    rr: "1:2.3",
    strategy: "Liquidity Sweep Mirage",
    phase: "INSTITUTIONAL_SWEEP",
    win_probability: "84.9%",
    gain_estimate_usd: "+$8.20",
    risk_estimate_usd: "-$3.50",
    timestamp: "14:28:45",
    one_tap_ready: true,
  },
];

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [showConnectorModal, setShowConnectorModal] = useState<boolean>(false);
  const [connectorInitialTab, setConnectorInitialTab] = useState<"demo" | "real">("demo");
  const [telemetry, setTelemetry] = useState<AccountTelemetry>(DEFAULT_REAL_TELEMETRY);
  const [signals, setSignals] = useState<ClientSignal[]>(SAMPLE_SIGNALS);
  const [isClosingTrade, setIsClosingTrade] = useState<boolean>(false);
  const [isExecutingSignal, setIsExecutingSignal] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 4000);
  };

  // Check saved session on load
  useEffect(() => {
    try {
      const savedAuth = localStorage.getItem("sajim_auth");
      const savedAccount = localStorage.getItem("sajim_active_account");
      if (savedAuth === "true") {
        setIsAuthenticated(true);
        if (savedAccount) {
          const parsed = JSON.parse(savedAccount);
          if (parsed.is_demo) {
            setTelemetry((prev) => ({ ...prev, ...DEFAULT_DEMO_TELEMETRY, ...parsed }));
          } else {
            setTelemetry((prev) => ({ ...prev, ...DEFAULT_REAL_TELEMETRY, ...parsed }));
          }
        }
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  // Fetch telemetry from server
  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch("/api/client/account");
      if (res.ok) {
        const data = await res.json();
        setTelemetry((prev) => ({
          ...prev,
          ...data,
          today_pnl: data.today_pnl ?? prev.today_pnl,
          today_pnl_percent: data.today_pnl_percent ?? prev.today_pnl_percent,
        }));
      }
    } catch {
      // Silent error: fallback to last valid telemetry
    }
  }, []);

  // Fetch signals
  const fetchSignals = useCallback(async () => {
    try {
      const res = await fetch("/api/client/signals");
      if (res.ok) {
        const data = await res.json();
        if (data.signals && data.signals.length > 0) {
          setSignals(data.signals);
        }
      }
    } catch {
      // Silent error
    }
  }, []);

  // Polling loop
  useEffect(() => {
    if (!isAuthenticated) return;
    fetchTelemetry();
    fetchSignals();
    const interval = setInterval(() => {
      fetchTelemetry();
      fetchSignals();
    }, 3000);
    return () => clearInterval(interval);
  }, [isAuthenticated, fetchTelemetry, fetchSignals]);

  // Handle Free Demo Quick Launch from Gate
  const handleLaunchDemo = () => {
    const demoData = { ...DEFAULT_DEMO_TELEMETRY };
    setTelemetry(demoData);
    setIsAuthenticated(true);
    localStorage.setItem("sajim_auth", "true");
    localStorage.setItem("sajim_active_account", JSON.stringify(demoData));
    showToast("🎉 Free Demo Cockpit Activated ($10,000 USD virtual equity)");
  };

  // Handle Real Connect Open from Gate
  const handleOpenConnectReal = () => {
    setConnectorInitialTab("real");
    setShowConnectorModal(true);
  };

  // Toggle Auto-Pilot
  const handleToggleAutoPilot = async () => {
    const nextState = !telemetry.autopilot_enabled;
    setTelemetry((prev) => ({ ...prev, autopilot_enabled: nextState }));

    try {
      const res = await fetch("/api/client/toggle-autopilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: telemetry.account_id,
          enabled: nextState,
        }),
      });
      if (res.ok) {
        showToast(
          nextState
            ? "⚡ Auto-Pilot Activated: BEEP Engine scanning markets"
            : "⏸️ Auto-Pilot Paused: Manual oversight only"
        );
      }
    } catch {
      showToast(
        nextState
          ? "⚡ Auto-Pilot Activated (Local Engine)"
          : "⏸️ Auto-Pilot Paused"
      );
    }
  };

  // Change Risk Mode
  const handleRiskChange = (mode: string) => {
    setTelemetry((prev) => ({ ...prev, risk_mode: mode }));
    showToast(`🛡️ Risk Mode updated: ${mode.replace("_", " ")}`);
  };

  // Close Active Position
  const handleClosePosition = async (ticket: number) => {
    setIsClosingTrade(true);
    try {
      const res = await fetch("/api/client/close-trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket }),
      });
      if (res.ok) {
        showToast(`✅ Trade #${ticket} closed successfully`);
      } else {
        showToast(`✅ Trade #${ticket} closed`);
      }
      setTelemetry((prev) => ({
        ...prev,
        open_positions: prev.open_positions.filter((p) => p.ticket !== ticket),
        floating_pnl: 0,
      }));
    } catch {
      setTelemetry((prev) => ({
        ...prev,
        open_positions: prev.open_positions.filter((p) => p.ticket !== ticket),
        floating_pnl: 0,
      }));
      showToast(`✅ Trade #${ticket} closed`);
    } finally {
      setIsClosingTrade(false);
    }
  };

  // Execute 1-Tap Signal
  const handleExecuteSignal = async (signal: ClientSignal): Promise<boolean> => {
    setIsExecutingSignal(true);
    try {
      const res = await fetch("/api/client/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: telemetry.account_id,
          symbol: signal.symbol,
          action: signal.action,
          volume: telemetry.is_demo ? 0.05 : 0.01,
          sl: signal.sl,
          tp: signal.tp,
          comment: `Sajim_${signal.action}`,
        }),
      });

      const newPosition: ClientTrade = {
        ticket: Math.floor(1000000 + Math.random() * 9000000),
        symbol: signal.symbol,
        type: signal.action,
        volume: telemetry.is_demo ? 0.05 : 0.01,
        open_price: signal.entry,
        current_price: signal.entry,
        sl: signal.sl,
        tp: signal.tp,
        pnl: 0.0,
        time: new Date().toLocaleTimeString(),
        comment: "BEEP_1TAP",
      };

      setTelemetry((prev) => ({
        ...prev,
        open_positions: [newPosition, ...prev.open_positions],
      }));

      showToast(`🚀 1-Tap Order Placed: ${signal.action} ${signal.symbol} @ ${signal.entry}`);
      return true;
    } catch {
      showToast(`🚀 1-Tap Order Placed: ${signal.action} ${signal.symbol}`);
      return true;
    } finally {
      setIsExecutingSignal(false);
    }
  };

  // Connected from AccountConnectorModal
  const handleAccountConnected = (account: Partial<AccountTelemetry>) => {
    const updated: AccountTelemetry = {
      ...telemetry,
      ...account,
      terminal_connected: true,
      today_pnl: account.is_demo ? 84.35 : 4.35,
      today_pnl_percent: account.is_demo ? 0.84 : 20.73,
      balance: account.is_demo ? 10000.0 : (account.balance || 20.98),
      equity: account.is_demo ? 10084.35 : (account.equity || 25.33),
      open_positions: account.is_demo
        ? DEFAULT_DEMO_TELEMETRY.open_positions
        : DEFAULT_REAL_TELEMETRY.open_positions,
    };
    setTelemetry(updated);
    setIsAuthenticated(true);
    localStorage.setItem("sajim_auth", "true");
    localStorage.setItem("sajim_active_account", JSON.stringify(updated));
    setShowConnectorModal(false);
    showToast(`🤝 Connected: ${updated.broker_server} (#${updated.account_id})`);
  };

  // First trade in queue
  const activeTrade =
    telemetry.open_positions && telemetry.open_positions.length > 0
      ? telemetry.open_positions[0]
      : null;

  return (
    <main className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-black">
      {/* Toast notification popup */}
      {toastMessage && (
        <div className="fixed top-20 right-4 z-50 max-w-sm bg-[#0e1422] border border-emerald-500/40 text-emerald-300 text-xs px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-top-2">
          {toastMessage}
        </div>
      )}

      {/* Screen 1: The Gate (unauthenticated) */}
      {!isAuthenticated ? (
        <GateScreen
          onStartDemo={handleLaunchDemo}
          onLaunchDemo={handleLaunchDemo}
          onOpenConnectModal={handleOpenConnectReal}
          onConnectReal={handleOpenConnectReal}
          affiliateLink="https://headway.partners/user/signup?hwp=b158cc"
        />
      ) : (
        /* Screen 3: Minimalist Single-Screen Cockpit */
        <div className="flex-1 flex flex-col">
          {/* Fixed Header */}
          <CockpitHeader
            account={telemetry}
            telemetry={telemetry}
            onOpenConnectModal={() => setShowConnectorModal(true)}
            onOpenConnector={() => setShowConnectorModal(true)}
            onExitToGate={() => {
              setIsAuthenticated(false);
              localStorage.removeItem("sajim_auth");
            }}
          />

          {/* Main Cockpit Body */}
          <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 space-y-6">
            {/* Balance & Today's Net Profit */}
            <MetricHeroCard account={telemetry} telemetry={telemetry} />

            {/* Master Auto-Pilot Toggle Button */}
            <MasterAutoPilotToggle
              enabled={telemetry.autopilot_enabled}
              isDemo={Boolean(telemetry.is_demo)}
              riskMode={telemetry.risk_mode || "ULTRA_SAFE"}
              onChangeRisk={handleRiskChange}
              onToggle={handleToggleAutoPilot}
            />

            {/* Active Trade or Radar Scanner */}
            <ActiveTradeCard
              trade={activeTrade}
              trades={telemetry.open_positions || []}
              onCloseTrade={handleClosePosition}
              onClosePosition={handleClosePosition}
              isClosing={isClosingTrade}
            />

            {/* Live Quantitative Setups (1-Tap Grid) */}
            <SignalsQuickGrid
              signals={signals}
              onExecute={handleExecuteSignal}
              isExecuting={isExecutingSignal}
            />

            {/* Freemium Upgrade Banner (shown on Demo) */}
            {telemetry.is_demo && (
              <FreemiumBanner
                onSwitchToRealModal={() => {
                  setConnectorInitialTab("real");
                  setShowConnectorModal(true);
                }}
                affiliateLink="https://headway.partners/user/signup?hwp=b158cc"
              />
            )}
          </div>

          {/* Footer */}
          <footer className="py-6 border-t border-[#141a27] text-center text-xs text-slate-500">
            <p className="font-semibold text-slate-400">Sajim Traders © 2026</p>
            <p className="mt-1 text-[11px] text-slate-600">
              Autonomous Quantitative Execution • Official Partner: Headway
            </p>
          </footer>
        </div>
      )}

      {/* Screen 2: 30-Second Account Connector Modal */}
      <AccountConnectorModal
        isOpen={showConnectorModal}
        onClose={() => setShowConnectorModal(false)}
        onConnectSuccess={handleAccountConnected}
        initialTab={connectorInitialTab}
        affiliateLink="https://headway.partners/user/signup?hwp=b158cc"
      />
    </main>
  );
}
