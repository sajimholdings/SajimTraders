"use client";

import React from "react";
import Image from "next/image";
import { Zap, Rocket, ShieldCheck, ArrowRight, Lock, CheckCircle2 } from "lucide-react";

interface GateScreenProps {
  onStartDemo: () => void;
  onOpenConnectModal: () => void;
}

export const GateScreen: React.FC<GateScreenProps> = ({
  onStartDemo,
  onOpenConnectModal,
}) => {
  return (
    <section className="min-h-screen flex items-center justify-center px-4 py-8 relative">
      {/* Ambient background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-[#0d121c]/90 backdrop-blur-xl border border-white/10 rounded-2xl p-7 text-center relative z-10 shadow-2xl">
        
        {/* Official Logo */}
        <div className="flex flex-col items-center gap-3 mb-5">
          <div className="relative w-20 h-20 rounded-xl overflow-hidden border-2 border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.3)] bg-white p-1">
            <Image
              src="/assets/sajim_logo.png"
              alt="Sajim Traders Official Logo"
              width={80}
              height={80}
              className="object-contain w-full h-full"
              priority
            />
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-bold tracking-wider text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
            <Zap className="w-3.5 h-3.5" /> 100% HANDS-FREE QUANT
          </span>
        </div>

        {/* Hook Headline */}
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2 leading-tight">
          Autonomous Quantitative Trading.{" "}
          <span className="text-emerald-400 drop-shadow-[0_0_15px_rgba(16,185,129,0.4)]">
            100% Hands-Free.
          </span>
        </h1>

        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          Connect your MT5 account in 30 seconds. Start with a Free Demo with zero capital risk.
        </p>

        {/* Primary Action Buttons */}
        <div className="flex flex-col gap-3 mb-6">
          <button
            onClick={onStartDemo}
            className="w-full flex items-center justify-center gap-3 p-4 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white font-bold text-base shadow-[0_4px_20px_rgba(16,185,129,0.4)] transition-all hover:-translate-y-0.5"
          >
            <Rocket className="w-5 h-5" />
            <div className="text-left">
              <div className="leading-tight font-extrabold">Start with Free Demo</div>
              <div className="text-xs text-emerald-100 font-normal">Test our algo with zero risk</div>
            </div>
          </button>

          <button
            onClick={onOpenConnectModal}
            className="w-full flex items-center justify-center gap-3 p-3.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold text-sm transition-all hover:-translate-y-0.5"
          >
            <Zap className="w-4 h-4 text-emerald-400" />
            <div className="text-left">
              <div className="leading-tight font-bold">Connect Real MT5 Account</div>
              <div className="text-xs text-slate-400">Trade real capital with +0.35R shield</div>
            </div>
          </button>
        </div>

        {/* Partner Broker Callout */}
        <div className="bg-sky-500/5 border border-sky-500/20 rounded-xl p-4 mb-5 text-left">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-extrabold tracking-wider text-sky-400">OFFICIAL BROKER PARTNER</span>
            <span className="text-[11px] text-slate-400">Headway</span>
          </div>
          <p className="text-xs text-slate-300 mb-2.5 leading-snug">
            Don&apos;t have an MT5 account yet? Get 1:2000 leverage & instant M-Pesa deposits.
          </p>
          <a
            href="https://headway.partners/user/signup?hwp=b158cc"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 w-full py-2 px-3 bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 rounded-lg text-sky-300 text-xs font-bold transition-colors"
          >
            👉 Open Account on Headway (Takes 1 min)
            <ArrowRight className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Trust Strip */}
        <div className="flex items-center justify-center gap-3 text-[11px] text-slate-500 font-medium">
          <span className="inline-flex items-center gap-1">
            <Lock className="w-3 h-3 text-emerald-400" /> 0.01 Micro Risk
          </span>
          <span>•</span>
          <span className="inline-flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" /> +0.35R BE Shield
          </span>
          <span>•</span>
          <span className="inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> 92.6% Win Rate
          </span>
        </div>

      </div>
    </section>
  );
};
