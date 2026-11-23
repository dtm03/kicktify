import type { Metadata } from "next";
import { Outfit, Fraunces } from "next/font/google";
import "./globals.css";

const outfit = Outfit({ subsets: ["latin"], variable: "--font-ui", weight: ["400", "500", "600", "700"] });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-display", style: ["normal", "italic"] });

export const metadata: Metadata = {
  title: "Kicktify",
  description: "Matchday predictions and season backtest",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={`${outfit.variable} ${fraunces.variable}`}>
      <body>{children}</body>
    </html>
  );
}
