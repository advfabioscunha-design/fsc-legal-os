"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";
const OCULTAR_FLOATING = ["/entrar", "/cliente", "/crm", "/equipe", "/portal", "/processos", "/admin", "/agenda", "/assistente"];

type Msg = { autor: "CLIENTE" | "AGENTE"; conteudo: string };

const SAUDACAO: Msg = {
  autor: "AGENTE",
  conteudo:
    "Olá! Seja muito bem-vindo(a) à FC Advocacia. Muito obrigado pela sua preferência! " +
    "Estou aqui para te ajudar a resolver o seu problema com toda atenção e cuidado. " +
    "Me conte, com suas palavras, o que está acontecendo — vou te orientar agora mesmo.",
};

const FALLBACK =
  "Recebi sua mensagem e já estou cuidando do seu caso. Me dê só mais um detalhe enquanto " +
  "preparo o próximo passo. Não vou te deixar sem resposta — se preferir, também posso te " +
  "encaminhar para o nosso WhatsApp.";

type Variant = "inline" | "floating";

export default function AtendimentoChat({
  label = "Tire suas dúvidas agora",
  className = "",
  variant = "inline",
}: { label?: string; className?: string; variant?: Variant }) {
  const pathname = usePathname();
  const [aberto, setAberto] = useState(false);
  const [iniciado, setIniciado] = useState(false);
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [casoId, setCasoId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([SAUDACAO]);
  const [input, setInput] = useState("");
  const [enviando, setEnviando] = useState(false);
  const fimRef = useRef<HTMLDivElement | null>(null);

  function iniciarConversa(e: React.FormEvent) {
    e.preventDefault();
    if (!nome.trim() || telefone.replace(/\D/g, "").length < 10) return;
    const pn = nome.trim().split(" ")[0];
    setMsgs([{
      autor: "AGENTE",
      conteudo:
        `Olá, ${pn}! Seja muito bem-vindo(a) à FC Advocacia. Muito obrigado pela sua preferência! ` +
        `Estou aqui para te ajudar a resolver o seu problema com toda atenção. ` +
        `Me conte, com suas palavras, o que está acontecendo.`,
    }]);
    setIniciado(true);
  }

  useEffect(() => {
    if (aberto) fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, enviando, aberto]);

  function addAgente(resposta?: string | null) {
    setMsgs((m) => [...m, { autor: "AGENTE", conteudo: (resposta || "").trim() || FALLBACK }]);
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const texto = input.trim();
    if (!texto || enviando) return;
    setMsgs((m) => [...m, { autor: "CLIENTE", conteudo: texto }]);
    setInput("");
    setEnviando(true);
    try {
      if (!casoId) {
        const r = await fetch(`${API}/api/v1/leads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nome: nome.trim() || "Visitante do site", contato: telefone.trim() || "site", relato: texto, canal: "SITE" }),
        });
        const data = r.ok ? await r.json() : null;
        if (data?.caso_id) setCasoId(data.caso_id);
        addAgente(data?.primeira_resposta);
      } else {
        const r = await fetch(`${API}/api/v1/casos/${casoId}/mensagens`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conteudo: texto, canal: "SITE" }),
        });
        const data = r.ok ? await r.json() : null;
        addAgente(data?.resposta);
      }
    } catch {
      addAgente(null);
    } finally {
      setEnviando(false);
    }
  }

  if (variant === "floating" && OCULTAR_FLOATING.some((p) => pathname?.startsWith(p))) return null;

  const botao =
    variant === "floating" ? (
      <button
        onClick={() => setAberto(true)}
        aria-label="Atendimento"
        className="fixed bottom-24 right-5 z-40 flex items-center gap-2 rounded-full bg-gold px-5 py-3 text-sm font-bold text-navy shadow-xl transition hover:bg-amber"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.8 9.8 0 01-4-.8L3 20l.8-4A8 8 0 013 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        Tire suas dúvidas
      </button>
    ) : (
      <button onClick={() => setAberto(true)} className={className || "rounded-full bg-gold px-8 py-4 text-sm font-bold text-navy transition hover:bg-amber"}>
        {label}
      </button>
    );

  return (
    <>
      {botao}

      {aberto && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
          onClick={() => setAberto(false)}>
          <div onClick={(e) => e.stopPropagation()}
            className="flex h-[90vh] w-full max-w-md flex-col overflow-hidden rounded-t-2xl bg-white shadow-2xl sm:h-[600px] sm:rounded-2xl">
            {/* Cabeçalho */}
            <div className="flex items-center justify-between bg-navy px-4 py-3 text-white">
              <div>
                <p className="text-sm font-bold">Atendimento FC Advocacia</p>
                <p className="text-[11px] text-white/60">Estamos aqui para resolver o seu caso</p>
              </div>
              <button onClick={() => setAberto(false)} aria-label="Fechar" className="text-white/70 hover:text-white">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {!iniciado ? (
              /* Pré-atendimento: nome + telefone */
              <form onSubmit={iniciarConversa} className="flex flex-1 flex-col justify-center gap-4 bg-ice px-6 py-8">
                <div className="text-center">
                  <p className="font-serif text-lg font-bold text-navy">Antes de começarmos</p>
                  <p className="mt-1 text-sm text-charcoal/60">Como podemos te chamar e em qual número falar com você?</p>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-charcoal/60">Seu nome</label>
                  <input value={nome} onChange={(e) => setNome(e.target.value)} required placeholder="Nome completo"
                    className="w-full rounded-lg border border-black/10 bg-white px-3 py-2.5 text-sm text-charcoal outline-none focus:border-gold" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-charcoal/60">Seu telefone / WhatsApp</label>
                  <input value={telefone} onChange={(e) => setTelefone(e.target.value)} required inputMode="tel" placeholder="(00) 00000-0000"
                    className="w-full rounded-lg border border-black/10 bg-white px-3 py-2.5 text-sm text-charcoal outline-none focus:border-gold" />
                </div>
                <button type="submit"
                  className="mt-2 w-full rounded-xl bg-gold px-5 py-3 text-sm font-bold text-navy transition hover:bg-amber">
                  Iniciar atendimento
                </button>
                <p className="text-center text-[11px] text-charcoal/45">Seus dados estão protegidos e usados apenas para o seu atendimento.</p>
              </form>
            ) : (
              <>
                {/* Mensagens */}
                <div className="flex flex-1 flex-col gap-3 overflow-y-auto bg-ice px-4 py-4">
                  {msgs.map((m, i) => (
                    <div key={i} className={`flex ${m.autor === "CLIENTE" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[82%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                        m.autor === "CLIENTE" ? "rounded-br-md bg-navy text-white" : "rounded-bl-md bg-white text-charcoal shadow-sm"
                      }`}>
                        {m.conteudo}
                      </div>
                    </div>
                  ))}
                  {enviando && (
                    <div className="flex justify-start">
                      <div className="rounded-2xl rounded-bl-md bg-white px-4 py-2.5 text-sm text-charcoal/50 shadow-sm">digitando…</div>
                    </div>
                  )}
                  <div ref={fimRef} />
                </div>

                {/* Oferta de cadastro */}
                <div className="border-t border-black/5 bg-white px-4 py-2 text-center">
                  <Link href="/entrar?next=/cliente" className="text-xs font-medium text-gold hover:underline">
                    Quer acompanhar seu caso pela plataforma? Crie seu acesso →
                  </Link>
                </div>

                {/* Composer */}
                <form onSubmit={enviar} className="flex items-end gap-2 border-t border-black/5 bg-white p-3">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(e as any); } }}
                    rows={1}
                    placeholder="Escreva sua mensagem…"
                    className="max-h-28 flex-1 resize-none rounded-xl border border-black/10 px-4 py-2.5 text-sm text-charcoal outline-none focus:border-gold"
                  />
                  <button type="submit" disabled={enviando}
                    className="rounded-xl bg-gold px-5 py-2.5 text-sm font-bold text-navy transition hover:bg-amber disabled:opacity-50">
                    Enviar
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
