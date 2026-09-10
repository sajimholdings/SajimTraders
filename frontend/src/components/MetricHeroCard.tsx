"use client";

import React from "react";
import { TrendingUp } from "lucide-react";
import { AccountTelemetry } from "../lib/types";

interface MetricHeroCardProps {
  account: AccountTelemetry;
}

export const MetricHeroCard: React.FC<MetricHeroCardProps> = ({ account }) => {
  const isPositive = (account.today_pnl || 0) >= 0;

  return (
    <section className="bg-[#0d121c] border border-white/10 rounded-2xl p-5 shadow-lg relative overflow-hidden">
      {/* Subtle top glow */}
      <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-48 h-20 bg-emerald-500/10 rounded-full blur-xl pointer-events-none" />

      <div className="flex justify-between items-end mb-4 relative z-10">
        <div>
          <span className="block text-[11px] font-extrabold tracking-wider text-slate-400 mb-1">
            ACCOUNT BALANCE
          </span>
          <div className="flex items-baseline gap-1.5 font-mono">
            <span className="text-3xl sm:text-4xl font-black text-white tracking-tight">
              ${account.balance.toFixed(2)}
            </span>
            <span className="text-xs font-bold text-slate-400">{account.currency || "USD"}</span>
          </div>
        </div>

        {/* Today's Net Profit Pill */}
        <div className="flex flex-col items-end bg-emerald-500/10 border border-emerald-500/30 px-3.5 py-2 rounded-xl">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">
            Today&apos;s Net Profit
          </span>
          <div className="flex items-center gap-1 text-emerald-400 font-mono font-black text-base leading-none">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>
              {isPositive ? "+" : ""}${account.today_pnl.toFixed(2)}
            </span>
          </div>
          <span className="text-[10px] font-bold text-emerald-300 font-mono mt-0.5">
            🟢 {isPositive ? "+" : ""}{account.today_pnl_percent.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Secondary Telemetry Strip */}
      <div className="pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
        <div>
          <span>Equity: </span>
          <strong className="text-white font-mono">${account.equity.toFixed(2)}</strong>
        </div>
        <span className="text-white/10">•</span>
        <div>
          <span>Free Margin: </span>
          <strong className="text-white font-mono">${account.free_margin.toFixed(2)}</strong>
        </div>
        <span className="text-white/10">•</span>
        <div>
          <span>Server: </span>
          <strong className="text-sky-400 font-mono text-[11px]">
            {account.broker_server || "Headway-Real"}
          </strong>
        </div>
      </div>
    </section>
  );
};
