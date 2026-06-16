import AreaLanding from "../../components/AreaLanding";

export const metadata = { title: "Recuperação de Consumo de Energia Elétrica | FC Advocacia" };

export default function Page() {
  return (
    <AreaLanding
      titulo="Recuperação de Consumo de Energia Elétrica"
      subnichos="Multa por Irregularidade • Recuperação de Consumo • TOI • Corte Indevido"
      chamada="A concessionária aplicou uma cobrança retroativa enorme alegando 'recuperação de consumo' ou irregularidade no medidor? Essa cobrança pode ser ilegal — e você não precisa pagar para ter a energia religada."
      dores={[
        "Conta retroativa de milhares de reais por suposta 'recuperação de consumo'.",
        "Acusação de fraude/irregularidade no medidor com base só no TOI (Termo de Ocorrência) feito pela própria distribuidora.",
        "Ameaça de corte ou energia já cortada como forma de pressão para você pagar.",
        "Multa e cálculo unilateral, sem perícia independente e sem direito de defesa.",
        "Negativação do seu nome e cobrança que cresce a cada mês.",
      ]}
      solucoes={[
        "Ação para suspender a cobrança e impedir/cancelar o corte por dívida pretérita (o corte só é legítimo para conta atual).",
        "Anulação da 'recuperação de consumo' baseada em TOI unilateral, sem perícia técnica imparcial e sem contraditório (CDC e jurisprudência do STJ).",
        "Impugnação do cálculo retroativo e dos critérios de estimativa usados pela concessionária.",
        "Pedido de tutela de urgência para religar a energia e retirar a negativação do seu nome.",
        "Quando cabível, indenização por danos morais pelo corte indevido e pela cobrança abusiva.",
      ]}
    />
  );
}
