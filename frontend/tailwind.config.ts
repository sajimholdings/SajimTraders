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
        background: "#000000",
        surface: "#111111",
        surfaceHover: "#1A1A1A",
        borderSubtle: "rgba(255, 255, 255, 0.06)",
        borderHover: "rgba(255, 255, 255, 0.10)",
        accent: {
          DEFAULT: "#22C55E",
          light: "#4ADE80",
          glow: "rgba(34, 197, 94, 0.15)",
          muted: "rgba(34, 197, 94, 0.10)",
        },
        loss: {
          DEFAULT: "#EF4444",
          glow: "rgba(239, 68, 68, 0.15)",
          muted: "rgba(239, 68, 68, 0.10)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "-apple-system", "SF Pro Display", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "SF Mono", "monospace"],
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        livePulse: {
          "0%": { boxShadow: "0 0 0 0 rgba(34, 197, 94, 0.5)" },
          "70%": { boxShadow: "0 0 0 10px rgba(34, 197, 94, 0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(34, 197, 94, 0)" },
        },
        radarExpand: {
          "0%": { transform: "scale(0.2)", opacity: "0.8" },
          "100%": { transform: "scale(1.4)", opacity: "0" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.4s ease-out forwards",
        livePulse: "livePulse 2s infinite",
        radarExpand: "radarExpand 2.5s infinite linear",
      },
    },
  },
  plugins: [],
};

export default config;
