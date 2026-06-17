"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";
import ContratoChat from "../components/ContratoChat";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

// Esteira de trabalho visível ao cliente (mapeada para os estados do caso)
const ESTEIRA = [
  { id: "ASSINATURA", label: "Assinatura de documentos iniciais", estados: ["CONTRATO", "PAGAMENTO"] },
  { id: "COLETA", label: "Coleta de informações e provas", estados: ["COLETA_DOCS", "COLETA_PROVAS"] },
  { id: "CONFERENCIA", label: "Conferência de documentos", estados: ["ANALISE", "CONFERENCIA"] },
  { id: "PETICAO", label: "Elaboração da petição", estados: ["PETICAO"] },
  { id: "REVISAO", label: "Revisão", estados: ["REVISAO"] },
  { id: "PROTOCOLO", label: "Protocolo", estados: ["APROVADO", "PROTOCOLO_RPA", "PROTOCOLADO"] },
  { id: "RECEBIMENTO", label: "Recebimento da petição", estados: ["RECEBIDO", "DISTRIBUIDO"] },
];
const PRE_CONTRATO = ["LEAD", "QUALIFICACAO", "PROPOSTA"];

type Caso = {
  id: string; estado: string; grupo: string | null;
  numero_processo?: string | null; movimentacoes?: any[];
  aguardando_cliente?: boolean; aguardando_desc?: string | null;
};
type Msg = { autor: "CLIENTE" | "AGENTE"; conteudo: string };
type Vista = "home" | "acompanhar" | "atendimento" | "contrato";

const WHATS = "5569993225383";
const WHATS_LINK = `https://wa.me/${WHATS}?text=${encodeURIComponent(
  "Olá! Estou na minha área de cliente da FC Advocacia e gostaria de continuar meu atendimento."
)}`;

const FALLBACK =
  "Recebi sua mensagem e já estou cuidando do seu caso. Me dê só mais um detalhe " +
  "enquanto preparo o próximo passo. Se preferir, fale agora com nossa equipe pelo WhatsApp — " +
  "não vou te deixar sem resposta.";

