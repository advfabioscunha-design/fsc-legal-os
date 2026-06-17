"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";
import CasoDetalhe from "../components/CasoDetalhe";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

const COLUNAS = [
  { id: "QUALIFICACAO",   label: "Qualificacao",     cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "PROPOSTA",       label: "Negociacao/Proposta", cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "CONTRATO",       label: "Contrato",          cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "PAGAMENTO",      label: "Pagamento",         cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "COLETA_DOCS",    label: "Coleta Docs",       cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "COLETA_PROVAS",  label: "Coleta Provas",     cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "ANALISE",        label: "Analise",           cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "PETICAO",        label: "Peticionamento",    cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "REVISAO",        label: "Revisao",           cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "PROTOCOLO_RPA",  label: "Protocolo RPA",     cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
  { id: "PROTOCOLADO",    label: "Protocolado",       cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
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

export default function CRM() {
  const router = useRouter();
  const [autorizado, setAutorizado] = useState(false);
  const [casos, setCasos] = useState<Caso[]>([]);
  const [pendencias, setPendencias] = useState<Caso[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [aba, setAba] = useState<"esteira" | "suspensos" | "arquivados">("esteira");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [form, setForm] = useState({ ...formVazio });
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.replace("/entrar"); return; }
      const { data: perfil } = await supabase
        .from("perfis").select("papel").eq("id", sess.session.user.id).maybeSingle();
      if (perfil?.papel !== "OPERADOR") { router.replace("/cliente"); return; }
      setAutorizado(true);
    })();
  }, [router]);

  function load() {
    setLoading(true);
    const situ = aba === "esteira" ? "ATIVO" : aba === "suspensos" ? "SUSPENSO" : "ARQUIVADO";
    Promise.all([
      fetch(`${API}/api/v1/casos?situacao=${situ}`).then((r) => r.json()).catch(() => []),
      aba === "esteira"
        ? fetch(`${API}/api/v1/pendencias`).then((r) => r.json()).catch(() => [])
        : Promise.resolve([]),
    ]).then(([cs, ps]) => {
      setCasos(Array.isArray(cs) ? cs : []);
      setPendencias(Array.isArray(ps) ? ps : []);
    }).finally(() => setLoading(false));
  }

  useEffect(() => { if (autorizado) load(); /* eslint-disable-next-line */ }, [autorizado, aba]);

  async function aprovar(id: string) {
    await fetch(`${API}/api/v1/casos/${id}/aprovar-protocolar`, { method: "POST" });
    load();
  }

  async function criarEscritorio(e: React.FormEvent) {
    e.preventDefault();
    if (!form.nome.trim()) return;
    setSalvando(true);
    try {
      await fetch(`${API}/api/v1/casos/escritorio`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: form.nome, cpf: form.cpf || null, contato: form.contato || null,
          grupo: form.grupo || null, fase: form.fase,
          numero_processo: form.numero_processo || null,
          honorarios: form.honorarios || null, descricao: form.descricao || null,
        }),
      });
      setModal(false); setForm({ ...formVazio }); load();
    } finally { setSalvando(false); }
  }

  const ehEscritorio = (c: Caso) => c.clientes?.origem === "ESCRITORIO";

  if (!autorizado) {
    return (
      <div className="flex min-h-screen items-center justify-center text-white/60" style={{ background: "#0A1628", fontFamily: "Inter, sans-serif" }}>
        Verificando acesso...
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#0A1628", fontFamily: "Inter, sans-serif" }}>
      <header className="border-b border-white/5 bg-[#0A1628] px-6 py-4 sticky top-0 z-40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm text-[#8899AA] hover:text-white transition-colors">&larr; Site</Link>
            <div className="flex flex-col leading-none">
              <span className="text-lg font-bold text-white">FC <span className="text-[#C5A880]">Legal OS</span></span>
              <span className="text-[10px] text-[#8899AA] tracking-widest uppercase">Esteira de Casos</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#8899AA]">{loading ? "Carregando..." : `${casos.length} caso(s)`}</span>
            <button onClick={() => setModal(true)}
              className="rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
              + Montar Processo do Escritório
            </button>
            <button onClick={load}
              className="text-sm text-[#8899AA] hover:text-white border border-white/10 rounded-md px-3 py-1.5 transition-colors">
              Atualizar
            </button>
          </div>
        </div>
      </header>

      {/* Abas */}
      <div className="flex gap-2 px-4 pt-4">
        {([["esteira", "Esteira"], ["suspensos", "Suspensos"], ["arquivados", "Arquivados"]] as const).map(([k, l]) => (
          <button key={k} onClick={() => setAba(k)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${aba === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Caixa de Intervenção Urgente */}
      {pendencias.length > 0 && (
        <div className="mx-4 mt-4 rounded-lg border border-[#C0392B]/50 bg-[#C0392B]/10 p-4">
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
      <div className="p-4 overflow-x-auto">
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

      {selecionado && (
        <CasoDetalhe casoId={selecionado} onFechar={() => setSelecionado(null)} onMudou={load} />
      )}
    </div>
  );
}
