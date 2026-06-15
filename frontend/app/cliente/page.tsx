"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

// Fases visíveis ao cliente (do contato inicial ao protocolo)
const FASES = [
  { id: "LEAD", label: "Contato inicial" },
  { id: "QUALIFICACAO", label: "Análise de viabilidade" },
  { id: "PROPOSTA", label: "Proposta" },
  { id: "CONTRATO", label: "Contrato" },
  { id: "PAGAMENTO", label: "Pagamento" },
  { id: "COLETA_DOCS", label: "Coleta de documentos" },
  { id: "COLETA_PROVAS", label: "Coleta de provas" },
  { id: "ANALISE", label: "Análise técnica" },
  { id: "PETICAO", label: "Elaboração da petição" },
  { id: "REVISAO", label: "Revisão do advogado" },
  { id: "PROTOCOLADO", label: "Protocolado" },
];

type Caso = { id: string; estado: string; grupo: string | null; numero_processo?: string | null };
type Msg = { autor: "CLIENTE" | "AGENTE"; conteudo: string };

// WhatsApp de apoio (fallback humano)
const WHATS = "5569993225383";
const WHATS_LINK = `https://wa.me/${WHATS}?text=${encodeURIComponent(
  "Olá! Estou na minha área de cliente da FC Advocacia e gostaria de continuar meu atendimento."
)}`;

// Validação de CPF (dígitos verificadores) — gratuita, no próprio navegador
function cpfValido(valor: string): boolean {
  const c = (valor || "").replace(/\D/g, "");
  if (c.length !== 11 || /^(\d)\1{10}$/.test(c)) return false;
  for (const i of [9, 10]) {
    let soma = 0;
    for (let n = 0; n < i; n++) soma += parseInt(c[n]) * (i + 1 - n);
    let dig = (soma * 10) % 11;
    if (dig === 10) dig = 0;
    if (dig !== parseInt(c[i])) return false;
  }
  return true;
}

const FALLBACK =
  "Recebi sua mensagem e já estou cuidando do seu caso. Me dê só mais um detalhe " +
  "enquanto preparo o próximo passo — e, se preferir falar agora com nossa equipe, " +
  "é só tocar em \"Falar no WhatsApp\" aqui ao lado. Não vou te deixar sem resposta.";

