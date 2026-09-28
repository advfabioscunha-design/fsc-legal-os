"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import PainelLayout from "./PainelLayout";
import CasoDetalhe from "./CasoDetalhe";
import ImportarProcessos from "./ImportarProcessos";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A esteira é a mesma peça, usada em duas telas, porque são dois
   trabalhos diferentes com ritmos diferentes.

   CONTRATOS é a fase comercial: quem chegou, o que foi proposto, quem
   assinou e quem pagou. PRODUÇÃO começa quando o contrato está fechado:
   documento, análise, peça, revisão e protocolo.

   Misturar os dois, como estava, fazia o advogado que ia redigir uma
   petição atravessar dez colunas de negociação para chegar no caso dele. */
const COLUNAS_CONTRATOS = [
  { id: "LEAD",           label: "Novos contatos",     cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "QUALIFICACAO",   label: "Qualificação",       cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "PROPOSTA",       label: "Negociação/Proposta", cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "CONTRATO",       label: "Assinatura",         cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "PAGAMENTO",      label: "Pagamento",          cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "LEAD_FRIO",      label: "Sem retorno",        cor: "border-[#5A6B7C]", hdr: "bg-[#5A6B7C]/10" },
];

/* JUDICIAL e RECEBIMENTO são as duas fases que vêm depois do protocolo.
   As colunas aqui não são etapas de trabalho interno, e sim o estado do
   processo em juízo — por isso são poucas e largas. */
