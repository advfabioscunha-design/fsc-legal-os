"use client";
import { useEffect, useState } from "react";
import PainelLayout from "../components/PainelLayout";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

const CORES = ["#C9A24D", "#2D7DD2", "#1DB954", "#F39C12", "#9B59B6", "#E74C3C", "#1ABC9C"];
const brl = (v: number) => (Number(v) || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const inp = "rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-sm text-white outline-none focus:border-[#C9A24D]";

function Pizza({ dados }: { dados: [string, number][] }) {
  const total = dados.reduce((s, [, v]) => s + v, 0) || 1;
  const r = 70, C = 2 * Math.PI * r;
  let acc = 0;
  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <g transform="translate(90,90) rotate(-90)">
          <circle r={r} fill="none" stroke="#ffffff14" strokeWidth="22" />
          {dados.map(([nome, v], i) => {
            const len = (v / total) * C;
            const seg = <circle key={nome} r={r} fill="none" stroke={CORES[i % CORES.length]} strokeWidth="22" strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-acc} />;
            acc += len; return seg;
          })}
        </g>
        <text x="90" y="86" textAnchor="middle" className="fill-white" fontSize="26" fontWeight="700">{total}</text>
        <text x="90" y="104" textAnchor="middle" fill="#8899AA" fontSize="11">casos</text>
      </svg>
      <ul className="space-y-1 text-sm">
        {dados.map(([nome, v], i) => (
          <li key={nome} className="flex items-center gap-2 text-white/80">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: CORES[i % CORES.length] }} />
            {nome} <span className="text-[#8899AA]">· {v} ({Math.round((v / total) * 100)}%)</span>
          </li>
        ))}
        {dados.length === 0 && <li className="text-[#8899AA]/60">Sem dados no período.</li>}
      </ul>
    </div>
  );
}

function Card({ titulo, valor, sub }: { titulo: string; valor: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5">
      <p className="text-xs uppercase tracking-wide text-[#8899AA]">{titulo}</p>
      <p className="mt-1 text-2xl font-bold text-white">{valor}</p>
      {sub && <p className="mt-1 text-xs text-[#8899AA]">{sub}</p>}
    </div>
  );
}

