import React from "react";
import { X, Shield, Gauge, Flame, Check } from "lucide-react";
import type { RiskMode } from "../lib/types";
import { RISK_MODES } from "../lib/constants";

const MODE_ICONS = {
  ULTRA_SAFE: Shield,
  PRO_SCALP: Gauge,
  MAX_YIELD: Flame,
} as const;

const MODE_PALETTE = {
  ULTRA_SAFE: { color: "text-green-400", bg: "bg-green-500/10 border-green-500/30" },
  PRO_SCALP: { color: "text-sky-400", bg: "bg-sky-500/10 border-sky-500/30" },
  MAX_YIELD: { color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/30" },
} as const;

interface RiskModeSheetProps {
  isOpen: boolean;
  onClose: () => void;
  currentMode: string;
  onSelectMode: (mode: RiskMode) => void;
}

export const RiskModeSheet: React.FC<RiskModeSheetProps> = ({
  isOpen,
  onClose,
  currentMode,
  onSelectMode,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4 animate-fadeUp"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md bg-[#111111] border border-white/[0.08] rounded-t-3xl sm:rounded-2xl p-6 text-white shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-green-400" />
            <h3 className="text-sm font-bold">Execution Risk Profile</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
          All profiles are protected by the proprietary{" "}
          <strong className="text-green-400">+0.35R Breakeven Shield</strong>. Stop Loss moves to
          entry + lock fee automatically.
        </p>

        <div className="space-y-2.5">
          {RISK_MODES.map((m) => {
            const Icon = MODE_ICONS[m.id];
            const palette = MODE_PALETTE[m.id];
            const isSelected = currentMode === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  onSelectMode(m.id);
                  onClose();
                }}
                className={`w-full p-4 rounded-2xl border text-left transition-all flex items-center justify-between cursor-pointer ${
                  isSelected
                    ? "bg-green-500/10 border-green-500/50 shadow-[0_0_15px_rgba(34,197,94,0.15)]"
                    : "bg-black/40 border-white/[0.06] hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-xl border flex items-center justify-center ${palette.bg}`}>
                    <Icon className={`w-4 h-4 ${palette.color}`} />
                  </div>
                  <div>
                    <strong className="block text-xs font-bold text-white">{m.title}</strong>
                    <span className="block text-[11px] text-gray-500 mt-0.5">{m.subtitle}</span>
                  </div>
                </div>
                {isSelected && <Check className="w-4 h-4 text-green-400" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
