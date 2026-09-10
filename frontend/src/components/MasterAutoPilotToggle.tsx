"use client";

import React from "react";
import { Bot, Zap, Play, Shield, Flame, Gauge } from "lucide-react";

interface MasterAutoPilotToggleProps {
  enabled: boolean;
  isDemo?: boolean;
  riskMode?: string;
  onChangeRisk?: (mode: string) => void;
  onToggle: () => void;
}

export const MasterAutoPilotToggle: React.FC<MasterAutoPilotToggleProps> = ({
  enabled,
  isDemo = false,
  riskMode = "ULTRA_SAFE",
  onChangeRisk,
  onToggle,
}) => {
  return (
    <section className="bg-[#0d121c] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm text-white">ALGO AUTO-PILOT</h3>
            <p className="text-[11px] text-slate-400">
              Automatically mirror high-accuracy quantitative setups
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
        type="button"
        onClick={onToggle}
        className={`w-full py-4 px-5 rounded-xl font-extrabold text-sm tracking-wide transition-all flex items-center justify-center gap-2.5 cursor-pointer active:scale-[0.98] ${
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

      {/* Risk Mode Selector */}
      {onChangeRisk && (
        <div className="grid grid-cols-3 gap-2 pt-1">
          <button
            type="button"
            onClick={() => onChangeRisk("ULTRA_SAFE")}
            className={`p-2 rounded-xl border text-center transition-all ${
              riskMode === "ULTRA_SAFE"
                ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-300"
                : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            <div className="flex items-center justify-center gap-1 text-[11px] font-bold">
              <Shield className="w-3 h-3" /> Ultra Safe
            </div>
            <div className="text-[9px] text-slate-500 mt-0.5">0.01 Micro • 1%</div>
          </button>

          <button
            type="button"
            onClick={() => onChangeRisk("PRO_SCALP")}
            className={`p-2 rounded-xl border text-center transition-all ${
              riskMode === "PRO_SCALP"
                ? "bg-sky-500/15 border-sky-500/50 text-sky-300"
                : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            <div className="flex items-center justify-center gap-1 text-[11px] font-bold">
              <Gauge className="w-3 h-3" /> Pro Scalp
            </div>
            <div className="text-[9px] text-slate-500 mt-0.5">Dynamic • 2%</div>
          </button>

          <button
            type="button"
            onClick={() => onChangeRisk("MAX_YIELD")}
            className={`p-2 rounded-xl border text-center transition-all ${
              riskMode === "MAX_YIELD"
                ? "bg-amber-500/15 border-amber-500/50 text-amber-300"
                : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            <div className="flex items-center justify-center gap-1 text-[11px] font-bold">
              <Flame className="w-3 h-3" /> Max Yield
            </div>
            <div className="text-[9px] text-slate-500 mt-0.5">Aggressive • 5%</div>
          </button>
        </div>
      )}
    </section>
  );
};
