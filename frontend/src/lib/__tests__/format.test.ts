import { describe, expect, it } from "vitest";
import {
  formatCurrency,
  formatPercent,
  formatPrice,
  formatSignedCurrency,
  pricePrecision,
} from "../format";

describe("formatCurrency", () => {
  it("formats positive values", () => {
    expect(formatCurrency(0)).toBe("$0.00");
    expect(formatCurrency(1234.5)).toBe("$1234.50");
    expect(formatCurrency(12345.678)).toBe("$12,345.68");
    expect(formatCurrency(2_500_000)).toBe("$2.50M");
  });

  it("keeps the minus sign for negative values", () => {
    expect(formatCurrency(-5)).toBe("-$5.00");
    expect(formatCurrency(-12345.6)).toBe("-$12,345.60");
    expect(formatCurrency(-1_200_000)).toBe("-$1.20M");
  });
});

describe("formatSignedCurrency", () => {
  it("prefixes exactly one sign", () => {
    expect(formatSignedCurrency(10)).toBe("+$10.00");
    expect(formatSignedCurrency(0)).toBe("+$0.00");
    expect(formatSignedCurrency(-10)).toBe("-$10.00");
  });
});

describe("formatPercent", () => {
  it("formats with sign and one decimal", () => {
    expect(formatPercent(1.234)).toBe("+1.2%");
    expect(formatPercent(-0.56)).toBe("-0.6%");
  });
});

describe("pricePrecision / formatPrice", () => {
  it("uses symbol-appropriate precision", () => {
    expect(pricePrecision("EURUSD")).toBe(5);
    expect(pricePrecision("GBPJPY")).toBe(3);
    expect(pricePrecision("USDJPY.m")).toBe(3);
    expect(pricePrecision("XAUUSD")).toBe(2);
    expect(pricePrecision("XAGUSD")).toBe(3);
    expect(pricePrecision("US30")).toBe(1);
    expect(pricePrecision("NAS100")).toBe(1);
    expect(pricePrecision("BTCUSD")).toBe(2);
    expect(pricePrecision(undefined)).toBe(2);
  });

  it("formats prices", () => {
    expect(formatPrice(1.0851234, "EURUSD")).toBe("1.08512");
    expect(formatPrice(151.2346, "USDJPY")).toBe("151.235");
    expect(formatPrice(2350.456, "XAUUSD")).toBe("2350.46");
    expect(formatPrice(undefined, "EURUSD")).toBe("—");
  });
});
