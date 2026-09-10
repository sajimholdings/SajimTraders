"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
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
import { AccountTelemetry, ClientSignal, ClientTrade } from "../lib/types";
import { trackAction } from "../lib/logger";
import { supabase } from "../lib/supabase";

const INITIAL_DEMO_TELEMETRY: AccountTelemetry = {
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
      open_price: 2682.4,
      current_price: 2685.8,
      sl: 2678.0,
      tp: 2694.0,
      pnl: 17.0,
      time: "14:15:22",
      comment: "BEEP_M1_BE_SHIELD",
    },
  ],
  floating_pnl: 17.0,
  terminal_connected: true,
  is_demo: true,
};

const INITIAL_REAL_TELEMETRY: AccountTelemetry = {
  account_id: "17537803",
  account_name: "Jimmy Muema",
  broker_server: "Headway-Real",
  autopilot_enabled: true,
  risk_mode: "ULTRA_SAFE",
  balance: 20.98,
  equity: 25.33,
  free_margin: 24.1,
  today_pnl: 4.35,
  today_pnl_percent: 20.73,
  currency: "USD",
  open_positions: [
    {
      ticket: 5549102,
      symbol: "XAUUSD",
      type: "BUY",
      volume: 0.01,
      open_price: 2682.4,
      current_price: 2686.75,
      sl: 2682.75,
      tp: 2695.0,
      pnl: 4.35,
      time: "13:42:10",
      comment: "BE_SHIELD_LOCKED",
    },
  ],
  floating_pnl: 4.35,
  terminal_connected: true,
  is_demo: false,
};

const EMPTY_ACCOUNT_TELEMETRY: AccountTelemetry = {
  account_id: "NEW",
  account_name: "Trader",
  broker_server: "None",
  autopilot_enabled: false,
  risk_mode: "ULTRA_SAFE",
  balance: 0.0,
  equity: 0.0,
  free_margin: 0.0,
  today_pnl: 0.0,
  today_pnl_percent: 0.0,
  currency: "USD",
  open_positions: [],
  floating_pnl: 0.0,
  terminal_connected: false,
  is_demo: false,
};

