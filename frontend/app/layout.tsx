import "./globals.css";
import type { Metadata } from "next";
import { Playfair_Display, Inter } from "next/font/google";
import AtendimentoWhats from "./components/AtendimentoWhats";
import AtendimentoChat from "./components/AtendimentoChat";

const playfair = Playfair_Display({
  subsets: ["latin"], weight: ["500", "600", "700", "800"], variable: "--font-playfair", display: "swap",
});
const inter = Inter({
  subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-inter", display: "swap",
});

export const metadata: Metadata = {
  title: "FC Advocacia | Dr. Fábio Cunha — Recuperação Patrimonial",
  description:
    "FC Advocacia — Especialistas em Recuperação Patrimonial. Distrato Imobiliário, Execução Fiscal, Recuperação de Consumo e Direito Bancário. Dr. Fábio Cunha.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${playfair.variable} ${inter.variable}`}>
      <body className="bg-white text-charcoal antialiased">
        {children}
        <AtendimentoChat variant="floating" />
        <AtendimentoWhats variant="floating" />
      </body>
    </html>
  );
}
