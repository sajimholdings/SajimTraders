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
    <div className="bg-[#111111] border border-green-500/20 rounded-2xl p-5 shadow-[0_0_20px_rgba(34,197,94,0.1)] relative overflow-hidden">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1.5 max-w-md">
          <div className="flex items-center gap-1.5 text-xs font-bold text-green-400">
            <Sparkles className="w-4 h-4" />
            <span>Keep 100% of Your Profits in Real USD</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">
            You are running on <strong className="text-white">Free Demo Mode</strong>. Switch to a verified real account with official partner broker Headway to withdraw live daily gains.
          </p>
          <div className="flex items-center gap-3 pt-1 text-[11px] text-gray-500">
            <span className="flex items-center gap-1 text-green-400 font-medium">
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
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-black text-xs font-extrabold transition-all shadow-lg active:scale-95 cursor-pointer"
          >
            <span>Open Real Account</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          {onSwitchToRealModal && (
            <button
              type="button"
              onClick={onSwitchToRealModal}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-white text-xs font-bold border border-white/[0.08] transition-colors cursor-pointer"
            >
              <span>Connect MT5</span>
              <ArrowRight className="w-3.5 h-3.5 text-green-400" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
