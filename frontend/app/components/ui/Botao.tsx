"use client";
import Link from "next/link";
import type { ReactNode } from "react";

/* BOTÕES
 *
 * Antes cada tela escrevia as suas classes à mão, e o site acabou com
 * botões de sete alturas, cinco raios de canto e três verdes de
 * WhatsApp diferentes. Ninguém nota um botão isolado fora do padrão,
 * mas todo mundo sente a página inteira: é o que faz um site parecer
 * montado às pressas mesmo quando o conteúdo é bom.
 *
 * As variantes existem em número pequeno de propósito. Se um dia
 * aparecer a necessidade de uma oitava variante, quase sempre o certo é
 * repensar a tela, não criar a variante.
 */

type Variante = "primario" | "premium" | "fantasma" | "claro" | "whats";
type Tamanho = "sm" | "md" | "lg";

const VARIANTES: Record<Variante, string> = {
  // Ação principal. Azul porque é o que se clica no sistema inteiro.
  primario:
    "bg-electric text-white hover:bg-indigo shadow-card hover:shadow-glow",
  // Dourado reservado ao premium. Em tudo vira enfeite e perde o sentido.
  premium:
    "bg-gold text-navy hover:brightness-95 shadow-card font-bold",
  // Secundária sobre fundo escuro.
  fantasma:
    "border border-white/25 text-white hover:border-white/60 hover:bg-white/5",
  // Secundária sobre fundo claro.
  claro:
    "border border-navy/15 text-navy hover:border-navy/40 hover:bg-navy/[.03]",
  // Verde oficial do WhatsApp. Não é escolha de design, é a marca deles.
  whats:
    "bg-whats text-white hover:brightness-95 shadow-card",
};

const TAMANHOS: Record<Tamanho, string> = {
  sm: "px-4 py-2 text-small gap-2",
  md: "px-6 py-3 text-body gap-2.5",
  lg: "px-8 py-4 text-subtitle gap-3",
};

const BASE =
  "inline-flex items-center justify-center rounded-lg font-semibold " +
  "transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none " +
  "whitespace-nowrap";

export function classesBotao(v: Variante = "primario", t: Tamanho = "md",
                             extra = "") {
  return `${BASE} ${VARIANTES[v]} ${TAMANHOS[t]} ${extra}`.trim();
}

type Props = {
  children: ReactNode;
  variante?: Variante;
  tamanho?: Tamanho;
  href?: string;
  externo?: boolean;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  type?: "button" | "submit";
};

export default function Botao({
  children, variante = "primario", tamanho = "md",
  href, externo, onClick, className = "", disabled, type = "button",
}: Props) {
  const cls = classesBotao(variante, tamanho, className);

  if (href && externo) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>
        {children}
      </a>
    );
  }
  if (href) {
    return <Link href={href} className={cls}>{children}</Link>;
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={cls}>
      {children}
    </button>
  );
}

/* O logo do WhatsApp, em vetor.
 *
 * O site usava um emoji e um círculo verde qualquer. Emoji muda de
 * desenho conforme o aparelho, e um verde aproximado numa marca que
 * todo mundo reconhece de imediato é o tipo de detalhe que passa
 * descuido. */
export function IconeWhatsApp({ tamanho = 20 }: { tamanho?: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24"
      fill="currentColor" aria-hidden="true">
      <path d="M17.47 14.38c-.3-.15-1.75-.86-2.02-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.64.07-.3-.15-1.25-.46-2.38-1.47-.88-.78-1.47-1.75-1.64-2.05-.17-.3-.02-.46.13-.6.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.67-1.6-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.01-1.04 2.47s1.06 2.86 1.21 3.06c.15.2 2.1 3.2 5.08 4.48.71.31 1.26.49 1.69.63.71.22 1.36.19 1.87.12.57-.09 1.75-.72 2-1.41.25-.69.25-1.28.17-1.41-.07-.13-.27-.2-.57-.35z"/>
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.87 9.87 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2zm0 18.13h-.01a8.2 8.2 0 0 1-4.18-1.15l-.3-.18-3.11.82.83-3.04-.2-.31a8.17 8.17 0 0 1-1.26-4.36c0-4.54 3.7-8.24 8.24-8.24 2.2 0 4.27.86 5.82 2.42a8.18 8.18 0 0 1 2.41 5.83c0 4.54-3.7 8.21-8.24 8.21z"/>
    </svg>
  );
}

/* Botão de WhatsApp padrão. Existe para que o número, o texto e a marca
   fiquem num lugar só: eles estavam repetidos em cinco telas, com
   variações. */
export function BotaoWhatsApp({
  numero, texto = "Falar no WhatsApp", mensagem, tamanho = "md", className = "",
}: {
  numero: string; texto?: string; mensagem?: string;
  tamanho?: Tamanho; className?: string;
}) {
  const url = `https://wa.me/${numero.replace(/\D/g, "")}`
    + (mensagem ? `?text=${encodeURIComponent(mensagem)}` : "");
  return (
    <Botao href={url} externo variante="whats" tamanho={tamanho} className={className}>
      <IconeWhatsApp tamanho={tamanho === "lg" ? 22 : 18} />
      {texto}
    </Botao>
  );
}
