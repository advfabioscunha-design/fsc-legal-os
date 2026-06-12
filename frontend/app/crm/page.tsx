"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.seudominio.com.br";

const COLUNAS = [
  { id: "QUALIFICACAO",   label: "Qualificacao",     cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "PROPOSTA",       label: "Proposta",          cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "CONTRATO",       label: "Contrato",          cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "PAGAMENTO",      label: "Pagamento",         cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "COLETA_DOCS",    label: "Coleta Docs",       cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "COLETA_PROVAS",  label: "Coleta Provas",     cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "ANALISE",        label: "Analise",           cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "PETICAO",        label: "Peticao",           cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "REVISAO",        label: "Revisao",           cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "PROTOCOLO_RPA",  label: "Protocolo RPA",     cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
  { id: "PROTOCOLADO",    label: "Protocolado",       cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
  { id: "ESCALADO_HUMANO",label: "Escalado",          cor: "border-[#C0392B]", hdr: "bg-[#C0392B]/10" },
];

type Caso = {
  id: string; estado: string; grupo: string | null; subtipo: string | null;
  clientes: { nome: string } | null; tese_id: string | null;
};

export default function CRM() {
  const [casos, setCasos] = useState<Caso[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    fetch(`${API}/api/v1/casos`)
      .then((r) => r.json())
      .then(setCasos)
      .catch(() => setCasos([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function aprovar(id: string) {
    await fetch(`${API}/api/v1/casos/${id}/aprovar-protocolar`, { method: "POST" });
    load();
  }

  return (
    <div className="min-h-screen" style={{ background: "#0A1628", fontFamily: "Inter, sans-serif" }}>
      <header className="border-b border-white/5 bg-[#0A1628] px-6 py-4 sticky top-0 z-40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm text-[#8899AA] hover:text-white transition-colors">
              &larr; Site
            </Link>
            <div className="flex flex-col leading-none">
              <span className="text-lg font-bold text-white" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                FSC <span className="text-[#2D7DD2]">Legal OS</span>
              </span>
              <span className="text-[10px] text-[#8899AA] tracking-widest uppercase">Esteira de Casos</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#8899AA]">
              {loading ? "Carregando..." : `${casos.length} caso(s)`}
            </span>
            <button onClick={load}
              className="text-sm text-[#8899AA] hover:text-white border border-white/10 rounded-md px-3 py-1.5 transition-colors">
              Atualizar
            </button>
          </div>
        </div>
      </header>

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
                    <div key={c.id} className="rounded-lg bg-[#1A3A6B]/30 border border-white/5 p-3 hover:border-[#2D7DD2]/30 transition-colors">
                      <p className="font-semibold text-white text-sm truncate">{c.clientes?.nome ?? "—"}</p>
                      <p className="text-xs text-[#8899AA] mt-1 truncate">
                        {c.grupo}{c.subtipo ? ` > ${c.subtipo}` : ""}
                      </p>
                      {c.tese_id && (
                        <span className="inline-block mt-1 text-[10px] bg-[#2D7DD2]/15 text-[#2D7DD2] rounded px-2 py-0.5">
                          {c.tese_id}
                        </span>
                      )}
                      {col.id === "REVISAO" && (
                        <button onClick={() => aprovar(c.id)}
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
    </div>
  );
}
