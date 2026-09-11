import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { AccountTelemetry } from "../lib/types";
import { formatCurrency, formatSignedCurrency, formatPercent } from "../lib/format";

interface MetricHeroCardProps {
  telemetry: AccountTelemetry;
  onOpenConnector?: () => void;
}

export const MetricHeroCard: React.FC<MetricHeroCardProps> = ({
  telemetry,
  onOpenConnector,
}) => {
  const equity = telemetry.equity ?? 0;
  const pnl = telemetry.today_pnl ?? 0;
  const pnlPercent = telemetry.today_pnl_percent ?? 0;
  const freeMargin = telemetry.free_margin ?? 0;
  const isPositive = pnl >= 0;
  const hasNoBroker = telemetry.broker_server === "None" || telemetry.account_id === "NEW";

  return (
    <section className="pt-2 pb-1">
      {telemetry.is_demo && (
        <span className="inline-block mb-3 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
          Demo Mode
        </span>
      )}

      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-1.5">
        Portfolio value
      </p>

      <h1 className="text-[42px] sm:text-5xl font-bold text-white tracking-tight font-mono leading-none">
        {equity < 0 ? "-" : ""}
        {formatCurrency(equity)}
      </h1>

      <div className="mt-3">
        {hasNoBroker ? (
          <button
            type="button"
            onClick={onOpenConnector}
            className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition-all cursor-pointer active:scale-95"
          >
            <span>⚡ Connect MT5 Account to Start</span>
          </button>
        ) : (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
              isPositive
                ? "bg-green-500/10 text-green-400 border-green-500/20"
                : "bg-red-500/10 text-red-400 border-red-500/20"
            }`}
          >
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {formatSignedCurrency(pnl)} ({formatPercent(pnlPercent)})
          </span>
        )}
      </div>

      <div className="flex gap-6 mt-5 text-xs">
        <div>
          <span className="block text-gray-500 mb-0.5">Equity</span>
          <span className="text-white font-mono font-medium">{formatCurrency(equity)}</span>
        </div>
        <div>
          <span className="block text-gray-500 mb-0.5">Free Margin</span>
          <span className="text-white font-mono font-medium">{formatCurrency(freeMargin)}</span>
        </div>
        <div>
          <span className="block text-gray-500 mb-0.5">BE Shield</span>
          <span className="text-green-400 font-mono font-medium">+0.35R</span>
        </div>
      </div>
    </section>
  );
};
