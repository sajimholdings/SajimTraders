import React from "react";
import { X, ShieldCheck, Radio, ArrowUpRight, ArrowDownRight } from "lucide-react";
import type { ClientTrade } from "../lib/types";
import { SymbolIcon } from "./SymbolIcon";
import { formatSignedCurrency } from "../lib/format";

interface ActiveTradeCardProps {
  trades?: ClientTrade[];
  onClosePosition?: (ticket: number) => void;
  isClosing?: boolean;
}

export const ActiveTradeCard: React.FC<ActiveTradeCardProps> = ({
  trades = [],
  onClosePosition,
  isClosing = false,
}) => {
  const handleClose = onClosePosition ?? (() => {});

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-white text-lg font-bold tracking-tight">Positions</h2>
        <span className="text-[11px] font-semibold text-gray-400 bg-white/5 border border-white/[0.06] px-2.5 py-1 rounded-full font-mono">
          {trades.length} Active
        </span>
      </div>

      {trades.length === 0 ? (
        <div className="bg-[#111111] border border-white/[0.06] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center gap-4">
            <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
              <div className="absolute inset-0 border-2 border-green-500 rounded-full animate-radarExpand" />
              <div
                className="absolute inset-0 border-2 border-green-500 rounded-full animate-radarExpand"
                style={{ animationDelay: "1.25s" }}
              />
              <div className="w-2.5 h-2.5 bg-green-400 rounded-full shadow-[0_0_10px_#22c55e]" />
            </div>

            <div>
              <h4 className="font-bold text-sm text-white flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-green-400 animate-pulse" />
                AI Market Radar Active
              </h4>
              <p className="text-xs text-gray-500 my-0.5">
                Scanning Gold (XAUUSD), Indices & FX for institutional entries...
              </p>
              <span className="text-[10px] font-bold text-green-400">
                Auto-Pilot Armed • +0.35R BE Shield Guarded
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-2.5">
          {trades.map((t) => {
            const isProfit = (t.pnl || 0) >= 0;
            const isBuy = t.type === "BUY";
            const hasShield =
              (t.comment || "").toUpperCase().includes("BE_SHIELD") ||
              (t.comment || "").toUpperCase().includes("LOCKED");

            return (
              <div
                key={t.ticket}
                className="bg-[#111111] hover:bg-[#151515] border border-white/[0.06] hover:border-white/10 transition-all rounded-2xl p-4 flex items-center justify-between relative group"
              >
                <div className="flex items-center gap-3">
                  <SymbolIcon symbol={t.symbol} className="w-11 h-11" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white tracking-tight">{t.symbol}</span>
                      <span
                        className={`inline-flex items-center gap-0.5 text-[10px] font-extrabold px-1.5 py-0.5 rounded ${
                          isBuy ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400"
                        }`}
                      >
                        {isBuy ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {t.type} {t.volume}L
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500 font-mono">
                      <span>
                        Entry: {typeof t.open_price === "number" ? t.open_price.toFixed(2) : t.open_price}
                      </span>
                      {hasShield && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-green-400 font-bold bg-green-500/10 px-1.5 py-0.2 rounded border border-green-500/20">
                          <ShieldCheck className="w-3 h-3" /> +0.35R
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <strong
                      className={`block font-mono text-sm sm:text-base font-black ${
                        isProfit ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {formatSignedCurrency(typeof t.pnl === "number" ? t.pnl : 0)}
                    </strong>
                    <span className="block text-[10px] text-gray-500 font-mono">
                      Now: {typeof t.current_price === "number" ? t.current_price.toFixed(2) : t.current_price}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleClose(t.ticket)}
                    disabled={isClosing}
                    title="Close position"
                    className="p-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
