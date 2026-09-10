"use client";

import React from "react";
import { Sparkles, ArrowRight, ExternalLink, ShieldCheck } from "lucide-react";

interface FreemiumBannerProps {
  onSwitchToRealModal?: () => void;
  affiliateLink?: string;
}

export const FreemiumBanner: React.FC<FreemiumBannerProps> = ({
  onSwitchToRealModal,
  affiliateLink = "https://headway.partners/user/signup?hwp=b158cc",
}) => {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-950/40 via-[#0e121b] to-emerald-950/20 border border-emerald-500/20 p-5 shadow-xl">
      {/* Glow orb */}
      <div className="absolute -top-10 -right-10 w-36 h-36 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1 max-w-md">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <Sparkles className="w-4 h-4" />
            <span>Keep 100% of Your Profits in Real USD</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            You are currently running on <strong className="text-white">Free Demo Mode</strong>. Open a verified account with our official partner broker Headway to withdraw real daily gains.
          </p>
          <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400">
            <span className="flex items-center gap-1 text-emerald-400/90 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" /> Direct STP Execution
            </span>
            <span>•</span>
            <span>Zero Deposit Fees</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
          <a
            href={affiliateLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold transition-all shadow-lg shadow-emerald-500/20 active:scale-95"
          >
            Open Headway Real Account
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          {onSwitchToRealModal && (
            <button
              onClick={onSwitchToRealModal}
              className="inline-flex items-center justify-center gap-1 px-3 py-2.5 rounded-xl bg-[#141a27] hover:bg-[#1a2233] text-slate-200 text-xs font-semibold border border-[#222d42] transition-colors"
            >
              Connect Real MT5
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
