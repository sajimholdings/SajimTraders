"use client";

import React from "react";
import { Bot, Zap, Play, Pause } from "lucide-react";

interface MasterAutoPilotToggleProps {
  enabled: boolean;
  isDemo: boolean;
  onToggle: () => void;
}

export const MasterAutoPilotToggle: React.FC<MasterAutoPilotToggleProps> = ({
  enabled,
  isDemo,
  onToggle,
}) => {
  return (
    <section className="bg-[#0d121c] border border-white/10 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm text-white">ALGO AUTO-PILOT</h3>
            <p className="text-[11px] text-slate-400">
              Automatically mirror high-accuracy V2 trades (XAUUSD, US30, NAS100)
            </p>
          </div>
        </div>

        <span
          className={`text-[10px] font-extrabold px-2.5 py-1 rounded-md border ${
            isDemo
              ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
              : "bg-sky-500/10 border-sky-500/30 text-sky-400"
          }`}
        >
          {isDemo ? "FREE DEMO" : "REAL CAPITAL"}
        </span>
      </div>

      {/* Big Master Button */}
      <button
        onClick={onToggle}
        className={`w-full py-4 px-5 rounded-xl font-extrabold text-sm tracking-wide transition-all flex items-center justify-center gap-2.5 ${
          enabled
            ? "bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white shadow-[0_0_25px_rgba(16,185,129,0.35)] animate-pulseGlow"
            : "bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300"
        }`}
      >
        {enabled ? (
          <>
            <Zap className="w-4 h-4 fill-current text-white animate-bounce" />
            <span>⚡ AUTO-PILOT ACTIVE (TAP TO PAUSE)</span>
          </>
        ) : (
          <>
            <Play className="w-4 h-4 fill-current text-emerald-400" />
            <span>▷ TURN ON AUTO-PILOT (100% HANDS-FREE)</span>
          </>
        )}
      </button>
    </section>
  );
};
