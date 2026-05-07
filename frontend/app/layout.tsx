import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Querionyx V3",
  description: "Hybrid RAG + Text-to-SQL interface"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

