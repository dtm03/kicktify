import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bundesliga Kicktipp",
  description: "Matchday predictions and season backtest",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}