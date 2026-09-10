"use client";

import React, { useState } from "react";
import { Zap, TrendingUp, TrendingDown, Target, Shield, CheckCircle2 } from "lucide-react";
import { ClientSignal } from "../lib/types";

interface SignalsQuickGridProps {
  signals: ClientSignal[];
  onExecute: (signal: ClientSignal) => Promise<boolean>;
  isExecuting?: boolean;
}

export const SignalsQuickGrid: React.FC<SignalsQuickGridProps> = ({
  signals,
  onExecute,
  isExecuting = false,
}) => {
  const [executedIds, setExecutedIds] = useState<Record<string, boolean>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleTap = async (signal: ClientSignal) => {
    if (loadingId || executedIds[signal.id]) return;
    setLoadingId(signal.id);
    try {
      const success = await onExecute(signal);
      if (success) {
        setExecutedIds((prev) => ({ ...prev, [signal.id]: true }));
      }
    } finally {
      setLoadingId(null);
    }
  };

  if (!signals || signals.length === 0) {
    return (
      <div className="bg-[#0e121b] border border-[#1a2233] rounded-2xl p-6 text-center shadow-xl">
        <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-3">
          <Zap className="w-5 h-5 animate-pulse" />
        </div>
        <h4 className="text-sm font-semibold text-white">Scanning Active Markets</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
          Scanning XAUUSD, EURUSD & US30 for institutional liquidity setups with high statistical edge.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Live Quantitative Setups
          </h3>
        </div>
        <span className="text-[11px] font-medium text-emerald-400/90 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
          {signals.length} Setups Ready
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {signals.map((signal) => {
          const isBuy = signal.action === "BUY";
          const isExecuted = executedIds[signal.id];
          const isLoading = loadingId === signal.id;

          return (
            <div
              key={signal.id}
              className="bg-[#0e121b] border border-[#1a2233] hover:border-[#2a364f] transition-all rounded-2xl p-4 flex flex-col justify-between shadow-lg relative overflow-hidden group"
            >
              {/* Subtle top indicator bar */}
              <div
                className={`absolute top-0 left-0 right-0 h-[2px] ${
                  isBuy ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />

              <div>
                {/* Header: Symbol, Action badge, Probability */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-white tracking-wide">
                      {signal.symbol}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 ${
                        isBuy
                          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                          : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      {isBuy ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {signal.action}
                    </span>
                    <span className="text-[11px] font-medium text-slate-400">
                      {signal.timeframe}
                    </span>
                  </div>

                  <div className="text-right">
                    <div className="text-[11px] font-semibold text-emerald-400">
                      {signal.win_probability || "84.2%"} Win Edge
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase tracking-wider">
                      {signal.strategy || "Statistical Edge"}
                    </div>
                  </div>
                </div>

                {/* Price targets & estimated USD gain/risk */}
                <div className="grid grid-cols-3 gap-2 bg-[#080a0f] p-2.5 rounded-xl border border-[#141a27] mb-3 text-center">
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase font-medium">Entry</div>
                    <div className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                      {signal.entry.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-emerald-400 uppercase font-medium flex items-center justify-center gap-0.5">
                      <Target className="w-2.5 h-2.5" /> TP ({signal.rr || "1:3"})
                    </div>
                    <div className="text-xs font-mono font-bold text-emerald-300 mt-0.5">
                      {signal.gain_estimate_usd || `+${(signal.tp - signal.entry).toFixed(2)}`}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-rose-400 uppercase font-medium flex items-center justify-center gap-0.5">
                      <Shield className="w-2.5 h-2.5" /> Stop (Risk)
                    </div>
                    <div className="text-xs font-mono font-bold text-rose-300 mt-0.5">
                      {signal.risk_estimate_usd || `-${(signal.entry - signal.sl).toFixed(2)}`}
                    </div>
                  </div>
                </div>
              </div>

              {/* Execution Action Button */}
              <button
                onClick={() => handleTap(signal)}
                disabled={isExecuted || isLoading || isExecuting}
                className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                  isExecuted
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 cursor-default"
                    : isBuy
                    ? "bg-emerald-500 hover:bg-emerald-400 text-black shadow-lg shadow-emerald-500/20 active:scale-[0.98]"
                    : "bg-rose-500 hover:bg-rose-400 text-white shadow-lg shadow-rose-500/20 active:scale-[0.98]"
                }`}
              >
                {isLoading ? (
                  <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : isExecuted ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Order Placed to MT5
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-current" />
                    1-Tap Execute ({signal.action} {signal.symbol})
                  </>
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
