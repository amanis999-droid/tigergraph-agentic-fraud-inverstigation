import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Fraud Investigation Console",
  description: "TigerGraph Agentic Fraud Investigation — analyst dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-bg text-text font-sans min-h-screen">
        <header className="border-b border-border px-7 py-4 flex items-baseline gap-3">
          <span className="w-2 h-2 bg-risk-high inline-block rotate-45" />
          <h1 className="text-[15px] font-semibold tracking-wide">Fraud Investigation Console</h1>
          <span className="text-text-dim text-xs font-mono">HHGOA · agentic fraud investigation</span>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}