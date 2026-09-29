import AreaLanding from "../../components/AreaLanding";
import { IlustraFiscal } from "../../components/ui/Ilustracoes";

export const metadata = {
  title: "Execução fiscal | FC Advocacia",
  description:
    "Bloqueio de conta, penhora e cobrança tributária discutível. Defesa técnica e pedido de desbloqueio do patrimônio.",
};

export default function Page() {
  return (
    <AreaLanding
      titulo="Execução fiscal"
      subnichos="Penhora e bloqueio • Prescrição • Excesso de execução • Certidão negativa"
      chamada="Conta bloqueada por dívida tributária tem prazo para ser contestada, e boa parte dessas cobranças não resiste a uma leitura atenta da certidão de dívida ativa."
      ilustracao={<IlustraFiscal className="h-64 w-64 text-white/70" />}
      dores={[
        "Conta ou bem bloqueado de surpresa, sem você saber de onde veio a dívida.",
        "Cobrança de tributo já pago, já prescrito ou lançado contra a pessoa errada.",
        "Nome com restrição que impede financiamento e certidão negativa.",
        "Citação recebida e prazo correndo, sem saber por onde começar.",
      ]}
      solucoes={[
        "Pedido de desbloqueio do valor penhorado, com demonstração da impenhorabilidade quando for o caso.",
        "Defesa por prescrição, excesso de execução, nulidade da certidão e ilegitimidade.",
        "Pedido de suspensão da exigibilidade quando houver garantia ou parcelamento.",
        "Acompanhamento do processo com aviso de cada movimentação relevante.",
      ]}
      documentos={[
        "Citação ou intimação recebida",
        "Número do processo de execução",
        "Certidão de dívida ativa, se já tiver em mãos",
        "Comprovante de pagamento ou parcelamento do tributo",
        "Extrato do bloqueio da conta",
      ]}
    />
  );
}
