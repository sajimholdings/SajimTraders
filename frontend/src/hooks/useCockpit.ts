"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AccountTelemetry,
  AuthMode,
  AuthUser,
  ClientSignal,
  ClientTrade,
  GateStats,
  RiskMode,
} from "../lib/types";
import { DEMO_SIGNALS, DEMO_TELEMETRY, EMPTY_TELEMETRY } from "../lib/constants";
import { api } from "../lib/api";
import { isSupabaseConfigured, SUPABASE_CONFIG_ERROR, supabaseAuth } from "../lib/supabase";
import {
  expireSession,
  onSessionExpired,
  restoreSession,
  sessionFromHash,
  signOutSession,
} from "../lib/session";
import { storage } from "../lib/storage";
import { trackAction } from "../lib/logger";
import { usePolling } from "./usePolling";

const POLL_INTERVAL_MS = 3500;
const TOAST_DURATION_MS = 4000;

export const SESSION_EXPIRED_NOTICE = "Your session expired, please sign in again.";

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

function isLinkedAccount(t: AccountTelemetry): boolean {
  return !t.is_demo && t.account_id !== "NEW" && t.broker_server !== "None";
}

export function useCockpit() {
  const [isMounted, setIsMounted] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // Polling for real users waits until a restored session has been validated.
  const [sessionReady, setSessionReady] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [showConnectorModal, setShowConnectorModal] = useState(false);
  const [connectorTab, setConnectorTab] = useState<"demo" | "real">("demo");
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("signup");
  const [showRiskSheet, setShowRiskSheet] = useState(false);

  const [telemetry, setTelemetryState] = useState<AccountTelemetry>(EMPTY_TELEMETRY);
  const [signals, setSignals] = useState<ClientSignal[]>([]);
  const [gateStats, setGateStats] = useState<GateStats | null>(null);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);
  const [signalsError, setSignalsError] = useState<string | null>(null);

  const [isTogglingAutoPilot, setIsTogglingAutoPilot] = useState(false);
  const [isClosingTrade, setIsClosingTrade] = useState(false);
  const [isExecutingSignal, setIsExecutingSignal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [toast, setToast] = useState<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const signalsSectionRef = useRef<HTMLDivElement>(null);

  // Latest telemetry for async callbacks (avoids stale closures).
  const telemetryRef = useRef<AccountTelemetry>(EMPTY_TELEMETRY);
  // Bumped on sign-in, sign-out, session expiry and account switch. Responses
  // started under an older generation are discarded, and polling restarts.
  const sessionGenRef = useRef(0);
  const [sessionGen, setSessionGen] = useState(0);
  const executingRef = useRef(false);

  const setTelemetry = useCallback(
    (next: AccountTelemetry | ((prev: AccountTelemetry) => AccountTelemetry)) => {
      if (typeof next === "function") {
        setTelemetryState((prev) => {
          const value = next(prev);
          telemetryRef.current = value;
          return value;
        });
      } else {
        telemetryRef.current = next;
        setTelemetryState(next);
      }
    },
    []
  );

  const bumpSessionGen = useCallback(() => {
    sessionGenRef.current += 1;
    setSessionGen(sessionGenRef.current);
  }, []);

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), TOAST_DURATION_MS);
  }, []);

  const resetToGate = useCallback(() => {
    bumpSessionGen();
    setIsAuthenticated(false);
    setSessionReady(false);
    setTelemetry(EMPTY_TELEMETRY);
    setSignals([]);
    setTelemetryError(null);
    setSignalsError(null);
  }, [bumpSessionGen, setTelemetry]);

  // A session that cannot be refreshed: drop to the gate with a clear notice.
  const handleSessionExpired = useCallback(() => {
    if (telemetryRef.current.is_demo) return;
    storage.clear();
    resetToGate();
    setSessionExpired(true);
    showToast(`🔒 ${SESSION_EXPIRED_NOTICE}`);
    trackAction("SESSION_EXPIRED");
  }, [resetToGate, showToast]);

  useEffect(() => onSessionExpired(handleSessionExpired), [handleSessionExpired]);

  // After auth, auto-load the user's first registered MT5 account (if any) so the
  // live balance/equity shows without requiring a manual "Connect" step.
  const loadUserAccounts = useCallback(async () => {
    const gen = sessionGenRef.current;
    const listRes = await api.getAccounts();
    if (gen !== sessionGenRef.current || !listRes.ok) return;
    const accounts = Array.isArray(listRes.data.accounts) ? listRes.data.accounts : [];
    if (accounts.length === 0) return;
    const first = accounts[0];
    const accountId = String(first.account_id ?? "");
    if (!accountId) return;

    const accRes = await api.getAccount(accountId);
    if (gen !== sessionGenRef.current || !accRes.ok) return;
    const d = accRes.data as AccountTelemetry;
    const updated: AccountTelemetry = {
      ...EMPTY_TELEMETRY,
      ...d,
      account_id: String(d.account_id ?? accountId),
      account_name: d.account_name || first.account_name || "Trader",
      broker_server: d.broker_server || first.broker_server || "None",
      is_demo: false,
      terminal_connected: Boolean(d.terminal_connected),
      today_pnl: Number(d.today_pnl ?? 0),
      today_pnl_percent: Number(d.today_pnl_percent ?? 0),
      open_positions: Array.isArray(d.open_positions) ? d.open_positions : [],
    };
    setTelemetry(updated);
    storage.setAccount(updated);
    bumpSessionGen();
  }, [setTelemetry, bumpSessionGen]);

  // Restore a persisted session on first client mount, validating it with
  // Supabase (/auth/v1/user, refreshing if needed) before trusting it.
  useEffect(() => {
    // OAuth redirects are handled by the callback effect below.
    const isOAuthCallback =
      typeof window !== "undefined" && window.location.hash.includes("access_token=");
    const saved = storage.getAccount();
    const hasSession = Boolean(storage.getSession());
    let cancelled = false;

    if (!isOAuthCallback) {
      if (hasSession) {
        setTelemetry({ ...EMPTY_TELEMETRY, ...(saved && !saved.is_demo ? saved : {}), is_demo: false });
        setIsAuthenticated(true);
        void restoreSession().then((result) => {
          if (cancelled) return;
          if (result.status === "valid") {
            setSessionReady(true);
            if (!saved || saved.is_demo || saved.account_id === "NEW") void loadUserAccounts();
          } else if (result.status === "offline") {
            // Keep the session; polling will surface the connectivity error.
            setSessionReady(true);
          }
          // "expired": expireSession() already notified handleSessionExpired.
        });
      } else if (saved?.is_demo) {
        setTelemetry({ ...DEMO_TELEMETRY, ...saved, is_demo: true });
        setIsAuthenticated(true);
      } else if (saved) {
        // A real account persisted without a usable session (e.g. from an
        // older build that only stored the access token): ask to sign in again.
        storage.clear();
        setSessionExpired(true);
      }
    }
    setIsMounted(true);
    return () => {
      cancelled = true;
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
    // Mount-only: restoring must not re-run when callbacks change identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle Supabase OAuth redirect callback (#access_token=...).
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (!hash || !hash.includes("access_token=")) return;

    // Remove tokens from the URL before anything else (logging, analytics).
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    trackAction("OAUTH_CALLBACK_DETECTED");

    const session = sessionFromHash(hash);
    if (!session) return;
    storage.setSession(session);
    let cancelled = false;

    supabaseAuth
      .getUser(session.access_token)
      .then((user) => {
        if (cancelled) return;
        if (!user) {
          expireSession(); // notifies handleSessionExpired via onSessionExpired
          return;
        }
        const email = user.email || "";
        const fullName = user.user_metadata?.full_name || email.split("@")[0] || "Trader";
        const account: AccountTelemetry = { ...EMPTY_TELEMETRY, account_name: fullName };
        bumpSessionGen();
        setTelemetry(account);
        setIsAuthenticated(true);
        setSessionReady(true);
        setSessionExpired(false);
        storage.setAccount(account);
        void loadUserAccounts();
        showToast(`🎉 Welcome, ${fullName}!`);
        trackAction("GOOGLE_SIGNIN_SUCCESS", { id: user.id });
      })
      .catch(() => {
        if (cancelled) return;
        storage.clearSession();
        showToast("❌ Could not reach the sign-in server. Please try again.");
      });
    return () => {
      cancelled = true;
    };
  }, [showToast, loadUserAccounts, bumpSessionGen, setTelemetry]);

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

  /**
   * Pull live telemetry for `accountId` (defaults to the current account).
   * Responses are discarded if the session generation or account changed
   * while the request was in flight.
   */
  const fetchTelemetry = useCallback(
    async (accountId?: string, signal?: AbortSignal) => {
      const current = telemetryRef.current;
      // Demo mode is fully local — never overwrite the virtual balance.
      // No linked account yet — do not fetch the operator's account.
      if (!accountId && !isLinkedAccount(current)) return;
      const targetId = accountId || current.account_id;
      const gen = sessionGenRef.current;

      const res = await api.getAccount(targetId, signal);
      if (gen !== sessionGenRef.current || telemetryRef.current.account_id !== targetId) return;
      if (!res.ok) {
        if (res.aborted || res.status === 401) return; // 401 → session-expired flow
        setTelemetryError(res.error);
        return;
      }
      setTelemetryError(null);
      const data = res.data;
      if (!data.account_id || String(data.account_id) !== targetId) return;

      setTelemetry((prev) => ({
        ...prev,
        ...data,
        account_id: targetId,
        account_name: prev.account_name || data.account_name,
        is_demo: prev.is_demo,
      }));
    },
    [setTelemetry]
  );

  const fetchSignals = useCallback(async (signal?: AbortSignal) => {
    // Demo users are not signed in: never call the authenticated feed.
    if (telemetryRef.current.is_demo) {
      setSignals(DEMO_SIGNALS);
      setSignalsError(null);
      return;
    }
    const gen = sessionGenRef.current;
    const res = await api.getSignals(signal);
    if (gen !== sessionGenRef.current) return;
    if (!res.ok) {
      if (res.aborted || res.status === 401) return;
      setSignalsError(res.error);
      return;
    }
    setSignalsError(null);
    setSignals(Array.isArray(res.data.signals) ? res.data.signals : []);
  }, []);

  usePolling(
    async (signal) => {
      await Promise.all([fetchTelemetry(undefined, signal), fetchSignals(signal)]);
    },
    POLL_INTERVAL_MS,
    isAuthenticated && (telemetry.is_demo || sessionReady),
    sessionGen
  );

  const handleLaunchDemo = useCallback(() => {
    const demo = { ...DEMO_TELEMETRY };
    bumpSessionGen();
    setTelemetry(demo);
    setSignals(DEMO_SIGNALS);
    setIsAuthenticated(true);
    setSessionExpired(false);
    storage.setAccount(demo);
    showToast("🎉 Free Demo Cockpit Activated ($10,000 USD virtual equity)");
    trackAction("CLICK_START_DEMO", { balance: 10000, is_demo: true });
  }, [showToast, bumpSessionGen, setTelemetry]);

  const handleGoogleSignIn = useCallback(() => {
    trackAction("CLICK_GOOGLE_AUTH");
    if (!supabaseAuth.signInWithOAuth("google")) showToast(`❌ ${SUPABASE_CONFIG_ERROR}`);
  }, [showToast]);

  const handleToggleAutoPilot = useCallback(async () => {
    if (isTogglingAutoPilot) return;
    const current = telemetryRef.current;
    const nextState = !current.autopilot_enabled;
    setIsTogglingAutoPilot(true);
    setTelemetry((prev) => ({ ...prev, autopilot_enabled: nextState }));
    trackAction("TOGGLE_AUTOPILOT", { enabled: nextState, is_demo: current.is_demo });

    // Demo / unlinked accounts toggle locally only.
    if (current.is_demo || current.account_id === "NEW") {
      setIsTogglingAutoPilot(false);
      showToast(nextState ? "⚡ Auto-Pilot Activated (Demo)" : "⏸️ Auto-Pilot Paused (Demo)");
      return;
    }

    const res = await api.toggleAutopilot(current.account_id, nextState);
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
  }, [isTogglingAutoPilot, showToast, setTelemetry]);

  const handleRiskChange = useCallback(
    async (mode: RiskMode) => {
      const current = telemetryRef.current;
      const previousMode = current.risk_mode;
      const updated: AccountTelemetry = { ...current, risk_mode: mode };
      setTelemetry(updated);
      storage.setAccount(updated);
      trackAction("CHANGE_RISK_MODE", { mode });

      // Persist server-side only for a linked real account.
      if (!isLinkedAccount(current)) {
        showToast(`🛡️ Risk Mode updated: ${mode.replace(/_/g, " ")}`);
        return;
      }
      const res = await api.connect({
        account_id: current.account_id,
        broker_server: current.broker_server,
        account_name: current.account_name,
        currency: current.currency,
        risk_mode: mode,
      });
      if (res.ok && res.data.success !== false) {
        showToast(`🛡️ Risk Mode updated: ${mode.replace(/_/g, " ")}`);
        return;
      }
      // Roll back if the account is still the same one.
      if (telemetryRef.current.account_id === current.account_id) {
        const reverted = { ...telemetryRef.current, risk_mode: previousMode };
        setTelemetry(reverted);
        storage.setAccount(reverted);
      }
      showToast(
        `❌ Failed to update Risk Mode: ${res.ok ? res.data.error || "Server rejected change" : res.error}`
      );
    },
    [showToast, setTelemetry]
  );

  const handleClosePosition = useCallback(
    async (ticket: number) => {
      const current = telemetryRef.current;
      setIsClosingTrade(true);
      trackAction("CLOSE_POSITION", { ticket, is_demo: current.is_demo });

      // Demo / unlinked-account positions are simulated locally — no broker
      // call (the backend requires a real account_id for close-trade).
      if (!isLinkedAccount(current)) {
        setTelemetry((prev) => ({
          ...prev,
          open_positions: prev.open_positions.filter((p) => p.ticket !== ticket),
          floating_pnl: 0,
        }));
        setIsClosingTrade(false);
        showToast(`✅ ${current.is_demo ? "Demo " : ""}Trade #${ticket} closed`);
        return;
      }

      const position = current.open_positions.find((p) => p.ticket === ticket);
      const res = await api.closeTrade(ticket, current.account_id, position?.symbol);
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
    [showToast, setTelemetry]
  );

  const handleExecuteSignal = useCallback(
    async (signal: ClientSignal): Promise<boolean> => {
      // Synchronous guard: state updates are async, so a ref blocks double taps.
      if (executingRef.current) return false;
      executingRef.current = true;
      setIsExecutingSignal(true);
      const current = telemetryRef.current;
      trackAction("EXECUTE_1TAP_SIGNAL", {
        symbol: signal.symbol,
        action: signal.action,
        entry: signal.entry,
        is_demo: current.is_demo,
      });

      try {
        if (isLinkedAccount(current)) {
          const res = await api.execute({
            account_id: current.account_id,
            symbol: signal.symbol,
            action: signal.action,
            volume: 0.01,
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
              current,
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
        const position = buildPosition(signal, current);
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
        executingRef.current = false;
        setIsExecutingSignal(false);
      }
    },
    [showToast, setTelemetry]
  );

  const handleAccountConnected = useCallback(
    (account: Partial<AccountTelemetry>) => {
      const isDemo = Boolean(account.is_demo);
      const updated: AccountTelemetry = isDemo
        ? { ...DEMO_TELEMETRY, account_name: account.account_name || DEMO_TELEMETRY.account_name }
        : {
            ...EMPTY_TELEMETRY,
            ...account,
            account_id: String(account.account_id ?? EMPTY_TELEMETRY.account_id),
            is_demo: false,
            terminal_connected: true,
          };

      // New account: cancel in-flight requests for the previous one. Bumping
      // the generation restarts polling, whose immediate tick fetches live
      // telemetry for `updated.account_id` (read from telemetryRef, which is
      // set synchronously below — no stale closure).
      bumpSessionGen();
      setTelemetry(updated);
      if (isDemo) setSignals(DEMO_SIGNALS);
      setIsAuthenticated(true);
      if (!isDemo) setSessionReady(true);
      setTelemetryError(null);
      storage.setAccount(updated);
      setShowConnectorModal(false);
      showToast(`🤝 Connected: ${updated.broker_server} (#${updated.account_id})`);
      trackAction("ACCOUNT_CONNECTED", {
        broker: updated.broker_server,
        id: updated.account_id,
        is_demo: updated.is_demo,
      });
    },
    [showToast, bumpSessionGen, setTelemetry]
  );

  const handleAuthSuccess = useCallback(
    (user: AuthUser) => {
      const account: AccountTelemetry = { ...EMPTY_TELEMETRY, account_name: user.fullName };
      bumpSessionGen();
      setTelemetry(account);
      setSignals([]);
      setIsAuthenticated(true);
      setSessionReady(true);
      setSessionExpired(false);
      storage.setAccount(account);
      void loadUserAccounts();
      showToast(`🎉 Welcome, ${user.fullName}!`);
      trackAction("USER_AUTHENTICATED", { id: user.id });
    },
    [showToast, loadUserAccounts, bumpSessionGen, setTelemetry]
  );

  const handleExitToGate = useCallback(async () => {
    const wasDemo = telemetryRef.current.is_demo;
    resetToGate();
    setSessionExpired(false);
    // Reads the session before clearing it, then revokes it server-side.
    const revoke = signOutSession();
    storage.clear();
    showToast("👋 Signed out successfully");
    trackAction("SIGN_OUT", { is_demo: wasDemo });
    await revoke;
  }, [resetToGate, showToast]);

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
  const openAuth = useCallback(() => {
    setAuthMode("signup");
    setShowAuthModal(true);
  }, []);
  const openSignIn = useCallback(() => {
    setAuthMode("signin");
    setShowAuthModal(true);
  }, []);
  const closeAuth = useCallback(() => setShowAuthModal(false), []);
  const openRiskSheet = useCallback(() => setShowRiskSheet(true), []);
  const closeRiskSheet = useCallback(() => setShowRiskSheet(false), []);
  const dismissSessionExpired = useCallback(() => setSessionExpired(false), []);

  const handleScrollToSignals = useCallback(() => {
    signalsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const connectionError = telemetryError || signalsError;

  return {
    // UI state
    isMounted,
    isAuthenticated,
    sessionExpired,
    authConfigError: isSupabaseConfigured ? null : SUPABASE_CONFIG_ERROR,
    connectionError,
    telemetry,
    signals,
    gateStats,
    toast,
    // modal / sheet state
    showConnectorModal,
    connectorTab,
    showAuthModal,
    authMode,
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
    openSignIn,
    closeAuth,
    openRiskSheet,
    closeRiskSheet,
    dismissSessionExpired,
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
