"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AccountTelemetry,
  AuthUser,
  ClientSignal,
  ClientTrade,
  GateStats,
  RiskMode,
} from "../lib/types";
import { DEMO_TELEMETRY, EMPTY_TELEMETRY } from "../lib/constants";
import { api } from "../lib/api";
import { supabaseAuth } from "../lib/supabase";
import { storage } from "../lib/storage";
import { trackAction } from "../lib/logger";
import { usePolling } from "./usePolling";

const POLL_INTERVAL_MS = 3500;
const TOAST_DURATION_MS = 4000;

function buildPosition(
  signal: ClientSignal,
  telemetry: AccountTelemetry,
  ticket?: number,
  volume?: number,
  price?: number
): ClientTrade {
  return {
    ticket: ticket ?? Math.floor(1_000_000 + Math.random() * 9_000_000),
    symbol: signal.symbol,
    type: signal.action,
    volume: volume ?? (telemetry.is_demo ? 0.05 : 0.01),
    open_price: price ?? signal.entry,
    current_price: price ?? signal.entry,
    sl: signal.sl,
    tp: signal.tp,
    pnl: 0,
    time: new Date().toLocaleTimeString(),
    comment: telemetry.is_demo ? "DEMO_1TAP" : "BEEP_1TAP",
  };
}

