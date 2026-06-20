"use client";
import { useEffect, useState } from "react";
import PainelLayout from "../components/PainelLayout";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

const TRIBUNAIS = ["STF", "STJ", "TST", "TJAC", "TJAL", "TJAP", "TJAM", "TJBA", "TJCE", "TJDFT", "TJES", "TJGO", "TJMA", "TJMT", "TJMS", "TJMG", "TJPA", "TJPB", "TJPR", "TJPE", "TJPI", "TJRJ", "TJRN", "TJRS", "TJRO", "TJRR", "TJSC", "TJSP", "TJSE", "TJTO", "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6", "TRT2", "TRT3", "TRT14"];
const NICHOS = ["BANCARIO", "IMOBILIARIO", "TRABALHISTA", "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"];
const FASES = ["QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO", "COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO", "PROTOCOLADO", "CONCLUIDO"];

const STATUS_INFO: Record<string, { label: string; cls: string }> = {
  RESOLVIDO: { label: "Resolvido", cls: "bg-[#1DB954]/20 text-[#1DB954]" },
  A_RESOLVER: { label: "A Resolver", cls: "bg-[#F39C12]/20 text-[#F39C12]" },
  PERDA_PRAZO: { label: "Perda de Prazo", cls: "bg-[#C0392B]/20 text-[#C0392B]" },
};

