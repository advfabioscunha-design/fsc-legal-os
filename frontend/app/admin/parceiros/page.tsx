"use client";

import { useCallback, useEffect, useState } from "react";
import PainelLayout from "../../components/PainelLayout";
import { supabase } from "@/lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* ADVOGADOS PARCEIROS — a mesa de quem decide.
 *
 * Esta tela é do administrador, e só dele. O operador trabalha nos
 * casos; quem decide quem trabalha é quem responde pelo escritório.
 *
 * A ORDEM DAS COISAS NÃO É DECORATIVA
 *
 * Quem está em análise aparece primeiro, sempre. É o único grupo em que
 * alguém está esperando do outro lado — um advogado que se cadastrou,
 * viu "em análise" e não pode fazer nada até alguém aqui clicar. Deixar
 * isso misturado no meio da lista é o jeito de esquecer por uma semana.
 *
 * APROVAR NÃO É DAR ACESSO A CASO
 *
 * Aprovar diz "este advogado existe e é quem diz ser". Quem dá acesso é
 * a PARCERIA, caso a caso. Um parceiro aprovado sem parceria continua
 * vendo lista vazia — e isso está certo. A tela separa as duas coisas
 * de propósito, porque confundi-las é como se vaza uma carteira.
 */

type Parceiro = {
  id: string; nome: string; email?: string; whatsapp?: string;
  oab_numero?: string; oab_uf?: string; cpf_cnpj?: string;
  status: string; casos_ativos: number; falta_dados_bancarios: boolean;
  pode_usar_ia: boolean; pode_falar_com_cliente: boolean;
  criado_em?: string; observacao?: string;
};

