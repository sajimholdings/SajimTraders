import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#07090e",
        surface: "#0d121c",
        card: "rgba(16, 23, 37, 0.85)",
        cardHover: "rgba(22, 32, 51, 0.95)",
        borderSubtle: "rgba(255, 255, 255, 0.08)",
        borderActive: "rgba(56, 189, 248, 0.35)",
        borderEmerald: "rgba(16, 185, 129, 0.45)",
        emeraldCustom: {
          DEFAULT: "#10b981",
          light: "#34d399",
          glow: "rgba(16, 185, 129, 0.35)",
        },
        cyanCustom: {
          DEFAULT: "#38bdf8",
          glow: "rgba(56, 189, 248, 0.25)",
        },
        roseCustom: {
          DEFAULT: "#f43f5e",
          glow: "rgba(244, 63, 94, 0.25)",
        },
        goldCustom: {
          DEFAULT: "#f59e0b",
          glow: "rgba(245, 158, 11, 0.25)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Plus Jakarta Sans", "-apple-system", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
      },
      keyframes: {
        pulseGlow: {
          "0%": { boxShadow: "0 0 0 0 rgba(16, 185, 129, 0.5)" },
          "70%": { boxShadow: "0 0 0 16px rgba(16, 185, 129, 0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(16, 185, 129, 0)" },
        },
        radarExpand: {
          "0%": { transform: "scale(0.2)", opacity: "0.8" },
          "100%": { transform: "scale(1.4)", opacity: "0" },
        },
      },
      animation: {
        pulseGlow: "pulseGlow 2.5s infinite",
        radarExpand: "radarExpand 2.5s infinite linear",
      },
    },
  },
  plugins: [],
};

export default config;
