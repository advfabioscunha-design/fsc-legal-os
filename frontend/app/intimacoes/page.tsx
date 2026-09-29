"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PainelLayout from "../components/PainelLayout";
import { porOab, FonteOcupada } from "../../lib/cnj";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";
const OAB_PADRAO = { numero: "10849", uf: "RO" };

/* INTIMAÇÕES E PRAZOS

   Duas listas, e a ordem entre elas é intencional.

   Primeiro os PRAZOS, ordenados pelo que vence antes — é a fila de
   trabalho do dia. A data que aparece grande é a data de TRABALHO (dois
   dias antes do prazo fatal); o prazo fatal vem ao lado, menor, porque
   ele é a referência, não a meta.

   Depois as INTIMAÇÕES, as publicações como chegaram do Diário. Serve
   para conferir o que a controladoria leu e para achar o que ela não
   transformou em prazo.

   Todo prazo calculado automaticamente aparece com a marca "estimado":
   o cálculo usa o padrão do tipo de ato e não conhece feriado local nem
   suspensão de expediente. Quem confirma é o advogado. */

/* "Abrir caso" tem que cair na tela onde o caso está — um processo em
   execução não aparece na tela do judicial. */
function telaDaFase(fase?: string | null) {
  if (fase === "RECEBIMENTO" || fase === "CONCLUIDO") return "/recebimento";
  if (fase === "JUDICIAL" || fase === "PROTOCOLADO" || fase === "TRANSITO_JULGADO")
    return "/judicial";
  return "/crm";
}

function cor(dias: number) {
  if (dias < 0) return "#C0392B";
  if (dias <= 2) return "#E5A44C";
  if (dias <= 7) return "#C9A84C";
  return "#8899AA";
}

function rotuloDias(d: number) {
  if (d < 0) return `${Math.abs(d)}d atrás`;
  if (d === 0) return "hoje";
  if (d === 1) return "amanhã";
  return `${d} dias`;
}