const COLUNAS_JUDICIAL = [
  { id: "PROTOCOLADO",      label: "Protocolado",         cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
  { id: "JUDICIAL",         label: "Em tramitação",       cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "TRANSITO_JULGADO", label: "Trânsito em julgado",  cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
];

const COLUNAS_RECEBIMENTO = [
  { id: "RECEBIMENTO", label: "Execução / Recebimento", cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/15" },
  { id: "CONCLUIDO",   label: "Concluído",              cor: "border-[#5A6B7C]", hdr: "bg-[#5A6B7C]/10" },
];

const COLUNAS_PRODUCAO = [
  { id: "COLETA_DOCS",    label: "Coleta Docs",        cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "AGUARDANDO_DOCUMENTOS", label: "Aguardando Cliente", cor: "border-[#E5A44C]", hdr: "bg-[#E5A44C]/15" },
  { id: "PRONTO_PARA_ANALISE",   label: "Pronto p/ Análise",  cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/15" },
  { id: "COLETA_PROVAS",  label: "Coleta Provas",      cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "ANALISE",        label: "Análise",            cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "PETICAO",        label: "Peticionamento",     cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "REVISAO",        label: "Revisão",            cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "PROTOCOLO_RPA",  label: "Protocolo",          cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
  { id: "PROTOCOLADO",    label: "Protocolado",        cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
];

const FASES_FORM = [
  { v: "QUALIFICACAO", l: "Qualificação" },
  { v: "PROPOSTA", l: "Negociação / Proposta" },
  { v: "CONTRATO", l: "Assinatura de Contrato" },
  { v: "PAGAMENTO", l: "Pagamento" },
  { v: "COLETA_DOCS", l: "Coleta de Documentos" },
  { v: "COLETA_PROVAS", l: "Coleta de Provas" },
  { v: "ANALISE", l: "Análise" },
  { v: "PETICAO", l: "Peticionamento" },
  { v: "REVISAO", l: "Revisão" },
];
const GRUPOS_FORM = ["BANCARIO", "IMOBILIARIO", "TRABALHISTA", "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"];

type Caso = {
  id: string; estado: string; grupo: string | null; subtipo: string | null;
  numero_processo?: string | null;
  clientes: { nome: string; origem?: string } | null; tese_id: string | null;
  mensagens_nao_respondidas?: number;
};

const formVazio = { nome: "", cpf: "", contato: "", grupo: "", fase: "PETICAO", numero_processo: "", honorarios: "", descricao: "" };

export type ModoEsteira = "contratos" | "producao" | "judicial" | "recebimento";

const POR_MODO: Record<ModoEsteira, { titulo: string; colunas: typeof COLUNAS_CONTRATOS }> = {
  contratos:   { titulo: "Contratos",             colunas: COLUNAS_CONTRATOS },
  producao:    { titulo: "Produção",              colunas: COLUNAS_PRODUCAO },
  judicial:    { titulo: "Judicial",              colunas: COLUNAS_JUDICIAL },
  recebimento: { titulo: "Execução / Recebimento", colunas: COLUNAS_RECEBIMENTO },
};

export default function Esteira({ modo }: { modo: ModoEsteira }) {
  const contratos = modo === "contratos";
  const judicial = modo === "judicial";
  const recebimento = modo === "recebimento";
  const processual = judicial || recebimento;
  const COLUNAS = POR_MODO[modo].colunas;
  const estados = COLUNAS.map((c) => c.id);
  const [casos, setCasos] = useState<Caso[]>([]);
  const [pendencias, setPendencias] = useState<Caso[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [aba, setAba] = useState<"esteira" | "suspensos" | "arquivados" | "lixeira">("esteira");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [lixeira, setLixeira] = useState<any[]>([]);
  const [form, setForm] = useState({ ...formVazio });
  const [salvando, setSalvando] = useState(false);
  const [importar, setImportar] = useState(false);
  const [movendo, setMovendo] = useState<string | null>(null);

  function load() {
    setLoading(true);
    if (aba === "lixeira") {
      fetch(`${API}/api/v1/lixeira`).then((r) => r.json())
        .then((d) => setLixeira(Array.isArray(d) ? d : []))
        .catch(() => setLixeira([])).finally(() => setLoading(false));
      return;
    }
    const situ = aba === "esteira" ? "ATIVO" : aba === "suspensos" ? "SUSPENSO" : "ARQUIVADO";
    Promise.all([
      fetch(`${API}/api/v1/casos?situacao=${situ}`).then((r) => r.json()).catch(() => []),
      aba === "esteira"
        ? fetch(`${API}/api/v1/pendencias`).then((r) => r.json()).catch(() => [])
        : Promise.resolve([]),
    ]).then(([cs, ps]) => {
      // cada tela mostra apenas as etapas que lhe dizem respeito
      const lista = Array.isArray(cs) ? cs : [];
      setCasos(aba === "esteira" ? lista.filter((c: Caso) => estados.includes(c.estado)) : lista);
      setPendencias(Array.isArray(ps) ? ps : []);
    }).finally(() => setLoading(false));
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [aba, modo]);

  async function aprovar(id: string) {
    await fetch(`${API}/api/v1/casos/${id}/aprovar-protocolar`, { method: "POST" });
    load();
  }

  /* Mover de fase pela mão: o automático cobre protocolo e trânsito em
     julgado, mas há caso que anda por fora (acordo, cumprimento
     voluntário, desmembramento). O botão existe para isso. */
  async function moverFase(id: string, destino: "JUDICIAL" | "RECEBIMENTO") {
    const rotulo = destino === "RECEBIMENTO" ? "execução / recebimento" : "judicial";
    if (!confirm(`Mover este caso para a fase ${rotulo}?`)) return;
    setMovendo(id);
    try {
      const r = await fetch(`${API}/api/v1/casos/${id}/mover-fase`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destino, motivo: "movido na tela" }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({} as any));
        alert(e.detail || `Não foi possível mover (erro ${r.status}).`);
        return;
      }
      load();
    } finally { setMovendo(null); }
  }

  async function restaurar(id: string) {
    await fetch(`${API}/api/v1/lixeira/${id}/restaurar`, { method: "POST" });
    load();
  }

  async function criarEscritorio(e: React.FormEvent) {
    e.preventDefault();
    if (!form.nome.trim()) { alert("Informe o nome do cliente."); return; }
    if (!form.contato.trim()) { alert("Informe o contato do cliente (e-mail ou WhatsApp) para acionamento."); return; }
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/escritorio`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: form.nome, cpf: form.cpf || null, contato: form.contato,
          grupo: form.grupo || null, fase: form.fase,
          numero_processo: form.numero_processo || null,
          honorarios: form.honorarios || null, descricao: form.descricao || null,
        }),
      });
      if (!r.ok) {
        const er = await r.json().catch(() => ({} as any));
        alert("Não foi possível cadastrar: " + (er.detail || `erro ${r.status}`));
        return;
      }
      setModal(false); setForm({ ...formVazio }); setAba("esteira"); load();
    } catch {
      alert("Falha de conexão com o servidor. Verifique a internet e tente de novo.");
    } finally { setSalvando(false); }
  }

  const ehEscritorio = (c: Caso) => c.clientes?.origem === "ESCRITORIO";

  return (
    <PainelLayout titulo={POR_MODO[modo].titulo}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm text-[#8899AA]">
          {loading ? "Carregando..." : `${casos.length} caso(s)`}
        </span>
        {processual ? (
          <>
            <button onClick={() => setImportar(true)}
              className="ml-auto rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
              + Carregar processos (OAB ou número)
            </button>
            <Link href="/intimacoes"
              className="rounded-md border border-[#C9A84C]/50 px-3 py-1.5 text-sm font-semibold text-[#C9A84C] transition hover:bg-[#C9A84C]/10">
              Intimações e prazos →
            </Link>
          </>
        ) : contratos ? (
          <button onClick={() => { setForm({ ...formVazio, fase: "QUALIFICACAO" }); setModal(true); }}
            className="ml-auto rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
            + Novo contrato / cliente
          </button>
        ) : (
          <>
            <button onClick={() => { setForm({ ...formVazio }); setModal(true); }}
              className="ml-auto rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
              + Montar processo do escritório
            </button>
            <Link href="/processos"
              className="rounded-md border border-[#C9A84C]/50 px-3 py-1.5 text-sm font-semibold text-[#C9A84C] transition hover:bg-[#C9A84C]/10">
              Processos em andamento →
            </Link>
          </>
        )}
        <button onClick={load}
          className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8899AA] transition-colors hover:text-white">
          Atualizar
        </button>
      </div>

      {/* Abas */}
      <div className="flex gap-2">
        {([["esteira", "Esteira"], ["suspensos", "Suspensos"], ["arquivados", "Arquivados"], ["lixeira", "Lixeira"]] as const).map(([k, l]) => (
          <button key={k} onClick={() => setAba(k)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${aba === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Caixa de Intervenção Urgente */}
      {pendencias.length > 0 && (
        <div className="mt-4 rounded-lg border border-[#C0392B]/50 bg-[#C0392B]/10 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded bg-[#C0392B] px-2 py-0.5 text-xs font-bold text-white">INTERVENÇÃO URGENTE</span>
            <span className="text-sm text-white/80">{pendencias.length} caso(s) aguardando atendimento humano</span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {pendencias.map((c) => (
              <div key={c.id} className="w-60 shrink-0 rounded-lg bg-[#1A3A6B]/40 border border-[#C0392B]/30 p-3">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-white text-sm truncate">{c.clientes?.nome ?? "—"}</p>
                  {(c.mensagens_nao_respondidas ?? 0) > 0 && (
                    <span className="ml-2 shrink-0 rounded-full bg-[#C0392B] px-2 py-0.5 text-[11px] font-bold text-white">
                      {c.mensagens_nao_respondidas} msg
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#8899AA] mt-1 truncate">{c.grupo ?? "—"}</p>
                {ehEscritorio(c) && (
                  <span className="mt-1 inline-block text-[10px] text-[#C9A84C]">★ Escritório</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Esteira (aba ativa) ou listas de Suspensos/Arquivados */}
      {aba === "esteira" ? (
      <div className="mt-4 overflow-x-auto">
        <div className="flex gap-3 min-w-max pb-4">
          {COLUNAS.map((col) => {
            const cards = casos.filter((c) => c.estado === col.id);
            return (
              <div key={col.id} className="w-56 shrink-0 flex flex-col gap-2">
                <div className={`rounded-lg px-3 py-2 border-l-4 ${col.cor} ${col.hdr} flex items-center justify-between`}>
                  <h2 className="text-xs font-bold text-white truncate">{col.label}</h2>
                  <span className="text-xs text-[#8899AA] ml-1">{cards.length}</span>
                </div>
                <div className="space-y-2 min-h-[3rem]">
                  {cards.map((c) => (
                    <div key={c.id} onClick={() => setSelecionado(c.id)}
                      className={`cursor-pointer rounded-lg bg-[#1A3A6B]/30 border p-3 transition-colors ${ehEscritorio(c) ? "border-[#C9A84C]/40" : "border-white/5 hover:border-[#2D7DD2]/30"}`}>
                      <div className="flex items-start justify-between gap-1">
                        <p className="font-semibold text-white text-sm truncate">{c.clientes?.nome ?? "—"}</p>
                      </div>
                      {ehEscritorio(c) && (
                        <span className="mt-1 inline-block rounded bg-[#C9A84C]/20 px-2 py-0.5 text-[10px] font-bold text-[#C9A84C]">★ ESCRITÓRIO</span>
                      )}
                      <p className="text-xs text-[#8899AA] mt-1 truncate">
                        {c.grupo}{c.subtipo ? ` > ${c.subtipo}` : ""}
                      </p>
                      {c.numero_processo && (
                        <p className="text-[10px] text-[#8899AA]/70 mt-0.5 truncate">Proc. {c.numero_processo}</p>
                      )}
                      {c.tese_id && (
                        <span className="inline-block mt-1 text-[10px] bg-[#2D7DD2]/15 text-[#2D7DD2] rounded px-2 py-0.5">{c.tese_id}</span>
                      )}
                      {/* Mover de fase: do judicial para a execução, e o
                          caminho de volta, se a fase foi virada cedo. */}
                      {judicial && (
                        <button onClick={(e) => { e.stopPropagation(); moverFase(c.id, "RECEBIMENTO"); }}
                          disabled={movendo === c.id}
                          className="mt-2 w-full rounded-md border border-[#C9A84C]/60 py-1.5 text-xs font-bold text-[#C9A84C] transition hover:bg-[#C9A84C]/10 disabled:opacity-40">
                          {movendo === c.id ? "movendo…" : "Mover para execução →"}
                        </button>
                      )}
                      {recebimento && col.id === "RECEBIMENTO" && (
                        <button onClick={(e) => { e.stopPropagation(); moverFase(c.id, "JUDICIAL"); }}
                          disabled={movendo === c.id}
                          className="mt-2 w-full rounded-md border border-white/20 py-1.5 text-xs font-semibold text-white/70 transition hover:bg-white/5 disabled:opacity-40">
                          {movendo === c.id ? "movendo…" : "← Voltar para o judicial"}
                        </button>
                      )}
                      {col.id === "REVISAO" && (
                        <button onClick={(e) => { e.stopPropagation(); aprovar(c.id); }}
                          className="mt-2 w-full rounded-md bg-[#1DB954] hover:bg-[#17a349] py-1.5 text-xs font-bold text-white transition-colors">
                          Aprovar e Protocolar
                        </button>
                      )}
                    </div>
                  ))}
                  {cards.length === 0 && (
                    <div className="rounded-lg border border-dashed border-white/10 p-3 text-center">
                      <p className="text-xs text-[#8899AA]/40">vazio</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      ) : aba === "lixeira" ? (
        <div className="p-4">
          {loading ? (
            <p className="text-[#8899AA]">Carregando...</p>
          ) : lixeira.length === 0 ? (
            <p className="text-[#8899AA]/50">Lixeira vazia.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {lixeira.map((it) => (
                <div key={it.id} className="rounded-lg border border-white/10 bg-[#1A3A6B]/30 p-4">
                  <p className="text-sm font-semibold text-white">{it.rotulo || "—"}</p>
                  <p className="mt-1 text-xs text-[#8899AA]">Excluído: {new Date(it.excluido_em).toLocaleString("pt-BR")}</p>
                  <p className="text-[10px] text-[#8899AA]/60">Guardado até: {new Date(it.expira_em).toLocaleDateString("pt-BR")}</p>
                  <button onClick={() => restaurar(it.id)} className="mt-2 rounded-lg bg-[#1DB954] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#17a349]">Restaurar</button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="p-4">
          {loading ? (
            <p className="text-[#8899AA]">Carregando...</p>
          ) : casos.length === 0 ? (
            <p className="text-[#8899AA]/50">Nenhum caso {aba === "suspensos" ? "suspenso" : "arquivado"}.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {casos.map((c) => (
                <button key={c.id} onClick={() => setSelecionado(c.id)}
                  className="rounded-lg border border-white/10 bg-[#1A3A6B]/30 p-4 text-left transition hover:border-[#C9A84C]/40">
                  <p className="text-sm font-semibold text-white">{c.clientes?.nome ?? "—"}</p>
                  <p className="mt-1 text-xs text-[#8899AA]">{c.grupo ?? "—"} · {c.estado}</p>
                  {ehEscritorio(c) && <span className="mt-1 inline-block text-[10px] text-[#C9A84C]">★ Escritório</span>}
                  <p className="mt-2 text-xs text-[#C9A84C]">Abrir para ativar →</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Montar Processo do Escritório */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setModal(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={criarEscritorio}
            className="w-full max-w-lg rounded-2xl bg-[#0F2A44] p-6 text-white shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">Montar Processo do Escritório</h2>
              <button type="button" onClick={() => setModal(false)} className="text-white/60 hover:text-white">✕</button>
            </div>
            <p className="mb-4 text-xs text-white/55">
              Cadastra o cliente direto na plataforma e insere o processo na fase atual, entrando na esteira de produção.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Nome do cliente *"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C] sm:col-span-2" />
              <input value={form.cpf} onChange={(e) => setForm({ ...form, cpf: e.target.value })} placeholder="CPF/CNPJ"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <input value={form.contato} onChange={(e) => setForm({ ...form, contato: e.target.value })} placeholder="E-mail ou WhatsApp"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <select value={form.grupo} onChange={(e) => setForm({ ...form, grupo: e.target.value })}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]">
                <option value="">Grupo (área)…</option>
                {GRUPOS_FORM.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
              <select value={form.fase} onChange={(e) => setForm({ ...form, fase: e.target.value })}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]">
                {FASES_FORM.map((f) => <option key={f.v} value={f.v}>{f.l}</option>)}
              </select>
              <input value={form.numero_processo} onChange={(e) => setForm({ ...form, numero_processo: e.target.value })} placeholder="Nº do processo (se houver)"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <input value={form.honorarios} onChange={(e) => setForm({ ...form, honorarios: e.target.value })} placeholder="Honorários (ex.: R$ 1.500)"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <textarea value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Descrição / observações" rows={3}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C] sm:col-span-2" />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(false)} className="rounded-lg border border-white/15 px-4 py-2 text-sm text-white/70 hover:text-white">Cancelar</button>
              <button type="submit" disabled={salvando}
                className="rounded-lg bg-[#C9A84C] px-5 py-2 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e] disabled:opacity-50">
                {salvando ? "Cadastrando..." : "Cadastrar na esteira"}
              </button>
            </div>
          </form>
        </div>
      )}

      {importar && (
        <ImportarProcessos
          fase={judicial ? "JUDICIAL" : "RECEBIMENTO"}
          onFechar={() => setImportar(false)}
          onPronto={load}
        />
      )}

      {selecionado && (
        <CasoDetalhe casoId={selecionado} onFechar={() => setSelecionado(null)} onMudou={load} />
      )}
    </PainelLayout>
  );
}
