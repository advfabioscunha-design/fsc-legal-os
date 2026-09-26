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

type Msg = { id?: number; autor: "CLIENTE" | "AGENTE" | "HUMANO"; conteudo: string; criado_em?: string };
type Solicitacao = { id: string; descricao: string; status: string; criado_em: string };
type Doc = { id: string; observacao: string | null; tipo: string; status: string; enviado_por?: string; criado_em: string };
type Caso = {
  id: string; estado: string; grupo: string | null;
  numero_processo?: string | null; movimentacoes?: any[];
  aguardando_cliente?: boolean; aguardando_desc?: string | null;
  mensagens?: Msg[]; solicitacoes?: Solicitacao[]; documentos?: Doc[];
};
type Cadastro = { id: string; nome: string; email: string; cpf_cnpj: string | null; whatsapp: string | null };
type Vista = "home" | "acompanhar" | "atendimento" | "contrato" | "cadastro";

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

  const [cadastro, setCadastro] = useState<Cadastro | null>(null);
  const [caso, setCaso] = useState<Caso | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [enviando, setEnviando] = useState(false);

  // anexos aguardando o botão ENVIAR
  const [anexos, setAnexos] = useState<File[]>([]);
  const [subindo, setSubindo] = useState(false);
  const [alvoSolicitacao, setAlvoSolicitacao] = useState<string | null>(null);
  const arquivoRef = useRef<HTMLInputElement | null>(null);
  const cameraRef = useRef<HTMLInputElement | null>(null);

  const fimRef = useRef<HTMLDivElement | null>(null);
  const primeiroNome = (nome || "").trim().split(" ")[0] || "tudo bem";

  const auth = (tk = token) => ({ Authorization: `Bearer ${tk}` });

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

  /* Carrega o caso completo: conversa, pendências e documentos.
     A conversa é sempre a MESMA thread — nada recomeça do zero. */
  async function carregarCaso(casoId: string, tk: string, nm: string) {
    try {
      const d = await fetch(`${API}/api/v1/cliente/caso/${casoId}`, { headers: auth(tk) });
      if (!d.ok) return;
      const det: Caso = await d.json();
      setCaso(det);
      const hist = (det.mensagens || []).filter((m) => m.conteudo?.trim());
      setMsgs(hist.length ? hist : [boasVindas(nm)]);
      const pendente = (det.solicitacoes || []).find((s) => s.status === "PENDENTE");
      setAlvoSolicitacao(pendente ? pendente.id : null);
    } catch { /* mantém o que já está na tela */ }
  }

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.push("/entrar"); return; }
      const tk = sess.session.access_token;
      const nm = sess.session.user.user_metadata?.nome || sess.session.user.email || "";
      setToken(tk); setNome(nm); setEmail(sess.session.user.email || "");
      try {
        const rc = await fetch(`${API}/api/v1/cliente/cadastro`, { headers: auth(tk) });
        if (rc.ok) setCadastro(await rc.json());
      } catch { /* segue sem cadastro carregado */ }
      try {
        const r = await fetch(`${API}/api/v1/cliente/meus-casos`, { headers: auth(tk) });
        const casos: Caso[] = r.ok ? await r.json() : [];
        if (casos.length > 0) await carregarCaso(casos[0].id, tk, nm);
        else setMsgs([boasVindas(nm)]);
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
          body: JSON.stringify({ nome, email, contato: email, relato: texto, canal: "PORTAL" }),
        });
        const data = r.ok ? await r.json() : null;
        if (data?.caso_id) {
          setCaso({ id: data.caso_id, estado: "QUALIFICACAO", grupo: data.grupo ?? null });
        }
        addAgente(data?.primeira_resposta);
      } else {
        const r = await fetch(`${API}/api/v1/cliente/caso/${caso.id}/mensagens`, {
          method: "POST", headers: { "Content-Type": "application/json", ...auth() },
          body: JSON.stringify({ conteudo: texto }),
        });
        const data = r.ok ? await r.json() : null;
        addAgente(data?.resposta);
      }
    } catch { addAgente(null); }
    finally { setEnviando(false); }
  }

  /* ── Anexos: escolher do aparelho ou fotografar na hora ── */
  function escolher(e: React.ChangeEvent<HTMLInputElement>) {
    const novos = Array.from(e.target.files || []);
    if (novos.length) setAnexos((a) => [...a, ...novos]);
    e.target.value = "";
  }
  function removerAnexo(i: number) { setAnexos((a) => a.filter((_, j) => j !== i)); }

  /* Envia os anexos. Se o caso da tela estiver desatualizado (o cadastro
     do cliente pode ter mais de um caso), busca o caso atual e reenvia
     uma vez antes de avisar o usuário. */
  async function postarDocumentos(casoId: string) {
    const fd = new FormData();
    anexos.forEach((f) => fd.append("arquivos", f));
    const qs = alvoSolicitacao ? `?solicitacao_id=${encodeURIComponent(alvoSolicitacao)}` : "";
    const r = await fetch(`${API}/api/v1/cliente/caso/${casoId}/documentos${qs}`, {
      method: "POST", headers: auth(), body: fd,
    });
    return { r, data: await r.json().catch(() => ({} as any)) };
  }

  async function enviarDocumentos() {
    if (!anexos.length || subindo) return;
    setSubindo(true);
    try {
      // sem atendimento aberto ainda? abre um agora para o documento ter destino
      let atual = caso;
      if (!atual) {
        try {
          const rl = await fetch(`${API}/api/v1/leads`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              nome, email, contato: email, canal: "PORTAL",
              relato: "Envio de documentos pela área do cliente.",
            }),
          });
          const dl = rl.ok ? await rl.json() : null;
          if (dl?.caso_id) {
            atual = { id: dl.caso_id, estado: "QUALIFICACAO", grupo: dl.grupo ?? null };
            setCaso(atual);
          }
        } catch { /* cai no aviso abaixo */ }
      }
      if (!atual) {
        alert("Não consegui abrir seu atendimento agora. Escreva uma mensagem no chat e tente de novo.");
        return;
      }

      let idUsado = atual.id;
      let { r, data } = await postarDocumentos(idUsado);

      if (r.status === 404 || r.status === 403) {
        // recarrega a lista de casos do cadastro e tenta de novo
        try {
          const lista = await fetch(`${API}/api/v1/cliente/meus-casos`, { headers: auth() });
          const casos: Caso[] = lista.ok ? await lista.json() : [];
          if (casos.length && casos[0].id !== idUsado) {
            idUsado = casos[0].id;
            setCaso((c) => (c ? { ...c, id: idUsado } : { ...casos[0] }));
            ({ r, data } = await postarDocumentos(idUsado));
          }
        } catch { /* mantém o erro original */ }
      }

      if (!r.ok) {
        alert(
          r.status === 404 || r.status === 403
            ? "Não consegui localizar o seu atendimento para anexar o documento. " +
              "Saia e entre de novo na plataforma, ou nos chame pelo WhatsApp que " +
              "recebemos o documento por lá e eu anexo no seu processo."
            : data.detail || "Não foi possível enviar os documentos."
        );
        return;
      }
      setAnexos([]);
      setMsgs((m) => [...m, {
        autor: "CLIENTE",
        conteudo: `📎 Enviei ${data.enviados.length} documento(s): ${data.enviados.join(", ")}`,
      }, {
        autor: "AGENTE",
        conteudo: data.retomou_producao
          ? "Recebi os documentos, muito obrigado! Já estão na sua pasta e o seu processo voltou para a produção. Qualquer outra coisa que eu precisar, aviso por aqui."
          : "Recebi os documentos, obrigado! Já estão na sua pasta. Ainda falta um item que pedimos — assim que enviar, o processo volta para a produção.",
      }]);
      await carregarCaso(idUsado, token, nome);
    } catch { alert("Falha de conexão ao enviar os documentos."); }
    finally { setSubindo(false); }
  }

  // índice atual na esteira
  const idxEsteira = (() => {
    if (!caso) return -1;
    if (PRE_CONTRATO.includes(caso.estado)) return -1;
    return ESTEIRA.findIndex((f) => f.estados.includes(caso.estado));
  })();
  const recebido = caso && ESTEIRA[ESTEIRA.length - 1].estados.includes(caso.estado);
  const pendentes = (caso?.solicitacoes || []).filter((s) => s.status === "PENDENTE");

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

        {/* CAIXA DE MENSAGENS — o que o escritório precisa de você */}
        {!carregando && pendentes.length > 0 && vista !== "atendimento" && (
          <div className="mb-6 rounded-2xl border border-gold/40 bg-gold/10 p-5">
            <p className="text-sm font-bold text-navy">
              ✉ Você tem {pendentes.length} {pendentes.length === 1 ? "pedido" : "pedidos"} do escritório
            </p>
            <ul className="mt-2 space-y-1 text-sm text-charcoal/75">
              {pendentes.map((s) => <li key={s.id}>• {s.descricao}</li>)}
            </ul>
            <button onClick={() => setVista("atendimento")}
              className="mt-3 rounded-xl bg-gold px-5 py-2 text-sm font-bold text-navy hover:bg-amber">
              Responder e enviar documentos →
            </button>
          </div>
        )}

        {carregando ? (
          <p className="text-charcoal/50">Carregando...</p>
        ) : vista === "home" ? (
          /* ── HOME ── */
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
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">Atendimento e envio de documentos</h2>
              <p className="mt-2 text-sm text-charcoal/60">Converse com o nosso atendimento, tire dúvidas e envie documentos por anexo ou foto, no próprio chat.</p>
              <span className="mt-4 text-sm font-semibold text-gold">Abrir →</span>
            </button>

            <button onClick={() => setVista("contrato")}
              className="group flex flex-col items-start rounded-2xl border border-black/5 bg-white p-7 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-forest text-2xl">📝</span>
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">Solicitar Elaboração de Contrato</h2>
              <p className="mt-2 text-sm text-charcoal/60">Um especialista elabora seu contrato com segurança jurídica — preço por complexidade e documento em revisão.</p>
              <span className="mt-4 text-sm font-semibold text-gold">Abrir →</span>
            </button>

            <button onClick={() => setVista("cadastro")}
              className="group flex flex-col items-start rounded-2xl border border-black/5 bg-white p-7 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-charcoal text-2xl">👤</span>
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">Meu cadastro e meus documentos</h2>
              <p className="mt-2 text-sm text-charcoal/60">Confira seus dados de contato e tudo o que você já nos enviou.</p>
              <span className="mt-4 text-sm font-semibold text-gold">Abrir →</span>
            </button>
          </div>
        ) : vista === "cadastro" ? (
          /* ── MEU CADASTRO ── */
          <MeuCadastro cadastro={cadastro} email={email} caso={caso} token={token}
            onVoltar={() => setVista("home")} onSalvo={(c) => setCadastro(c)} />
        ) : vista === "acompanhar" ? (
          /* ── ACOMPANHAR DEMANDA ── */
          <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
            <button onClick={() => setVista("home")} className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            <h2 className="font-serif text-xl font-bold text-navy">Andamento da sua causa</h2>
            {caso?.aguardando_cliente && (
              <div className="mt-3 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm text-charcoal/80">
                <b className="text-navy">Seu processo saiu temporariamente da produção</b> porque precisamos de um complemento: {caso.aguardando_desc}. Envie pelo <button onClick={() => setVista("atendimento")} className="font-semibold text-gold underline">atendimento</button> e ele volta na hora para a produção.
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
          /* ── ATENDIMENTO + ENVIO DE DOCUMENTOS ── */
          <section className="flex flex-col rounded-2xl border border-black/5 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-black/5 px-5 py-3">
              <div>
                <p className="text-sm font-semibold text-navy">Atendimento FC Advocacia</p>
                <p className="text-xs text-charcoal/50">Tire dúvidas e envie documentos — tudo por aqui.</p>
              </div>
              <button onClick={() => setVista("home")} className="text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            </div>

            {pendentes.length > 0 && (
              <div className="border-b border-gold/30 bg-gold/10 px-5 py-3">
                <p className="text-xs font-bold uppercase tracking-wide text-navy">Precisamos de você</p>
                <ul className="mt-1 space-y-0.5 text-sm text-charcoal/80">
                  {pendentes.map((s) => <li key={s.id}>• {s.descricao}</li>)}
                </ul>
                <p className="mt-1 text-[11px] text-charcoal/55">Anexe abaixo ou tire a foto do documento e toque em <b>Enviar documentos</b>.</p>
              </div>
            )}

            <div className="flex h-[52vh] flex-col gap-3 overflow-y-auto px-5 py-4">
              {msgs.map((m, i) => {
                const meu = m.autor === "CLIENTE";
                const texto = (m.conteudo || "").replace("[SOLICITAÇÃO AO CLIENTE] ", "");
                return (
                  <div key={m.id ?? i} className={`flex ${meu ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      meu ? "rounded-br-md bg-navy text-white" : "rounded-bl-md bg-ice text-charcoal"
                    }`}>{texto}</div>
                  </div>
                );
              })}
              {enviando && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md bg-ice px-4 py-2.5 text-sm text-charcoal/50">digitando…</div>
                </div>
              )}
              <div ref={fimRef} />
            </div>

            {/* Anexos escolhidos, aguardando o botão ENVIAR */}
            {anexos.length > 0 && (
              <div className="border-t border-black/5 bg-ice px-5 py-3">
                <p className="mb-2 text-xs font-semibold text-navy">
                  {anexos.length} {anexos.length === 1 ? "documento pronto" : "documentos prontos"} para envio
                </p>
                <ul className="space-y-1">
                  {anexos.map((f, i) => (
                    <li key={i} className="flex items-center justify-between gap-2 rounded-lg bg-white px-3 py-1.5 text-xs">
                      <span className="truncate text-charcoal/80">
                        {f.type.startsWith("image/") ? "🖼" : "📄"} {f.name}
                        <span className="ml-2 text-charcoal/40">{(f.size / 1024).toFixed(0)} KB</span>
                      </span>
                      <button onClick={() => removerAnexo(i)} className="shrink-0 text-charcoal/40 hover:text-[#C0392B]">remover</button>
                    </li>
                  ))}
                </ul>
                <button onClick={enviarDocumentos} disabled={subindo}
                  className="mt-3 w-full rounded-xl bg-forest px-5 py-2.5 text-sm font-bold text-white transition hover:opacity-90 disabled:opacity-50">
                  {subindo ? "Enviando…" : `Enviar documento${anexos.length > 1 ? "s" : ""}`}
                </button>
              </div>
            )}

            <form onSubmit={enviar} className="flex items-end gap-2 border-t border-black/5 p-4">
              <input ref={arquivoRef} type="file" multiple onChange={escolher} className="hidden"
                accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx" />
              <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={escolher} className="hidden" />
              <button type="button" onClick={() => arquivoRef.current?.click()} title="Anexar documento"
                className="rounded-xl border border-black/10 px-3 py-2.5 text-lg leading-none text-charcoal/70 hover:border-gold hover:text-navy">📎</button>
              <button type="button" onClick={() => cameraRef.current?.click()} title="Tirar foto do documento"
                className="rounded-xl border border-black/10 px-3 py-2.5 text-lg leading-none text-charcoal/70 hover:border-gold hover:text-navy">📷</button>
              <textarea value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(e as any); } }}
                rows={1} placeholder="Escreva sua mensagem…"
                className="max-h-32 flex-1 resize-none rounded-xl border border-black/10 px-4 py-2.5 text-sm outline-none focus:border-gold" />
              <button type="submit" disabled={enviando}
                className="rounded-xl bg-gold px-5 py-2.5 text-sm font-semibold text-navy transition hover:bg-amber disabled:opacity-50">Enviar</button>
            </form>
          </section>
        ) : (
          <ContratoChat nome={nome} email={email} onVoltar={() => setVista("home")} />
        )}
      </div>
    </main>
  );
}

