"use client";
import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.seudominio.com.br";

const IconSend = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>
);
const IconBot = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

export default function Portal() {
  const [casoId, setCasoId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<{ autor: string; texto: string }[]>([]);
  const [input, setInput] = useState("");
  const [nome, setNome] = useState("");
  const [contato, setContato] = useState("");
  const [loading, setLoading] = useState(false);

  async function iniciar() {
    if (!nome.trim() || !input.trim()) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome, contato, relato: input }),
      });
      const d = await r.json();
      setCasoId(d.caso_id);
      setMsgs([
        { autor: "CLIENTE", texto: input },
        { autor: "AGENTE", texto: d.primeira_resposta ?? "Olá! Recebi sua mensagem. Um momento..." },
      ]);
      setInput("");
    } finally {
      setLoading(false);
    }
  }

  async function enviar() {
    if (!input.trim()) return;
    if (!casoId) return iniciar();
    const texto = input;
    setMsgs((m) => [...m, { autor: "CLIENTE", texto }]);
    setInput("");
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/${casoId}/mensagens`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conteudo: texto }),
      });
      const d = await r.json();
      if (d.resposta) setMsgs((m) => [...m, { autor: "AGENTE", texto: d.resposta }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#0A1628", fontFamily: "Inter, sans-serif" }}>
      {/* Header */}
      <header className="border-b border-white/5 bg-[#0A1628]/90 backdrop-blur-md px-6 py-4">
        <div className="mx-auto max-w-3xl flex items-center justify-between">
          <Link href="/" className="text-sm text-[#8899AA] hover:text-white transition-colors">
            &larr; Voltar
          </Link>
          <div className="flex flex-col items-center leading-none gap-1">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="FSC Advocacia" className="h-9 w-auto" />
            <span className="text-[10px] text-[#8899AA] tracking-widest uppercase">Portal de Atendimento</span>
          </div>
          <span className="text-xs text-[#8899AA] hidden md:block">OAB/RO 10.849</span>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-3xl px-4 py-6 flex flex-col gap-4">
        {/* Identificacao */}
        {!casoId && (
          <div className="rounded-xl bg-[#1A3A6B]/20 border border-[#2D7DD2]/20 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#2D7DD2]/20 flex items-center justify-center text-[#2D7DD2]">
                <IconBot />
              </div>
              <div>
                <p className="text-white font-semibold text-sm">Atendimento FSC</p>
                <p className="text-[#8899AA] text-xs">Assistente Juridico Digital</p>
              </div>
            </div>
            <p className="text-[#8899AA] text-sm mb-4 leading-relaxed">
              Ola! Para iniciarmos, informe seu nome e descreva sua situacao.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                className="rounded-lg border border-white/10 bg-[#0A1628] px-4 py-3 text-white placeholder-[#8899AA] text-sm focus:outline-none focus:border-[#2D7DD2] transition-colors"
                placeholder="Seu nome *"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
              />
              <input
                className="rounded-lg border border-white/10 bg-[#0A1628] px-4 py-3 text-white placeholder-[#8899AA] text-sm focus:outline-none focus:border-[#2D7DD2] transition-colors"
                placeholder="WhatsApp ou e-mail (opcional)"
                value={contato}
                onChange={(e) => setContato(e.target.value)}
              />
            </div>
          </div>
        )}

        {/* Mensagens */}
        <div className="flex-1 min-h-[16rem] space-y-4 overflow-y-auto rounded-xl border border-white/5 bg-[#0A1628] p-4">
          {msgs.length === 0 && (
            <div className="text-center text-[#8899AA] text-sm py-12">
              Descreva sua situacao abaixo para iniciar o atendimento.
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.autor === "CLIENTE" ? "justify-end" : "justify-start"}`}>
              {m.autor === "AGENTE" && (
                <div className="w-7 h-7 rounded-full bg-[#2D7DD2]/20 flex items-center justify-center text-[#2D7DD2] shrink-0 mr-2 mt-1">
                  <IconBot />
                </div>
              )}
              <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                m.autor === "CLIENTE"
                  ? "bg-[#2D7DD2] text-white"
                  : "bg-[#1A3A6B]/40 border border-white/5 text-white"
              }`}>
                {m.texto}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="w-7 h-7 rounded-full bg-[#2D7DD2]/20 flex items-center justify-center text-[#2D7DD2] shrink-0 mr-2">
                <IconBot />
              </div>
              <div className="bg-[#1A3A6B]/40 border border-white/5 rounded-xl px-4 py-3">
                <span className="flex gap-1">
                  {[0,1,2].map((i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-[#8899AA] animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex gap-3 items-end">
          <textarea
            className="flex-1 rounded-xl border border-white/10 bg-[#1A3A6B]/20 px-4 py-3 text-white placeholder-[#8899AA] text-sm focus:outline-none focus:border-[#2D7DD2] transition-colors resize-none"
            rows={3}
            placeholder="Descreva sua situacao detalhadamente... (Enter para enviar)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
          />
          <button
            onClick={enviar}
            disabled={loading || !input.trim()}
            className="rounded-xl bg-[#2D7DD2] hover:bg-[#4361EE] disabled:opacity-40 disabled:cursor-not-allowed text-white p-4 transition-colors shrink-0"
          >
            <IconSend />
          </button>
        </div>

        <p className="text-center text-xs text-[#8899AA]/60">
          Canal informativo. Nao constitui contratacao de servicos juridicos.
          Dr. Fabio Silva Cunha — OAB/RO 10.849
        </p>
      </main>
    </div>
  );
}
