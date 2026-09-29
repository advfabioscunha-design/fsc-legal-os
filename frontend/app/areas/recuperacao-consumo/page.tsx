import AreaLanding from "../../components/AreaLanding";
import { IlustraEnergia } from "../../components/ui/Ilustracoes";

export const metadata = {
  title: "Recuperação de consumo de energia | FC Advocacia",
  description:
    "Cobrança retroativa por TOI, ameaça de corte e negativação. Anulação da recuperação de consumo apurada sem perícia imparcial.",
};

export default function Page() {
  return (
    <AreaLanding
      titulo="Recuperação de consumo de energia"
      subnichos="TOI • Cobrança retroativa • Corte indevido • Negativação"
      chamada="A distribuidora lavrou um termo de ocorrência, calculou sozinha quanto você deveria ter consumido e mandou a conta. Esse cálculo tem regra, e quase nunca ela é seguida."
      ilustracao={<IlustraEnergia className="h-64 w-64 text-white/70" />}
      dores={[
        "Fatura retroativa de milhares de reais por suposta irregularidade no medidor.",
        "Acusação apoiada apenas no TOI lavrado pela própria distribuidora.",
        "Ameaça de corte, ou energia já cortada, para forçar o pagamento.",
        "Cálculo feito por estimativa, sem perícia imparcial e sem chance de defesa.",
        "Nome negativado enquanto a dívida cresce todo mês.",
      ]}
      solucoes={[
        "Pedido urgente para religar a energia e impedir novo corte por dívida antiga.",
        "Anulação da recuperação de consumo apurada sem perícia imparcial e sem contraditório.",
        "Impugnação do critério de estimativa usado para chegar ao valor cobrado.",
        "Retirada da negativação enquanto a cobrança estiver sendo discutida.",
        "Pedido de indenização quando houver corte indevido ou cobrança sem base.",
      ]}
      documentos={[
        "Cópia do TOI, o termo de ocorrência e inspeção",
        "Fatura com a cobrança retroativa",
        "Faturas dos doze meses anteriores à inspeção",
        "Aviso de corte ou de negativação",
        "Foto do medidor e do local, se possível",
      ]}
    />
  );
}
