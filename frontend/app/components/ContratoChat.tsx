"use client";
import { useEffect, useRef, useState } from "react";
import DocumentoRevisao from "./DocumentoRevisao";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";
const MARCADOR = "===CONTRATO EM REVISÃO===";

type Msg = { autor: "CLIENTE" | "AGENTE"; conteudo: string };

const FALLBACK =
  "Recebi sua mensagem e já estou cuidando do seu contrato. Me dê só mais um detalhe que eu sigo — não vou te deixar sem resposta.";

export default function ContratoChat({ nome, email, onVoltar }: { nome: string; email: string; onVoltar: () => void }) {
  const [casoId, setCasoId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [pago, setPago] = useState(false);
  const [docTexto, setDocTexto] = useState<string | null>(null);
  const [docAberto, setDocAberto] = useState(false);
  const fimRef = useRef<HTMLDivElement | null>(null);

  // inicia o serviço de contrato ao abrir
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/contrato/iniciar`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nome, contato: email, canal: "PORTAL" }),
        });
        const data = r.ok ? await r.json() : null;
        if (data?.caso_id) setCasoId(data.caso_id);
        setMsgs([{ autor: "AGENTE", conteudo: data?.resposta || "Olá! Vamos elaborar o seu contrato." }]);
      } catch {
        setMsgs([{ autor: "AGENTE", conteudo: "Olá! Vamos elaborar o seu contrato. Me conte qual contrato você precisa." }]);
      } finally { setCarregando(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { fimRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, enviando]);

  function processarResposta(texto: string) {
    const t = (texto || "").trim() || FALLBACK;
    if (t.includes(MARCADOR)) {
      const doc = t.split(MARCADOR)[1]?.trim() || t;
      setDocTexto(doc);
      setMsgs((m) => [...m, { autor: "AGENTE", conteudo: "Seu contrato está pronto para revisão. Toque em \"Abrir documento (revisão)\" para conferir." }]);
    } else {
      setMsgs((m) => [...m, { autor: "AGENTE", conteudo: t }]);
    }
  }

  async function enviarTexto(texto: string) {
    if (!texto.trim() || enviando || !casoId) return;
    setMsgs((m) => [...m, { autor: "CLIENTE", conteudo: texto }]);
    setEnviando(true);
    try {
      const r = await fetch(`${API}/api/v1/contrato/${casoId}/mensagens`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conteudo: texto, canal: "PORTAL" }),
      });
      const data = r.ok ? await r.json() : null;
      processarResposta(data?.resposta);
    } catch { processarResposta(""); }
    finally { setEnviando(false); }
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const texto = input.trim();
    setInput("");
    await enviarTexto(texto);
  }

  function pagar() {
    setPago(true);
    enviarTexto("Confirmo a contratação e o pagamento (modo simulado). Pode seguir com a coleta das informações do contrato.");
  }

  return (
    <section className="flex flex-col rounded-2xl border border-black/5 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-black/5 px-5 py-3">
        <div>
          <p className="text-sm font-semibold text-navy">Elaboração de Contrato</p>
          <p className="text-xs text-charcoal/50">Complexidade • coleta • revisão • envio</p>
        </div>
        <button onClick={onVoltar} className="text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
      </div>

      {/* Barra de ações: pagamento (simulado) + documento */}
      <div className="flex flex-wrap items-center gap-2 border-b border-black/5 bg-ice px-4 py-2">
        <button onClick={pagar} disabled={pago}
          className="rounded-full bg-navy px-4 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
          {pago ? "Pagamento confirmado (simulado)" : "Pagar / Contratar (simulado)"}
        </button>
        {docTexto && (
          <button onClick={() => setDocAberto(true)}
            className="rounded-full bg-gold px-4 py-1.5 text-xs font-bold text-navy hover:bg-amber">
            Abrir documento (revisão)
          </button>
        )}
        <span className="ml-auto text-[11px] text-charcoal/45">Asaas em modo simulado</span>
      </div>

      <div className="flex h-[50vh] flex-col gap-3 overflow-y-auto px-5 py-4">
        {carregando ? (
          <p className="text-charcoal/50">Iniciando atendimento...</p>
        ) : (
          msgs.map((m, i) => (
            <div key={i} className={`flex ${m.autor === "CLIENTE" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.autor === "CLIENTE" ? "rounded-br-md bg-navy text-white" : "rounded-bl-md bg-ice text-charcoal"
              }`}>{m.conteudo}</div>
            </div>
          ))
        )}
        {enviando && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md bg-ice px-4 py-2.5 text-sm text-charcoal/50">digitando…</div>
          </div>
        )}
        <div ref={fimRef} />
      </div>

      <form onSubmit={enviar} className="flex items-end gap-2 border-t border-black/5 p-4">
        <textarea value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(e as any); } }}
          rows={1} placeholder="Escreva sua mensagem…"
          className="max-h-32 flex-1 resize-none rounded-xl border border-black/10 px-4 py-2.5 text-sm outline-none focus:border-gold" />
        <button type="submit" disabled={enviando || !casoId}
          className="rounded-xl bg-gold px-5 py-2.5 text-sm font-semibold text-navy transition hover:bg-amber disabled:opacity-50">Enviar</button>
      </form>

      <DocumentoRevisao
        aberto={docAberto}
        onFechar={() => setDocAberto(false)}
        texto={docTexto || ""}
        onAprovar={() => { setDocAberto(false); enviarTexto("Aprovo o contrato. Pode me enviar a versão final por WhatsApp ou e-mail."); }}
      />
    </section>
  );
}
