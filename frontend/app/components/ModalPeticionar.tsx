"use client";

import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabaseClient";
import { comoLista, comoObjeto, comoTexto } from "@/lib/listas";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* MODAL DE PETICIONAMENTO — a trava antes do protocolo.

   O fluxo é: escolher a peça → validar → se travar, mostrar o motivo em
   vermelho. Para inicial, a validação confere o kit mínimo de documentos;
   para as demais peças, se ela cabe no momento processual.

   SOBRE O BOTÃO DE FORÇAR: esconder o botão de quem não é admin é
   conveniência de interface, não segurança. Qualquer pessoa com o console
   aberto conseguiria disparar a requisição. Quem realmente barra é o
   backend, que confere o papel no token e devolve 403. Este componente
   pergunta ao servidor quem é o usuário (/meu-perfil) em vez de confiar em
   algo guardado no navegador. */

type Parecer = {
  aprovado: boolean;
  motivo: string;
  faltando?: string[];
  gravidade?: string;
  regra?: string;
  override_usado?: boolean;
  pode_forcar?: boolean;
};

const TIPOS = [
  { v: "INICIAL", l: "Petição inicial" },
  { v: "CONTESTACAO", l: "Contestação" },
  { v: "REPLICA", l: "Réplica" },
  { v: "MANIFESTACAO", l: "Manifestação" },
  { v: "EMBARGOS_DECLARACAO", l: "Embargos de declaração" },
  { v: "APELACAO", l: "Apelação" },
  { v: "AGRAVO_INSTRUMENTO", l: "Agravo de instrumento" },
  { v: "CUMPRIMENTO_SENTENCA", l: "Cumprimento de sentença" },
  { v: "ALEGACOES_FINAIS", l: "Alegações finais" },
  { v: "OUTRA", l: "Outra peça" },
];

