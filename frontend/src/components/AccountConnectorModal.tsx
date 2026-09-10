"use client";

import React, { useState } from "react";
import Image from "next/image";
import { X, ArrowRight, Shield, Zap, Sparkles } from "lucide-react";

interface AccountConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectSuccess: (accountData: any) => void;
  initialTab?: "DEMO" | "REAL" | "demo" | "real";
  affiliateLink?: string;
}

export const AccountConnectorModal: React.FC<AccountConnectorModalProps> = ({
  isOpen,
  onClose,
  onConnectSuccess,
  initialTab = "DEMO",
  affiliateLink = "https://headway.partners/user/signup?hwp=b158cc",
}) => {
  const normalizedInitial = initialTab.toUpperCase() as "DEMO" | "REAL";
  const [activeTab, setActiveTab] = useState<"DEMO" | "REAL">(normalizedInitial);
  const [server, setServer] = useState(normalizedInitial === "DEMO" ? "Headway-Demo" : "Headway-Real");
  const [login, setLogin] = useState(normalizedInitial === "DEMO" ? "1200442972" : "");
  const [password, setPassword] = useState(normalizedInitial === "DEMO" ? "demo1234" : "");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handleTabSwitch = (tab: "DEMO" | "REAL") => {
    setActiveTab(tab);
    setErrorMsg("");
    if (tab === "DEMO") {
      setServer("Headway-Demo");
      setLogin("1200442972");
      setPassword("demo1234");
    } else {
      setServer("Headway-Real");
      setLogin("");
      setPassword("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");

    if (activeTab === "DEMO") {
      // Instant client-side demo initialization
      setTimeout(() => {
        setLoading(false);
        onConnectSuccess({
          account_id: login || "1200442972",
          account_name: "Free Demo Trader",
          broker_server: server,
          autopilot_enabled: true,
          balance: 50.0,
          equity: 52.6,
          free_margin: 49.8,
          today_pnl: 15.2,
          today_pnl_percent: 30.4,
          currency: "USD",
          terminal_connected: true,
          is_demo: true,
          open_positions: [],
        });
        onClose();
      }, 500);
      return;
    }

    try {
      const res = await fetch("/api/client/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: login,
          broker_server: server,
          password: password,
          autopilot_enabled: true,
          risk_mode: "MICRO_FIXED",
        }),
      });

      const data = await res.json();
      if (data.success) {
        onConnectSuccess(data.account || { account_id: login, broker_server: server });
        onClose();
      } else {
        setErrorMsg(data.error || "Failed to verify broker login. Check credentials.");
      }
    } catch (err: any) {
      setErrorMsg("Network error connecting to broker: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-sm bg-[#0d121c] border border-white/10 rounded-2xl p-6 shadow-2xl relative">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="relative w-8 h-8 rounded-lg overflow-hidden border border-emerald-500/30 bg-white p-0.5">
              <Image
                src="/assets/sajim_logo.png"
                alt="Sajim Logo"
                width={32}
                height={32}
                className="object-contain w-full h-full"
              />
            </div>
            <h3 className="font-extrabold text-sm text-white">Connect Trading Account</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 2 Options Tabs */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <button
            type="button"
            onClick={() => handleTabSwitch("DEMO")}
            className={`p-2.5 rounded-xl border text-center transition-all ${
              activeTab === "DEMO"
                ? "bg-emerald-500/15 border-emerald-500/50 text-white"
                : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            <span className="block text-[10px] font-extrabold text-emerald-400">★ RECOMMENDED</span>
            <strong className="block text-xs font-bold">Option 1: FREE DEMO</strong>
            <small className="block text-[10px] text-slate-400">Zero capital risk</small>
          </button>

          <button
            type="button"
            onClick={() => handleTabSwitch("REAL")}
            className={`p-2.5 rounded-xl border text-center transition-all ${
              activeTab === "REAL"
                ? "bg-sky-500/15 border-sky-500/50 text-white"
                : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            <span className="block text-[10px] font-extrabold text-sky-400">REAL CAPITAL</span>
            <strong className="block text-xs font-bold">Option 2: REAL ACC</strong>
            <small className="block text-[10px] text-slate-400">Trade live profits</small>
          </button>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 text-left">
          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1">Broker Server</label>
            <select
              value={server}
              onChange={(e) => setServer(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-400"
            >
              <option value="Headway-Real">Headway-Real (Official Partner)</option>
              <option value="Headway-Demo">Headway-Demo (Practice Server)</option>
              <option value="Exness-Real">Exness-Real</option>
              <option value="JustMarkets-Real">JustMarkets-Real</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1">MT5 Login Number</label>
            <input
              type="number"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="e.g. 17537803"
              required
              className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-sky-400"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1">MT5 Master Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-sky-400"
            />
          </div>

          {/* Headway Callout */}
          <div className="bg-sky-500/5 border border-sky-500/20 rounded-xl p-3 text-center">
            <span className="block text-[10px] font-extrabold text-sky-400">DON&apos;T HAVE AN ACCOUNT YET?</span>
            <p className="text-[11px] text-slate-300 my-1">
              Create an account under our official partnership in 60 seconds.
            </p>
            <a
              href={affiliateLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 w-full py-1.5 bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 rounded-lg text-sky-200 text-xs font-bold transition-colors"
            >
              👉 Open Account on Headway (Takes 1 min)
              <ArrowRight className="w-3 h-3" />
            </a>
            <span className="block text-[10px] text-slate-500 mt-1">
              ⚡ 1:2000 Leverage • Instant M-Pesa Deposits & Withdrawals
            </span>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white font-extrabold text-xs rounded-xl shadow-[0_4px_15px_rgba(16,185,129,0.3)] transition-all disabled:opacity-50"
          >
            {loading ? "CONNECTING TO BROKER..." : "⚡ CONNECT & LAUNCH COCKPIT"}
          </button>
        </form>

      </div>
    </div>
  );
};
