"use client";
// Portal do Cliente — chat com o Agente Especialista
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.seudominio.com.br";

export default function Portal() {
  const [casoId, setCasoId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<{ autor: string; texto: string }[]>([]);
  const [input, setInput] = useState("");
  const [nome, setNome] = useState("");
  const [contato, setContato] = useState("");

  async function iniciar() {
    const r = await fetch(`${API}/api/v1/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, contato, relato: input }),
    });
    const d = await r.json();
    setCasoId(d.caso_id);
    setMsgs([
      { autor: "CLIENTE", texto: input },
      { autor: "AGENTE", texto: d.primeira_resposta ?? "Um momento..." },
    ]);
    setInput("");
  }

  async function enviar() {
    if (!casoId) return iniciar();
    const texto = input;
    setMsgs((m) => [...m, { autor: "CLIENTE", texto }]);
    setInput("");
    const r = await fetch(`${API}/api/v1/casos/${casoId}/mensagens`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conteudo: texto }),
    });
    const d = await r.json();
    if (d.resposta) setMsgs((m) => [...m, { autor: "AGENTE", texto: d.resposta }]);
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-bold text-slate-800">
        FSC Advocacia — Atendimento
      </h1>
      {!casoId && (
        <div className="mt-4 space-y-2">
          <input className="w-full rounded border p-2" placeholder="Seu nome"
                 value={nome} onChange={(e) => setNome(e.target.value)} />
          <input className="w-full rounded border p-2" placeholder="WhatsApp ou e-mail"
                 value={contato} onChange={(e) => setContato(e.target.value)} />
        </div>
      )}
      <div className="mt-4 h-96 space-y-3 overflow-y-auto rounded border bg-slate-50 p-4">
        {msgs.map((m, i) => (
          <div key={i}
               className={`max-w-[80%] rounded-lg p-3 text-sm ${
                 m.autor === "CLIENTE"
                   ? "ml-auto bg-blue-600 text-white"
                   : "bg-white shadow"}`}>
            {m.texto}
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <textarea className="flex-1 rounded border p-2" rows={2}
                  placeholder="Conte o que aconteceu..."
                  value={input} onChange={(e) => setInput(e.target.value)} />
        <button onClick={enviar}
                className="rounded bg-blue-600 px-5 font-semibold text-white">
          Enviar
        </button>
      </div>
    </main>
  );
}
