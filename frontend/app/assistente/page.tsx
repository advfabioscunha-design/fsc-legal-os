"use client";
import { useEffect, useRef, useState } from "react";
import PainelLayout from "../components/PainelLayout";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";
type Msg = { role: "user" | "assistant"; content: string };

const SAUDACAO: Msg = {
  role: "assistant",
  content: "Olá! Sou o Assistente CEO da FC Advocacia. Posso te ajudar com dúvidas sobre a plataforma e a organização do trabalho. Me conte o que precisa.",
};

export default function AssistentePage() {
  const [msgs, setMsgs] = useState<Msg[]>([SAUDACAO]);
  const [input, setInput] = useState("");
  const [enviando, setEnviando] = useState(false);
  const fim = useRef<HTMLDivElement | null>(null);
  useEffect(() => { fim.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, enviando]);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const texto = input.trim();
    if (!texto || enviando) return;
    const historico = msgs.filter((m) => m !== SAUDACAO);
    setMsgs((m) => [...m, { role: "user", content: texto }]);
    setInput(""); setEnviando(true);
    try {
      const r = await fetch(`${API}/api/v1/assistente`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conteudo: texto, historico }),
      });
      const d = await r.json().catch(() => ({}));
      setMsgs((m) => [...m, { role: "assistant", content: d.resposta || "Pode repetir, por favor?" }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", content: "Tive um problema de conexão. Tente novamente." }]);
    } finally { setEnviando(false); }
  }

  return (
    <PainelLayout titulo="Assistente">
      <div className="mx-auto flex h-[calc(100vh-56px)] max-w-3xl flex-col p-5">
        <div className="mb-3">
          <h2 className="text-lg font-bold text-white">Assistente CEO — Tira Dúvidas</h2>
          <p className="text-xs text-[#8899AA]">Apoio interno da equipe. Para mérito jurídico, valide sempre com seu líder.</p>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "rounded-br-md bg-[#C9A24D] text-[#0A1628]" : "rounded-bl-md bg-[#0A1628] text-white"}`}>{m.content}</div>
            </div>
          ))}
          {enviando && <div className="text-sm text-[#8899AA]">digitando…</div>}
          <div ref={fim} />
        </div>
        <form onSubmit={enviar} className="mt-3 flex items-end gap-2">
          <textarea value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(e as any); } }}
            rows={1} placeholder="Escreva sua dúvida…"
            className="max-h-32 flex-1 resize-none rounded-xl border border-white/15 bg-[#0B1F3B] px-4 py-2.5 text-sm text-white outline-none focus:border-[#C9A24D]" />
          <button type="submit" disabled={enviando} className="rounded-xl bg-[#C9A24D] px-5 py-2.5 text-sm font-bold text-[#0A1628] disabled:opacity-50">Enviar</button>
        </form>
      </div>
    </PainelLayout>
  );
}
