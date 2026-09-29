import AreaLanding from "../../components/AreaLanding";
import { IlustraImobiliario } from "../../components/ui/Ilustracoes";

export const metadata = {
  title: "Distrato imobiliário | FC Advocacia",
  description:
    "Obra atrasada, retenção abusiva no distrato e devolução de valores pagos à construtora. Análise do contrato antes de qualquer proposta.",
};

export default function Page() {
  return (
    <AreaLanding
      titulo="Distrato imobiliário"
      subnichos="Atraso de obra • Devolução de valores • Cláusula abusiva • Vício construtivo"
      chamada="Comprou na planta e a obra atrasou, ou quer desfazer o negócio e a construtora quer reter quase tudo. A lei limita o quanto ela pode reter."
      ilustracao={<IlustraImobiliario className="h-64 w-64 text-white/70" />}
      dores={[
        "Entrega da obra passou do prazo, inclusive da tolerância de 180 dias.",
        "Construtora quer reter a maior parte do que já foi pago.",
        "Taxa de corretagem, SATI e multas que ninguém explicou na assinatura.",
        "Chaves entregues com defeito de construção que a construtora não resolve.",
      ]}
      solucoes={[
        "Leitura do contrato para separar o que é cláusula válida do que é abusivo.",
        "Ação de devolução com o maior percentual que o caso permitir.",
        "Cobrança de indenização pelo período de atraso, quando cabível.",
        "Acompanhamento do caso fase a fase, com o andamento na sua área da plataforma.",
      ]}
      documentos={[
        "Contrato de compra e venda ou de promessa",
        "Comprovantes de todas as parcelas pagas",
        "Correspondência trocada com a construtora",
        "Laudo, foto ou vídeo do defeito, se houver",
        "Documento de identidade e comprovante de endereço",
      ]}
    />
  );
}
