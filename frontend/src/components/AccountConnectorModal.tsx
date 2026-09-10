"use client";

import React, { useState } from "react";
import { X, ArrowRight, Zap, Shield } from "lucide-react";

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
      setTimeout(() => {
        setLoading(false);
        onConnectSuccess({
          account_id: login || "1200442972",
          account_name: "Free Demo Trader",
          broker_server: server,
          autopilot_enabled: true,
          balance: 10000.0,
          equity: 10084.35,
          free_margin: 9950.0,
          today_pnl: 84.35,
          today_pnl_percent: 0.84,
          currency: "USD",
          terminal_connected: true,
          is_demo: true,
          open_positions: [],
        });
        onClose();
      }, 400);
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
          risk_mode: "ULTRA_SAFE",
        }),
      });

      const data = await res.json();
      if (data.success) {
        onConnectSuccess(data.account || { account_id: login, broker_server: server, is_demo: false });
        onClose();
      } else {
        setErrorMsg(data.error || "Failed to verify broker login. Check MT5 credentials.");
      }
    } catch (err: any) {
      setErrorMsg("Connection error reaching broker gateway: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-fadeUp"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-sm bg-[#111111] border border-white/[0.08] rounded-3xl p-6 shadow-2xl relative text-white">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400">
              <Zap className="w-4 h-4 fill-current" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white leading-tight">Connect Trading Account</h3>
              <p className="text-[10px] text-gray-500">Secure MT5 Protocol</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-white p-1.5 rounded-full hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 2 Options Tabs */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <button
            type="button"
            onClick={() => handleTabSwitch("DEMO")}
            className={`p-2.5 rounded-2xl border text-center transition-all cursor-pointer ${
              activeTab === "DEMO"
                ? "bg-green-500/15 border-green-500/50 text-white shadow-[0_0_15px_rgba(34,197,94,0.15)]"
                : "bg-black/40 border-white/[0.06] text-gray-500 hover:text-gray-300"
            }`}
          >
            <span className="block text-[9px] font-extrabold text-green-400 uppercase tracking-wider">★ Free</span>
            <strong className="block text-xs font-bold mt-0.5">Option 1: Demo</strong>
            <small className="block text-[10px] text-gray-500">Zero capital risk</small>
          </button>

          <button
            type="button"
            onClick={() => handleTabSwitch("REAL")}
            className={`p-2.5 rounded-2xl border text-center transition-all cursor-pointer ${
              activeTab === "REAL"
                ? "bg-sky-500/15 border-sky-500/50 text-white shadow-[0_0_15px_rgba(56,189,248,0.15)]"
                : "bg-black/40 border-white/[0.06] text-gray-500 hover:text-gray-300"
            }`}
          >
            <span className="block text-[9px] font-extrabold text-sky-400 uppercase tracking-wider">Real Capital</span>
            <strong className="block text-xs font-bold mt-0.5">Option 2: Real MT5</strong>
            <small className="block text-[10px] text-gray-500">Trade live profits</small>
          </button>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 text-left">
          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Broker Server</label>
            <select
              value={server}
              onChange={(e) => setServer(e.target.value)}
              className="w-full bg-black/60 border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs font-mono text-white focus:outline-none focus:border-green-500 transition-colors"
            >
              <option value="Headway-Real">Headway-Real (Official Partner)</option>
              <option value="Headway-Demo">Headway-Demo (Practice Server)</option>
              <option value="Exness-Real">Exness-Real</option>
              <option value="JustMarkets-Real">JustMarkets-Real</option>
              <option value="JustMarkets-Demo3">JustMarkets-Demo3</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">MT5 Login Number</label>
            <input
              type="number"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="e.g. 17537803"
              required
              className="w-full bg-black/60 border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs font-mono text-white placeholder-gray-600 focus:outline-none focus:border-green-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">MT5 Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="w-full bg-black/60 border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs font-mono text-white placeholder-gray-600 focus:outline-none focus:border-green-500 transition-colors"
            />
          </div>

          {/* Headway Quick Referral */}
          <div className="bg-black/30 border border-white/[0.06] rounded-2xl p-3 text-center">
            <span className="block text-[10px] font-bold text-green-400 uppercase tracking-wider">
              Need a new MT5 account?
            </span>
            <p className="text-[11px] text-gray-400 my-1">
              Create an account with Headway in 60s for 1:2000 leverage & instant M-Pesa.
            </p>
            <a
              href={affiliateLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 w-full py-1.5 bg-white/5 hover:bg-white/10 border border-white/[0.08] rounded-xl text-white text-xs font-bold transition-colors cursor-pointer"
            >
              <span>👉 Open Headway Account</span>
              <ArrowRight className="w-3 h-3 text-green-400" />
            </a>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-black font-extrabold text-xs rounded-2xl shadow-[0_4px_20px_rgba(34,197,94,0.3)] transition-all disabled:opacity-50 cursor-pointer active:scale-[0.98]"
          >
            {loading ? "VERIFYING WITH BROKER..." : "⚡ CONNECT & LAUNCH COCKPIT"}
          </button>
        </form>
      </div>
    </div>
  );
};
