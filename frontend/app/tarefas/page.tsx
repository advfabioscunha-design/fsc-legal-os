"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PainelLayout from "../components/PainelLayout";
import CaixaArquivada from "../components/CaixaArquivada";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* TAREFAS — o que fazer hoje, e o que vem na semana.

   A diferença para a tela de Intimações: lá estão os prazos, que são
   fatos do processo. Aqui está a DECISÃO do escritório sobre quando
   fazer o trabalho — muda de dia, muda de responsável, é adiada, é
   concluída. Por isso cada tarefa mostra por que está na prioridade em
   que está: prioridade sem justificativa ninguém confere, e a lista
   perde a autoridade em uma semana. */

const CORES: Record<string, string> = {
  ALTA: "#C0392B", MEDIA: "#E5A44C", BAIXA: "#8899AA",
};

function dataBr(iso?: string | null) {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

function diaDaSemana(iso: string) {
  const nomes = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
  return nomes[new Date(iso + "T12:00").getDay()];
}

/* Fora do componente: a caixa de arquivo recarrega quando a função de
   busca muda de identidade, e uma função redefinida a cada render
   recarregaria sem parar. */
async function buscarTarefasFeitas() {
  const r = await fetch(`${API}/api/v1/tarefas?status=FEITA`);
  const d = await r.json();
  return (Array.isArray(d) ? d : []).map((t: any) => ({
    id: t.id,
    titulo: t.titulo,
    detalhe: [t.casos?.clientes?.nome, t.casos?.numero_processo]
      .filter(Boolean).join(" · "),
    quando: dataBr(t.data),
    resultado: t.nota || "",
  }));
}

export default function Tarefas() {
  const [aba, setAba] = useState<"hoje" | "semana" | "todas" | "arquivo">("hoje");
  const [tarefas, setTarefas] = useState<any[]>([]);
  const [membros, setMembros] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [rodando, setRodando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [reagendando, setReagendando] = useState<string | null>(null);
  const [novaData, setNovaData] = useState("");

  const hoje = new Date().toISOString().slice(0, 10);
  const daquiUmaSemana = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);

  function load() {
    setLoading(true);
    const faixa = aba === "hoje" ? `&de=${hoje}&ate=${hoje}`
      : aba === "semana" ? `&de=${hoje}&ate=${daquiUmaSemana}` : "";
    Promise.all([
      fetch(`${API}/api/v1/tarefas?status=${aba === "todas" ? "TODAS" : "ABERTA"}${faixa}`)
        .then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/membros`).then((r) => r.json()).catch(() => []),
    ]).then(([t, m]) => {
      setTarefas(Array.isArray(t) ? t : []);
      setMembros(Array.isArray(m) ? m : []);
    }).finally(() => setLoading(false));
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [aba]);

  async function montar(qual: "plano-do-dia" | "plano-da-semana") {
    setRodando(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/tarefas/${qual}`, { method: "POST" });
      const d = await r.json().catch(() => ({} as any));
      setAviso(r.ok
        ? `${d.criadas ?? 0} tarefa(s) criada(s)${d.semana ? ` para ${d.semana}` : ""}.`
        : (d.detail || `Erro ${r.status}`));
      load();
    } catch { setAviso("Não foi possível falar com o servidor."); }
    finally { setRodando(false); }
  }

  async function agir(id: string, rota: string, corpo: any) {
    await fetch(`${API}/api/v1/tarefas/${id}/${rota}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    setReagendando(null); setNovaData("");
    load();
  }

  const porDia: Record<string, any[]> = {};
  tarefas.forEach((t) => { (porDia[t.data] = porDia[t.data] || []).push(t); });
  const dias = Object.keys(porDia).sort();
  const altas = tarefas.filter((t) => t.prioridade === "ALTA").length;
  const atrasadas = tarefas.filter((t) => t.data < hoje && t.status !== "FEITA").length;

  return (
    <PainelLayout titulo="Tarefas">
      <div className="space-y-4">
        <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { r: "Abertas", v: tarefas.length, c: "#2D7DD2" },
            { r: "Prioridade alta", v: altas, c: "#C0392B" },
            { r: "Atrasadas", v: atrasadas, c: "#E5A44C" },
            { r: "Dias com trabalho", v: dias.length, c: "#1DB954" },
          ].map((k) => (
            <div key={k.r} className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
              <p className="text-2xl font-bold" style={{ color: k.c }}>{k.v}</p>
              <p className="mt-0.5 text-xs text-white/55">{k.r}</p>
            </div>
          ))}
        </section>

        <div className="flex flex-wrap items-center gap-2">
          {([["hoje", "Hoje"], ["semana", "Próximos 7 dias"], ["todas", "Todas"],
             ["arquivo", "Arquivo (feitas)"]] as const)
            .map(([k, l]) => (
              <button key={k} onClick={() => setAba(k)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
                  aba === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>
                {l}
              </button>
            ))}
          <button onClick={() => montar("plano-do-dia")} disabled={rodando}
            className="ml-auto rounded-md border border-[#2D7DD2]/60 px-3 py-1.5 text-sm font-semibold text-[#2D7DD2] hover:bg-[#2D7DD2]/10 disabled:opacity-50">
            Montar o dia
          </button>
          <button onClick={() => montar("plano-da-semana")} disabled={rodando}
            className="rounded-md bg-[#2D7DD2] px-3 py-1.5 text-sm font-bold text-white hover:bg-[#3a8ae0] disabled:opacity-50">
            {rodando ? "Montando…" : "Montar a próxima semana"}
          </button>
        </div>

        <p className="text-[11px] text-white/35">
          Sozinho: a controladoria roda às 7h10 todo dia, o Diário é varrido
          terça e quinta às 18h, e o plano da semana seguinte é montado na
          sexta às 18h — horário de Brasília.
        </p>

        {aviso && (
          <p className="rounded-lg border border-[#2D7DD2]/40 bg-[#2D7DD2]/10 px-3 py-2 text-xs text-white/80">{aviso}</p>
        )}

        {aba === "arquivo" ? (
          /* O que já foi feito sai da frente mas continua no arquivo, que
             é o que sustenta a prestação de contas. Apagar é escolha sua,
             item a item. */
          <CaixaArquivada caixa="tarefas" titulo="Tarefas concluídas"
            buscar={buscarTarefasFeitas} aoLimpar={load} />
        ) : loading ? (
          <p className="text-sm text-[#8899AA]">Carregando…</p>
        ) : dias.length === 0 ? (
          <p className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-white/40">
            Nenhuma tarefa aberta neste período. Use “Montar o dia” para o agente
            varrer publicações, prazos e triagem.
          </p>
        ) : dias.map((d) => (
          <section key={d}>
            <div className="mb-2 flex items-baseline gap-2">
              <h2 className="text-sm font-bold text-[#C9A24D]">
                {diaDaSemana(d)}, {dataBr(d)}
              </h2>
              {d < hoje && <span className="text-xs text-[#C0392B]">atrasado</span>}
              <span className="text-xs text-white/35">{porDia[d].length} tarefa(s)</span>
            </div>

            <div className="space-y-2">
              {porDia[d].map((t) => (
                <div key={t.id}
                  className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
                  <div className="flex flex-wrap items-start gap-3">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full"
                      style={{ background: CORES[t.prioridade] || "#8899AA" }} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-white/90">{t.titulo}</p>
                      <p className="mt-0.5 text-xs text-white/45">
                        {t.casos?.clientes?.nome ? <b>{t.casos.clientes.nome} · </b> : null}
                        {t.casos?.numero_processo || ""}
                        {t.prazo_fatal ? ` · prazo fatal ${dataBr(t.prazo_fatal)}` : ""}
                      </p>
                      {/* Por que está nesta prioridade — sem isso a
                          ordenação vira opinião da máquina. */}
                      {t.motivo && (
                        <p className="mt-1 text-[11px]" style={{ color: CORES[t.prioridade] }}>
                          {t.prioridade.toLowerCase()}: {t.motivo}
                        </p>
                      )}
                      {t.adiamentos > 0 && (
                        <p className="mt-0.5 text-[11px] text-[#E5A44C]">
                          adiada {t.adiamentos}×
                        </p>
                      )}
                    </div>

                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      <select
                        value={t.responsavel_id || ""}
                        onChange={(e) => agir(t.id, "responsavel",
                          { responsavel_id: e.target.value })}
                        className="rounded border border-white/10 bg-[#0A1628] px-2 py-1 text-[11px] text-white/70 outline-none focus:border-[#C9A84C]">
                        <option value="">sem responsável</option>
                        {membros.map((m) => (
                          <option key={m.id} value={m.id}>{m.nome}</option>
                        ))}
                      </select>

                      {reagendando === t.id ? (
                        <>
                          <input type="date" value={novaData}
                            onChange={(e) => setNovaData(e.target.value)}
                            className="rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-[11px] text-white outline-none" />
                          <button onClick={() => novaData && agir(t.id, "reagendar", { nova_data: novaData })}
                            className="rounded-md bg-[#E5A44C] px-2 py-1 text-[11px] font-bold text-[#0A1628]">
                            mover
                          </button>
                          <button onClick={() => setReagendando(null)}
                            className="text-[11px] text-white/40 underline">cancelar</button>
                        </>
                      ) : (
                        <button onClick={() => { setReagendando(t.id); setNovaData(t.data); }}
                          className="rounded-md border border-white/15 px-2.5 py-1 text-[11px] text-white/70 hover:text-white">
                          reagendar
                        </button>
                      )}

                      {t.caso_id && (
                        <Link href={`/judicial?caso=${t.caso_id}`}
                          className="rounded-md border border-white/15 px-2.5 py-1 text-[11px] text-white/70 hover:text-white">
                          abrir caso
                        </Link>
                      )}
                      {t.status !== "FEITA" && (
                        <button onClick={() => agir(t.id, "concluir", {})}
                          className="rounded-md bg-[#1DB954] px-3 py-1 text-[11px] font-bold text-white hover:bg-[#17a349]">
                          feito
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </PainelLayout>
  );
}
