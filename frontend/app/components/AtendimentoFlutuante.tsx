"use client";
import { usePathname } from "next/navigation";
import AtendimentoChat from "./AtendimentoChat";
import AtendimentoWhats from "./AtendimentoWhats";

/* Os botões flutuantes de atendimento são do SITE — existem para quem
   chega de fora e precisa falar com o escritório.

   Dentro da plataforma de trabalho da equipe eles não fazem sentido: o
   advogado não abre um chat de captação para falar consigo mesmo, e os
   dois círculos ficavam por cima do canto onde moram os botões de ação
   das telas. Como ficavam no layout raiz, apareciam em tudo.

   A lista abaixo é a das telas internas. Fora delas — site, portal,
   área do cliente, assinatura de contrato — nada muda. */
const INTERNAS = new Set([
  "inicio", "crm", "contratos", "judicial", "recebimento", "processos",
  "intimacoes", "agenda", "admin", "assistente", "equipe", "documento",
  "entrar",
  // a sala de atendimento também fica de fora: dois círculos por cima
  // do vídeo, durante uma conversa gravada, só atrapalham.
  "atendimento",
]);

export default function AtendimentoFlutuante() {
  const pathname = usePathname() || "/";
  // primeiro segmento: "/contratos/123" → "contratos"
  // (cuidado: "contrato", do site, é diferente de "contratos", da equipe)
  const raiz = pathname.split("/")[1] || "";
  if (INTERNAS.has(raiz)) return null;

  return (
    <>
      <AtendimentoChat variant="floating" />
      <AtendimentoWhats variant="floating" />
    </>
  );
}