export default function ProcessosPage() {
  const [aba, setAba] = useState<"processos" | "intimacoes">("intimacoes");

  // Intimações
  const [intimacoes, setIntimacoes] = useState<any[]>([]);
  const [fStatus, setFStatus] = useState("");
  const [fTribunal, setFTribunal] = useState("");
  const [lupaAberta, setLupaAberta] = useState(false);
  const [busca, setBusca] = useState("");
  const [naoLidas, setNaoLidas] = useState(0);
  const [modal, setModal] = useState(false);
  const [mon, setMon] = useState({ numero_processo: "", oab: "", tribunal: "" });
  const [salvando, setSalvando] = useState(false);

  // Processos
  const [processos, setProcessos] = useState<any[]>([]);
  const [pTribunal, setPTribunal] = useState("");
  const [pGrupo, setPGrupo] = useState("");
  const [pEstado, setPEstado] = useState("");
  const [pAno, setPAno] = useState("");
  const [porPagina, setPorPagina] = useState(25);

  function loadIntimacoes() {
    const p = new URLSearchParams();
    if (fStatus) p.set("status", fStatus);
    if (fTribunal) p.set("tribunal", fTribunal);
    if (busca) p.set("q", busca);
    fetch(`${API}/api/v1/intimacoes?${p}`).then((r) => r.json()).then((d) => setIntimacoes(Array.isArray(d) ? d : [])).catch(() => setIntimacoes([]));
    fetch(`${API}/api/v1/intimacoes/nao-lidas`).then((r) => r.json()).then((d) => setNaoLidas(d.total || 0)).catch(() => {});
  }
  function loadProcessos() {
    const p = new URLSearchParams();
    if (pTribunal) p.set("tribunal", pTribunal);
    if (pGrupo) p.set("grupo", pGrupo);
    if (pEstado) p.set("estado", pEstado);
    if (pAno) p.set("ano", pAno);
    fetch(`${API}/api/v1/processos?${p}`).then((r) => r.json()).then((d) => setProcessos(Array.isArray(d) ? d : [])).catch(() => setProcessos([]));
  }

  useEffect(() => { if (aba === "intimacoes") loadIntimacoes(); /* eslint-disable-next-line */ }, [aba, fStatus, fTribunal]);
  useEffect(() => { if (aba === "processos") loadProcessos(); /* eslint-disable-next-line */ }, [aba, pTribunal, pGrupo, pEstado, pAno]);

  async function mudarStatus(id: string, status: string) {
    await fetch(`${API}/api/v1/intimacoes/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    loadIntimacoes();
  }
  async function marcarLidas() {
    await fetch(`${API}/api/v1/intimacoes/marcar-lidas`, { method: "POST" });
    loadIntimacoes();
  }
  async function monitorar(e: React.FormEvent) {
    e.preventDefault();
    if (!mon.numero_processo && !mon.oab) { alert("Informe o número do processo ou a OAB."); return; }
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/processos/monitorar`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(mon) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { alert("Erro: " + (d.detail || r.status)); return; }
      if (d.erro) alert("Monitoramento salvo localmente, mas o Escavador retornou: " + d.erro + "\n(Confira o token/endpoint do Escavador.)");
      setModal(false); setMon({ numero_processo: "", oab: "", tribunal: "" });
    } finally { setSalvando(false); }
  }

  const inp = "rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-sm text-white outline-none focus:border-[#C9A24D]";

  return (
    <PainelLayout titulo="Pasta Processos">
      <div className="p-5">
        {/* Abas */}
        <div className="mb-4 flex gap-2">
          {([["intimacoes", "Intimações"], ["processos", "Processos"]] as const).map(([k, l]) => (
            <button key={k} onClick={() => setAba(k)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${aba === k ? "bg-[#C9A24D] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>{l}</button>
          ))}
        </div>

        {aba === "intimacoes" ? (
          <>
            {/* Ações */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <button onClick={() => setModal(true)} className="rounded-lg bg-[#C9A24D] px-4 py-2 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e]">+ Monitorar Processo</button>
              <button onClick={() => setLupaAberta(!lupaAberta)} title="Busca interna" className="rounded-lg border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/5">🔍</button>
              <button onClick={marcarLidas} title="Notificações não lidas" className="relative rounded-lg border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/5">
                🔔{naoLidas > 0 && <span className="absolute -right-1 -top-1 rounded-full bg-[#C0392B] px-1.5 text-[10px] font-bold text-white">{naoLidas}</span>}
              </button>
              <select value={fStatus} onChange={(e) => setFStatus(e.target.value)} className={inp}>
                <option value="">Todos os status</option>
                <option value="A_RESOLVER">A Resolver</option>
                <option value="RESOLVIDO">Resolvido</option>
                <option value="PERDA_PRAZO">Perda de Prazo</option>
              </select>
              <select value={fTribunal} onChange={(e) => setFTribunal(e.target.value)} className={inp}>
                <option value="">Todos os tribunais</option>
                {TRIBUNAIS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              {lupaAberta && (
                <input value={busca} onChange={(e) => setBusca(e.target.value)} onKeyDown={(e) => e.key === "Enter" && loadIntimacoes()}
                  placeholder="Nº do processo… (Enter)" className={inp + " flex-1"} />
              )}
            </div>

            {/* Tabela */}
            <div className="overflow-x-auto rounded-xl border border-white/10">
              <table className="min-w-full text-sm">
                <thead className="bg-white/5 text-left text-[#8899AA]">
                  <tr><th className="px-4 py-2">Tribunal</th><th className="px-4 py-2">Processo</th><th className="px-4 py-2">Status</th><th className="px-4 py-2">Data Movimento</th></tr>
                </thead>
                <tbody>
                  {intimacoes.map((i) => {
                    const si = STATUS_INFO[i.status] || STATUS_INFO.A_RESOLVER;
                    return (
                      <tr key={i.id} className="border-t border-white/5 text-white">
                        <td className="px-4 py-2">{i.tribunal || "—"}</td>
                        <td className="px-4 py-2">{i.numero_processo || "—"}<div className="max-w-md truncate text-xs text-[#8899AA]">{i.conteudo}</div></td>
                        <td className="px-4 py-2">
                          <select value={i.status} onChange={(e) => mudarStatus(i.id, e.target.value)}
                            className={`rounded-full px-2 py-1 text-xs font-semibold ${si.cls}`} style={{ background: "transparent" }}>
                            <option value="A_RESOLVER">A Resolver</option>
                            <option value="RESOLVIDO">Resolvido</option>
                            <option value="PERDA_PRAZO">Perda de Prazo</option>
                          </select>
                        </td>
                        <td className="px-4 py-2 text-[#8899AA]">{i.data_movimento ? new Date(i.data_movimento).toLocaleString("pt-BR") : "—"}</td>
                      </tr>
                    );
                  })}
                  {intimacoes.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-[#8899AA]/50">Nenhuma intimação. Cadastre um processo em “+ Monitorar Processo”.</td></tr>}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <>
            {/* Filtros Processos */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <select value={pTribunal} onChange={(e) => setPTribunal(e.target.value)} className={inp}><option value="">Tribunal</option>{TRIBUNAIS.map((t) => <option key={t} value={t}>{t}</option>)}</select>
              <select value={pGrupo} onChange={(e) => setPGrupo(e.target.value)} className={inp}><option value="">Nicho</option>{NICHOS.map((n) => <option key={n} value={n}>{n}</option>)}</select>
              <select value={pEstado} onChange={(e) => setPEstado(e.target.value)} className={inp}><option value="">Fase</option>{FASES.map((f) => <option key={f} value={f}>{f}</option>)}</select>
              <input value={pAno} onChange={(e) => setPAno(e.target.value)} placeholder="Ano" className={inp + " w-24"} />
              <select value={porPagina} onChange={(e) => setPorPagina(Number(e.target.value))} className={inp}>{[25, 50, 100].map((n) => <option key={n} value={n}>{n}/pág</option>)}</select>
            </div>
            <div className="overflow-x-auto rounded-xl border border-white/10">
              <table className="min-w-full text-sm">
                <thead className="bg-white/5 text-left text-[#8899AA]"><tr><th className="px-4 py-2">Cliente</th><th className="px-4 py-2">Processo</th><th className="px-4 py-2">Nicho</th><th className="px-4 py-2">Fase</th><th className="px-4 py-2">Tribunal</th></tr></thead>
                <tbody>
                  {processos.slice(0, porPagina).map((c) => (
                    <tr key={c.id} className="border-t border-white/5 text-white">
                      <td className="px-4 py-2">{c.clientes?.nome ?? "—"}</td>
                      <td className="px-4 py-2">{c.numero_processo}</td>
                      <td className="px-4 py-2 text-[#8899AA]">{c.grupo ?? "—"}</td>
                      <td className="px-4 py-2 text-[#8899AA]">{c.estado}</td>
                      <td className="px-4 py-2 text-[#8899AA]">{c.tribunal ?? "—"}</td>
                    </tr>
                  ))}
                  {processos.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-[#8899AA]/50">Nenhum processo com número cadastrado ainda.</td></tr>}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Modal Monitorar */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setModal(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={monitorar} className="w-full max-w-md rounded-2xl bg-[#0F2A44] p-6 text-white shadow-2xl">
            <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-bold">Monitorar Processo (Escavador)</h2><button type="button" onClick={() => setModal(false)} className="text-white/60 hover:text-white">✕</button></div>
            <p className="mb-4 text-xs text-white/55">Cadastre por número do processo (CNJ) ou por OAB. As intimações chegarão automaticamente nesta aba.</p>
            <div className="space-y-3">
              <input value={mon.numero_processo} onChange={(e) => setMon({ ...mon, numero_processo: e.target.value })} placeholder="Número do processo (CNJ)" className={inp + " w-full"} />
              <div className="text-center text-xs text-white/40">— ou —</div>
              <input value={mon.oab} onChange={(e) => setMon({ ...mon, oab: e.target.value })} placeholder="OAB (ex.: RO10849)" className={inp + " w-full"} />
              <select value={mon.tribunal} onChange={(e) => setMon({ ...mon, tribunal: e.target.value })} className={inp + " w-full"}><option value="">Tribunal (opcional)</option>{TRIBUNAIS.map((t) => <option key={t} value={t}>{t}</option>)}</select>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(false)} className="rounded-lg border border-white/15 px-4 py-2 text-sm text-white/70">Cancelar</button>
              <button type="submit" disabled={salvando} className="rounded-lg bg-[#C9A24D] px-5 py-2 text-sm font-bold text-[#0A1628] disabled:opacity-50">{salvando ? "Cadastrando…" : "Monitorar"}</button>
            </div>
          </form>
        </div>
      )}
    </PainelLayout>
  );
}
