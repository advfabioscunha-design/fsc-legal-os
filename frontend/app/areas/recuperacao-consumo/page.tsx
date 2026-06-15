import AreaLanding from "../../components/AreaLanding";

export const metadata = { title: "Recuperação de Consumo | FC Advocacia" };

export default function Page() {
  return (
    <AreaLanding
      titulo="Recuperação de Consumo"
      chamada="Os descontos de empréstimos consomem quase toda a sua renda? O superendividamento tem solução prevista em lei para você voltar a respirar."
      dores={[
        "Descontos que comprometem grande parte do salário/benefício.",
        "Várias dívidas ao mesmo tempo, sem conseguir pagar.",
        "Empréstimos e cartões que você não reconhece.",
        "Sensação de que nunca vai sair do vermelho.",
      ]}
      solucoes={[
        "Ação para limitar os descontos a um percentual legal da renda.",
        "Repactuação das dívidas com preservação do mínimo existencial.",
        "Revisão de contratos com juros e encargos abusivos.",
        "Plano para você recuperar o equilíbrio financeiro.",
      ]}
    />
  );
}
