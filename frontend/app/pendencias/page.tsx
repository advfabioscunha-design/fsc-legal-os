"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PainelLayout from "../components/PainelLayout";
import CaixaArquivada from "../components/CaixaArquivada";
import { useRascunho } from "@/lib/rascunho";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* PENDÊNCIAS — o que alguém anotou que precisa ser feito.

   Prazo nasce de intimação; tarefa nasce do plano do agente. Isto aqui
   nasce da cabeça de quem está cuidando do caso: ligar para a perita,
   juntar o comprovante que o cliente mandou no WhatsApp, conferir se o
   alvará saiu. Sem um lugar, essas coisas ficam no papel da mesa.

   Com data, a pendência entra no plano do dia e da semana junto com os
   prazos. Sem data, fica aqui como lembrete — e não ocupa espaço no
   dia de ninguém. */

const CORES: Record<string, string> = { ALTA: "#C0392B", MEDIA: "#E5A44C", BAIXA: "#8899AA" };

function dataBr(iso?: string | null) {
  if (!iso) return "sem data";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

/* Fora do componente: a caixa de arquivo recarrega quando a função de
   busca muda de identidade. */
async function buscarPendenciasResolvidas() {
  const r = await fetch(`${API}/api/v1/anotacoes?status=RESOLVIDA`);
  const d = await r.json();
  return (Array.isArray(d) ? d : []).map((a: any) => ({
    id: a.id,
    titulo: a.texto,
    detalhe: [a.casos?.clientes?.nome,
              a.numero_processo || a.casos?.numero_processo,
              a.membros_equipe?.nome].filter(Boolean).join(" · "),
    quando: dataBr(a.data_resolver),
    resultado: a.resultado ? `✓ ${a.resultado}` : "",
  }));
}

export default function Pendencias() {
  const [itens, setItens] = useState<any[]>([]);
  const [membros, setMembros] = useState<any[]>([]);
  const [status, setStatus] = useState("ABERTA");
  const [loading, setLoading] = useState(true);

  // formulário. O texto fica guardado: anotação de pendência é
  // escrita devagar, consultando outra tela, e perder no meio é o
  // que faz a pessoa desistir de anotar.
  const [texto, setTexto, limparRascunho] = useRascunho("pendencia-nova");
  const [data, setData] = useState("");
  const [prioridade, setPrioridade] = useState("MEDIA");
  const [responsavel, setResponsavel] = useState("");
  const [busca, setBusca] = useState("");
  const [achados, setAchados] = useState<any[]>([]);
  const [caso, setCaso] = useState<any>(null);
  const [salvando, setSalvando] = useState(false);

  // ações
  const [resolvendo, setResolvendo] = useState<string | null>(null);
  const [resultado, setResultado] = useState("");
  const [reagendando, setReagendando] = useState<string | null>(null);
  const [novaData, setNovaData] = useState("");

  function load() {
    setLoading(true);
    /* No arquivo a lista vem da própria caixa; aqui só os membros, que o
       formulário de anotar usa. */
    const lista = status === "ARQUIVO" ? "ABERTA" : status;
    Promise.all([
      fetch(`${API}/api/v1/anotacoes?status=${lista}`).then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/membros`).then((r) => r.json()).catch(() => []),
    ]).then(([a, m]) => {
      setItens(Array.isArray(a) ? a : []);
      setMembros(Array.isArray(m) ? m : []);
    }).finally(() => setLoading(false));
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  /* Busca do caso por nome do cliente ou número do processo —
     reaproveita a busca global, que já procura nos dois. */
  useEffect(() => {
    if (busca.trim().length < 3) { setAchados([]); return; }
    const t = setTimeout(() => {
      fetch(`${API}/api/v1/buscar?q=${encodeURIComponent(busca)}`)
        .then((r) => r.json())
        .then((d) => setAchados(Array.isArray(d.casos) ? d.casos.slice(0, 6) : []))
        .catch(() => setAchados([]));
    }, 350);
    return () => clearTimeout(t);
  }, [busca]);

  async function salvar() {
    if (texto.trim().length < 3) return;
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/anotacoes`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          texto, data_resolver: data || null, prioridade,
          responsavel_id: responsavel || null,
          caso_id: caso?.id || null,
          numero_processo: caso?.numero_processo || null,
        }),
      });
      if (r.ok) {
        limparRascunho(); setData(""); setCaso(null); setBusca(""); setAchados([]);
        setPrioridade("MEDIA"); setResponsavel("");
        load();
      }
    } finally { setSalvando(false); }
  }

  async function agir(id: string, rota: string, corpo: any) {
    await fetch(`${API}/api/v1/anotacoes/${id}/${rota}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    setResolvendo(null); setResultado(""); setReagendando(null); setNovaData("");
    load();
  }

  const hoje = new Date().toISOString().slice(0, 10);
  const atrasadas = itens.filter((a) => a.data_resolver && a.data_resolver < hoje).length;
  const semData = itens.filter((a) => !a.data_resolver).length;

  return (
    <PainelLayout titulo="Pendências">
      <div className="space-y-4">
        {/* Nova pendência */}
        <section className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
          <h2 className="mb-3 text-sm font-bold text-[#C9A24D]">Anotar uma pendência</h2>

          <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={2}
            placeholder="O que precisa ser feito. Ex.: ligar para a perita e confirmar a data da perícia"
            className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />

          <div className="mt-3 grid gap-3 md:grid-cols-4">
            <div className="md:col-span-2">
              <label className="text-[11px] text-white/50">
                Cliente ou número do processo
              </label>
              {caso ? (
                <div className="mt-1 flex items-center gap-2 rounded-lg border border-[#C9A84C]/40 bg-[#C9A84C]/10 px-3 py-2">
                  <span className="min-w-0 flex-1 truncate text-xs text-white/85">
                    {caso.clientes?.nome || "—"}
                    {caso.numero_processo ? ` · ${caso.numero_processo}` : ""}
                  </span>
                  <button onClick={() => { setCaso(null); setBusca(""); }}
                    className="text-xs text-white/50 hover:text-white">trocar</button>
                </div>
              ) : (
                <div className="relative">
                  <input value={busca} onChange={(e) => setBusca(e.target.value)}
                    placeholder="digite o nome ou o número…"
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
                  {achados.length > 0 && (
                    <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-white/15 bg-[#0B1F3B] shadow-2xl">
                      {achados.map((c) => (
                        <button key={c.id}
                          onClick={() => { setCaso(c); setAchados([]); }}
                          className="block w-full px-3 py-2 text-left text-xs text-white/80 hover:bg-white/5">
                          <b>{c.clientes?.nome || "—"}</b>
                          <span className="ml-2 text-white/45">
                            {c.numero_processo || c.grupo || ""} · {c.estado}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div>
              <label className="text-[11px] text-white/50">Resolver até</label>
              <input type="date" value={data} onChange={(e) => setData(e.target.value)}
                className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm text-white outline-none focus:border-[#C9A84C]" />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-white/50">Prioridade</label>
                <select value={prioridade} onChange={(e) => setPrioridade(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-2 py-2 text-sm outline-none focus:border-[#C9A84C]">
                  <option value="ALTA">Alta</option>
                  <option value="MEDIA">Média</option>
                  <option value="BAIXA">Baixa</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] text-white/50">Responsável</label>
                <select value={responsavel} onChange={(e) => setResponsavel(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-2 py-2 text-sm outline-none focus:border-[#C9A84C]">
                  <option value="">—</option>
                  {membros.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-3">
            <button onClick={salvar} disabled={salvando || texto.trim().length < 3}
              className="rounded-lg bg-[#C9A84C] px-5 py-2 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-40">
              {salvando ? "Salvando…" : "Anotar"}
            </button>
            <span className="text-[11px] text-white/35">
              Com data, entra no plano do dia e da semana junto com os prazos.
              Sem data, fica aqui como lembrete.
            </span>
          </div>
        </section>

        {/* Lista */}
        <div className="flex flex-wrap items-center gap-2">
          {([["ABERTA", "Abertas"], ["RESOLVIDA", "Resolvidas"],
             ["CANCELADA", "Canceladas"], ["TODAS", "Todas"],
             ["ARQUIVO", "Arquivo (resolvidas)"]] as const).map(([k, l]) => (
            <button key={k} onClick={() => setStatus(k)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
                status === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>
              {l}
            </button>
          ))}
          <span className="ml-auto text-xs text-white/45">
            {itens.length} item(ns)
            {atrasadas > 0 && <span className="text-[#C0392B]"> · {atrasadas} com data vencida</span>}
            {semData > 0 && <span> · {semData} sem data</span>}
          </span>
        </div>

        {status === "ARQUIVO" ? (
          /* Resolvida continua valendo como histórico do caso. Sai da
             frente, e apagar é decisão sua, item a item. */
          <CaixaArquivada caixa="anotacoes" titulo="Pendências resolvidas"
            buscar={buscarPendenciasResolvidas} aoLimpar={load} />
        ) : loading ? (
          <p className="text-sm text-[#8899AA]">Carregando…</p>
        ) : itens.length === 0 ? (
          <p className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-white/40">
            Nada anotado aqui.
          </p>
        ) : (
          <div className="space-y-2">
            {itens.map((a) => (
              <div key={a.id} className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
                <div className="flex flex-wrap items-start gap-3">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: CORES[a.prioridade] || "#8899AA" }} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white/90">{a.texto}</p>
                    <p className="mt-0.5 text-xs text-white/45">
                      <span style={{ color: a.data_resolver && a.data_resolver < hoje ? "#C0392B" : undefined }}>
                        {dataBr(a.data_resolver)}
                      </span>
                      {a.casos?.clientes?.nome ? ` · ${a.casos.clientes.nome}` : ""}
                      {a.numero_processo || a.casos?.numero_processo
                        ? ` · ${a.numero_processo || a.casos.numero_processo}` : ""}
                      {a.membros_equipe?.nome ? ` · ${a.membros_equipe.nome}` : ""}
                      {a.adiamentos > 0 ? ` · adiada ${a.adiamentos}×` : ""}
                    </p>
                    {a.resultado && (
                      <p className="mt-1 text-xs text-[#1DB954]">✓ {a.resultado}</p>
                    )}
                  </div>

                  {a.status === "ABERTA" && (
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      {a.caso_id && (
                        <Link href={`/judicial?caso=${a.caso_id}`}
                          className="rounded-md border border-white/15 px-2.5 py-1 text-[11px] text-white/70 hover:text-white">
                          abrir caso
                        </Link>
                      )}
                      {reagendando === a.id ? (
                        <>
                          <input type="date" value={novaData} onChange={(e) => setNovaData(e.target.value)}
                            className="rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-[11px] text-white outline-none" />
                          <button onClick={() => novaData && agir(a.id, "reagendar", { nova_data: novaData })}
                            className="rounded-md bg-[#E5A44C] px-2 py-1 text-[11px] font-bold text-[#0A1628]">mover</button>
                        </>
                      ) : (
                        <button onClick={() => { setReagendando(a.id); setNovaData(a.data_resolver || hoje); }}
                          className="rounded-md border border-white/15 px-2.5 py-1 text-[11px] text-white/70 hover:text-white">
                          reagendar
                        </button>
                      )}
                      <button onClick={() => setResolvendo(resolvendo === a.id ? null : a.id)}
                        className="rounded-md bg-[#1DB954] px-3 py-1 text-[11px] font-bold text-white hover:bg-[#17a349]">
                        resolver
                      </button>
                    </div>
                  )}
                </div>

                {resolvendo === a.id && (
                  <div className="mt-3 rounded-lg border border-white/10 bg-[#0A1628] p-3">
                    <label className="text-[11px] text-white/60">
                      O que foi feito? Isto vai para o histórico do cliente.
                    </label>
                    <input value={resultado} onChange={(e) => setResultado(e.target.value)}
                      placeholder="Ex.: perita confirmou a data para o dia 12/11, às 9h"
                      className="mt-1 w-full rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
                    <div className="mt-2 flex gap-2">
                      <button onClick={() => agir(a.id, "resolver", { resultado })}
                        className="rounded-md bg-[#1DB954] px-4 py-1.5 text-xs font-bold text-white">
                        registrar e concluir
                      </button>
                      <button onClick={() => agir(a.id, "cancelar", { motivo: resultado || "cancelada" })}
                        className="rounded-md border border-white/15 px-3 py-1.5 text-xs text-white/60 hover:text-white">
                        cancelar a pendência
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </PainelLayout>
  );
}
