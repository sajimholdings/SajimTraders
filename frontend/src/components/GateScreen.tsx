"use client";

import React from "react";
import { Rocket, Zap, ShieldCheck, Lock, CheckCircle2, ArrowRight } from "lucide-react";

interface GateScreenProps {
  onLaunchDemo?: () => void;
  onStartDemo?: () => void;
  onConnectReal?: () => void;
  onOpenConnectModal?: () => void;
  onGoogleSignIn?: () => void;
  affiliateLink?: string;
  liveStats?: { total_pnl: number; total_trades: number; win_rate: number } | null;
}

export const GateScreen: React.FC<GateScreenProps> = ({
  onLaunchDemo,
  onStartDemo,
  onConnectReal,
  onOpenConnectModal,
  onGoogleSignIn,
  affiliateLink = "https://headway.partners/user/signup?hwp=b158cc",
  liveStats,
}) => {
  const handleDemo = () => {
    (onLaunchDemo || onStartDemo)?.();
  };

  const handleReal = () => {
    (onConnectReal || onOpenConnectModal)?.();
  };

  const handleGoogle = () => {
    onGoogleSignIn?.();
  };

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

        {/* Hero Headline */}
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight mb-2">
          Your Money.{" "}
          <span className="text-green-400 drop-shadow-[0_0_20px_rgba(34,197,94,0.3)]">
            Working 24/7.
          </span>
        </h1>
        <p className="text-sm text-gray-500 max-w-xs leading-relaxed">
          Connect your MT5 account in 30 seconds. Zero code. 100% hands-free execution.
        </p>

        {/* Live Aggregated Telemetry Strip (if available) */}
        {liveStats && (
          <div className="grid grid-cols-3 gap-2 w-full mt-6 bg-[#111111] border border-white/[0.06] rounded-2xl p-3 text-center">
            <div>
              <span className="block text-[10px] text-gray-500 uppercase">Today P&L</span>
              <strong className="text-xs font-mono text-green-400 font-bold">
                {liveStats.total_pnl >= 0 ? "+" : ""}${liveStats.total_pnl.toFixed(2)}
              </strong>
            </div>
            <div>
              <span className="block text-[10px] text-gray-500 uppercase">Active Trades</span>
              <strong className="text-xs font-mono text-white font-bold">
                {liveStats.total_trades}
              </strong>
            </div>
            <div>
              <span className="block text-[10px] text-gray-500 uppercase">Win Edge</span>
              <strong className="text-xs font-mono text-green-400 font-bold">
                {liveStats.win_rate.toFixed(1)}%
              </strong>
            </div>
          </div>
        )}
      </div>

      {/* Middle Section: Zero Friction Actions */}
      <div className="my-8 space-y-3">
        {/* Google One-Tap Auth */}
        <button
          type="button"
          onClick={handleGoogle}
          className="w-full py-3.5 px-5 rounded-2xl bg-white hover:bg-gray-100 text-black font-extrabold text-sm shadow-[0_4px_20px_rgba(255,255,255,0.15)] transition-all flex items-center justify-center gap-2.5 active:scale-[0.98] cursor-pointer"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          <span>Continue with Google</span>
        </button>

        <div className="flex items-center gap-3 py-0.5 text-gray-600 text-[11px] font-semibold uppercase tracking-wider">
          <div className="h-px flex-1 bg-white/[0.08]" />
          <span>or launch instantly</span>
          <div className="h-px flex-1 bg-white/[0.08]" />
        </div>

        {/* Primary Demo Button */}
        <button
          type="button"
          onClick={handleDemo}
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

        {/* Secondary Real Account Button */}
        <button
          type="button"
          onClick={handleReal}
          className="w-full py-3.5 px-5 rounded-2xl bg-[#111111] hover:bg-[#161616] border border-white/[0.08] hover:border-white/20 text-white font-bold text-sm transition-all flex items-center justify-between group active:scale-[0.98] cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400">
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
        {/* Partner Card */}
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

        {/* Trust Badges */}
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
            <CheckCircle2 className="w-3 h-3 text-green-400" /> 92.6% Win Edge
          </span>
        </div>
      </div>
    </div>
  );
};
