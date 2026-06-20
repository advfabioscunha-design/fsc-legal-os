"use client";
import { useEffect, useMemo, useState } from "react";
import PainelLayout from "../components/PainelLayout";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";
const NICHOS = ["BANCARIO", "IMOBILIARIO", "TRABALHISTA", "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"];
const SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const inp = "rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-sm text-white outline-none focus:border-[#C9A24D]";
const fmt = (d: Date) => d.toISOString().slice(0, 10);

export default function AgendaPage() {
  const [ref, setRef] = useState(new Date());
  const [membros, setMembros] = useState<any[]>([]);
  const [prazos, setPrazos] = useState<any[]>([]);
  const [filtro, setFiltro] = useState("");
  const [modal, setModal] = useState<"" | "novo" | "distribuir" | "equipe">("");
  const [form, setForm] = useState({ titulo: "", descricao: "", data: fmt(new Date()), responsavel_id: "", especialidade: "" });
  const [novoM, setNovoM] = useState({ nome: "", especialidades: "", lider: false });

  const primeiro = new Date(ref.getFullYear(), ref.getMonth(), 1);
  const ultimo = new Date(ref.getFullYear(), ref.getMonth() + 1, 0);

  function loadMembros() { fetch(`${API}/api/v1/membros`).then((r) => r.json()).then((d) => setMembros(Array.isArray(d) ? d : [])).catch(() => {}); }
  function loadPrazos() {
    const p = new URLSearchParams({ inicio: fmt(primeiro), fim: fmt(ultimo) });
    if (filtro) p.set("responsavel_id", filtro);
    fetch(`${API}/api/v1/prazos?${p}`).then((r) => r.json()).then((d) => setPrazos(Array.isArray(d) ? d : [])).catch(() => {});
  }
  useEffect(() => { loadMembros(); }, []);
  useEffect(() => { loadPrazos(); /* eslint-disable-next-line */ }, [ref, filtro]);

  const dias = useMemo(() => {
    const arr: (Date | null)[] = [];
    for (let i = 0; i < primeiro.getDay(); i++) arr.push(null);
    for (let d = 1; d <= ultimo.getDate(); d++) arr.push(new Date(ref.getFullYear(), ref.getMonth(), d));
    return arr;
    // eslint-disable-next-line
  }, [ref]);

  const prazosDoDia = (d: Date) => prazos.filter((p) => String(p.data).slice(0, 10) === fmt(d));

  async function salvarPrazo(e: React.FormEvent) {
    e.preventDefault();
    if (!form.titulo || !form.data) return;
    await fetch(`${API}/api/v1/prazos`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
    setModal(""); setForm({ titulo: "", descricao: "", data: fmt(new Date()), responsavel_id: "", especialidade: "" }); loadPrazos();
  }
  async function distribuir(e: React.FormEvent) {
    e.preventDefault();
    if (!form.titulo || !form.data) return;
    const r = await fetch(`${API}/api/v1/prazos/distribuir`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ titulo: form.titulo, descricao: form.descricao, data: form.data, especialidade: form.especialidade }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { alert(d.detail || "Não foi possível distribuir."); return; }
    alert(`Prazo distribuído para ${d.responsavel} (carga na semana: ${d.carga_semana}).`);
    setModal(""); setForm({ titulo: "", descricao: "", data: fmt(new Date()), responsavel_id: "", especialidade: "" }); loadPrazos();
  }
  async function addMembro(e: React.FormEvent) {
    e.preventDefault();
    if (!novoM.nome) return;
    await fetch(`${API}/api/v1/membros`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: novoM.nome, lider: novoM.lider, especialidades: novoM.especialidades.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean) }) });
    setNovoM({ nome: "", especialidades: "", lider: false }); loadMembros();
  }
  async function delMembro(id: string) { await fetch(`${API}/api/v1/membros/${id}`, { method: "DELETE" }); loadMembros(); }
  async function concluir(id: string) { await fetch(`${API}/api/v1/prazos/${id}`, { method: "PATCH" }); loadPrazos(); }

  return (
    <PainelLayout titulo="Agenda">
      <div className="p-5">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button onClick={() => setRef(new Date(ref.getFullYear(), ref.getMonth() - 1, 1))} className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-white">‹</button>
          <span className="min-w-[10rem] text-center font-bold text-white">{ref.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</span>
          <button onClick={() => setRef(new Date(ref.getFullYear(), ref.getMonth() + 1, 1))} className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-white">›</button>
          <select value={filtro} onChange={(e) => setFiltro(e.target.value)} className={inp + " ml-2"}>
            <option value="">Equipe toda</option>
            {membros.map((m) => <option key={m.id} value={m.id}>{m.nome}{m.lider ? " (líder)" : ""}</option>)}
          </select>
          <div className="ml-auto flex gap-2">
            <button onClick={() => setModal("equipe")} className="rounded-lg border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/5">Equipe</button>
            <button onClick={() => setModal("distribuir")} className="rounded-lg bg-[#2D7DD2] px-4 py-2 text-sm font-bold text-white hover:bg-[#256bb3]">⚖ Distribuir (IA)</button>
            <button onClick={() => setModal("novo")} className="rounded-lg bg-[#C9A24D] px-4 py-2 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e]">+ Novo prazo</button>
          </div>
        </div>

        {/* Calendário */}
        <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-white/10 bg-white/10">
          {SEMANA.map((s) => <div key={s} className="bg-[#0B1F3B] px-2 py-2 text-center text-xs font-semibold text-[#8899AA]">{s}</div>)}
          {dias.map((d, i) => (
            <div key={i} className="min-h-[92px] bg-[#0A1628] p-1.5">
              {d && (
                <>
                  <p className="mb-1 text-xs text-[#8899AA]">{d.getDate()}</p>
                  {prazosDoDia(d).map((p) => (
                    <button key={p.id} onClick={() => { if (confirm(`Concluir "${p.titulo}"?`)) concluir(p.id); }}
                      className={`mb-1 block w-full truncate rounded px-1.5 py-1 text-left text-[11px] ${p.status === "CONCLUIDO" ? "bg-[#1DB954]/20 text-[#1DB954] line-through" : "bg-[#C9A24D]/20 text-[#C9A24D]"}`}
                      title={`${p.titulo} — ${p.membros_equipe?.nome || "sem responsável"}`}>
                      {p.titulo} <span className="text-white/50">· {p.membros_equipe?.nome?.split(" ")[0] || "—"}</span>
                    </button>
                  ))}
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Modais */}
      {(modal === "novo" || modal === "distribuir") && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setModal("")}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={modal === "novo" ? salvarPrazo : distribuir} className="w-full max-w-md rounded-2xl bg-[#0F2A44] p-6 text-white shadow-2xl">
            <h2 className="mb-4 text-lg font-bold">{modal === "novo" ? "Novo prazo" : "Distribuir automaticamente (Agente Controlador)"}</h2>
            <div className="space-y-3">
              <input value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} placeholder="Título do prazo" className={inp + " w-full"} />
              <textarea value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Descrição" rows={2} className={inp + " w-full"} />
              <input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} className={inp + " w-full"} />
              <select value={form.especialidade} onChange={(e) => setForm({ ...form, especialidade: e.target.value })} className={inp + " w-full"}>
                <option value="">Especialidade (nicho)</option>{NICHOS.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
              {modal === "novo" && (
                <select value={form.responsavel_id} onChange={(e) => setForm({ ...form, responsavel_id: e.target.value })} className={inp + " w-full"}>
                  <option value="">Responsável (opcional)</option>{membros.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
                </select>
              )}
              {modal === "distribuir" && <p className="text-xs text-white/55">A IA escolhe o membro apto (pela especialidade) com menos prazos abertos na semana.</p>}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal("")} className="rounded-lg border border-white/15 px-4 py-2 text-sm text-white/70">Cancelar</button>
              <button type="submit" className="rounded-lg bg-[#C9A24D] px-5 py-2 text-sm font-bold text-[#0A1628]">{modal === "novo" ? "Salvar" : "Distribuir"}</button>
            </div>
          </form>
        </div>
      )}

      {modal === "equipe" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setModal("")}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-lg rounded-2xl bg-[#0F2A44] p-6 text-white shadow-2xl">
            <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-bold">Equipe</h2><button onClick={() => setModal("")} className="text-white/60">✕</button></div>
            <form onSubmit={addMembro} className="mb-4 flex flex-wrap items-center gap-2">
              <input value={novoM.nome} onChange={(e) => setNovoM({ ...novoM, nome: e.target.value })} placeholder="Nome" className={inp + " flex-1 min-w-[8rem]"} />
              <input value={novoM.especialidades} onChange={(e) => setNovoM({ ...novoM, especialidades: e.target.value })} placeholder="Especialidades (ex.: BANCARIO, TRIBUTARIO)" className={inp + " flex-1 min-w-[10rem]"} />
              <label className="flex items-center gap-1 text-xs text-[#8899AA]"><input type="checkbox" checked={novoM.lider} onChange={(e) => setNovoM({ ...novoM, lider: e.target.checked })} /> líder</label>
              <button className="rounded-lg bg-[#C9A24D] px-3 py-2 text-sm font-bold text-[#0A1628]">+</button>
            </form>
            <ul className="space-y-2">
              {membros.map((m) => (
                <li key={m.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-[#0A1628]/50 px-3 py-2 text-sm">
                  <span>{m.nome}{m.lider && <span className="ml-1 text-[10px] text-[#C9A24D]">★ líder</span>}<span className="ml-2 text-xs text-[#8899AA]">{(m.especialidades || []).join(", ")}</span></span>
                  <button onClick={() => delMembro(m.id)} className="text-[#C0392B] hover:underline">remover</button>
                </li>
              ))}
              {membros.length === 0 && <li className="text-[#8899AA]/50">Nenhum membro cadastrado.</li>}
            </ul>
          </div>
        </div>
      )}
    </PainelLayout>
  );
}
