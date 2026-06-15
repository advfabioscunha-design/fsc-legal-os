import "./globals.css";
import type { Metadata } from "next";
import BotaoWhatsapp from "./components/BotaoWhatsapp";

export const metadata: Metadata = {
  title: "FSC Advocacia | Fábio Cunha — OAB/RO 10.849",
  description:
    "Advocacia digital especializada em Direito Bancário, Distrato Imobiliário, Execução Fiscal e Busca e Apreensão. Atendimento nacional — Dr. Fábio Silva Cunha (OAB/RO 10.849).",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700&family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&family=Space+Grotesk:wght@500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className="bg-[#0A1628] text-white antialiased"
        style={{ fontFamily: "Inter, sans-serif" }}
      >
        {children}
        <BotaoWhatsapp />
      </body>
    </html>
  );
}
