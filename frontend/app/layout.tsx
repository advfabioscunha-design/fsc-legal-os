import "./globals.css";
import type { Metadata } from "next";
import { Playfair_Display, Inter, Space_Grotesk } from "next/font/google";
import AtendimentoFlutuante from "./components/AtendimentoFlutuante";
import LevaParaRedefinirSenha from "./components/LevaParaRedefinirSenha";
import TokenNasChamadas from "./components/TokenNasChamadas";

/* TIPOGRAFIA
 *
 * Playfair nos títulos dá o peso institucional que um escritório
 * precisa ter. Inter no corpo porque foi desenhada para tela e aguenta
 * texto longo sem cansar. Space Grotesk só em número e código, onde a
 * largura fixa evita que valores dancem de linha em linha.
 *
 * Três famílias é o limite. A quarta começa a parecer indecisão. */
const display = Playfair_Display({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});
const mono = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FC Advocacia e Recuperação Patrimonial",
  description:
    "Escritório digital com atuação em todo o país. Direito bancário, distrato imobiliário, execução fiscal e recuperação de consumo de energia. Elaboração de contratos sob medida.",
  icons: { icon: "/icon.svg" },
  openGraph: {
    title: "FC Advocacia e Recuperação Patrimonial",
    description:
      "Cobraram de você o que não deviam? Entenda o que pode ser feito no seu caso.",
    locale: "pt_BR",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${display.variable} ${inter.variable} ${mono.variable}`}>
      <body className="bg-white text-charcoal antialiased">
        {/* Anexa o token da sessão a toda chamada feita à API do
            escritório. Fica antes do conteúdo para já estar de pé
            quando a primeira tela pedir dados. */}
        <TokenNasChamadas />
        {children}
        {/* Só no site e na área do cliente. Quem decide é o componente. */}
        <LevaParaRedefinirSenha />
        <AtendimentoFlutuante />
      </body>
    </html>
  );
}
