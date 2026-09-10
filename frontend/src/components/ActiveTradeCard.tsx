"use client";

import React from "react";
import { ShieldCheck, X, Radio } from "lucide-react";
import { ClientTrade } from "../lib/types";

interface ActiveTradeCardProps {
  trades: ClientTrade[];
  onCloseTrade: (ticket: number) => void;
}

export const ActiveTradeCard: React.FC<ActiveTradeCardProps> = ({
  trades,
  onCloseTrade,
}) => {
  return (
    <section className="bg-[#0d121c] border border-white/10 rounded-2xl p-5 shadow-lg">
      <div className="flex justify-between items-center mb-3 text-[11px] font-extrabold tracking-wider text-slate-400">
        <span>CURRENT RUNNING TRADE</span>
        <span className="font-mono text-sky-400">{trades.length} / 2 Active</span>
      </div>

      {trades.length === 0 ? (
        /* Sleek Radar State when no trades */
        <div className="flex items-center gap-4 p-4 rounded-xl bg-black/20 border border-dashed border-white/10">
          <div className="relative w-12 h-12 flex items-center justify-center flex-shrink-0">
            <div className="absolute inset-0 border-2 border-emerald-500 rounded-full animate-radarExpand" />
            <div
              className="absolute inset-0 border-2 border-emerald-500 rounded-full animate-radarExpand"
              style={{ animationDelay: "1.25s" }}
            />
            <div className="w-2.5 h-2.5 bg-emerald-400 rounded-full shadow-[0_0_10px_#10b981]" />
          </div>

          <div>
            <h4 className="font-bold text-xs text-white flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              Live Market Radar Active
            </h4>
            <p className="text-[11px] text-slate-400 my-0.5">
              Scanning Gold (XAUUSD), Indices & FX for high-velocity entries...
            </p>
            <span className="text-[10px] font-extrabold text-emerald-400">
              Auto-Pilot Armed • 0.01 Micro Lot
            </span>
          </div>
        </div>
      ) : (
        /* Active Open Trades */
        <div className="space-y-3">
          {trades.map((t) => {
            const isProfit = (t.pnl || 0) >= 0;
            return (
              <div
                key={t.ticket}
                className="bg-black/30 border border-emerald-500/30 rounded-xl p-4 shadow-sm"
              >
                <div className="flex justify-between items-center mb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-sm text-white">{t.symbol}</span>
                    <span
                      className={`text-[10px] font-black px-2 py-0.5 rounded ${
                        t.type === "BUY"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      {t.type} {t.volume} Lot
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">#{t.ticket}</span>
                </div>

                <div className="flex justify-between items-center text-xs font-mono text-slate-400 mb-2.5">
                  <span>
                    Entry: <strong className="text-slate-200">{t.open_price}</strong>
                  </span>
                  <span>──►</span>
                  <span>
                    Current: <strong className="text-slate-200">{t.current_price}</strong>
                  </span>
                </div>

                {/* Floating Profit Banner */}
                <div className="flex justify-between items-center bg-black/40 px-3 py-2 rounded-lg mb-2.5">
                  <span className="text-[11px] text-slate-400">Floating Profit</span>
                  <span
                    className={`font-mono text-base font-black ${
                      isProfit ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {isProfit ? "+" : ""}${t.pnl.toFixed(2)} USD
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-[11px] text-emerald-300 font-semibold mb-3">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>🛡️ Breakeven Protected ($0 Risk) • Auto-Trailing Target</span>
                </div>

                <button
                  onClick={() => onCloseTrade(t.ticket)}
                  className="w-full py-2 bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 hover:text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5"
                >
                  <X className="w-3.5 h-3.5" /> Close Position Now
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
