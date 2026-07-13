import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VeriCup Markets",
  description: "Prediction markets da Copa liquidados por provas TxLINE na Solana."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
