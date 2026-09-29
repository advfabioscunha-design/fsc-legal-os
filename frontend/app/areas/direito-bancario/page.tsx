import AreaLanding from "../../components/AreaLanding";
import { IlustraBancario } from "../../components/ui/Ilustracoes";

export const metadata = {
  title: "Direito bancário | FC Advocacia",
  description:
    "Juros abusivos, cartão consignado, fraude por PIX e busca e apreensão de veículo. Análise do contrato e do caso antes de qualquer proposta.",
};

export default function Page() {
  return (
    <AreaLanding
      titulo="Direito bancário"
      subnichos="Juros abusivos • Cartão RMC e RCC • Fraude por PIX • Busca e apreensão"
      chamada="Banco e financeira erram, e o erro costuma sair do bolso do cliente. O primeiro passo é ler o contrato e conferir o que foi cobrado."
      ilustracao={<IlustraBancario className="h-64 w-64 text-white/70" />}
      dores={[
        "Juros e tarifas acima do que foi combinado no financiamento.",
        "Cartão consignado RMC ou RCC descontado do benefício sem você ter pedido.",
        "Transferência por PIX feita por golpe e o banco se recusa a devolver.",
        "Veículo em busca e apreensão por causa de parcela discutida em juízo.",
      ]}
      solucoes={[
        "Revisão do contrato para apontar juros e encargos cobrados fora da regra.",
        "Ação para encerrar o RMC ou RCC e devolver o que foi descontado.",
        "Responsabilização do banco pela falha de segurança em fraude e golpe.",
        "Defesa na busca e apreensão, com pedido para manter o veículo com você.",
      ]}
      documentos={[
        "Contrato do empréstimo ou financiamento",
        "Extrato das parcelas pagas",
        "Extrato do benefício, quando houver desconto em folha",
        "Comprovante da transferência contestada",
        "Documento de identidade e comprovante de endereço",
      ]}
    />
  );
}
