import AreaLanding from "../../components/AreaLanding";

export const metadata = { title: "Distrato Imobiliário | FC Advocacia" };

export default function Page() {
  return (
    <AreaLanding
      titulo="Distrato Imobiliário"
      chamada="Comprou na planta e a obra atrasou? Quer desistir e a construtora quer reter quase tudo? A lei está do seu lado."
      dores={[
        "Atraso na entrega da obra além do prazo de tolerância.",
        "Retenção abusiva de valores no distrato.",
        "Multas e taxas que você nem entende no contrato.",
        "Dificuldade de reaver o dinheiro já pago.",
      ]}
      solucoes={[
        "Análise do contrato para identificar cláusulas abusivas.",
        "Ação para devolução dos valores com a maior restituição possível.",
        "Cobrança de indenização pelo atraso da obra, quando cabível.",
        "Acompanhamento de cada fase até a solução.",
      ]}
    />
  );
}