export function useCockpit() {
  const [isMounted, setIsMounted] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showConnectorModal, setShowConnectorModal] = useState(false);
  const [connectorTab, setConnectorTab] = useState<"demo" | "real">("demo");
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showRiskSheet, setShowRiskSheet] = useState(false);

  const [telemetry, setTelemetry] = useState<AccountTelemetry>(EMPTY_TELEMETRY);
  const [signals, setSignals] = useState<ClientSignal[]>([]);
  const [gateStats, setGateStats] = useState<GateStats | null>(null);

  const [isTogglingAutoPilot, setIsTogglingAutoPilot] = useState(false);
  const [isClosingTrade, setIsClosingTrade] = useState(false);
  const [isExecutingSignal, setIsExecutingSignal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [toast, setToast] = useState<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const signalsSectionRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), TOAST_DURATION_MS);
  }, []);

  // Restore a persisted session on first client mount.
  useEffect(() => {
    if (storage.isAuthenticated()) {
      const saved = storage.getAccount();
      if (saved) {
        setTelemetry({
          ...(saved.is_demo ? DEMO_TELEMETRY : EMPTY_TELEMETRY),
          ...saved,
        });
      }
      setIsAuthenticated(true);
    }
    setIsMounted(true);
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  // Handle Supabase OAuth redirect callback (#access_token=...).
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (!hash || !hash.includes("access_token=")) return;

    trackAction("OAUTH_CALLBACK_DETECTED");
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const accessToken = params.get("access_token");
    if (!accessToken) return;

    supabaseAuth.getUser(accessToken).then((user) => {
      if (!user) return;
      const email = user.email || "";
      const fullName = user.user_metadata?.full_name || email.split("@")[0] || "Trader";
      const account: AccountTelemetry = { ...EMPTY_TELEMETRY, account_name: fullName };
      setTelemetry(account);
      setIsAuthenticated(true);
      storage.setAuthenticated(true);
      storage.setAccount(account);
      showToast(`🎉 Welcome, ${fullName}!`);
      trackAction("GOOGLE_SIGNIN_SUCCESS", { email, id: user.id });
      window.history.replaceState(null, "", window.location.pathname);
    });
  }, [showToast]);

  // Load aggregated portfolio stats once on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await api.getStatus();
      if (cancelled) return;
      if (res.ok) {
        const d = res.data;
        setGateStats({
          system_online: d.system_online ?? false,
          today_pnl: typeof d.pnl?.combined_daily_net === "number" ? d.pnl.combined_daily_net : null,
          active_trades:
            typeof d.concurrency?.total_open === "number" ? d.concurrency.total_open : null,
        });
      } else {
        setGateStats({ system_online: false, today_pnl: null, active_trades: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const fetchTelemetry = useCallback(async () => {
    // Demo mode is fully local — never overwrite the virtual balance.
    if (telemetry.is_demo) return;
    // No linked account yet — do not fetch the operator's account.
    if (telemetry.account_id === "NEW" || telemetry.broker_server === "None") return;

    const res = await api.getAccount(telemetry.account_id);
    if (!res.ok) return;
    const data = res.data;
    if (!data.account_id) return;

    setTelemetry((prev) => ({
      ...prev,
      ...data,
      account_name: prev.account_name || data.account_name,
      is_demo: prev.is_demo,
    }));
  }, [telemetry.is_demo, telemetry.account_id, telemetry.broker_server]);

  const fetchSignals = useCallback(async () => {
    const res = await api.getSignals();
    if (!res.ok) return;
    setSignals(Array.isArray(res.data.signals) ? res.data.signals : []);
  }, []);

  usePolling(
    () => {
      void fetchTelemetry();
      void fetchSignals();
    },
    POLL_INTERVAL_MS,
    isAuthenticated
  );

  const handleLaunchDemo = useCallback(() => {
    const demo = { ...DEMO_TELEMETRY };
    setTelemetry(demo);
    setIsAuthenticated(true);
    storage.setAuthenticated(true);
    storage.setAccount(demo);
    showToast("🎉 Free Demo Cockpit Activated ($10,000 USD virtual equity)");
    trackAction("CLICK_START_DEMO", { balance: 10000, is_demo: true });
  }, [showToast]);

  const handleGoogleSignIn = useCallback(() => {
    trackAction("CLICK_GOOGLE_AUTH");
    supabaseAuth.signInWithOAuth("google");
  }, []);

  const handleToggleAutoPilot = useCallback(async () => {
    if (isTogglingAutoPilot) return;
    const nextState = !telemetry.autopilot_enabled;
    setIsTogglingAutoPilot(true);
    setTelemetry((prev) => ({ ...prev, autopilot_enabled: nextState }));
    trackAction("TOGGLE_AUTOPILOT", { enabled: nextState, is_demo: telemetry.is_demo });

    // Demo / unlinked accounts toggle locally only.
    if (telemetry.is_demo || telemetry.account_id === "NEW") {
      setIsTogglingAutoPilot(false);
      showToast(nextState ? "⚡ Auto-Pilot Activated (Demo)" : "⏸️ Auto-Pilot Paused (Demo)");
      return;
    }

    const res = await api.toggleAutopilot(telemetry.account_id, nextState);
    setIsTogglingAutoPilot(false);

    if (!res.ok) {
      setTelemetry((prev) => ({ ...prev, autopilot_enabled: !nextState }));
      showToast(`❌ Network error toggling Auto-Pilot: ${res.error}`);
    } else if (res.data.success === false) {
      setTelemetry((prev) => ({ ...prev, autopilot_enabled: !nextState }));
      showToast(`❌ Auto-Pilot error: ${res.data.error || "Server rejected toggle"}`);
    } else {
      showToast(
        nextState
          ? "⚡ Auto-Pilot Activated: BEEP Engine scanning markets"
          : "⏸️ Auto-Pilot Paused: Manual oversight mode"
      );
    }
  }, [isTogglingAutoPilot, telemetry.autopilot_enabled, telemetry.is_demo, telemetry.account_id, showToast]);

  const handleRiskChange = useCallback(
    async (mode: RiskMode) => {
      const updated: AccountTelemetry = { ...telemetry, risk_mode: mode };
      setTelemetry(updated);
      storage.setAccount(updated);
      trackAction("CHANGE_RISK_MODE", { mode });
      showToast(`🛡️ Risk Mode updated: ${mode.replace(/_/g, " ")}`);

      // Persist server-side only for a linked real account.
      if (telemetry.is_demo || telemetry.account_id === "NEW" || telemetry.broker_server === "None") {
        return;
      }
      await api.connect({
        account_id: telemetry.account_id,
        broker_server: telemetry.broker_server,
        account_name: telemetry.account_name,
        currency: telemetry.currency,
        risk_mode: mode,
      });
    },
    [telemetry, showToast]
  );

  const handleClosePosition = useCallback(
    async (ticket: number) => {
      setIsClosingTrade(true);
      trackAction("CLOSE_POSITION", { ticket, is_demo: telemetry.is_demo });

      // Demo positions are simulated locally — no broker call.
      if (telemetry.is_demo) {
        setTelemetry((prev) => ({
          ...prev,
          open_positions: prev.open_positions.filter((p) => p.ticket !== ticket),
          floating_pnl: 0,
        }));
        setIsClosingTrade(false);
        showToast(`✅ Demo Trade #${ticket} closed`);
        return;
      }

      const res = await api.closeTrade(ticket);
      setIsClosingTrade(false);

      if (res.ok && res.data.success) {
        setTelemetry((prev) => ({
          ...prev,
          open_positions: prev.open_positions.filter((p) => p.ticket !== ticket),
          floating_pnl: 0,
        }));
        showToast(`✅ Trade #${ticket} closed successfully`);
      } else {
        showToast(`❌ Failed to close Trade #${ticket}: ${res.ok ? res.data.error : res.error}`);
      }
    },
    [telemetry.is_demo, showToast]
  );

  const handleExecuteSignal = useCallback(
    async (signal: ClientSignal): Promise<boolean> => {
      setIsExecutingSignal(true);
      trackAction("EXECUTE_1TAP_SIGNAL", {
        symbol: signal.symbol,
        action: signal.action,
        entry: signal.entry,
        is_demo: telemetry.is_demo,
      });

      try {
        if (!telemetry.is_demo && telemetry.account_id !== "NEW") {
          const res = await api.execute({
            account_id: telemetry.account_id,
            symbol: signal.symbol,
            action: signal.action,
            volume: telemetry.is_demo ? 0.05 : 0.01,
            sl: signal.sl,
            tp: signal.tp,
            comment: `Sajim_${signal.action}`,
          });

          if (res.ok && res.data.success) {
            if (res.data.status === "QUEUED_FOR_BRIDGE") {
              showToast(`⚡ Order queued for MT5 Bridge: ${signal.action} ${signal.symbol}`);
              return true;
            }
            const position = buildPosition(
              signal,
              telemetry,
              res.data.ticket,
              res.data.volume,
              res.data.price
            );
            setTelemetry((prev) => ({
              ...prev,
              open_positions: [position, ...prev.open_positions],
            }));
            showToast(`🚀 1-Tap Order Filled: ${signal.action} ${signal.symbol} (Ticket #${position.ticket})`);
            return true;
          }

          showToast(`❌ 1-Tap Execution Failed: ${res.ok ? res.data.error || "Broker rejected order" : res.error}`);
          return false;
        }

        // Demo / unlinked account: simulate locally.
        const position = buildPosition(signal, telemetry);
        setTelemetry((prev) => ({
          ...prev,
          open_positions: [position, ...prev.open_positions],
        }));
        showToast(`🚀 [Demo] 1-Tap Order Filled: ${signal.action} ${signal.symbol}`);
        return true;
      } catch (err) {
        showToast(`❌ Execution error reaching broker: ${err instanceof Error ? err.message : "Unknown error"}`);
        return false;
      } finally {
        setIsExecutingSignal(false);
      }
    },
    [telemetry, showToast]
  );

  const handleAccountConnected = useCallback(
    (account: Partial<AccountTelemetry>) => {
      const isDemo = Boolean(account.is_demo);
      const updated: AccountTelemetry = isDemo
        ? { ...DEMO_TELEMETRY, account_name: account.account_name || DEMO_TELEMETRY.account_name }
        : {
            ...EMPTY_TELEMETRY,
            ...account,
            is_demo: false,
            terminal_connected: true,
          };

      setTelemetry(updated);
      setIsAuthenticated(true);
      storage.setAuthenticated(true);
      storage.setAccount(updated);
      setShowConnectorModal(false);
      showToast(`🤝 Connected: ${updated.broker_server} (#${updated.account_id})`);
      trackAction("ACCOUNT_CONNECTED", {
        broker: updated.broker_server,
        id: updated.account_id,
        is_demo: updated.is_demo,
      });

      // Pull fresh live telemetry for a newly linked real account.
      if (!isDemo && updated.account_id && updated.account_id !== "NEW") {
        void fetchTelemetry();
      }
    },
    [showToast, fetchTelemetry]
  );

  const handleAuthSuccess = useCallback(
    (user: AuthUser) => {
      const account: AccountTelemetry = { ...EMPTY_TELEMETRY, account_name: user.fullName };
      setTelemetry(account);
      setIsAuthenticated(true);
      storage.setAuthenticated(true);
      storage.setAccount(account);
      showToast(`🎉 Welcome, ${user.fullName}!`);
      trackAction("USER_AUTHENTICATED", { email: user.email, id: user.id });
    },
    [showToast]
  );

  const handleExitToGate = useCallback(() => {
    setIsAuthenticated(false);
    storage.clear();
    setTelemetry(EMPTY_TELEMETRY);
    setSignals([]);
    showToast("👋 Signed out successfully");
  }, [showToast]);

  const handleManualRefresh = useCallback(async () => {
    setIsRefreshing(true);
    trackAction("MANUAL_SYNC_TRIGGERED");
    await Promise.all([fetchTelemetry(), fetchSignals()]);
    setIsRefreshing(false);
    showToast("🟢 Telemetry & Signals Synchronized");
  }, [fetchTelemetry, fetchSignals, showToast]);

  const openConnector = useCallback(() => {
    setConnectorTab("demo");
    setShowConnectorModal(true);
  }, []);

  const openConnectorReal = useCallback(() => {
    trackAction("OPEN_CONNECT_MODAL");
    setConnectorTab("real");
    setShowConnectorModal(true);
  }, []);

  const closeConnector = useCallback(() => setShowConnectorModal(false), []);
  const openAuth = useCallback(() => setShowAuthModal(true), []);
  const closeAuth = useCallback(() => setShowAuthModal(false), []);
  const openRiskSheet = useCallback(() => setShowRiskSheet(true), []);
  const closeRiskSheet = useCallback(() => setShowRiskSheet(false), []);

  const handleScrollToSignals = useCallback(() => {
    signalsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  return {
    // UI state
    isMounted,
    isAuthenticated,
    telemetry,
    signals,
    gateStats,
    toast,
    // modal / sheet state
    showConnectorModal,
    connectorTab,
    showAuthModal,
    showRiskSheet,
    // busy flags
    isTogglingAutoPilot,
    isClosingTrade,
    isExecutingSignal,
    isRefreshing,
    // refs
    signalsSectionRef,
    // actions
    showToast,
    openConnector,
    openConnectorReal,
    closeConnector,
    openAuth,
    closeAuth,
    openRiskSheet,
    closeRiskSheet,
    onLaunchDemo: handleLaunchDemo,
    onGoogleSignIn: handleGoogleSignIn,
    onToggleAutoPilot: handleToggleAutoPilot,
    onRiskChange: handleRiskChange,
    onClosePosition: handleClosePosition,
    onExecuteSignal: handleExecuteSignal,
    onAccountConnected: handleAccountConnected,
    onAuthSuccess: handleAuthSuccess,
    onExitToGate: handleExitToGate,
    onRefresh: handleManualRefresh,
    onScrollToSignals: handleScrollToSignals,
  };
}
