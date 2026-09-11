// Display formatting helpers. All currency is assumed USD unless noted.

export function formatCurrency(value: number): string {
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
  return `${sign}${formatCurrency(value)}`;
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}