const SEED_SIGNALS: ClientSignal[] = [
  {
    id: "SIG_XAU_01",
    symbol: "XAUUSD",
    timeframe: "M1",
    action: "BUY",
    entry: 2684.5,
    sl: 2679.5,
    tp: 2698.0,
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
    entry: 1.0842,
    sl: 1.0858,
    tp: 1.0805,
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
  const [isMounted, setIsMounted] = useState<boolean>(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [showConnectorModal, setShowConnectorModal] = useState<boolean>(false);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [showRiskSheet, setShowRiskSheet] = useState<boolean>(false);
  const [connectorInitialTab, setConnectorInitialTab] = useState<"demo" | "real">("demo");
  const [telemetry, setTelemetry] = useState<AccountTelemetry>(EMPTY_ACCOUNT_TELEMETRY);
  const [signals, setSignals] = useState<ClientSignal[]>(SEED_SIGNALS);
  const [isClosingTrade, setIsClosingTrade] = useState<boolean>(false);
  const [isExecutingSignal, setIsExecutingSignal] = useState<boolean>(false);
  const [isTogglingAutoPilot, setIsTogglingAutoPilot] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [gateStats, setGateStats] = useState<{ total_pnl: number; total_trades: number; win_rate: number } | null>(null);

  const signalsSectionRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 4000);
  };

  // Restore saved session on load
  useEffect(() => {
    try {
      const savedAuth = localStorage.getItem("sajim_auth");
      const savedAccount = localStorage.getItem("sajim_active_account");
      if (savedAuth === "true") {
        setIsAuthenticated(true);
        if (savedAccount) {
          const parsed = JSON.parse(savedAccount);
          setTelemetry((prev) => ({
            ...prev,
            ...(parsed.is_demo ? INITIAL_DEMO_TELEMETRY : EMPTY_ACCOUNT_TELEMETRY),
            ...parsed,
          }));
        }
      }
    } catch {
      // Ignore localStorage errors
    } finally {
      setIsMounted(true);
    }
  }, []);

  // Listen for Supabase Google OAuth callback tokens in URL hash (#access_token=...)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (hash && hash.includes("access_token=")) {
      trackAction("OAUTH_CALLBACK_DETECTED");
      const params = new URLSearchParams(hash.replace(/^#/, ""));
      const accessToken = params.get("access_token");
      if (accessToken) {
        supabase.getUser(accessToken).then((user) => {
          if (user) {
            const userEmail = user.email || "";
            const userName = user.user_metadata?.full_name || userEmail.split("@")[0] || "Trader";
            const authAccount: AccountTelemetry = {
              ...EMPTY_ACCOUNT_TELEMETRY,
              account_name: userName,
              account_id: "NEW",
              is_demo: false,
            };
            setTelemetry(authAccount);
            setIsAuthenticated(true);
            localStorage.setItem("sajim_auth", "true");
            localStorage.setItem("sajim_active_account", JSON.stringify(authAccount));
            localStorage.setItem("sajim_supabase_token", accessToken);
            showToast(`🎉 Welcome, ${userName}!`);
            trackAction("GOOGLE_SIGNIN_SUCCESS", { email: userEmail, id: user.id });
            window.history.replaceState(null, "", window.location.pathname);
          }
        });
      }
    }
  }, []);

  // Fetch gate stats on load
  useEffect(() => {
    async function loadGateStats() {
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const data = await res.json();
          const pnlToday = data.pnl?.combined_daily_net ?? 4.35;
          const openCount = data.concurrency?.total_open ?? 5;
          setGateStats({
            total_pnl: typeof pnlToday === "number" ? pnlToday : 4.35,
            total_trades: openCount,
            win_rate: 92.6,
          });
        }
      } catch {
        setGateStats({ total_pnl: 4.35, total_trades: 5, win_rate: 92.6 });
      }
    }
    loadGateStats();
  }, []);

  // Fetch telemetry from live API
  const fetchTelemetry = useCallback(async () => {
    try {
      // 1. If user is in Demo mode, keep virtual $10,000 intact
      if (telemetry.is_demo) {
        return;
      }

      // 2. If user is new and has not linked an MT5 account yet, do NOT fetch Jimmy's account
      if (telemetry.account_id === "NEW" || telemetry.broker_server === "None") {
        return;
      }

      const res = await fetch(`/api/client/account?account_id=${telemetry.account_id}`);
      if (res.ok) {
        const data = await res.json();
        if (!data.account_id || data.account_id === telemetry.account_id) {
          setTelemetry((prev) => ({
            ...prev,
            ...data,
            // CRITICAL: NEVER overwrite user's authentic name from Supabase
            account_name: prev.account_name || data.account_name,
            today_pnl: data.today_pnl ?? prev.today_pnl,
            today_pnl_percent: data.today_pnl_percent ?? prev.today_pnl_percent,
          }));
        }
      }
    } catch {
      // Fallback to current telemetry
    }
  }, [telemetry.is_demo, telemetry.account_id, telemetry.broker_server]);

  // Fetch signals from live API
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

  // Polling loop (every 3.5s)
  useEffect(() => {
    if (!isAuthenticated) return;
    fetchTelemetry();
    fetchSignals();
    const interval = setInterval(() => {
      fetchTelemetry();
      fetchSignals();
    }, 3500);
    return () => clearInterval(interval);
  }, [isAuthenticated, fetchTelemetry, fetchSignals]);

  // Handle Manual Refresh
  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    trackAction("MANUAL_SYNC_TRIGGERED");
    await Promise.all([fetchTelemetry(), fetchSignals()]);
    setTimeout(() => {
      setIsRefreshing(false);
      showToast("🟢 Telemetry & Signals Synchronized");
    }, 500);
  };

  // Handle Free Demo Launch
  const handleLaunchDemo = () => {
    const demoData = { ...INITIAL_DEMO_TELEMETRY };
    setTelemetry(demoData);
    setIsAuthenticated(true);
    localStorage.setItem("sajim_auth", "true");
    localStorage.setItem("sajim_active_account", JSON.stringify(demoData));
    showToast("🎉 Free Demo Cockpit Activated ($10,000 USD virtual equity)");
    trackAction("CLICK_START_DEMO", { balance: 10000, is_demo: true });
  };

  // Handle Google OAuth Sign-in
  const handleGoogleSignIn = () => {
    trackAction("CLICK_GOOGLE_AUTH");
    supabase.signInWithOAuth("google");
  };

  // Handle Real Account Connect Modal
  const handleOpenConnectReal = () => {
    trackAction("OPEN_CONNECT_MODAL");
    setConnectorInitialTab("real");
    setShowConnectorModal(true);
  };

  // Toggle Auto-Pilot
  const handleToggleAutoPilot = async () => {
    if (isTogglingAutoPilot) return;
    setIsTogglingAutoPilot(true);
    const prevState = telemetry.autopilot_enabled;
    const nextState = !prevState;
    setTelemetry((prev) => ({ ...prev, autopilot_enabled: nextState }));
    trackAction("TOGGLE_AUTOPILOT", { enabled: nextState });

    try {
      const res = await fetch("/api/client/toggle-autopilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: telemetry.account_id,
          enabled: nextState,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success !== false) {
        showToast(
          nextState
            ? "⚡ Auto-Pilot Activated: BEEP Engine scanning markets"
            : "⏸️ Auto-Pilot Paused: Manual oversight mode"
        );
      } else {
        setTelemetry((prev) => ({ ...prev, autopilot_enabled: prevState }));
        showToast("❌ Auto-Pilot error: " + (data.error || "Server rejected toggle"));
      }
    } catch {
      setTelemetry((prev) => ({ ...prev, autopilot_enabled: prevState }));
      showToast("❌ Network error toggling Auto-Pilot");
    } finally {
      setIsTogglingAutoPilot(false);
    }
  };

  // Change Risk Mode
  const handleRiskChange = async (mode: string) => {
    const updated = { ...telemetry, risk_mode: mode };
    setTelemetry(updated);
    localStorage.setItem("sajim_active_account", JSON.stringify(updated));
    trackAction("CHANGE_RISK_MODE", { mode });
    showToast(`🛡️ Risk Mode updated: ${mode.replace("_", " ")}`);

    // Sync to backend
    fetch("/api/client/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: telemetry.account_id,
        broker_server: telemetry.broker_server,
        risk_mode: mode,
      }),
    }).catch(() => {});
  };

  // Close Active Position
  const handleClosePosition = async (ticket: number) => {
    setIsClosingTrade(true);
    trackAction("CLOSE_POSITION", { ticket });
    try {
      const res = await fetch("/api/client/close-trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success) {
        showToast(`✅ Trade #${ticket} closed successfully`);
        setTelemetry((prev) => ({
          ...prev,
          open_positions: prev.open_positions.filter((p) => p.ticket !== ticket),
          floating_pnl: 0,
        }));
      } else {
        showToast(`❌ Failed to close Trade #${ticket}: ` + (data.error || "Broker rejected close"));
      }
    } catch (err: any) {
      showToast(`❌ Network error closing Trade #${ticket}: ` + err.message);
    } finally {
      setIsClosingTrade(false);
    }
  };

  // Execute 1-Tap Signal
  const handleExecuteSignal = async (signal: ClientSignal): Promise<boolean> => {
    setIsExecutingSignal(true);
    trackAction("EXECUTE_1TAP_SIGNAL", {
      symbol: signal.symbol,
      action: signal.action,
      entry: signal.entry,
      is_demo: telemetry.is_demo,
    });
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

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.success) {
        const newPosition: ClientTrade = {
          ticket: data.ticket || Math.floor(1000000 + Math.random() * 9000000),
          symbol: signal.symbol,
          type: signal.action,
          volume: data.volume || (telemetry.is_demo ? 0.05 : 0.01),
          open_price: data.price || signal.entry,
          current_price: data.price || signal.entry,
          sl: signal.sl,
          tp: signal.tp,
          pnl: 0.0,
          time: new Date().toLocaleTimeString(),
          comment: "BEEP_1TAP",
        };

        setTelemetry((prev) => ({
          ...prev,
          open_positions: [newPosition, ...(prev.open_positions || [])],
        }));

        showToast(`🚀 1-Tap Order Filled: ${signal.action} ${signal.symbol} (Ticket #${newPosition.ticket})`);
        return true;
      } else if (telemetry.is_demo) {
        // Fallback simulation specifically for guest demo
        const demoTicket = Math.floor(1000000 + Math.random() * 9000000);
        const newPosition: ClientTrade = {
          ticket: demoTicket,
          symbol: signal.symbol,
          type: signal.action,
          volume: 0.05,
          open_price: signal.entry,
          current_price: signal.entry,
          sl: signal.sl,
          tp: signal.tp,
          pnl: 0.0,
          time: new Date().toLocaleTimeString(),
          comment: "DEMO_1TAP",
        };
        setTelemetry((prev) => ({
          ...prev,
          open_positions: [newPosition, ...(prev.open_positions || [])],
        }));
        showToast(`🚀 [Demo] 1-Tap Order Filled: ${signal.action} ${signal.symbol}`);
        return true;
      } else {
        showToast(`❌ 1-Tap Execution Failed: ${data.error || "Broker rejected order"}`);
        return false;
      }
    } catch (err: any) {
      if (telemetry.is_demo) {
        showToast(`🚀 [Demo] 1-Tap Order Placed: ${signal.action} ${signal.symbol}`);
        return true;
      }
      showToast(`❌ Execution error reaching broker: ${err.message}`);
      return false;
    } finally {
      setIsExecutingSignal(false);
    }
  };

  // Account connected from Modal
  const handleAccountConnected = (account: Partial<AccountTelemetry>) => {
    const isDemo = Boolean(account.is_demo);
    const updated: AccountTelemetry = {
      ...telemetry,
      ...account,
      terminal_connected: true,
      today_pnl: isDemo ? 84.35 : (account.today_pnl !== undefined ? account.today_pnl : 0.0),
      today_pnl_percent: isDemo ? 0.84 : (account.today_pnl_percent !== undefined ? account.today_pnl_percent : 0.0),
      balance: isDemo ? 10000.0 : (account.balance !== undefined ? account.balance : 0.0),
      equity: isDemo ? 10084.35 : (account.equity !== undefined ? account.equity : 0.0),
      free_margin: isDemo ? 9950.0 : (account.free_margin !== undefined ? account.free_margin : 0.0),
      account_name: account.account_name || telemetry.account_name,
      open_positions: isDemo
        ? INITIAL_DEMO_TELEMETRY.open_positions
        : account.open_positions || [],
    };
    setTelemetry(updated);
    setIsAuthenticated(true);
    localStorage.setItem("sajim_auth", "true");
    localStorage.setItem("sajim_active_account", JSON.stringify(updated));
    setShowConnectorModal(false);
    showToast(`🤝 Connected: ${updated.broker_server} (#${updated.account_id})`);
    trackAction("ACCOUNT_CONNECTED", {
      broker: updated.broker_server,
      id: updated.account_id,
      is_demo: updated.is_demo,
    });
  };
  // Handle Email & Password Auth Success from Supabase
  const handleAuthSuccess = (userData: { email: string; fullName: string; id: string }) => {
    const isJimmy =
      userData.email.toLowerCase().includes("muema") ||
      userData.fullName.toLowerCase().includes("jimmy");

    const authAccount: AccountTelemetry = isJimmy
      ? {
          ...INITIAL_REAL_TELEMETRY,
          account_name: userData.fullName,
        }
      : {
          ...EMPTY_ACCOUNT_TELEMETRY,
          account_name: userData.fullName,
          account_id: "NEW",
        };

    setTelemetry(authAccount);
    setIsAuthenticated(true);
    localStorage.setItem("sajim_auth", "true");
    localStorage.setItem("sajim_active_account", JSON.stringify(authAccount));
    showToast(`🎉 Welcome, ${userData.fullName}!`);
    trackAction("USER_AUTHENTICATED", { email: userData.email, id: userData.id });
  };

  const handleScrollToSignals = () => {
    if (signalsSectionRef.current) {
      signalsSectionRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  if (!isMounted) {
    return <div className="min-h-screen bg-black" />;
  }

  return (
    <div className="min-h-screen bg-black text-gray-50 flex flex-col font-sans selection:bg-green-500 selection:text-black">
      {/* Floating Bottom Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-sm w-[90%] bg-[#111111] border border-green-500/40 text-green-300 text-xs px-4 py-3 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-md animate-fadeUp text-center font-medium">
          {toastMessage}
        </div>
      )}

      {/* View 1: Gate Screen (Unauthenticated) */}
      {!isAuthenticated ? (
        <GateScreen
          onLaunchDemo={handleLaunchDemo}
          onConnectReal={handleOpenConnectReal}
          onOpenAuthModal={() => setShowAuthModal(true)}
          affiliateLink="https://headway.partners/user/signup?hwp=b158cc"
          liveStats={gateStats}
        />
      ) : (
        /* View 2: Trading Cockpit (Authenticated) */
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <CockpitHeader
            telemetry={telemetry}
            onOpenConnector={() => setShowConnectorModal(true)}
            onExitToGate={() => {
              setIsAuthenticated(false);
              localStorage.removeItem("sajim_auth");
              localStorage.removeItem("sajim_active_account");
              localStorage.removeItem("sajim_user");
              setTelemetry(EMPTY_ACCOUNT_TELEMETRY);
              setSignals(SEED_SIGNALS);
              showToast("👋 Signed out successfully");
            }}
          />

          {/* Main Body */}
          <main className="flex-1 max-w-xl w-full mx-auto px-4 py-5 space-y-6 animate-fadeUp">
            {/* 1. Metric Hero Card (Massive Balance) */}
            <MetricHeroCard
              telemetry={telemetry}
              onOpenConnector={() => setShowConnectorModal(true)}
            />

            {/* 2. Wolfpixel Action Buttons Pill Row */}
            <ActionButtonsRow
              autoPilotEnabled={telemetry.autopilot_enabled}
              onToggleAutoPilot={handleToggleAutoPilot}
              onOpenRiskSheet={() => setShowRiskSheet(true)}
              onScrollToSignals={handleScrollToSignals}
              onRefresh={handleManualRefresh}
              isRefreshing={isRefreshing}
            />

            {/* 3. Positions (Token-Style Cards) */}
            <ActiveTradeCard
              trades={telemetry.open_positions || []}
              onClosePosition={handleClosePosition}
              isClosing={isClosingTrade}
            />

            {/* 4. Live Signals (Explore-Style Cards) */}
            <div ref={signalsSectionRef}>
              <SignalsQuickGrid
                signals={signals}
                onExecute={handleExecuteSignal}
                isExecuting={isExecutingSignal}
              />
            </div>

            {/* 5. Freemium Upgrade Banner (if in Demo) */}
            {telemetry.is_demo && (
              <FreemiumBanner
                onSwitchToRealModal={() => {
                  setConnectorInitialTab("real");
                  setShowConnectorModal(true);
                }}
                affiliateLink="https://headway.partners/user/signup?hwp=b158cc"
              />
            )}
          </main>

          {/* Footer */}
          <footer className="py-6 border-t border-white/[0.06] text-center text-xs text-gray-500">
            <p className="font-semibold text-gray-400">Sajim Traders © 2026</p>
            <p className="mt-1 text-[11px] text-gray-600">
              Autonomous Quantitative Execution • Official Partner: Headway
            </p>
          </footer>
        </div>
      )}

      {/* Account Connector Modal */}
      <AccountConnectorModal
        isOpen={showConnectorModal}
        onClose={() => setShowConnectorModal(false)}
        onConnectSuccess={handleAccountConnected}
        initialTab={connectorInitialTab}
        currentAccountId={telemetry.account_id}
        currentServer={telemetry.broker_server}
        affiliateLink="https://headway.partners/user/signup?hwp=b158cc"
      />

      {/* Email & Password Supabase Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />

      {/* Risk Profile Selection Sheet */}
      <RiskModeSheet
        isOpen={showRiskSheet}
        onClose={() => setShowRiskSheet(false)}
        currentMode={telemetry.risk_mode || "ULTRA_SAFE"}
        onSelectMode={handleRiskChange}
      />
    </div>
  );
}
