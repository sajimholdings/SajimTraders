import React from "react";
import { Rocket, Zap, ShieldCheck, Lock, CheckCircle2, ArrowRight } from "lucide-react";
import type { GateStats } from "../lib/types";
import { AFFILIATE_URL } from "../lib/constants";
import { formatSignedCurrency } from "../lib/format";

interface GateScreenProps {
  onLaunchDemo: () => void;
  onConnectReal: () => void;
  onOpenAuth: () => void;
  liveStats: GateStats | null;
  affiliateLink?: string;
}

export const GateScreen: React.FC<GateScreenProps> = ({
  onLaunchDemo,
  onConnectReal,
  onOpenAuth,
  liveStats,
  affiliateLink = AFFILIATE_URL,
}) => {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col justify-between px-4 py-8 sm:py-12 max-w-md mx-auto animate-fadeUp">
      {/* Top Section: Logo & Badge */}
      <div className="flex flex-col items-center text-center pt-4">
        <div className="relative mb-4">
          <div className="w-16 h-16 rounded-2xl overflow-hidden border-2 border-green-500/40 p-1 bg-white shadow-[0_0_25px_rgba(34,197,94,0.25)]">
            <img
              src="/assets/sajim_logo.png"
              alt="Sajim Traders Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-green-400 border-2 border-black rounded-full animate-livePulse" />
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-[11px] font-bold tracking-wider uppercase mb-5">
          <Zap className="w-3 h-3 fill-current" />
          Autonomous Quant Engine
        </span>

        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight mb-2">
          Your Money.{" "}
          <span className="text-green-400 drop-shadow-[0_0_20px_rgba(34,197,94,0.3)]">
            Working 24/7.
          </span>
        </h1>
        <p className="text-sm text-gray-500 max-w-xs leading-relaxed">
          Connect your MT5 account in 30 seconds. Zero code. 100% hands-free execution.
        </p>

        {/* Live Aggregated Telemetry Strip */}
        {liveStats && (
          <div className="grid grid-cols-3 gap-2 w-full mt-6 bg-[#111111] border border-white/[0.06] rounded-2xl p-3 text-center">
            <div>
              <span className="block text-[10px] text-gray-500 uppercase">Today P&L</span>
              <strong className="text-xs font-mono text-green-400 font-bold">
                {liveStats.today_pnl === null ? "—" : formatSignedCurrency(liveStats.today_pnl)}
              </strong>
            </div>
            <div>
              <span className="block text-[10px] text-gray-500 uppercase">Active Trades</span>
              <strong className="text-xs font-mono text-white font-bold">
                {liveStats.active_trades ?? "—"}
              </strong>
            </div>
            <div>
              <span className="block text-[10px] text-gray-500 uppercase">Engine</span>
              <strong
                className={`text-xs font-mono font-bold ${
                  liveStats.system_online ? "text-green-400" : "text-gray-500"
                }`}
              >
                {liveStats.system_online ? "LIVE" : "OFFLINE"}
              </strong>
            </div>
          </div>
        )}
      </div>

      {/* Middle Section: Zero Friction Actions */}
      <div className="my-8 space-y-3">
        <button
          type="button"
          onClick={onLaunchDemo}
          className="w-full py-4 px-5 rounded-2xl bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-black font-extrabold text-sm shadow-[0_4px_25px_rgba(34,197,94,0.3)] transition-all flex items-center justify-between group active:scale-[0.98] cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-black/10 flex items-center justify-center text-black">
              <Rocket className="w-5 h-5" />
            </div>
            <div className="text-left">
              <div className="leading-tight text-sm font-black">Start with Free Demo</div>
              <div className="text-[11px] text-emerald-950 font-semibold">
                Test with $10,000 virtual equity
              </div>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-black group-hover:translate-x-1 transition-transform" />
        </button>

        <button
          type="button"
          onClick={onOpenAuth}
          className="w-full py-3.5 px-5 rounded-2xl bg-[#111111] hover:bg-[#161616] border border-white/[0.08] hover:border-white/20 text-white font-bold text-sm transition-all flex items-center justify-between group active:scale-[0.98] cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400">
              <Lock className="w-4 h-4" />
            </div>
            <div className="text-left">
              <div className="leading-tight text-sm font-bold">Create Account / Sign In</div>
              <div className="text-[11px] text-gray-500 font-normal">
                Email & password saved to Supabase
              </div>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-500 group-hover:translate-x-1 transition-transform" />
        </button>

        <button
          type="button"
          onClick={onConnectReal}
          className="w-full py-3.5 px-5 rounded-2xl bg-[#111111] hover:bg-[#161616] border border-white/[0.08] hover:border-white/20 text-white font-bold text-sm transition-all flex items-center justify-between group active:scale-[0.98] cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Zap className="w-4 h-4 fill-current" />
            </div>
            <div className="text-left">
              <div className="leading-tight text-sm font-bold">Connect Real MT5 Account</div>
              <div className="text-[11px] text-gray-500 font-normal">
                Trade real capital with +0.35R shield
              </div>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-500 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>

      {/* Bottom Section: Headway Partner & Trust Strip */}
      <div className="space-y-4">
        <div className="bg-[#111111] border border-white/[0.06] rounded-2xl p-4 text-left">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-extrabold text-green-400 tracking-wider uppercase">
              Official Broker Partner
            </span>
            <span className="text-[11px] font-semibold text-gray-400">Headway</span>
          </div>
          <p className="text-xs text-gray-400 mb-3 leading-snug">
            Don&apos;t have an MT5 account yet? Get 1:2000 leverage & instant M-Pesa deposits.
          </p>
          <a
            href={affiliateLink}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/[0.08] text-white text-xs font-bold transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <span>👉 Open Account on Headway (Takes 1 min)</span>
            <ArrowRight className="w-3.5 h-3.5 text-green-400" />
          </a>
        </div>

        <div className="flex items-center justify-center gap-3 text-[11px] text-gray-600 font-medium py-1">
          <span className="inline-flex items-center gap-1">
            <Lock className="w-3 h-3 text-green-400" /> 0.01 Micro Risk
          </span>
          <span>•</span>
          <span className="inline-flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-green-400" /> +0.35R BE Shield
          </span>
          <span>•</span>
          <span className="inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-green-400" /> 24/7 Hands-Free
          </span>
        </div>
      </div>
    </div>
  );
};
