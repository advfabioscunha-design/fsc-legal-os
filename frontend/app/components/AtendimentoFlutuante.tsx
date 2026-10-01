"use client";
import { usePathname } from "next/navigation";
import AtendimentoChat from "./AtendimentoChat";
import AtendimentoWhats from "./AtendimentoWhats";

/* Os botões flutuantes de atendimento são do SITE — existem para quem
   chega de fora e precisa falar com o escritório.

   Dentro da plataforma de trabalho da equipe eles não fazem sentido: o
   advogado não abre um chat de captação para falar consigo mesmo, e os
   dois círculos ficam por cima do canto onde moram os botões de ação
   das telas.

   A LISTA ERA AO CONTRÁRIO, E ERA O DEFEITO

   Antes aqui havia a lista das telas INTERNAS, e tudo que não estivesse
   nela ganhava os dois círculos. Isso significava que toda tela nova da
   equipe nascia com o chat de captação por cima dos botões, e só se
   descobria quando alguém reclamava. Aconteceu com tarefas, com
   pendências, com o balcão, com a área do cliente, e de novo com a mesa
   do documento.

   Agora a lista é a das telas PÚBLICAS, que são poucas e mudam pouco.
   Tela nova nasce sem os círculos, que é o certo: a plataforma tem
   muito mais telas de trabalho do que páginas de site, e esquecer de
   tirar é mais provável do que esquecer de pôr. */
const PUBLICAS = new Set([
  "",              // a página inicial do site
  "areas",         // as áreas de atuação
  "contrato",      // o fluxo de contrato pelo site, antes de haver conta
  "portal",
  "privacidade",
]);

export default function AtendimentoFlutuante() {
  const pathname = usePathname() || "/";
  // primeiro segmento: "/contratos/123" → "contratos"
  // (cuidado: "contrato", do site, é diferente de "contratos", da equipe)
  const raiz = pathname.split("/")[1] || "";
  if (!PUBLICAS.has(raiz)) return null;

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
