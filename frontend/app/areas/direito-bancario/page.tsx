import AreaLanding from "../../components/AreaLanding";

export const metadata = { title: "Direito Bancário | FC Advocacia" };

export default function Page() {
  return (
    <AreaLanding
      titulo="Direito Bancário"
      subnichos="Juros Abusivos • Cartão RMC/RCC • Fraudes PIX • Busca e Apreensão"
      chamada="Bancos e financeiras cometem abusos todos os dias. Nós conhecemos cada brecha para proteger o seu dinheiro e o seu nome."
      dores={[
        "Juros e tarifas abusivos em empréstimos e financiamentos.",
        "Cartão consignado RMC/RCC contratado sem você entender.",
        "Fraudes e golpes via PIX e transferências indevidas.",
        "Veículo em busca e apreensão por contrato abusivo.",
      ]}
      solucoes={[
        "Revisão de contrato para reduzir juros e excluir cobranças indevidas.",
        "Ação contra o RMC/RCC e devolução de valores descontados.",
        "Responsabilização do banco em fraudes de PIX e golpes.",
        "Defesa na busca e apreensão para manter o seu veículo.",
      ]}
    />
  );
}
