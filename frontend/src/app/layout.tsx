import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sajim Traders — Autonomous Quantitative Trading",
  description: "Scale-Invariant Quantitative Execution & 100% Hands-Free Copy-Trading. Powered by Headway MT5.",
  icons: {
    icon: "/assets/sajim_logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#07090e] text-slate-100 min-h-screen antialiased flex flex-col">
        {children}
      </body>
    </html>
  );
}