export default function AreaCliente() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [vista, setVista] = useState<Vista>("home");

  const [caso, setCaso] = useState<Caso | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [enviando, setEnviando] = useState(false);

  const fimRef = useRef<HTMLDivElement | null>(null);
  const primeiroNome = (nome || "").trim().split(" ")[0] || "tudo bem";

  function boasVindas(nm: string): Msg {
    const pn = (nm || "").trim().split(" ")[0] || "";
    return {
      autor: "AGENTE",
      conteudo:
        `Olá${pn ? ", " + pn : ""}! Estou aqui para te ajudar. Pode me contar o que precisa ou ` +
        `tirar qualquer dúvida sobre o seu processo, um documento ou algo que não entendeu — ` +
        `explico tudo de forma simples e tranquila.`,
    };
  }

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.push("/entrar"); return; }
      const tk = sess.session.access_token;
      const nm = sess.session.user.user_metadata?.nome || sess.session.user.email || "";
      setToken(tk); setNome(nm); setEmail(sess.session.user.email || "");
      try {
        const r = await fetch(`${API}/api/v1/cliente/meus-casos`, { headers: { Authorization: `Bearer ${tk}` } });
        const casos: Caso[] = r.ok ? await r.json() : [];
        if (casos.length > 0) {
          const c = casos[0];
          try {
            const d = await fetch(`${API}/api/v1/casos/${c.id}`);
            if (d.ok) {
              const det = await d.json();
              setCaso({ ...c, estado: det.estado ?? c.estado, numero_processo: det.numero_processo ?? c.numero_processo, movimentacoes: det.movimentacoes || det.eventos || [], aguardando_cliente: det.aguardando_cliente, aguardando_desc: det.aguardando_desc });
              const hist: Msg[] = (det.mensagens || [])
                .filter((m: any) => m.autor === "CLIENTE" || m.autor === "AGENTE")
                .map((m: any) => ({ autor: m.autor, conteudo: m.conteudo }));
              setMsgs(hist.length ? hist : [boasVindas(nm)]);
            } else { setCaso(c); setMsgs([boasVindas(nm)]); }
          } catch { setCaso(c); setMsgs([boasVindas(nm)]); }
        } else { setMsgs([boasVindas(nm)]); }
      } catch { setMsgs([boasVindas(nm)]); }
      finally { setCarregando(false); }
    })();
  }, [router]);

  useEffect(() => { if (vista === "atendimento") fimRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, enviando, vista]);

  async function sair() { await supabase.auth.signOut(); router.push("/entrar"); }

  function addAgente(resposta?: string | null) {
    setMsgs((m) => [...m, { autor: "AGENTE", conteudo: (resposta || "").trim() || FALLBACK }]);
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const texto = input.trim();
    if (!texto || enviando) return;
    setMsgs((m) => [...m, { autor: "CLIENTE", conteudo: texto }]);
    setInput(""); setEnviando(true);
    try {
      if (!caso) {
        const r = await fetch(`${API}/api/v1/leads`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nome, contato: email, relato: texto, canal: "PORTAL" }),
        });
        const data = r.ok ? await r.json() : null;
        if (data?.caso_id) setCaso({ id: data.caso_id, estado: "QUALIFICACAO", grupo: data.grupo ?? null });
        addAgente(data?.primeira_resposta);
      } else {
        const r = await fetch(`${API}/api/v1/casos/${caso.id}/mensagens`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conteudo: texto, canal: "PORTAL" }),
        });
        const data = r.ok ? await r.json() : null;
        addAgente(data?.resposta);
      }
    } catch { addAgente(null); }
    finally { setEnviando(false); }
  }

  // índice atual na esteira
  const idxEsteira = (() => {
    if (!caso) return -1;
    if (PRE_CONTRATO.includes(caso.estado)) return -1;
    const i = ESTEIRA.findIndex((f) => f.estados.includes(caso.estado));
    return i;
  })();
  const recebido = caso && ESTEIRA[ESTEIRA.length - 1].estados.includes(caso.estado);

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
              className="rounded-full bg-[#25D366] px-4 py-1.5 text-xs font-semibold text-white">WhatsApp</a>
            <button onClick={sair} className="text-sm text-charcoal/50 hover:text-charcoal">Sair</button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-6">
        <h1 className="font-serif text-2xl font-bold text-navy">Olá, {primeiroNome}</h1>
        <p className="mb-6 text-sm text-charcoal/60">Bem-vindo(a) à sua área. Como podemos te ajudar hoje?</p>

        {carregando ? (
          <p className="text-charcoal/50">Carregando...</p>
        ) : vista === "home" ? (
          /* ── HOME: 2 botões ── */
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <button onClick={() => setVista("acompanhar")}
              className="group flex flex-col items-start rounded-2xl border border-black/5 bg-white p-7 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-navy text-2xl">📁</span>
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">Acompanhar Demanda</h2>
              <p className="mt-2 text-sm text-charcoal/60">Veja a esteira do seu caso, do início ao protocolo, e as movimentações do processo.</p>
              <span className="mt-4 text-sm font-semibold text-gold">Abrir →</span>
            </button>

            <button onClick={() => setVista("atendimento")}
              className="group flex flex-col items-start rounded-2xl border border-black/5 bg-white p-7 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gold text-2xl">💬</span>
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">Atendimento / Tirar Dúvidas</h2>
              <p className="mt-2 text-sm text-charcoal/60">Converse com o nosso atendimento e tire qualquer dúvida sobre o seu processo, em linguagem simples.</p>
              <span className="mt-4 text-sm font-semibold text-gold">Abrir →</span>
            </button>

            <button onClick={() => setVista("contrato")}
              className="group flex flex-col items-start rounded-2xl border border-black/5 bg-white p-7 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-forest text-2xl">📝</span>
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">Solicitar Elaboração de Contrato</h2>
              <p className="mt-2 text-sm text-charcoal/60">Um especialista elabora seu contrato com segurança jurídica — preço por complexidade e documento em revisão.</p>
              <span className="mt-4 text-sm font-semibold text-gold">Abrir →</span>
            </button>
          </div>
        ) : vista === "acompanhar" ? (
          /* ── ACOMPANHAR DEMANDA ── */
          <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
            <button onClick={() => setVista("home")} className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            <h2 className="font-serif text-xl font-bold text-navy">Andamento da sua causa</h2>
            {caso?.aguardando_cliente && (
              <div className="mt-3 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm text-charcoal/80">
                <b className="text-navy">Seu processo saiu temporariamente da produção</b> porque precisamos de um complemento: {caso.aguardando_desc}. Por favor, entre em contato ou responda nossa equipe o quanto antes para retornarmos seu caso à produção.
              </div>
            )}
            {!caso ? (
              <p className="mt-3 text-sm text-charcoal/60">
                Você ainda não tem um caso aberto. Use o <b>Atendimento</b> para iniciar — assim que contratar,
                a esteira aparece aqui para você acompanhar cada etapa.
              </p>
            ) : (
              <>
                {caso.numero_processo && <p className="mt-1 text-xs text-charcoal/50">Processo nº {caso.numero_processo}</p>}
                {idxEsteira < 0 && (
                  <p className="mt-3 rounded-lg bg-gold/10 px-4 py-3 text-sm text-charcoal/70">
                    Seu caso está em análise para contratação. A esteira começa após a assinatura dos documentos iniciais.
                  </p>
                )}
                <ol className="mt-5 space-y-3">
                  {ESTEIRA.map((f, i) => {
                    const feita = idxEsteira > i;
                    const atual = idxEsteira === i;
                    return (
                      <li key={f.id} className="flex items-center gap-3 text-sm">
                        <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] ${
                          feita ? "bg-navy text-white" : atual ? "bg-gold text-navy" : "bg-black/10 text-charcoal/40"
                        }`}>{feita ? "✓" : i + 1}</span>
                        <span className={atual ? "font-semibold text-navy" : feita ? "text-charcoal/70" : "text-charcoal/40"}>{f.label}</span>
                      </li>
                    );
                  })}
                </ol>

                {/* Acompanhamento processual */}
                <div className="mt-7 border-t border-black/5 pt-5">
                  <h3 className="text-sm font-semibold text-navy">Movimentações do processo</h3>
                  {recebido && caso.movimentacoes && caso.movimentacoes.length > 0 ? (
                    <ul className="mt-3 space-y-3">
                      {caso.movimentacoes.map((m: any, i: number) => (
                        <li key={i} className="rounded-lg border border-black/5 bg-ice p-3 text-sm">
                          <p className="text-xs text-charcoal/50">{m.data || m.criado_em || ""}</p>
                          <p className="text-charcoal/80">{m.descricao || m.titulo || m.texto || "Movimentação"}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-charcoal/55">
                      Após o protocolo, cada movimentação ou intimação do processo aparecerá aqui automaticamente —
                      e o status acima é atualizado a cada novo passo. Você não precisa fazer nada: nós te avisamos.
                    </p>
                  )}
                </div>
              </>
            )}
          </section>
        ) : vista === "atendimento" ? (
          /* ── ATENDIMENTO / DÚVIDAS ── */
          <section className="flex flex-col rounded-2xl border border-black/5 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-black/5 px-5 py-3">
              <div>
                <p className="text-sm font-semibold text-navy">Atendimento FC Advocacia</p>
                <p className="text-xs text-charcoal/50">Tire suas dúvidas — explicamos de forma simples.</p>
              </div>
              <button onClick={() => setVista("home")} className="text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            </div>

            <div className="flex h-[55vh] flex-col gap-3 overflow-y-auto px-5 py-4">
              {msgs.map((m, i) => (
                <div key={i} className={`flex ${m.autor === "CLIENTE" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.autor === "CLIENTE" ? "rounded-br-md bg-navy text-white" : "rounded-bl-md bg-ice text-charcoal"
                  }`}>{m.conteudo}</div>
                </div>
              ))}
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
              <button type="submit" disabled={enviando}
                className="rounded-xl bg-gold px-5 py-2.5 text-sm font-semibold text-navy transition hover:bg-amber disabled:opacity-50">Enviar</button>
            </form>
          </section>
        ) : (
          /* ── ELABORAÇÃO DE CONTRATO ── */
          <ContratoChat nome={nome} email={email} onVoltar={() => setVista("home")} />
        )}
      </div>
    </main>
  );
}