/* ── Meu cadastro + documentos já enviados ─────────────────────── */
function MeuCadastro({ cadastro, email, caso, token, onVoltar, onSalvo }: {
  cadastro: Cadastro | null; email: string; caso: Caso | null; token: string;
  onVoltar: () => void; onSalvo: (c: Cadastro) => void;
}) {
  const [form, setForm] = useState({
    nome: cadastro?.nome || "", cpf_cnpj: cadastro?.cpf_cnpj || "", whatsapp: cadastro?.whatsapp || "",
  });
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState("");

  async function salvar() {
    setSalvando(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/cliente/cadastro`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { setAviso(d.detail || "Não foi possível salvar."); return; }
      setAviso("Cadastro atualizado.");
      if (cadastro) onSalvo({ ...cadastro, ...form });
    } catch { setAviso("Falha de conexão."); }
    finally { setSalvando(false); }
  }

  const docs = caso?.documentos || [];
  return (
    <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
      <button onClick={onVoltar} className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
      <h2 className="font-serif text-xl font-bold text-navy">Meu cadastro</h2>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="text-xs font-medium text-charcoal/60">Nome completo
          <input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">E-mail (seu acesso)
          <input disabled value={cadastro?.email || email}
            className="mt-1 w-full rounded-lg border border-black/10 bg-ice px-3 py-2 text-sm text-charcoal/60" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">CPF / CNPJ
          <input value={form.cpf_cnpj} onChange={(e) => setForm({ ...form, cpf_cnpj: e.target.value })} inputMode="numeric"
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">WhatsApp
          <input value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} inputMode="tel"
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button onClick={salvar} disabled={salvando}
          className="rounded-xl bg-gold px-5 py-2 text-sm font-bold text-navy hover:bg-amber disabled:opacity-50">
          {salvando ? "Salvando…" : "Salvar"}
        </button>
        {aviso && <span className="text-xs text-charcoal/60">{aviso}</span>}
      </div>

      <div className="mt-8 border-t border-black/5 pt-5">
        <h3 className="text-sm font-semibold text-navy">Documentos que você já enviou</h3>
        {docs.length === 0 ? (
          <p className="mt-2 text-sm text-charcoal/55">
            Nada enviado ainda. Quando precisarmos de algum documento, o pedido aparece aqui e no atendimento.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center justify-between gap-3 rounded-lg border border-black/5 bg-ice px-3 py-2 text-sm">
                <span className="truncate text-charcoal/80">📄 {d.observacao || d.tipo}</span>
                <span className="shrink-0 text-xs text-charcoal/45">
                  {d.enviado_por === "CLIENTE" ? "enviado por você" : "do escritório"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
