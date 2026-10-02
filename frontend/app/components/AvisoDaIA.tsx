"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* A FAIXA QUE APARECE ANTES DE A PESSOA CLICAR.
 *
 * Quando a conta de IA bloqueia, todo agente para junto: redator,
 * revisor, atendente, negociador, esteira. Até aqui o operador só
 * descobria isso DEPOIS de abrir um pedido, clicar num botão e tomar um
 * erro em inglês — e aí ele clicava de novo, e de novo, achando que era
 * defeito do sistema.
 *
 * A faixa diz o que houve e o que fazer, antes do clique. Ela só
 * aparece quando há problema: tela cheia de aviso verde dizendo que
 * está tudo bem é tela que ninguém lê.
 */
export default function AvisoDaIA() {
  const [estado, setEstado] = useState<any>(null);

  useEffect(() => {
    let vivo = true;
    const conferir = async () => {
      try {
        const r = await fetch(`${API}/api/v1/ia/estado`);
        const j = await r.json().catch(() => null);
        if (vivo) setEstado(j);
      } catch { /* sem resposta, sem faixa: não inventa problema */ }
    };
    conferir();
    // De minuto em minuto. Barato, e some sozinha quando a conta volta.
    const t = setInterval(conferir, 60000);
    return () => { vivo = false; clearInterval(t); };
  }, []);

  if (!estado || estado.disponivel !== false) return null;

  const temporario = !!estado.pode_tentar_de_novo;
  return (
    <div className={`mb-4 rounded-xl border p-4 ${temporario
      ? "border-[#E5A44C]/40 bg-[#E5A44C]/5"
      : "border-[#E57373]/40 bg-[#E57373]/5"}`}>
      <p className={`text-[11px] font-bold uppercase tracking-wide ${temporario ? "text-[#E5A44C]" : "text-[#E57373]"}`}>
        {temporario ? "Os agentes estão lentos agora"
                    : "Os agentes estão parados"}
      </p>
      <p className="mt-1.5 text-[12px] leading-relaxed text-white/75">
        {estado.detalhe}
      </p>
      {!temporario && (
        <p className="mt-2 text-[11px] text-white/45">
          Enquanto isso, a esteira não tenta de novo para não encher o
          registro de erro. Os prazos continuam correndo normalmente, e
          nenhum pedido se perdeu.
        </p>
      )}
    </div>
  );
}
