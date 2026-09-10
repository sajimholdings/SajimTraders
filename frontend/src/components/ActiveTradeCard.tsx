"use client";

import React from "react";
import { ShieldCheck, X, Radio, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { ClientTrade } from "../lib/types";

interface ActiveTradeCardProps {
  trade?: ClientTrade | null;
  trades?: ClientTrade[];
  onCloseTrade?: (ticket: number) => void;
  onClosePosition?: (ticket: number) => void;
  isClosing?: boolean;
}

export const ActiveTradeCard: React.FC<ActiveTradeCardProps> = ({
  trade,
  trades,
  onCloseTrade,
  onClosePosition,
  isClosing = false,
}) => {
  const closeHandler = onCloseTrade || onClosePosition || (() => {});
  
  // Resolve list of active trades
  let activeList: ClientTrade[] = [];
  if (trades && trades.length > 0) {
    activeList = trades;
  } else if (trade) {
    activeList = [trade];
  }

  return (
    <section className="bg-[#0d121c] border border-white/10 rounded-2xl p-5 shadow-lg">
      <div className="flex justify-between items-center mb-3 text-[11px] font-extrabold tracking-wider text-slate-400">
        <span>CURRENT RUNNING TRADE</span>
        <span className="font-mono text-sky-400">{activeList.length} Active</span>
      </div>

      {activeList.length === 0 ? (
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
              AI Market Radar Active
            </h4>
            <p className="text-[11px] text-slate-400 my-0.5">
              Scanning Gold (XAUUSD), Indices & FX for institutional entries...
            </p>
            <span className="text-[10px] font-extrabold text-emerald-400">
              Auto-Pilot Armed • +0.35R BE Shield Guarded
            </span>
          </div>
        </div>
      ) : (
        /* Active Open Trades */
        <div className="space-y-3">
          {activeList.map((t) => {
            const isProfit = (t.pnl || 0) >= 0;
            const isBuy = t.type === "BUY";
            return (
              <div
                key={t.ticket}
                className="bg-black/30 border border-emerald-500/30 rounded-xl p-4 shadow-sm relative overflow-hidden"
              >
                <div className="flex justify-between items-center mb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-sm text-white">{t.symbol}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-0.5 ${
                        isBuy
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-rose-500/20 text-rose-400"
                      }`}
                    >
                      {isBuy ? (
                        <ArrowUpRight className="w-3 h-3" />
                      ) : (
                        <ArrowDownRight className="w-3 h-3" />
                      )}
                      {t.type} {t.volume}L
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => closeHandler(t.ticket)}
                    disabled={isClosing}
                    className="flex items-center gap-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 px-2.5 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Close Trade</span>
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2 bg-white/5 rounded-lg p-2.5 text-center text-xs">
                  <div>
                    <span className="block text-[10px] text-slate-500">Entry</span>
                    <strong className="font-mono text-slate-200">
                      {typeof t.open_price === "number" ? t.open_price.toFixed(2) : t.open_price}
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">Current</span>
                    <strong className="font-mono text-slate-200">
                      {typeof t.current_price === "number" ? t.current_price.toFixed(2) : t.current_price}
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">Floating Gain</span>
                    <strong
                      className={`font-mono font-bold ${
                        isProfit ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {isProfit ? "+" : ""}${typeof t.pnl === "number" ? t.pnl.toFixed(2) : t.pnl}
                    </strong>
                  </div>
                </div>

                {/* Breakeven Shield active badge */}
                <div className="mt-2.5 flex items-center justify-between text-[11px]">
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    <ShieldCheck className="w-3.5 h-3.5" /> +0.35R BE Shield Active
                  </span>
                  <span className="text-slate-500 font-mono text-[10px]">
                    Ticket #{t.ticket}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
