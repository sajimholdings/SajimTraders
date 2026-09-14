const requiredMql5Markers = [
  "#include <Trade\\Trade.mqh>",
  "OnInit()",
  "OnTick()",
  "CTrade",
  "strategy",
  "CopyBuffer",
  "trade.Buy",
  "trade.Sell",
  "magicNumber",
];

export function validateMql5Source(source: string): { ok: boolean; missing: string[] } {
  const missing = requiredMql5Markers.filter((marker) => !source.includes(marker));
  return { ok: missing.length === 0, missing };
}