export default function AreaCliente() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [carregando, setCarregando] = useState(true);

  const [caso, setCaso] = useState<Caso | null>(null);
  const [mensagens, setMensagens] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [cpf, setCpf] = useState("");
  const [erroCpf, setErroCpf] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const fimRef = useRef<HTMLDivElement | null>(null);
  const primeiroNome = (nome || "").trim().split(" ")[0] || "tudo bem";

  // ── Carrega sessão + caso ativo + histórico ──
  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.push("/entrar"); return; }
      const tk = sess.session.access_token;
      const nm = sess.session.user.user_metadata?.nome || sess.session.user.email || "";
      setToken(tk);
      setNome(nm);
      setEmail(sess.session.user.email || "");
      try {
        const r = await fetch(`${API}/api/v1/cliente/meus-casos`, {
          headers: { Authorization: `Bearer ${tk}` },
        });
        const casos: Caso[] = r.ok ? await r.json() : [];
        if (casos.length > 0) {
          const c = casos[0];
          setCaso(c);
          // carrega histórico de mensagens do caso
          try {
            const d = await fetch(`${API}/api/v1/casos/${c.id}`);
            if (d.ok) {
              const det = await d.json();
              const hist: Msg[] = (det.mensagens || [])
                .filter((m: any) => m.autor === "CLIENTE" || m.autor === "AGENTE")
                .map((m: any) => ({ autor: m.autor, conteudo: m.conteudo }));
              setMensagens(hist.length ? hist : [boasVindas(nm)]);
            } else {
              setMensagens([boasVindas(nm)]);
            }
          } catch { setMensagens([boasVindas(nm)]); }
        } else {
          setMensagens([boasVindas(nm)]);
        }
      } catch {
        setMensagens([boasVindas(nm)]);
      } finally {
        setCarregando(false);
      }
    })();
  }, [router]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, enviando]);

  function boasVindas(nm: string): Msg {
    const pn = (nm || "").trim().split(" ")[0] || "";
    return {
      autor: "AGENTE",
      conteudo:
        `Olá${pn ? ", " + pn : ""}! Seja muito bem-vindo(a). Sinto muito que você esteja ` +
        `passando por isso, mas fique tranquilo(a): você está no lugar certo. ` +
        `Me conte com detalhes o que aconteceu — estou aqui para te ajudar a resolver.`,
    };
  }

  async function sair() {
    await supabase.auth.signOut();
    router.push("/entrar");
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const texto = input.trim();
    if (!texto || enviando) return;

    // Primeira mensagem cria o caso e exige CPF
    if (!caso) {
      if (!cpfValido(cpf)) {
        setErroCpf("CPF inválido — confira os números.");
        return;
      }
      setErroCpf(null);
    }

    setMensagens((m) => [...m, { autor: "CLIENTE", conteudo: texto }]);
    setInput("");
    setEnviando(true);

    try {
      if (!caso) {
        const r = await fetch(`${API}/api/v1/leads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nome, contato: email, relato: texto, cpf, canal: "PORTAL" }),
        });
        const data = r.ok ? await r.json() : null;
        if (data?.caso_id) {
          setCaso({ id: data.caso_id, estado: "QUALIFICACAO", grupo: data.grupo ?? null });
        }
        adicionarAgente(data?.primeira_resposta);
      } else {
        const r = await fetch(`${API}/api/v1/casos/${caso.id}/mensagens`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conteudo: texto, canal: "PORTAL" }),
        });
        const data = r.ok ? await r.json() : null;
        adicionarAgente(data?.resposta);
      }
    } catch {
      adicionarAgente(null); // nunca deixa o cliente sem resposta
    } finally {
      setEnviando(false);
    }
  }

  function adicionarAgente(resposta?: string | null) {
    const texto = (resposta || "").trim() || FALLBACK;
    setMensagens((m) => [...m, { autor: "AGENTE", conteudo: texto }]);
  }

  const idxFase = caso ? Math.max(0, FASES.findIndex((f) => f.id === caso.estado)) : 0;

  return (
    <main className="min-h-screen bg-ice text-charcoal">
      {/* Barra superior */}
      <header className="sticky top-0 z-30 border-b border-black/5 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="font-serif text-xl font-bold text-navy">FC</span>
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Advocacia</span>
          </Link>
          <div className="flex items-center gap-4">
            <a href={WHATS_LINK} target="_blank" rel="noreferrer"
              className="rounded-full bg-[#25D366] px-4 py-1.5 text-xs font-semibold text-white">
              Falar no WhatsApp
            </a>
            <button onClick={sair} className="text-sm text-charcoal/50 hover:text-charcoal">Sair</button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-6">
        <h1 className="font-serif text-2xl font-bold text-navy">Olá, {primeiroNome}</h1>
        <p className="mb-5 text-sm text-charcoal/60">
          Converse com o nosso atendimento e acompanhe aqui cada fase da sua causa.
        </p>

        {carregando ? (
          <p className="text-charcoal/50">Carregando seu atendimento...</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* ── CHAT ── */}
            <section className="flex flex-col rounded-2xl border border-black/5 bg-white shadow-sm lg:col-span-2">
              <div className="border-b border-black/5 px-5 py-3">
                <p className="text-sm font-semibold text-navy">Atendimento FC Advocacia</p>
                <p className="text-xs text-charcoal/50">Estamos ao seu lado até a solução do seu caso.</p>
              </div>

              <div className="flex h-[55vh] flex-col gap-3 overflow-y-auto px-5 py-4">
                {mensagens.map((m, i) => (
                  <div key={i}
                    className={`flex ${m.autor === "CLIENTE" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      m.autor === "CLIENTE"
                        ? "rounded-br-md bg-navy text-white"
                        : "rounded-bl-md bg-ice text-charcoal"
                    }`}>
                      {m.conteudo}
                    </div>
                  </div>
                ))}
                {enviando && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl rounded-bl-md bg-ice px-4 py-2.5 text-sm text-charcoal/50">
                      digitando…
                    </div>
                  </div>
                )}
                <div ref={fimRef} />
              </div>

              {/* Composer */}
              <form onSubmit={enviar} className="border-t border-black/5 p-4">
                {!caso && (
                  <div className="mb-3">
                    <label className="mb-1 block text-xs font-medium text-charcoal/60">
                      Para iniciar seu atendimento, confirme seu CPF
                    </label>
                    <input
                      value={cpf}
                      onChange={(e) => setCpf(e.target.value)}
                      inputMode="numeric"
                      placeholder="000.000.000-00"
                      className="w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold"
                    />
                    {erroCpf && <p className="mt-1 text-xs text-red-600">{erroCpf}</p>}
                  </div>
                )}
                <div className="flex items-end gap-2">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(e as any); }
                    }}
                    rows={1}
                    placeholder="Escreva sua mensagem…"
                    className="max-h-32 flex-1 resize-none rounded-xl border border-black/10 px-4 py-2.5 text-sm outline-none focus:border-gold"
                  />
                  <button type="submit" disabled={enviando}
                    className="rounded-xl bg-gold px-5 py-2.5 text-sm font-semibold text-navy transition hover:bg-[#b89971] disabled:opacity-50">
                    Enviar
                  </button>
                </div>
              </form>
            </section>

            {/* ── ANDAMENTO ── */}
            <aside className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold text-navy">Andamento da sua causa</p>
              {caso ? (
                <>
                  {caso.numero_processo && (
                    <p className="mt-1 text-xs text-charcoal/50">Processo {caso.numero_processo}</p>
                  )}
                  <ol className="mt-4 space-y-2.5">
                    {FASES.map((f, i) => {
                      const feita = i < idxFase;
                      const atual = i === idxFase;
                      return (
                        <li key={f.id} className="flex items-center gap-3 text-sm">
                          <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] ${
                            feita ? "bg-navy text-white" : atual ? "bg-gold text-navy" : "bg-black/10 text-charcoal/40"
                          }`}>
                            {feita ? "✓" : i + 1}
                          </span>
                          <span className={atual ? "font-semibold text-navy" : feita ? "text-charcoal/70" : "text-charcoal/40"}>
                            {f.label}
                          </span>
                        </li>
                      );
                    })}
                  </ol>
                </>
              ) : (
                <p className="mt-3 text-sm text-charcoal/55">
                  Assim que você nos contar seu caso aqui no chat, abriremos seu atendimento e as
                  fases aparecerão neste painel para você acompanhar tudo de perto.
                </p>
              )}
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