export default function AdminPage() {
  const [aba, setAba] = useState<"painel" | "custos">("painel");
  const [periodo, setPeriodo] = useState("mes");
  const [m, setM] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Custos
  const [resumo, setResumo] = useState<any>(null);
  const [lancs, setLancs] = useState<any[]>([]);
  const [folha, setFolha] = useState<any[]>([]);
  const [novoL, setNovoL] = useState({ tipo: "SAIDA", categoria: "", descricao: "", valor: "", recorrente: false });
  const [novoF, setNovoF] = useState({ nome: "", cargo: "", salario: "" });

  useEffect(() => {
    if (aba !== "painel") return;
    setLoading(true);
    fetch(`${API}/api/v1/admin/metricas?periodo=${periodo}`).then((r) => r.json()).then(setM).catch(() => setM(null)).finally(() => setLoading(false));
  }, [aba, periodo]);

  function loadCustos() {
    fetch(`${API}/api/v1/financeiro/resumo?periodo=${periodo}`).then((r) => r.json()).then(setResumo).catch(() => {});
    fetch(`${API}/api/v1/financeiro/lancamentos`).then((r) => r.json()).then((d) => setLancs(Array.isArray(d) ? d : [])).catch(() => {});
    fetch(`${API}/api/v1/financeiro/folha`).then((r) => r.json()).then((d) => setFolha(Array.isArray(d) ? d : [])).catch(() => {});
  }
  useEffect(() => { if (aba === "custos") loadCustos(); /* eslint-disable-next-line */ }, [aba, periodo]);

  async function addLanc(e: React.FormEvent) {
    e.preventDefault();
    if (!novoL.valor) return;
    await fetch(`${API}/api/v1/financeiro/lancamentos`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...novoL, valor: Number(String(novoL.valor).replace(",", ".")) }) });
    setNovoL({ tipo: "SAIDA", categoria: "", descricao: "", valor: "", recorrente: false }); loadCustos();
  }
  async function delLanc(id: string) { await fetch(`${API}/api/v1/financeiro/lancamentos/${id}`, { method: "DELETE" }); loadCustos(); }
  async function addFolha(e: React.FormEvent) {
    e.preventDefault();
    if (!novoF.nome || !novoF.salario) return;
    await fetch(`${API}/api/v1/financeiro/folha`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...novoF, salario: Number(String(novoF.salario).replace(",", ".")) }) });
    setNovoF({ nome: "", cargo: "", salario: "" }); loadCustos();
  }
  async function delFolha(id: string) { await fetch(`${API}/api/v1/financeiro/folha/${id}`, { method: "DELETE" }); loadCustos(); }

  const nicho: [string, number][] = m ? (Object.entries(m.por_nicho || {}) as any) : [];
  const fin = m?.financeiro || {};

  return (
    <PainelLayout titulo="Administração">
      <div className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-2">
            {([["painel", "Painel de Gestão"], ["custos", "Custos"]] as const).map(([k, l]) => (
              <button key={k} onClick={() => setAba(k)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${aba === k ? "bg-[#C9A24D] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>{l}</button>
            ))}
          </div>
          <div className="flex gap-2">
            {([["dia", "Diário"], ["semana", "Semanal"], ["mes", "Mensal"], ["ano", "Anual"]] as const).map(([k, l]) => (
              <button key={k} onClick={() => setPeriodo(k)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${periodo === k ? "bg-[#2D7DD2] text-white" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>{l}</button>
            ))}
          </div>
        </div>

        {aba === "painel" ? (
          loading ? <p className="text-[#8899AA]">Carregando métricas...</p> : (
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Card titulo="Esteira de Contratação" valor={String(m?.funil?.contratacao ?? 0)} sub="leads → pagamento" />
                <Card titulo="Em Produção" valor={String(m?.funil?.producao ?? 0)} sub="coleta → revisão" />
                <Card titulo="Ativos / Protocolados" valor={String(m?.funil?.ativos ?? 0)} sub="protocolado → concluído" />
                <Card titulo="Casos no Período" valor={String(m?.total_casos ?? 0)} sub={periodo} />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <Card titulo="Honorários Recebidos" valor={brl(fin.recebido ?? 0)} sub="pagamentos confirmados" />
                <Card titulo="Honorários a Receber" valor={brl(fin.a_receber ?? 0)} sub="contratados em andamento" />
                <Card titulo="Ticket Médio" valor={brl(fin.ticket_medio ?? 0)} sub={`base: ${fin.qtd_valores ?? 0} casos`} />
              </div>
              <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5">
                <p className="mb-4 text-sm font-bold text-[#C9A24D]">Distribuição de casos por nicho</p>
                <Pizza dados={nicho} />
              </div>
            </div>
          )
        ) : (
          /* ── CUSTOS ── */
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card titulo="Entradas (período)" valor={brl(resumo?.entradas ?? 0)} />
              <Card titulo="Saídas (período)" valor={brl(resumo?.saidas ?? 0)} />
              <Card titulo="Saldo" valor={brl(resumo?.saldo ?? 0)} />
              <Card titulo="Folha Mensal" valor={brl(resumo?.folha_mensal ?? 0)} sub={`Projeção anual de custos: ${brl(resumo?.projecao_anual_custos ?? 0)}`} />
            </div>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
              {/* Lançamentos */}
              <div className="lg:col-span-2 rounded-xl border border-white/10 bg-[#0B1F3B] p-5">
                <p className="mb-3 text-sm font-bold text-[#C9A24D]">Entradas e Saídas</p>
                <form onSubmit={addLanc} className="mb-4 flex flex-wrap items-center gap-2">
                  <select value={novoL.tipo} onChange={(e) => setNovoL({ ...novoL, tipo: e.target.value })} className={inp}>
                    <option value="SAIDA">Saída</option><option value="ENTRADA">Entrada</option>
                  </select>
                  <input value={novoL.categoria} onChange={(e) => setNovoL({ ...novoL, categoria: e.target.value })} placeholder="Categoria" className={inp + " w-32"} />
                  <input value={novoL.descricao} onChange={(e) => setNovoL({ ...novoL, descricao: e.target.value })} placeholder="Descrição" className={inp + " flex-1 min-w-[8rem]"} />
                  <input value={novoL.valor} onChange={(e) => setNovoL({ ...novoL, valor: e.target.value })} placeholder="Valor" inputMode="decimal" className={inp + " w-28"} />
                  <label className="flex items-center gap-1 text-xs text-[#8899AA]"><input type="checkbox" checked={novoL.recorrente} onChange={(e) => setNovoL({ ...novoL, recorrente: e.target.checked })} /> fixo mensal</label>
                  <button className="rounded-lg bg-[#C9A24D] px-4 py-2 text-sm font-bold text-[#0A1628]">Adicionar</button>
                </form>
                <div className="max-h-80 overflow-y-auto">
                  <table className="min-w-full text-sm">
                    <thead className="text-left text-[#8899AA]"><tr><th className="py-1">Data</th><th>Tipo</th><th>Descrição</th><th className="text-right">Valor</th><th></th></tr></thead>
                    <tbody>
                      {lancs.map((l) => (
                        <tr key={l.id} className="border-t border-white/5 text-white">
                          <td className="py-1 text-[#8899AA]">{l.data}</td>
                          <td className={l.tipo === "ENTRADA" ? "text-[#1DB954]" : "text-[#E74C3C]"}>{l.tipo === "ENTRADA" ? "Entrada" : "Saída"}{l.recorrente ? " (fixo)" : ""}</td>
                          <td>{l.descricao || l.categoria || "—"}</td>
                          <td className="text-right">{brl(Number(l.valor))}</td>
                          <td className="text-right"><button onClick={() => delLanc(l.id)} className="text-[#C0392B] hover:underline">x</button></td>
                        </tr>
                      ))}
                      {lancs.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-[#8899AA]/50">Sem lançamentos.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Folha */}
              <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5">
                <p className="mb-3 text-sm font-bold text-[#C9A24D]">Folha da Equipe</p>
                <form onSubmit={addFolha} className="mb-4 space-y-2">
                  <input value={novoF.nome} onChange={(e) => setNovoF({ ...novoF, nome: e.target.value })} placeholder="Nome" className={inp + " w-full"} />
                  <input value={novoF.cargo} onChange={(e) => setNovoF({ ...novoF, cargo: e.target.value })} placeholder="Cargo" className={inp + " w-full"} />
                  <div className="flex gap-2">
                    <input value={novoF.salario} onChange={(e) => setNovoF({ ...novoF, salario: e.target.value })} placeholder="Salário" inputMode="decimal" className={inp + " flex-1"} />
                    <button className="rounded-lg bg-[#C9A24D] px-3 py-2 text-sm font-bold text-[#0A1628]">+</button>
                  </div>
                </form>
                <ul className="space-y-2">
                  {folha.map((f) => (
                    <li key={f.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-[#0A1628]/50 px-3 py-2 text-sm text-white">
                      <span>{f.nome} <span className="text-xs text-[#8899AA]">{f.cargo || ""}</span></span>
                      <span className="flex items-center gap-2">{brl(Number(f.salario))}<button onClick={() => delFolha(f.id)} className="text-[#C0392B] hover:underline">x</button></span>
                    </li>
                  ))}
                  {folha.length === 0 && <li className="text-[#8899AA]/50">Sem membros cadastrados.</li>}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </PainelLayout>
  );
}
