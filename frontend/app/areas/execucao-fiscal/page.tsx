import AreaLanding from "../../components/AreaLanding";

export const metadata = { title: "Execução Fiscal | FC Advocacia" };

export default function Page() {
  return (
    <AreaLanding
      titulo="Execução Fiscal"
      chamada="Teve contas ou bens bloqueados por uma dívida tributária? Existem caminhos para desbloquear o seu patrimônio e questionar a cobrança."
      dores={[
        "Bloqueio de contas e bens (penhora) de surpresa.",
        "Cobrança de dívida tributária possivelmente indevida ou prescrita.",
        "Nome negativado e restrições que travam sua vida financeira.",
        "Insegurança sobre como reagir à execução.",
      ]}
      solucoes={[
        "Pedido de desbloqueio de patrimônio (impugnação à penhora).",
        "Defesa técnica: prescrição, excesso de execução e nulidades.",
        "Estratégia para suspender a exigibilidade quando possível.",
        "Proteção do seu patrimônio com acompanhamento próximo.",
      ]}
    />
  );
}
