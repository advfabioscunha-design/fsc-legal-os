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
  // Telas de trabalho acrescentadas depois. Toda tela nova da equipe
  // precisa entrar aqui, senão os dois círculos voltam a aparecer por
  // cima dos botões de ação — foi o que aconteceu com estas duas.
  "tarefas", "pendencias",
  // O convite é a primeira tela que um futuro colega vê. Oferecer ali
  // o atendimento ao cliente seria oferecer a porta errada.
  "convite", "acesso-equipe",
  // "atendimento" tem dois sentidos: a esteira da primeira fase do caso
  // (tela da equipe) e a sala de telepresença em /atendimento/<id>. As
  // duas ficam de fora — na sala, dois círculos por cima do vídeo
  // durante uma conversa gravada só atrapalham.
  "atendimento",
  // O BALCÃO JÁ TEM A CONVERSA DELE
  //
  // O pedido tem uma conversa própria, presa ao protocolo, com foto e
  // anexo. O círculo flutuante abre uma segunda conversa, que é de
  // captação e não sabe nada daquele pedido: a pessoa escreve ali
  // achando que fala com quem cuida do documento dela, e ninguém do
  // outro lado faz a ligação. Duas portas para salas diferentes com a
  // mesma cara é pior do que uma porta só.
  "balcao",
]);

export default function AtendimentoFlutuante() {
  const pathname = usePathname() || "/";
  // primeiro segmento: "/contratos/123" → "contratos"
  // (cuidado: "contrato", do site, é diferente de "contratos", da equipe)
  const raiz = pathname.split("/")[1] || "";
  if (INTERNAS.has(raiz)) return null;

  /* UMA COLUNA, NÃO DOIS BOTÕES SOLTOS.

     Cada componente posicionava a si mesmo com `fixed`, e os valores
     escolhidos deixavam dezesseis pixels entre eles, com quatro de
     desalinhamento lateral. Na tela do cliente os dois pareciam um
     borrão só, e no celular um cobria o outro.

     Agora existe um contêiner: alinhamento à direita idêntico para os
     dois, respiro de doze pixels entre eles, e uma margem inferior
     maior no celular para não brigar com a barra do navegador. */
  return (
    <div className="fixed bottom-5 right-4 z-50 flex flex-col items-end gap-3
                    sm:bottom-6 sm:right-6">
      <AtendimentoChat variant="floating" />
      <AtendimentoWhats variant="floating" />
    </div>
  );
}