export default function AdminParceiros() {
  const [lista, setLista] = useState<Parceiro[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState("");

  const chamar = useCallback(async (caminho: string, opcoes: any = {}) => {
    const { data } = await supabase.auth.getSession();
    const r = await fetch(`${API}${caminho}`, {
      ...opcoes,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${data.session?.access_token}`,
        ...(opcoes.headers || {}),
      },
    });
    const d = await r.json().catch(() => ({} as any));
    return { ok: r.ok, status: r.status, dados: d };
  }, []);

  const carregar = useCallback(async () => {
    const r = await chamar("/api/v1/admin/parceiros");
    if (!r.ok) {
      setErro(r.status === 403
        ? "Só o administrador abre esta tela."
        : (r.dados?.detail || "Não consegui carregar os parceiros."));
      setLista([]);
    } else {
      setErro("");
      setLista(Array.isArray(r.dados) ? r.dados : []);
    }
    setCarregando(false);
  }, [chamar]);

  useEffect(() => { carregar(); }, [carregar]);

  async function agir(id: string, caminho: string, corpo: any = {}) {
    setOcupado(id);
    const r = await chamar(`/api/v1/admin/parceiros/${id}/${caminho}`, {
      method: "POST", body: JSON.stringify(corpo),
    });
    setOcupado("");
    if (!r.ok) { alert(r.dados?.detail || "Não foi possível concluir."); return; }
    carregar();
  }

  const emAnalise = lista.filter((p) => p.status === "PENDENTE");
  const ativos = lista.filter((p) => p.status === "ATIVO");
  const fora = lista.filter((p) => !["PENDENTE", "ATIVO"].includes(p.status));

  const Cartao = ({ p }: { p: Parceiro }) => (
    <li className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
      <div className="flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-white">{p.nome}</p>
          <p className="mt-0.5 text-[12px] text-white/45">
            {[p.oab_numero && `OAB ${p.oab_numero}/${p.oab_uf}`,
              p.email, p.cpf_cnpj].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${
            p.status === "ATIVO" ? "bg-[#1DB954]/15 text-[#1DB954]"
            : p.status === "PENDENTE" ? "bg-[#E5A44C]/15 text-[#E5A44C]"
            : "bg-[#C0392B]/15 text-[#E57373]"}`}>
            {p.status}
          </span>
          {p.casos_ativos > 0 && (
            <span className="text-[11px] text-white/40">
              {p.casos_ativos} caso{p.casos_ativos > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {p.falta_dados_bancarios && (
        <p className="mt-2 text-[11px] text-[#E5A44C]">
          Sem dados bancários — não dá para repassar a parte dele.
        </p>
      )}

      {/* AS DUAS CHAVES
          Ficam visíveis em todo parceiro, ligadas ou não, porque o
          administrador precisa ver de relance quem já tem o quê — e não
          descobrir ao abrir um a um. */}
      {p.status === "ATIVO" && (
        <div className="mt-3 flex flex-wrap gap-2">
          {([["pode_usar_ia", "usar os agentes de IA"],
             ["pode_falar_com_cliente", "falar com o cliente"]] as const)
            .map(([chave, rotulo]) => (
            <button key={chave} disabled={ocupado === p.id}
              onClick={() => agir(p.id, "permissoes", { [chave]: !p[chave] })}
              className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold transition ${
                p[chave]
                  ? "border-[#1DB954]/40 bg-[#1DB954]/10 text-[#1DB954]"
                  : "border-white/15 text-white/45 hover:border-white/35"}`}>
              {p[chave] ? "✓ " : "○ "}{rotulo}
            </button>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {p.status === "PENDENTE" && (
          <button disabled={ocupado === p.id}
            onClick={() => {
              if (!confirm(`Aprovar ${p.nome}?\n\nConfira a inscrição na OAB `
                + `${p.oab_numero}/${p.oab_uf} antes. Aprovar não dá acesso a `
                + `caso nenhum — isso vem da parceria, caso a caso.`)) return;
              agir(p.id, "aprovar");
            }}
            className="rounded-lg bg-[#1DB954] px-3 py-1.5 text-xs font-bold text-white transition hover:bg-[#17a349] disabled:opacity-40">
            {ocupado === p.id ? "…" : "Aprovar"}
          </button>
        )}
        {p.status === "ATIVO" && (
          <button disabled={ocupado === p.id}
            onClick={() => {
              const m = prompt("Motivo da suspensão (fica registrado):");
              if (m === null) return;
              agir(p.id, "suspender", { motivo: m });
            }}
            className="rounded-lg border border-[#C0392B]/40 px-3 py-1.5 text-xs font-semibold text-[#E57373] transition hover:bg-[#C0392B]/10">
            Suspender
          </button>
        )}
        {p.status === "SUSPENSO" && (
          <button disabled={ocupado === p.id} onClick={() => agir(p.id, "reativar")}
            className="rounded-lg border border-white/20 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:border-white/45">
            Reativar
          </button>
        )}
      </div>
    </li>
  );

  return (
    <PainelLayout titulo="Advogados parceiros">
      {erro && (
        <p className="rounded-xl border border-[#C0392B]/40 bg-[#C0392B]/10 px-4 py-3 text-sm text-white">
          {erro}
        </p>
      )}

      {carregando ? (
        <p className="text-sm text-[#8899AA]">Carregando…</p>
      ) : (
        <div className="space-y-8">

          {emAnalise.length > 0 && (
            <section>
              <h2 className="mb-1 font-display text-base font-bold text-[#E5A44C]">
                Esperando a sua análise ({emAnalise.length})
              </h2>
              <p className="mb-3 text-[12px] leading-relaxed text-white/45">
                Estes advogados se cadastraram e estão parados até alguém aqui
                decidir. Confira a inscrição na OAB antes de aprovar — é a
                única conferência que o sistema não faz sozinho.
              </p>
              <ul className="space-y-2">
                {emAnalise.map((p) => <Cartao key={p.id} p={p} />)}
              </ul>
            </section>
          )}

          <section>
            <h2 className="mb-1 font-display text-base font-bold text-white">
              Parceiros ativos ({ativos.length})
            </h2>
            <p className="mb-3 text-[12px] leading-relaxed text-white/45">
              Aprovado não é o mesmo que ter acesso: cada um vê apenas as causas
              em que há parceria dele. A parceria é criada no card do caso, com
              o percentual combinado.
            </p>
            <ul className="space-y-2">
              {ativos.map((p) => <Cartao key={p.id} p={p} />)}
              {ativos.length === 0 && (
                <li className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5 text-center text-sm text-white/45">
                  Nenhum parceiro ativo ainda.
                </li>
              )}
            </ul>
          </section>

          {fora.length > 0 && (
            <section>
              <h2 className="mb-3 font-display text-base font-bold text-white/60">
                Suspensos e encerrados ({fora.length})
              </h2>
              <ul className="space-y-2">
                {fora.map((p) => <Cartao key={p.id} p={p} />)}
              </ul>
            </section>
          )}
        </div>
      )}
    </PainelLayout>
  );
}
