"use client";
// CRM — Kanban da esteira (back-office)
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.seudominio.com.br";

const COLUNAS = [
  "QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO", "COLETA_DOCS",
  "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO", "PROTOCOLO_RPA",
  "PROTOCOLADO", "ESCALADO_HUMANO",
];

type Caso = {
  id: string; estado: string; grupo: string | null; subtipo: string | null;
  clientes: { nome: string } | null; tese_id: string | null;
};

export default function CRM() {
  const [casos, setCasos] = useState<Caso[]>([]);

  useEffect(() => {
    fetch(`${API}/api/v1/casos`).then((r) => r.json()).then(setCasos);
  }, []);

  async function aprovar(id: string) {
    await fetch(`${API}/api/v1/casos/${id}/aprovar-protocolar`, { method: "POST" });
    location.reload();
  }

  return (
    <main className="p-4">
      <h1 className="mb-4 text-xl font-bold">FSC Legal OS — Esteira</h1>
      <div className="flex gap-3 overflow-x-auto">
        {COLUNAS.map((col) => (
          <div key={col} className="w-64 shrink-0 rounded bg-slate-100 p-2">
            <h2 className="mb-2 text-xs font-bold text-slate-600">{col}</h2>
            {casos.filter((c) => c.estado === col).map((c) => (
              <div key={c.id} className="mb-2 rounded bg-white p-2 text-sm shadow">
                <p className="font-semibold">{c.clientes?.nome ?? "—"}</p>
                <p className="text-xs text-slate-500">
                  {c.grupo}{c.subtipo ? ` › ${c.subtipo}` : ""} · {c.tese_id ?? "sem tese"}
                </p>
                {col === "REVISAO" && (
                  <button onClick={() => aprovar(c.id)}
                          className="mt-2 w-full rounded bg-emerald-600 py-1 text-xs font-bold text-white">
                    APROVAR E PROTOCOLAR
                  </button>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </main>
  );
}
