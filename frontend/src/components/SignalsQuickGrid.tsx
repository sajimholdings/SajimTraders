"use client";

import React, { useState, useCallback } from "react";
import { Zap, CheckCircle2 } from "lucide-react";
import type { ClientSignal } from "../lib/types";

interface SignalsQuickGridProps {
  signals: ClientSignal[];
  onExecute: (signal: ClientSignal) => Promise<boolean>;
  isExecuting: boolean;
}

function healthBadgeClass(status?: string): string {
  const s = (status || "").toUpperCase();
  if (s.includes("PRIME")) return "bg-green-500/15 text-green-400 border-green-500/30";
  if (s.includes("HEALTHY")) return "bg-sky-500/15 text-sky-400 border-sky-500/30";
  return "bg-amber-500/15 text-amber-400 border-amber-500/30";
}

export const SignalsQuickGrid: React.FC<SignalsQuickGridProps> = ({
  signals,
  onExecute,
  isExecuting,
}) => {
  const [executedIds, setExecutedIds] = useState<Set<string>>(new Set());
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleTap = useCallback(
    async (signal: ClientSignal) => {
      if (executedIds.has(signal.id) || loadingId || isExecuting) return;
      setLoadingId(signal.id);
      try {
        const success = await onExecute(signal);
        if (success) {
          setExecutedIds((prev) => new Set(prev).add(signal.id));
        }
      } finally {
        setLoadingId(null);
      }
    },
    [executedIds, loadingId, isExecuting, onExecute]
  );

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          <h2 className="text-white text-lg font-bold tracking-tight">Live Signals</h2>
        </div>
        <span className="text-[11px] font-semibold text-green-400 bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded-full">
          {signals.length} Ready
        </span>
      </div>

      {signals.length === 0 && (
        <div className="bg-[#111111] border border-white/[0.06] rounded-2xl p-6 text-center">
          <Zap className="w-8 h-8 text-green-400 mx-auto mb-3 animate-pulse" />
          <p className="text-white font-semibold text-sm mb-1">Scanning Active Markets</p>
          <p className="text-gray-500 text-xs">
            Analyzing XAUUSD, EURUSD, GBPJPY and more for high-probability setups…
          </p>
        </div>
      )}

      {signals.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {signals.map((signal) => {
            const isBuy = signal.action === "BUY";
            const executed = executedIds.has(signal.id);
            const loading = loadingId === signal.id;
            const disabled = executed || loading || isExecuting;

            return (
              <div
                key={signal.id}
                className="relative bg-[#111111] border border-white/[0.06] rounded-2xl p-4 overflow-hidden hover:border-white/10 transition-colors"
              >
                <div
                  className={`absolute top-0 left-0 right-0 h-[2px] ${
                    isBuy ? "bg-green-400" : "bg-red-400"
                  }`}
                />

                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-white">{signal.symbol}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        isBuy ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400"
                      }`}
                    >
                      {signal.action}
                    </span>
                    <span className="text-gray-500 text-[11px]">{signal.timeframe}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 text-xs font-bold">{signal.win_probability}</p>
                    <p className="text-gray-500 text-[10px]">{signal.strategy}</p>
                  </div>
                </div>

                <div className="bg-black/50 rounded-xl p-2.5 grid grid-cols-3 gap-2 text-center mb-3">
                  <div>
                    <p className="text-gray-500 text-[10px] mb-0.5">Entry</p>
                    <p className="text-white text-xs font-mono font-semibold">{signal.entry}</p>
                  </div>
                  <div>
                    <p className="text-green-400 text-[10px] mb-0.5">TP ({signal.rr})</p>
                    <p className="text-green-400 text-xs font-mono font-semibold">
                      {signal.gain_estimate_usd}
                    </p>
                  </div>
                  <div>
                    <p className="text-red-400 text-[10px] mb-0.5">Risk</p>
                    <p className="text-red-400 text-xs font-mono font-semibold">
                      {signal.risk_estimate_usd}
                    </p>
                  </div>
                </div>

                {(signal.expected_duration || signal.trade_health_status) && (
                  <div className="flex items-center justify-between text-[10px] text-gray-500 mb-2.5">
                    {signal.expected_duration ? (
                      <span>⏱ {signal.expected_duration}</span>
                    ) : (
                      <span />
                    )}
                    {signal.trade_health_status && (
                      <span
                        className={`px-1.5 py-0.5 rounded border font-bold ${healthBadgeClass(
                          signal.trade_health_status
                        )}`}
                      >
                        {signal.trade_health_status}
                      </span>
                    )}
                  </div>
                )}

                {signal.trade_explainer && (
                  <p className="text-[11px] text-gray-500 leading-snug mb-3 line-clamp-2">
                    {signal.trade_explainer}
                  </p>
                )}

                <button
                  disabled={disabled}
                  onClick={() => handleTap(signal)}
                  className={`w-full rounded-xl py-2.5 text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                    executed
                      ? "bg-green-500/10 text-green-400 border border-green-500/20 cursor-default"
                      : loading
                      ? isBuy
                        ? "bg-green-500/60 text-black cursor-wait"
                        : "bg-red-500/60 text-white cursor-wait"
                      : isBuy
                      ? "bg-green-500 text-black hover:bg-green-400 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
                      : "bg-red-500 text-white hover:bg-red-400 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
                  }`}
                >
                  {executed ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Sent to MT5
                    </>
                  ) : loading ? (
                    <div className="border-2 border-current border-t-transparent rounded-full animate-spin w-4 h-4" />
                  ) : (
                    <>
                      <Zap className="w-3.5 h-3.5" />
                      ⚡ 1-Tap Execute ({signal.action} {signal.symbol})
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
