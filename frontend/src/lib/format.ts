// Display formatting helpers. All currency is assumed USD unless noted.

/** Format an amount as USD, keeping the minus sign for negative values. */
export function formatCurrency(value: number): string {
  const sign = value < 0 ? "-" : "";
  return `${sign}${formatAbsCurrency(value)}`;
}

function formatAbsCurrency(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) {
    return `$${(abs / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 10_000) {
    return `$${abs.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }
  return `$${abs.toFixed(2)}`;
}

export function formatSignedCurrency(value: number): string {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${formatAbsCurrency(value)}`;
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

const METALS = ["XAU", "XAG", "XPT", "XPD"];
const INDEX_HINTS = [
  "US30", "US100", "US500", "NAS", "SPX", "DJ", "GER", "DE40", "DAX", "UK100",
  "FTSE", "JP225", "NIK", "HK50", "AUS200", "FRA40", "EU50", "STOXX",
];
const CRYPTO_HINTS = ["BTC", "ETH", "LTC", "XRP", "SOL"];

/** Number of decimals to display for a quoted price of `symbol`. */
export function pricePrecision(symbol: string | undefined | null): number {
  const s = (symbol || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (!s) return 2;
  if (METALS.some((m) => s.startsWith(m))) return s.startsWith("XAG") ? 3 : 2;
  if (CRYPTO_HINTS.some((c) => s.startsWith(c))) return 2;
  if (INDEX_HINTS.some((i) => s.startsWith(i))) return 1;
  if (/^[A-Z]{6}/.test(s)) return s.slice(3, 6) === "JPY" ? 3 : 5;
  return 2;
}

/** Format a price with symbol-appropriate precision; non-numbers pass through. */
export function formatPrice(value: number | string | undefined | null, symbol?: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return value === undefined || value === null ? "—" : String(value);
  }
  return value.toFixed(pricePrecision(symbol));
}
