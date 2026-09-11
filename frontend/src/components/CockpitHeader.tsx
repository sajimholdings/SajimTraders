import React from "react";
import { LogOut, ChevronDown } from "lucide-react";
import type { AccountTelemetry } from "../lib/types";

interface CockpitHeaderProps {
  telemetry: AccountTelemetry;
  onOpenConnector: () => void;
  onExitToGate: () => void;
}

export const CockpitHeader: React.FC<CockpitHeaderProps> = ({
  telemetry,
  onOpenConnector,
  onExitToGate,
}) => {
  const name = telemetry.account_name || "Trader";
  const initial = name.charAt(0).toUpperCase();
  const connected = telemetry.terminal_connected;
  const brokerShort = (telemetry.broker_server || "Broker").split("-")[0];

  return (
    <header className="sticky top-0 z-40 bg-black/90 backdrop-blur-md border-b border-white/[0.06] px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs text-gray-500">Welcome back,</span>
          <span className="text-sm font-bold text-white">{name}</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <div
              className={`w-9 h-9 rounded-full bg-[#111111] flex items-center justify-center border-2 ${
                connected ? "border-green-500" : "border-yellow-500"
              }`}
            >
              <span className="text-sm font-bold text-white">{initial}</span>
            </div>
            {connected && (
              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-400 rounded-full ring-2 ring-black animate-livePulse" />
            )}
          </div>

          <button
            type="button"
            onClick={onExitToGate}
            title="Exit to Gate"
            className="p-2 rounded-full bg-[#111111] hover:bg-white/10 text-gray-500 hover:text-white transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="mt-2">
        <button
          type="button"
          onClick={onOpenConnector}
          className="inline-flex items-center gap-1.5 bg-[#111111] hover:bg-white/10 border border-white/[0.06] rounded-full px-3 py-1 text-xs text-gray-400 font-mono transition-colors cursor-pointer"
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? "bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.5)]" : "bg-yellow-400"
            }`}
          />
          {telemetry.broker_server === "None" || telemetry.account_id === "NEW" ? (
            <span className="text-amber-400 font-sans font-semibold">⚡ Connect MT5 Broker</span>
          ) : (
            <>{brokerShort} #{telemetry.account_id}</>
          )}
          <ChevronDown className="w-3 h-3 text-gray-500" />
        </button>
      </div>
    </header>
  );
};