function dataBr(iso?: string | null) {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export default function Intimacoes() {
  const [aba, setAba] = useState<"prazos" | "semana" | "conformidade" | "intimacoes">("prazos");
  const [plano, setPlano] = useState<any>(null);   // a semana pela frente
  const [auditoria, setAuditoria] = useState<any>(null);
  const [prazos, setPrazos] = useState<any[]>([]);
  const [intimacoes, setIntimacoes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [rodando, setRodando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [aberta, setAberta] = useState<string | null>(null);

  function load() {
    setLoading(true);
    Promise.all([
      fetch(`${API}/api/v1/controladoria/fila?dias=120`).then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/intimacoes?limite=200`).then((r) => r.json()).catch(() => []),
      fetch(`${API}/api/v1/controladoria/semana`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/api/v1/controladoria/auditoria`).then((r) => r.json()).catch(() => null),
    ]).then(([f, i, s, a]) => {
      setPrazos(Array.isArray(f) ? f : []);
      setIntimacoes(Array.isArray(i) ? i : []);
      setPlano(s); setAuditoria(a);
    }).finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  /* A rodada tem duas metades, por uma razão de infraestrutura:
     a consulta ao CNJ precisa sair deste navegador (o servidor está
     fora do Brasil e o CNJ o recusa); o resto — recalcular datas, virar
     fases, mandar convites — roda no servidor. */
  async function rodarControladoria() {
    setRodando(true); setAviso("");
    const partes: string[] = [];
    try {
      try {
        const { itens: comunicacoes } = await porOab(OAB_PADRAO.numero, OAB_PADRAO.uf, 15);
        const rs = await fetch(`${API}/api/v1/controladoria/sincronizar`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ comunicacoes }),
        });
        const s = await rs.json().catch(() => ({}));
        if (rs.ok) {
          partes.push(
            `${s.publicacoes ?? 0} publicação(ões) lida(s) no Diário, ` +
            `${s.intimacoes ?? 0} nova(s) e ${s.prazos ?? 0} prazo(s) criado(s)` +
            (s.novos_para_conferir
              ? `; ${s.novos_para_conferir} processo(s) fora do acervo aguardando conferência na tela Judicializado`
              : "") + "."
          );
        } else {
          partes.push(`O servidor não aceitou as publicações (${s.detail || rs.status}).`);
        }
      } catch (e: any) {
        partes.push(e instanceof FonteOcupada
          ? `O Diário do CNJ não respondeu agora (${e.message}).`
          : "Não foi possível consultar o Diário agora.");
      }

      const r = await fetch(`${API}/api/v1/controladoria/rodar`, { method: "POST" });
      const d = await r.json().catch(() => ({}));
      partes.push(
        `${d.datas_ajustadas ?? 0} data(s) de trabalho reajustada(s), ` +
        `${d.fases?.para_judicial ?? 0} caso(s) para o judicial, ` +
        `${d.fases?.para_recebimento ?? 0} para recebimento, ` +
        `${d.convites?.escritorio ?? 0} convite(s) para o escritório e ` +
        `${d.convites?.cliente ?? 0} para clientes.`
      );
      load();
    } catch {
      setAviso("Não foi possível falar com o servidor.");
      setRodando(false);
      return;
    }
    setAviso(partes.join(" "));
    setRodando(false);
  }

  async function concluir(id: string) {
    await fetch(`${API}/api/v1/prazos/${id}?status=CONCLUIDO`, { method: "PATCH" });
    load();
  }

  async function resolver(id: string) {
    await fetch(`${API}/api/v1/intimacoes/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "RESOLVIDO" }),
    });
    load();
  }

  const vencidos = prazos.filter((p) => p.dias_restantes < 0).length;
  const semana = prazos.filter((p) => p.dias_restantes >= 0 && p.dias_restantes <= 7).length;
  const doCliente = prazos.filter((p) => p.depende_do_cliente).length;

  return (
    <PainelLayout titulo="Intimações e prazos">
      <div className="space-y-4">
        {/* Termômetro */}
        <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { r: "Passaram da data de trabalho", v: vencidos, c: "#C0392B" },
            { r: "Vencem em 7 dias", v: semana, c: "#E5A44C" },
            { r: "Dependem do cliente", v: doCliente, c: "#2D7DD2" },
            { r: "Intimações registradas", v: intimacoes.length, c: "#1DB954" },
          ].map((k) => (
            <div key={k.r} className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
              <p className="text-2xl font-bold" style={{ color: k.c }}>{k.v}</p>
              <p className="mt-0.5 text-xs text-white/55">{k.r}</p>
            </div>
          ))}
        </section>

        <div className="flex flex-wrap items-center gap-2">
          {([["prazos", "Prazos (fila do dia)"], ["semana", "Minha semana"],
             ["conformidade", "Conformidade"], ["intimacoes", "Publicações do Diário"]] as const)
            .map(([k, l]) => (
              <button key={k} onClick={() => setAba(k)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
                  aba === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>
                {l}
              </button>
            ))}
          <button onClick={rodarControladoria} disabled={rodando}
            className="ml-auto rounded-md bg-[#2D7DD2] px-3 py-1.5 text-sm font-bold text-white transition hover:bg-[#3a8ae0] disabled:opacity-50">
            {rodando ? "Consultando o Diário…" : "Atualizar pelo Diário (CNJ)"}
          </button>
          <button onClick={load}
            className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8899AA] transition hover:text-white">
            Recarregar
          </button>
        </div>

        {aviso && (
          <p className="rounded-lg border border-[#2D7DD2]/40 bg-[#2D7DD2]/10 px-3 py-2 text-xs text-white/80">
            {aviso}
          </p>
        )}

        {loading ? (
          <p className="text-sm text-[#8899AA]">Carregando…</p>
        ) : aba === "prazos" ? (
          <section className="space-y-2">
            {prazos.length === 0 ? (
              <p className="rounded-xl border border-dashed border-white/10 p-6 text-center text-sm text-white/40">
                Nenhum prazo aberto. Use “Atualizar pelo Diário” para buscar as publicações da OAB.
              </p>
            ) : prazos.map((p) => (
              <div key={p.id}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
                <div className="w-24 shrink-0 text-center">
                  <p className="text-sm font-bold" style={{ color: cor(p.dias_restantes) }}>
                    {rotuloDias(p.dias_restantes)}
                  </p>
                  <p className="text-[11px] text-white/45">{dataBr(p.data_trabalho)}</p>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-white/90">
                    {p.cliente ? <span className="text-[#C9A84C]">{p.cliente} · </span> : null}
                    {p.descricao}
                  </p>
                  <p className="mt-0.5 text-xs text-white/50">
                    Prazo fatal {dataBr(p.prazo_fatal)}
                    {p.numero_processo ? ` · ${p.numero_processo}` : ""}
                    {p.fase ? ` · ${p.fase}` : ""}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <span className="rounded bg-[#E5A44C]/15 px-1.5 py-0.5 text-[10px] text-[#E5A44C]">
                      prazo estimado — conferir no processo
                    </span>
                    {p.depende_do_cliente && (
                      <span className="rounded bg-[#2D7DD2]/15 px-1.5 py-0.5 text-[10px] text-[#2D7DD2]">
                        depende do cliente (vai para a agenda dele)
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  {p.caso_id && (
                    <Link href={`${telaDaFase(p.fase)}?caso=${p.caso_id}`}
                      className="rounded-md border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:text-white">
                      abrir caso
                    </Link>
                  )}
                  <button onClick={() => concluir(p.id)}
                    className="rounded-md bg-[#1DB954] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#17a349]">
                    cumprido
                  </button>
                </div>
              </div>
            ))}
          </section>
        ) : aba === "semana" ? (
          /* A semana pela frente. A fila por urgência responde "o que é
             mais urgente"; esta responde "como está a minha semana",
             que é a pergunta de segunda de manhã. */
          <section className="space-y-3">
            {plano?.atrasados?.length > 0 && (
              <div className="rounded-xl border border-[#C0392B]/40 bg-[#C0392B]/10 p-3">
                <p className="text-sm font-bold text-[#C0392B]">
                  {plano.atrasados.length} item(ns) passaram da data de trabalho
                </p>
                <ul className="mt-1 space-y-0.5">
                  {plano.atrasados.slice(0, 5).map((a: any, i: number) => (
                    <li key={i} className="truncate text-xs text-white/70">
                      • {a.cliente ? <b>{a.cliente}</b> : null} {a.titulo}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-4">
              {(plano?.dias || []).map((d: any) => {
                const dt = new Date(d.data + "T12:00");
                const nomes = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
                const fds = [0, 6].includes(dt.getDay());
                return (
                  <div key={d.data}
                    className={`rounded-xl border p-3 ${d.total ? "border-white/15 bg-[#0B1F3B]" : "border-white/5 bg-[#0B1F3B]/40"}`}>
                    <div className="mb-2 flex items-baseline justify-between">
                      <span className={`text-xs font-bold ${fds ? "text-white/35" : "text-[#C9A24D]"}`}>
                        {nomes[dt.getDay()]} {dataBr(d.data).slice(0, 5)}
                      </span>
                      {d.total > 0 && <span className="text-xs text-white/50">{d.total}</span>}
                    </div>
                    {d.total === 0 ? (
                      <p className="text-[11px] text-white/25">livre</p>
                    ) : (
                      <ul className="space-y-1.5">
                        {d.itens.map((it: any) => (
                          <li key={it.id} className="rounded bg-[#0A1628]/60 px-2 py-1.5">
                            <p className="truncate text-[11px] font-semibold text-white/85">
                              {it.cliente || "—"}
                            </p>
                            <p className="truncate text-[10px] text-white/50">{it.titulo}</p>
                            {it.depende_do_cliente && (
                              <span className="mt-0.5 inline-block rounded bg-[#2D7DD2]/20 px-1 text-[9px] text-[#2D7DD2]">
                                cliente comparece
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ) : aba === "conformidade" ? (
          /* O que está quebrado e precisa da mão de alguém — não é
             relatório de produtividade. */
          <section className="space-y-2">
            <div className="flex flex-wrap gap-3 text-xs text-white/60">
              <span>{auditoria?.casos_conferidos ?? 0} caso(s) conferido(s)</span>
              {["ALTA", "MEDIA", "BAIXA"].map((g) => (
                <span key={g} style={{ color: g === "ALTA" ? "#C0392B" : g === "MEDIA" ? "#E5A44C" : "#8899AA" }}>
                  {auditoria?.por_gravidade?.[g] ?? 0} {g.toLowerCase()}
                </span>
              ))}
            </div>
            {(auditoria?.achados || []).length === 0 ? (
              <p className="rounded-xl border border-dashed border-[#1DB954]/30 p-6 text-center text-sm text-[#1DB954]">
                Nada fora dos conformes.
              </p>
            ) : (auditoria.achados).map((a: any, i: number) => (
              <div key={i} className="flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
                <span className="w-14 shrink-0 text-[10px] font-bold"
                  style={{ color: a.gravidade === "ALTA" ? "#C0392B" : a.gravidade === "MEDIA" ? "#E5A44C" : "#8899AA" }}>
                  {a.gravidade}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-white/85">{a.o_que}</p>
                  <p className="truncate text-xs text-white/45">{a.caso} — {a.fazer}</p>
                </div>
                {a.caso_id && (
                  <Link href={`/judicial?caso=${a.caso_id}`}
                    className="shrink-0 rounded-md border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:text-white">
                    abrir
                  </Link>
                )}
              </div>
            ))}
          </section>
        ) : (
          <section className="space-y-2">
            {intimacoes.length === 0 ? (
              <p className="rounded-xl border border-dashed border-white/10 p-6 text-center text-sm text-white/40">
                Nenhuma publicação registrada ainda.
              </p>
            ) : intimacoes.map((i) => (
              <div key={i.id} className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-white/70">
                    {i.tribunal || "—"}
                  </span>
                  <span className="font-mono text-xs text-white/80">{i.numero_processo || "—"}</span>
                  <span className="text-xs text-white/50">{i.tipo || i.orgao || ""}</span>
                  <span className="text-xs text-white/40">{dataBr(i.data_movimento)}</span>
                  {i.status === "RESOLVIDO" && (
                    <span className="rounded bg-[#1DB954]/15 px-1.5 py-0.5 text-[10px] text-[#1DB954]">resolvida</span>
                  )}
                  <div className="ml-auto flex gap-2">
                    {i.link && (
                      <a href={i.link} target="_blank" rel="noopener noreferrer"
                        className="rounded-md border border-white/15 px-2 py-1 text-[11px] text-white/70 hover:text-white">
                        ver no tribunal
                      </a>
                    )}
                    <button onClick={() => setAberta(aberta === i.id ? null : i.id)}
                      className="rounded-md border border-white/15 px-2 py-1 text-[11px] text-white/70 hover:text-white">
                      {aberta === i.id ? "fechar" : "ler"}
                    </button>
                    {i.status !== "RESOLVIDO" && (
                      <button onClick={() => resolver(i.id)}
                        className="rounded-md bg-[#1DB954] px-2 py-1 text-[11px] font-bold text-white hover:bg-[#17a349]">
                        resolvida
                      </button>
                    )}
                  </div>
                </div>
                {aberta === i.id && (
                  <pre className="mt-2 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg bg-[#0A1628]/70 p-3 text-xs leading-relaxed text-white/75">
                    {i.conteudo || "(sem texto)"}
                  </pre>
                )}
              </div>
            ))}
          </section>
        )}
      </div>
    </PainelLayout>
  );
}
