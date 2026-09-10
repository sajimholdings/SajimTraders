"use client";

import React from "react";
import Image from "next/image";
import { LogOut, ChevronDown } from "lucide-react";
import { AccountTelemetry } from "../lib/types";

interface CockpitHeaderProps {
  account: AccountTelemetry;
  onOpenConnectModal: () => void;
  onExitToGate: () => void;
}

export const CockpitHeader: React.FC<CockpitHeaderProps> = ({
  account,
  onOpenConnectModal,
  onExitToGate,
}) => {
  const brokerShort = (account.broker_server || "Headway").split("-")[0];

  return (
    <header className="sticky top-0 z-40 bg-[#07090e]/90 backdrop-blur-md border-b border-white/10 px-4 py-3 flex items-center justify-between">
      <div
        className="flex items-center gap-2.5 cursor-pointer hover:opacity-90 transition-opacity"
        onClick={onExitToGate}
      >
        <div className="relative w-8 h-8 rounded-lg overflow-hidden border border-emerald-500/40 bg-white p-0.5 shadow-sm">
          <Image
            src="/assets/sajim_logo.png"
            alt="Sajim Logo"
            width={32}
            height={32}
            className="object-contain w-full h-full"
          />
        </div>
        <div>
          <div className="flex items-center gap-1.5 leading-none">
            <span className="font-extrabold text-sm tracking-tight text-white">SAJIM</span>
            <span className="font-extrabold text-sm tracking-tight text-emerald-400">TRADERS</span>
          </div>
          <span className="text-[10px] font-bold text-emerald-400 tracking-wider">V2 AUTO-PILOT</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenConnectModal}
          className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full px-3 py-1.5 text-xs font-semibold text-slate-200 transition-all hover:border-sky-400/40"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              account.terminal_connected ? "bg-emerald-400 shadow-[0_0_8px_#10b981]" : "bg-amber-400"
            }`}
          />
          <span className="font-mono text-[11px]">{brokerShort} #{account.account_id}</span>
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </button>

        <button
          onClick={onExitToGate}
          title="Switch Account / Log Out"
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
