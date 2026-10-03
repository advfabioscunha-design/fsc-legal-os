"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "../../../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* O CASO, PELOS OLHOS DO PARCEIRO.
 *
 * Tudo nesta tela passou por duas portas no servidor: a que pergunta se
 * ele pode chamar a rota, e a que pergunta se AQUELE caso é da parceria
 * dele. Trocar o id no endereço devolve 404 — a mesma resposta que um
 * caso inexistente, de propósito: dizer "este caso existe, mas não é
 * seu" já entrega que o escritório tem aquele processo.
 *
 * O QUE ELE NÃO VÊ, E POR QUÊ
 *
 * Não vê o repasse ao cliente nem a composição completa dos honorários.
 * Vê a base e a parte dele. Quem é parceiro hoje pode ser concorrente
 * amanhã, e margem é informação de quem corre o risco do escritório.
 */

export default function CasoDoParceiro() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [dados, setDados] = useState<any>(null);
  const [mensagens, setMensagens] = useState<any[]>([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  const [recado, setRecado] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const arquivoRef = useRef<HTMLInputElement | null>(null);

  const [tarefa, setTarefa] = useState({ titulo: "", descricao: "", prazo: "" });
  const [abrirTarefa, setAbrirTarefa] = useState(false);

  const chamar = useCallback(async (caminho: string, opcoes: any = {}) => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) { router.replace("/entrar"); return null; }
    const r = await fetch(`${API}${caminho}`, {
      ...opcoes,
      headers: {
        Authorization: `Bearer ${data.session.access_token}`,
        ...(opcoes.body instanceof FormData
          ? {} : { "Content-Type": "application/json" }),
        ...(opcoes.headers || {}),
      },
    });
    const d = await r.json().catch(() => ({} as any));
    return { ok: r.ok, status: r.status, dados: d };
  }, [router]);

  const carregar = useCallback(async () => {
    const c = await chamar(`/api/v1/parceiro/caso/${id}`);
    if (!c) return;
    if (!c.ok) {
      setErro(c.status === 404
        ? "Este caso não está na sua parceria."
        : (c.dados?.detail || "Não consegui abrir o caso."));
      setCarregando(false);
      return;
    }
    setDados(c.dados);
    const m = await chamar(`/api/v1/parceiro/caso/${id}/mensagens`);
    if (m?.ok) setMensagens(Array.isArray(m.dados) ? m.dados : []);
    setCarregando(false);
  }, [chamar, id]);

  useEffect(() => { carregar(); }, [carregar]);

  async function escrever() {
    const texto = recado.trim();
    if (!texto) return;
    setEnviando(true);
    const r = await chamar(`/api/v1/parceiro/caso/${id}/mensagens`, {
      method: "POST", body: JSON.stringify({ conteudo: texto }),
    });
    setEnviando(false);
    if (!r?.ok) { setAviso(r?.dados?.detail || "Não consegui enviar."); return; }
    setRecado(""); setAviso(""); carregar();
  }

  async function anexar(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const corpo = new FormData();
    corpo.append("arquivo", f);
    setEnviando(true);
    const r = await chamar(`/api/v1/parceiro/caso/${id}/documentos`, {
      method: "POST", body: corpo,
    });
    setEnviando(false);
    if (arquivoRef.current) arquivoRef.current.value = "";
    if (!r?.ok) { setAviso(r?.dados?.detail || "Não consegui anexar."); return; }
    setAviso("Documento anexado à pasta do caso."); carregar();
  }

  async function criarTarefa() {
    if (!tarefa.titulo.trim()) return;
    setEnviando(true);
    const r = await chamar(`/api/v1/parceiro/caso/${id}/tarefas`, {
      method: "POST", body: JSON.stringify(tarefa),
    });
    setEnviando(false);
    if (!r?.ok) { setAviso(r?.dados?.detail || "Não consegui criar a tarefa."); return; }
    setTarefa({ titulo: "", descricao: "", prazo: "" });
    setAbrirTarefa(false); setAviso("Tarefa criada."); carregar();
  }

  const campo = "w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2.5 "
    + "text-sm text-white outline-none focus:border-[#C9A84C]";

  if (carregando) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A1628] text-sm text-white/60">
        Abrindo o caso…
      </main>
    );
  }

  if (erro) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#0A1628] px-5 text-white">
        <p className="max-w-sm text-center text-sm text-white/70">{erro}</p>
        <a href="/parceiro"
          className="rounded-lg border border-white/20 px-4 py-2 text-sm">
          voltar aos meus casos
        </a>
      </main>
    );
  }

  const c = dados?.caso || {};
  const pa = dados?.parceria || {};

  return (
    <main className="min-h-screen bg-[#0A1628] px-5 py-8 font-sans text-white">
      <div className="mx-auto max-w-3xl">

        <a href="/parceiro" className="text-xs text-white/45 hover:text-white">
          ← meus casos
        </a>

        <header className="mt-3">
          <h1 className="font-display text-2xl font-bold">
            {c.titulo || "Causa sem título"}
          </h1>
          <p className="mt-1 text-sm text-white/45">
            {[c.numero_atendimento, c.grupo, c.estado, c.numero_processo]
              .filter(Boolean).join(" · ")}
          </p>
          {pa.percentual != null && (
            <p className={`mt-2 inline-block rounded px-2.5 py-1 text-xs font-bold ${
              pa.aprovada_em ? "bg-[#1DB954]/15 text-[#1DB954]"
                             : "bg-[#E5A44C]/15 text-[#E5A44C]"}`}>
              Sua parte: {pa.percentual}%
              {!pa.aprovada_em && " — aguardando aprovação do escritório"}
            </p>
          )}
        </header>

        {dados?.cliente?.nome && (
          <section className="mt-6 rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <p className="text-xs uppercase tracking-wide text-white/40">Cliente</p>
            <p className="mt-1 font-semibold">{dados.cliente.nome}</p>
            <p className="text-[13px] text-white/50">
              {[dados.cliente.whatsapp, dados.cliente.email]
                .filter(Boolean).join(" · ")}
            </p>
          </section>
        )}

        {/* ── DOCUMENTOS ─────────────────────────────────────── */}
        <section className="mt-6 rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-base font-bold">Documentos do caso</h2>
            <button onClick={() => arquivoRef.current?.click()} disabled={enviando}
              className="rounded-lg bg-[#2D7DD2] px-3 py-1.5 text-xs font-bold text-white transition hover:bg-[#256bb3] disabled:opacity-40">
              {enviando ? "…" : "+ anexar documento"}
            </button>
            <input ref={arquivoRef} type="file" onChange={anexar} className="hidden" />
          </div>

          <ul className="mt-3 space-y-1.5">
            {(dados?.documentos || []).map((d: any) => (
              <li key={d.id}>
                <a href={`${API}/api/v1/parceiro/caso/${id}/documentos/${d.id}/baixar`}
                  target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-[13px] text-white/75 transition hover:border-white/30">
                  <span className="truncate">
                    {d.observacao || d.tipo}
                  </span>
                  <span className="ml-auto shrink-0 text-[11px] text-white/35">
                    {d.criado_em ? new Date(d.criado_em).toLocaleDateString("pt-BR") : ""}
                  </span>
                </a>
              </li>
            ))}
            {(dados?.documentos || []).length === 0 && (
              <li className="text-[13px] text-white/35">
                Nenhum documento na pasta ainda.
              </li>
            )}
          </ul>
        </section>

        {/* ── TAREFAS ────────────────────────────────────────── */}
        <section className="mt-6 rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-base font-bold">Tarefas</h2>
            <button onClick={() => setAbrirTarefa((v) => !v)}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/70 transition hover:border-white/40">
              {abrirTarefa ? "fechar" : "+ nova tarefa"}
            </button>
          </div>

          {abrirTarefa && (
            <div className="mt-3 space-y-2">
              <input value={tarefa.titulo} placeholder="O que precisa ser feito"
                onChange={(e) => setTarefa({ ...tarefa, titulo: e.target.value })}
                className={campo} />
              <textarea value={tarefa.descricao} rows={2} placeholder="Detalhe, se precisar"
                onChange={(e) => setTarefa({ ...tarefa, descricao: e.target.value })}
                className={campo} />
              <label className="block text-[11px] text-white/45">
                Prazo (deixe em branco para hoje)
                <input type="date" value={tarefa.prazo}
                  onChange={(e) => setTarefa({ ...tarefa, prazo: e.target.value })}
                  className={`mt-1 ${campo}`} />
              </label>
              <button onClick={criarTarefa} disabled={enviando}
                className="w-full rounded-lg bg-[#C9A84C] px-4 py-2.5 text-sm font-bold text-[#0A1628] disabled:opacity-40">
                Criar tarefa
              </button>
            </div>
          )}

          <ul className="mt-3 space-y-1.5">
            {(dados?.tarefas || []).slice(0, 10).map((t: any) => (
              <li key={t.id} className="rounded-lg border border-white/10 px-3 py-2 text-[13px]">
                <span className={t.status === "FEITA" ? "text-white/35 line-through" : ""}>
                  {t.titulo}
                </span>
                {t.data && (
                  <span className="ml-2 text-[11px] text-white/35">
                    {new Date(t.data + "T00:00").toLocaleDateString("pt-BR")}
                  </span>
                )}
              </li>
            ))}
            {(dados?.tarefas || []).length === 0 && (
              <li className="text-[13px] text-white/35">Nenhuma tarefa.</li>
            )}
          </ul>
        </section>

        {/* ── CONVERSA COM A EQUIPE ──────────────────────────── */}
        <section className="mt-6 rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
          <h2 className="font-display text-base font-bold">Conversa com o escritório</h2>
          <p className="mt-1 text-[12px] leading-relaxed text-white/40">
            Esta conversa é interna, entre o senhor e a equipe. O cliente não lê
            o que é escrito aqui.
          </p>

          <div className="mt-3 max-h-80 space-y-2 overflow-y-auto">
            {mensagens.map((m) => (
              <div key={m.id} className="rounded-lg bg-black/20 px-3 py-2">
                <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-white/80">
                  {m.conteudo}
                </p>
                <p className="mt-1 text-[10px] text-white/30">
                  {m.criado_em ? new Date(m.criado_em).toLocaleString("pt-BR") : ""}
                </p>
              </div>
            ))}
            {mensagens.length === 0 && (
              <p className="text-[13px] text-white/35">Nenhuma mensagem ainda.</p>
            )}
          </div>

          <textarea value={recado} rows={3} placeholder="Escreva para a equipe…"
            onChange={(e) => setRecado(e.target.value)}
            className={`mt-3 ${campo}`} />
          <button onClick={escrever} disabled={enviando || !recado.trim()}
            className="mt-2 w-full rounded-lg bg-[#C9A84C] px-4 py-2.5 text-sm font-bold text-[#0A1628] disabled:opacity-40">
            {enviando ? "Enviando…" : "Enviar"}
          </button>
        </section>

        {aviso && (
          <p className="mt-4 rounded-xl bg-white/5 px-4 py-3 text-[13px] text-white/70">
            {aviso}
          </p>
        )}
      </div>
    </main>
  );
}
