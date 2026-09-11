import React from "react";

interface SymbolIconProps {
  symbol: string;
  className?: string;
}

export const SymbolIcon: React.FC<SymbolIconProps> = ({ symbol, className = "w-10 h-10" }) => {
  const s = (symbol || "").toUpperCase();

  let bgClass = "bg-gray-500/10 border-gray-500/20 text-gray-400";
  let displayLetters = s.slice(0, 3);

  if (s.includes("XAU") || s.includes("GOLD")) {
    bgClass = "bg-amber-500/15 border-amber-500/30 text-amber-400";
    displayLetters = "AU";
  } else if (s.includes("EUR")) {
    bgClass = "bg-blue-500/15 border-blue-500/30 text-blue-400";
    displayLetters = "EU";
  } else if (s.includes("GBP")) {
    bgClass = "bg-purple-500/15 border-purple-500/30 text-purple-400";
    displayLetters = "GB";
  } else if (s.includes("JPY")) {
    bgClass = "bg-rose-500/15 border-rose-500/30 text-rose-400";
    displayLetters = "JP";
  } else if (s.includes("30") || s.includes("100") || s.includes("US")) {
    bgClass = "bg-emerald-500/15 border-emerald-500/30 text-emerald-400";
    displayLetters = "US";
  }

  return (
    <div
      className={`${className} rounded-full border flex items-center justify-center font-mono font-bold text-xs ${bgClass} shrink-0`}
    >
      {displayLetters}
    </div>
  );
};