export default function ModalPeticionar({
  casoId, aberto, aoFechar, aoLiberar,
}: {
  casoId: string;
  aberto: boolean;
  aoFechar: () => void;
  aoLiberar?: (tipo: string, forcado: boolean) => void;
}) {
  const [tipo, setTipo] = useState("INICIAL");
  const [outra, setOutra] = useState("");
  const [validando, setValidando] = useState(false);
  const [parecer, setParecer] = useState<Parecer | null>(null);
  const [podeForcar, setPodeForcar] = useState(false);
  const [papel, setPapel] = useState("");
  const [justificativa, setJustificativa] = useState("");
  const [forcando, setForcando] = useState(false);
  const [erro, setErro] = useState("");

  // quem pode forçar é o servidor que diz, não o navegador
  useEffect(() => {
    if (!aberto) return;
    (async () => {
      try {
        const { data: sess } = await supabase.auth.getSession();
        const token = sess.session?.access_token;
        if (!token) return;
        const r = await fetch(`${API}/api/v1/meu-perfil`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) return;
        const d = await r.json();
        setPodeForcar(!!d.pode_forcar_peticao);
        setPapel(d.papel || "");
      } catch { /* sem perfil, o botão simplesmente não aparece */ }
    })();
  }, [aberto]);

  useEffect(() => {
    if (!aberto) { setParecer(null); setErro(""); setJustificativa(""); }
  }, [aberto]);

  async function chamar(override: boolean) {
    const nome = tipo === "OUTRA" ? outra.trim() : tipo;
    if (!nome) { setErro("Diga qual é a peça."); return; }
    if (override && justificativa.trim().length < 10) {
      setErro("Escreva a justificativa da liberação — ela fica no histórico do caso.");
      return;
    }
    override ? setForcando(true) : setValidando(true);
    setErro("");
    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      const r = await fetch(`${API}/api/v1/validar-peticionamento`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          caso_id: casoId, tipo_peticao: nome,
          override, justificativa: override ? justificativa : null,
        }),
      });
      const d = await r.json();
      if (r.status === 403) {
        setErro(d.detail || "Você não tem permissão para liberar este peticionamento.");
        return;
      }
      if (!r.ok) { setErro(d.detail || "Não foi possível validar."); return; }
      setParecer(d);
      if (d.aprovado) aoLiberar?.(nome, !!d.override_usado);
    } catch {
      setErro("Falha de conexão. Tente novamente.");
    } finally {
      setValidando(false); setForcando(false);
    }
  }

  if (!aberto) return null;

  const travado = parecer && !parecer.aprovado;
  const impeditivo = parecer?.gravidade === "IMPEDITIVO";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/10 bg-[#0A1628] p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-[#C9A84C]">Peticionar</h3>
            <p className="mt-0.5 text-xs text-white/50">
              Antes de protocolar, a plataforma confere o que for verificável.
            </p>
          </div>
          <button onClick={aoFechar} className="text-white/40 hover:text-white">✕</button>
        </div>

        <label className="mt-4 block text-xs text-white/60">
          Tipo de petição
          <select
            value={tipo}
            onChange={(e) => { setTipo(e.target.value); setParecer(null); }}
            className="mt-1 w-full rounded-lg border border-white/15 bg-[#060D18] px-3 py-2 text-sm text-white"
          >
            {TIPOS.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}
          </select>
        </label>

        {tipo === "OUTRA" && (
          <input
            value={outra}
            onChange={(e) => { setOutra(e.target.value); setParecer(null); }}
            placeholder="Qual peça? Ex.: impugnação ao cumprimento de sentença"
            className="mt-2 w-full rounded-lg border border-white/15 bg-[#060D18] px-3 py-2 text-sm text-white"
          />
        )}

        <p className="mt-2 text-[11px] text-white/40">
          {tipo === "INICIAL"
            ? "Para a inicial, conferimos o kit mínimo: procuração e contrato assinados, documento de identidade e comprovante de endereço."
            : "Para as demais peças, conferimos se ela cabe no último andamento do processo."}
        </p>

        {erro && (
          <p className="mt-3 rounded-lg bg-[#C0392B]/20 px-3 py-2 text-xs text-[#E57373]">{erro}</p>
        )}

        {parecer?.aprovado && (
          <div className="mt-4 rounded-lg border border-[#1DB954]/40 bg-[#1DB954]/10 p-3 text-xs">
            <p className="font-bold text-[#1DB954]">
              {parecer.override_usado ? "✓ Liberado por decisão do administrador" : "✓ Liberado para peticionar"}
            </p>
            <p className="mt-1 text-white/70">{parecer.motivo}</p>
          </div>
        )}

        {travado && (
          <div className={`mt-4 rounded-lg border p-3 text-xs ${
            impeditivo ? "border-[#C0392B]/50 bg-[#C0392B]/15" : "border-[#E5A44C]/50 bg-[#E5A44C]/10"
          }`}>
            <p className={`font-bold ${impeditivo ? "text-[#E57373]" : "text-[#E5A44C]"}`}>
              {impeditivo ? "⛔ Peticionamento travado" : "⚠ Revise antes de protocolar"}
              {parecer?.regra && <span className="ml-2 font-normal text-white/40">regra {parecer.regra}</span>}
            </p>
            <p className="mt-1 text-white/80">{parecer?.motivo}</p>
            {!!parecer?.faltando?.length && (
              <ul className="mt-2 space-y-0.5 text-white/65">
                {comoLista(parecer.faltando).map((f: any, i: number) =>
                  <li key={i}>• {comoTexto(f)}</li>)}
              </ul>
            )}

            {podeForcar ? (
              <div className="mt-3 border-t border-white/10 pt-3">
                <p className="text-white/60">
                  Como <b className="text-white/80">{papel}</b>, o senhor pode
                  seguir assim mesmo. A decisão fica registrada no histórico do
                  caso, com o que a trava apontou.
                </p>
                <textarea
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  rows={2}
                  placeholder="Por que seguir mesmo assim? (obrigatório)"
                  className="mt-2 w-full rounded-lg border border-white/15 bg-[#060D18] px-3 py-2 text-xs text-white"
                />
                <button
                  onClick={() => chamar(true)}
                  disabled={forcando}
                  className="mt-2 w-full rounded-lg border border-[#C0392B]/60 bg-[#C0392B]/25 px-4 py-2 text-xs font-bold text-[#E57373] hover:bg-[#C0392B]/35 disabled:opacity-50"
                >
                  {forcando ? "Registrando…" : "Forçar peticionamento (bypass)"}
                </button>
              </div>
            ) : (
              <p className="mt-3 border-t border-white/10 pt-3 text-white/50">
                Resolva os pontos acima. Se entender que a peça deve ir assim
                mesmo, peça a liberação ao Dr. Fábio Cunha.
              </p>
            )}
          </div>
        )}

        <div className="mt-5 flex gap-2">
          <button
            onClick={() => chamar(false)}
            disabled={validando}
            className="flex-1 rounded-lg bg-[#C9A84C] px-4 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50"
          >
            {validando ? "Validando…" : parecer ? "Validar de novo" : "Validar e peticionar"}
          </button>
          <button onClick={aoFechar} className="rounded-lg border border-white/15 px-4 py-2.5 text-sm text-white/70 hover:text-white">
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
