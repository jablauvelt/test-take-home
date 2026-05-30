import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BTC-USD Backtester",
  description: "A tiny BTC-USD moving-average crossover backtesting platform"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

