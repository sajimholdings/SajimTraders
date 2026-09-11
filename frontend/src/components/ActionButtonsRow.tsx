import React from "react";
import { Zap, Target, Shield, RotateCw } from "lucide-react";

interface ActionButtonsRowProps {
  autoPilotEnabled: boolean;
  onToggleAutoPilot: () => void;
  onOpenRiskSheet: () => void;
  onScrollToSignals: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export const ActionButtonsRow: React.FC<ActionButtonsRowProps> = ({
  autoPilotEnabled,
  onToggleAutoPilot,
  onOpenRiskSheet,
  onScrollToSignals,
  onRefresh,
  isRefreshing = false,
}) => {
  return (
    <div className="grid grid-cols-4 gap-2.5">
      <button
        type="button"
        onClick={onToggleAutoPilot}
        className={`flex flex-col items-center justify-center p-3 rounded-2xl border transition-all cursor-pointer active:scale-95 ${
          autoPilotEnabled
            ? "bg-green-500/15 border-green-500/40 text-green-400 shadow-[0_0_15px_rgba(34,197,94,0.2)]"
            : "bg-[#111111] hover:bg-[#161616] border-white/[0.06] text-gray-400 hover:text-white"
        }`}
      >
        <div className="relative mb-1">
          <Zap className={`w-5 h-5 ${autoPilotEnabled ? "fill-current animate-bounce" : ""}`} />
          {autoPilotEnabled && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-400 rounded-full animate-ping" />
          )}
        </div>
        <span className="text-[11px] font-bold tracking-tight">Auto-Pilot</span>
        <span className="text-[9px] text-gray-500 font-mono mt-0.5">
          {autoPilotEnabled ? "ON" : "PAUSED"}
        </span>
      </button>

      <button
        type="button"
        onClick={onScrollToSignals}
        className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111111] hover:bg-[#161616] border border-white/[0.06] text-gray-400 hover:text-white transition-all cursor-pointer active:scale-95"
      >
        <Target className="w-5 h-5 mb-1 text-green-400" />
        <span className="text-[11px] font-bold tracking-tight">Signals</span>
        <span className="text-[9px] text-gray-500 font-mono mt-0.5">1-Tap</span>
      </button>

      <button
        type="button"
        onClick={onOpenRiskSheet}
        className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111111] hover:bg-[#161616] border border-white/[0.06] text-gray-400 hover:text-white transition-all cursor-pointer active:scale-95"
      >
        <Shield className="w-5 h-5 mb-1 text-sky-400" />
        <span className="text-[11px] font-bold tracking-tight">Risk Mode</span>
        <span className="text-[9px] text-gray-500 font-mono mt-0.5">+0.35R</span>
      </button>

      <button
        type="button"
        onClick={onRefresh}
        disabled={isRefreshing}
        className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111111] hover:bg-[#161616] border border-white/[0.06] text-gray-400 hover:text-white transition-all cursor-pointer active:scale-95 disabled:opacity-50"
      >
        <RotateCw className={`w-5 h-5 mb-1 ${isRefreshing ? "animate-spin text-green-400" : ""}`} />
        <span className="text-[11px] font-bold tracking-tight">Sync</span>
        <span className="text-[9px] text-gray-500 font-mono mt-0.5">Live</span>
      </button>
    </div>
  );
};
