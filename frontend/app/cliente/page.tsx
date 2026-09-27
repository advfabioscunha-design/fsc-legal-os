"use client";
import { useCallback, useEffect, useRef, useState } from "react";
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
type Aviso = {
  id: string; tipo: string; titulo: string; mensagem: string;
  criado_em: string; ciencia_em: string | null; ciencia_canal?: string | null;
};
type Caso = {
  id: string; estado: string; grupo: string | null;
  titulo?: string | null; numero_atendimento?: string | null;
  numero_processo?: string | null; movimentacoes?: any[];
  aguardando_cliente?: boolean; aguardando_desc?: string | null;
  avisos_sem_ciencia?: number; documentos_pendentes?: number;
  criado_em?: string;
  mensagens?: Msg[]; solicitacoes?: Solicitacao[]; documentos?: Doc[]; avisos?: Aviso[];
  assinaturas?: Assinatura[];
};
type Assinatura = {
  id: string; tipo: string; titulo: string; status: string;
  link_assinatura: string | null; enviado_em: string | null; assinado_em: string | null;
};
type Cadastro = {
  id: string; nome: string; email: string; cpf_cnpj: string | null; whatsapp: string | null;
  nacionalidade?: string | null; estado_civil?: string | null; profissao?: string | null;
  rg?: string | null; endereco_rua?: string | null; endereco_numero?: string | null;
  endereco_complemento?: string | null; endereco_bairro?: string | null;
  endereco_cidade?: string | null; endereco_uf?: string | null; endereco_cep?: string | null;
};
type Vista = "home" | "casos" | "acompanhar" | "atendimento" | "contrato" | "cadastro";

const WHATS_RO = "5569993225383";
const WHATS_SC = "5548988357992";
const FALLBACK =
  "Recebi sua mensagem e já estou cuidando do seu caso. Me dê só mais um detalhe " +
  "enquanto preparo o próximo passo. Se preferir, fale agora com nossa equipe pelo WhatsApp — " +
  "não vou te deixar sem resposta.";

const dataHora = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "";

export default function AreaCliente() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [vista, setVista] = useState<Vista>("home");

  const [cadastro, setCadastro] = useState<Cadastro | null>(null);
  const [casos, setCasos] = useState<Caso[]>([]);
  const [caso, setCaso] = useState<Caso | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [dandoCiencia, setDandoCiencia] = useState<string | null>(null);

  const [anexos, setAnexos] = useState<File[]>([]);
  const [subindo, setSubindo] = useState(false);
  const [alvoSolicitacao, setAlvoSolicitacao] = useState<string | null>(null);
  const arquivoRef = useRef<HTMLInputElement | null>(null);
  const cameraRef = useRef<HTMLInputElement | null>(null);

  const fimRef = useRef<HTMLDivElement | null>(null);
  const primeiroNome = (nome || "").trim().split(" ")[0] || "tudo bem";
  const whatsEscritorio = (cadastro?.whatsapp || "").replace(/\D/g, "").replace(/^55/, "").startsWith("69") ? WHATS_RO : WHATS_SC;
  const whatsLink = `https://wa.me/${whatsEscritorio}?text=${encodeURIComponent(
    "Olá! Estou na minha área de cliente da FC Advocacia e gostaria de continuar meu atendimento."
  )}`;

  const auth = useCallback((tk = token) => ({ Authorization: `Bearer ${tk}` }), [token]);

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

  const carregarCaso = useCallback(async (casoId: string, tk: string, nm: string) => {
    try {
      const d = await fetch(`${API}/api/v1/cliente/caso/${casoId}`, { headers: { Authorization: `Bearer ${tk}` } });
      if (!d.ok) return;
      const det: Caso = await d.json();
      setCaso(det);
      const hist = (det.mensagens || []).filter((m) => m.conteudo?.trim());
      setMsgs(hist.length ? hist : [boasVindas(nm)]);
      const pendente = (det.solicitacoes || []).find((s) => s.status === "PENDENTE");
      setAlvoSolicitacao(pendente ? pendente.id : null);
    } catch { /* mantém o que já está na tela */ }
  }, []);

  const carregarCasos = useCallback(async (tk: string) => {
    try {
      const r = await fetch(`${API}/api/v1/cliente/meus-casos`, { headers: { Authorization: `Bearer ${tk}` } });
      const lista: Caso[] = r.ok ? await r.json() : [];
      setCasos(lista);
      return lista;
    } catch { return []; }
  }, []);

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.push("/entrar"); return; }
      const tk = sess.session.access_token;
      const nm = sess.session.user.user_metadata?.nome || sess.session.user.email || "";
      setToken(tk); setNome(nm); setEmail(sess.session.user.email || "");
      try {
        const rc = await fetch(`${API}/api/v1/cliente/cadastro`, { headers: { Authorization: `Bearer ${tk}` } });
        if (rc.ok) setCadastro(await rc.json());
      } catch { /* segue */ }
      const lista = await carregarCasos(tk);
      // abre direto o caso indicado no link do aviso (?caso=...)
      const alvo = new URLSearchParams(window.location.search).get("caso");
      const escolhido = lista.find((c) => c.id === alvo) || lista[0];
      if (escolhido) {
        await carregarCaso(escolhido.id, tk, nm);
        if (alvo) setVista("acompanhar");
      } else {
        setMsgs([boasVindas(nm)]);
      }
      setCarregando(false);
    })();
  }, [router, carregarCasos, carregarCaso]);

  useEffect(() => { if (vista === "atendimento") fimRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, enviando, vista]);

  async function sair() { await supabase.auth.signOut(); router.push("/entrar"); }

  function addAgente(resposta?: string | null) {
    setMsgs((m) => [...m, { autor: "AGENTE", conteudo: (resposta || "").trim() || FALLBACK }]);
  }

  async function abrirCaso(c: Caso, destino: Vista = "acompanhar") {
    setCaso(c);
    await carregarCaso(c.id, token, nome);
    setVista(destino);
  }

  async function darCiencia(avisoId: string) {
    setDandoCiencia(avisoId);
    try {
      const r = await fetch(`${API}/api/v1/cliente/avisos/${avisoId}/ciencia`, {
        method: "POST", headers: auth(),
      });
      if (!r.ok) { alert("Não foi possível registrar a ciência. Tente novamente."); return; }
      if (caso) await carregarCaso(caso.id, token, nome);
      await carregarCasos(token);
    } catch { alert("Falha de conexão ao registrar a ciência."); }
    finally { setDandoCiencia(null); }
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
          await carregarCasos(token);
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
          if (dl?.caso_id) { atual = { id: dl.caso_id, estado: "QUALIFICACAO", grupo: dl.grupo ?? null }; setCaso(atual); }
        } catch { /* cai no aviso abaixo */ }
      }
      if (!atual) {
        alert("Não consegui abrir seu atendimento agora. Escreva uma mensagem no chat e tente de novo.");
        return;
      }

      let idUsado = atual.id;
      let { r, data } = await postarDocumentos(idUsado);

      if (r.status === 404 || r.status === 403) {
        const lista = await carregarCasos(token);
        if (lista.length && lista[0].id !== idUsado) {
          idUsado = lista[0].id;
          setCaso((c) => (c ? { ...c, id: idUsado } : { ...lista[0] }));
          ({ r, data } = await postarDocumentos(idUsado));
        }
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
      await carregarCasos(token);
    } catch { alert("Falha de conexão ao enviar os documentos."); }
    finally { setSubindo(false); }
  }

  const idxEsteira = (() => {
    if (!caso) return -1;
    if (PRE_CONTRATO.includes(caso.estado)) return -1;
    return ESTEIRA.findIndex((f) => f.estados.includes(caso.estado));
  })();
  const recebido = caso && ESTEIRA[ESTEIRA.length - 1].estados.includes(caso.estado);
  const pendentes = (caso?.solicitacoes || []).filter((s) => s.status === "PENDENTE");
  const avisosSemCiencia = (caso?.avisos || []).filter((a) => !a.ciencia_em);
  const totalPendencias = casos.reduce((n, c) => n + (c.avisos_sem_ciencia || 0), 0);
  const nomeCaso = (c: Caso) => c.titulo || "Atendimento jurídico";

  return (
    <main className="min-h-screen bg-ice text-charcoal">
      <header className="sticky top-0 z-30 border-b border-black/5 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="font-serif text-xl font-bold text-navy">FC</span>
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Advocacia</span>
          </Link>
          <div className="flex items-center gap-4">
            <a href={whatsLink} target="_blank" rel="noreferrer"
              className="rounded-full bg-[#25D366] px-4 py-1.5 text-xs font-semibold text-white">WhatsApp</a>
            <button onClick={sair} className="text-sm text-charcoal/50 hover:text-charcoal">Sair</button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-6">
        <h1 className="font-serif text-2xl font-bold text-navy">Olá, {primeiroNome}</h1>
        <p className="mb-6 text-sm text-charcoal/60">
          {casos.length > 1
            ? `Você tem ${casos.length} atendimentos conosco. Cada um tem o seu próprio número — é por ele que identificamos o seu caso.`
            : "Bem-vindo(a) à sua área. Como podemos te ajudar hoje?"}
        </p>

        {/* Documentos aguardando a sua assinatura */}
        {!carregando && (caso?.assinaturas || []).some((a) => a.status === "ENVIADO") && (
          <div className="mb-6 rounded-2xl border border-forest/40 bg-forest/10 p-5">
            <p className="text-sm font-bold text-navy">✍ Documento aguardando a sua assinatura</p>
            <ul className="mt-3 space-y-2">
              {(caso!.assinaturas || []).filter((a) => a.status === "ENVIADO").map((a) => (
                <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white px-4 py-3">
                  <span className="min-w-0">
                    <span className="block font-semibold text-navy">{a.titulo}</span>
                    <span className="block text-xs text-charcoal/50">Enviado em {dataHora(a.enviado_em)}</span>
                  </span>
                  {a.link_assinatura && (
                    <a href={a.link_assinatura} target="_blank" rel="noreferrer"
                      className="shrink-0 rounded-xl bg-forest px-5 py-2 text-sm font-bold text-white hover:opacity-90">
                      Assinar agora →
                    </a>
                  )}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[11px] text-charcoal/55">
              A assinatura é digital e vale juridicamente. Abra o link, confira o documento e assine na própria tela.
            </p>
          </div>
        )}

        {/* Avisos sem ciência — o que o escritório precisa que você veja */}
        {!carregando && avisosSemCiencia.length > 0 && vista !== "acompanhar" && (
          <div className="mb-6 rounded-2xl border border-gold/40 bg-gold/10 p-5">
            <p className="text-sm font-bold text-navy">
              ✉ {avisosSemCiencia.length === 1 ? "Há um aviso novo sobre o seu caso" : `Há ${avisosSemCiencia.length} avisos novos sobre o seu caso`}
            </p>
            <button onClick={() => setVista("acompanhar")}
              className="mt-3 rounded-xl bg-gold px-5 py-2 text-sm font-bold text-navy hover:bg-amber">
              Ver e confirmar recebimento →
            </button>
          </div>
        )}

        {carregando ? (
          <p className="text-charcoal/50">Carregando...</p>
        ) : vista === "home" ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <button onClick={() => setVista(casos.length > 1 ? "casos" : "acompanhar")}
              className="group relative flex flex-col items-start rounded-2xl border border-black/5 bg-white p-7 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-navy text-2xl">📁</span>
              {totalPendencias > 0 && (
                <span className="absolute right-5 top-5 rounded-full bg-gold px-2 py-0.5 text-[11px] font-bold text-navy">{totalPendencias}</span>
              )}
              <h2 className="mt-4 font-serif text-xl font-bold text-navy">
                {casos.length > 1 ? "Meus atendimentos" : "Acompanhar Demanda"}
              </h2>
              <p className="mt-2 text-sm text-charcoal/60">
                {casos.length > 1
                  ? `Escolha qual dos seus ${casos.length} atendimentos deseja acompanhar.`
                  : "Veja a esteira do seu caso, do início ao protocolo, e as movimentações do processo."}
              </p>
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
        ) : vista === "casos" ? (
          /* ── LISTA DE ATENDIMENTOS ── */
          <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
            <button onClick={() => setVista("home")} className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            <h2 className="font-serif text-xl font-bold text-navy">Meus atendimentos</h2>
            <p className="mt-1 text-sm text-charcoal/60">
              Cada caso tem um número próprio. Use esse número sempre que falar conosco — assim
              sabemos na hora de qual processo você está tratando.
            </p>
            <ul className="mt-5 space-y-3">
              {casos.map((c) => {
                const pend = (c.avisos_sem_ciencia || 0) + (c.documentos_pendentes || 0);
                return (
                  <li key={c.id}>
                    <button onClick={() => abrirCaso(c)}
                      className="flex w-full items-center justify-between gap-4 rounded-xl border border-black/5 bg-ice px-4 py-4 text-left transition hover:border-gold hover:bg-white">
                      <span className="min-w-0">
                        <span className="block font-semibold text-navy">{nomeCaso(c)}</span>
                        <span className="mt-0.5 block font-mono text-xs tracking-wide text-gold">
                          Atendimento nº {c.numero_atendimento || "—"}
                        </span>
                        <span className="mt-1 block text-xs text-charcoal/50">
                          Aberto em {dataHora(c.criado_em).split(",")[0]}
                          {c.numero_processo ? ` · Processo ${c.numero_processo}` : ""}
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-2">
                        {pend > 0 && (
                          <span className="rounded-full bg-gold px-2.5 py-1 text-[11px] font-bold text-navy">{pend} pendência{pend > 1 ? "s" : ""}</span>
                        )}
                        <span className="text-gold">→</span>
                      </span>
                    </button>
                  </li>
                );
              })}
              {casos.length === 0 && (
                <li className="text-sm text-charcoal/55">
                  Você ainda não tem atendimento aberto. Use o chat para iniciar.
                </li>
              )}
            </ul>
          </section>
        ) : vista === "cadastro" ? (
          <MeuCadastro cadastro={cadastro} email={email} caso={caso} token={token}
            onVoltar={() => setVista("home")} onSalvo={(c) => setCadastro(c)} />
        ) : vista === "acompanhar" ? (
          /* ── ACOMPANHAR UM ATENDIMENTO ── */
          <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
            <button onClick={() => setVista(casos.length > 1 ? "casos" : "home")}
              className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>

            <h2 className="font-serif text-xl font-bold text-navy">{caso ? nomeCaso(caso) : "Andamento da sua causa"}</h2>
            {caso?.numero_atendimento && (
              <p className="mt-0.5 font-mono text-xs tracking-wide text-gold">Atendimento nº {caso.numero_atendimento}</p>
            )}
            {caso?.numero_processo && <p className="mt-1 text-xs text-charcoal/50">Processo nº {caso.numero_processo}</p>}

            {/* Avisos do escritório, com ciência */}
            {(caso?.avisos || []).length > 0 && (
              <div className="mt-5 space-y-3">
                {(caso!.avisos || []).map((a) => (
                  <div key={a.id}
                    className={`rounded-xl border p-4 ${a.ciencia_em ? "border-black/5 bg-ice" : "border-gold/50 bg-gold/10"}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-navy">{a.titulo}</p>
                        <p className="mt-1 whitespace-pre-line text-sm text-charcoal/75">{a.mensagem}</p>
                        <p className="mt-2 text-[11px] text-charcoal/45">Enviado em {dataHora(a.criado_em)}</p>
                      </div>
                      {!a.ciencia_em && <span className="shrink-0 rounded-full bg-gold px-2 py-0.5 text-[10px] font-bold text-navy">NOVO</span>}
                    </div>
                    {a.ciencia_em ? (
                      <p className="mt-3 text-xs font-medium text-forest">
                        ✓ Você confirmou o recebimento em {dataHora(a.ciencia_em)}
                      </p>
                    ) : (
                      <button onClick={() => darCiencia(a.id)} disabled={dandoCiencia === a.id}
                        className="mt-3 rounded-xl bg-navy px-5 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50">
                        {dandoCiencia === a.id ? "Registrando…" : "Li e estou ciente"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {caso?.aguardando_cliente && (
              <div className="mt-4 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm text-charcoal/80">
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
                {idxEsteira < 0 && (
                  <p className="mt-5 rounded-lg bg-gold/10 px-4 py-3 text-sm text-charcoal/70">
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
                      e avisamos você por e-mail e WhatsApp a cada novo passo.
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
              <div className="min-w-0">
                <p className="text-sm font-semibold text-navy">Atendimento FC Advocacia</p>
                <p className="truncate text-xs text-charcoal/50">
                  {caso?.numero_atendimento
                    ? `${nomeCaso(caso)} · nº ${caso.numero_atendimento}`
                    : "Tire dúvidas e envie documentos — tudo por aqui."}
                </p>
              </div>
              <button onClick={() => setVista("home")} className="shrink-0 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
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
  const [form, setForm] = useState<Record<string, string>>({
    nome: cadastro?.nome || "", cpf_cnpj: cadastro?.cpf_cnpj || "", whatsapp: cadastro?.whatsapp || "",
    rg: cadastro?.rg || "", nacionalidade: cadastro?.nacionalidade || "brasileiro(a)",
    estado_civil: cadastro?.estado_civil || "", profissao: cadastro?.profissao || "",
    endereco_cep: cadastro?.endereco_cep || "", endereco_rua: cadastro?.endereco_rua || "",
    endereco_numero: cadastro?.endereco_numero || "", endereco_complemento: cadastro?.endereco_complemento || "",
    endereco_bairro: cadastro?.endereco_bairro || "", endereco_cidade: cadastro?.endereco_cidade || "",
    endereco_uf: cadastro?.endereco_uf || "",
  });
  const faltando = ["nome", "cpf_cnpj", "estado_civil", "profissao", "endereco_rua",
    "endereco_numero", "endereco_bairro", "endereco_cidade", "endereco_uf", "endereco_cep"]
    .filter((k) => !(form[k] || "").trim());
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
  const assinados = (caso?.assinaturas || []).filter((a) => a.status === "ASSINADO");
  return (
    <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
      <button onClick={onVoltar} className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
      <h2 className="font-serif text-xl font-bold text-navy">Meu cadastro</h2>
      <p className="mt-1 text-sm text-charcoal/60">
        É por estes contatos que avisamos você a cada movimentação do seu caso — por e-mail e WhatsApp.
      </p>

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
        <label className="text-xs font-medium text-charcoal/60">RG
          <input value={form.rg} onChange={(e) => setForm({ ...form, rg: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Estado civil
          <input value={form.estado_civil} onChange={(e) => setForm({ ...form, estado_civil: e.target.value })}
            placeholder="solteiro(a), casado(a)…" className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Profissão
          <input value={form.profissao} onChange={(e) => setForm({ ...form, profissao: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">CEP
          <input value={form.endereco_cep} onChange={(e) => setForm({ ...form, endereco_cep: e.target.value })} inputMode="numeric"
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60 sm:col-span-2">Endereço
          <input value={form.endereco_rua} onChange={(e) => setForm({ ...form, endereco_rua: e.target.value })}
            placeholder="Avenida Sete de Setembro" className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Número
          <input value={form.endereco_numero} onChange={(e) => setForm({ ...form, endereco_numero: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Complemento
          <input value={form.endereco_complemento} onChange={(e) => setForm({ ...form, endereco_complemento: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Bairro
          <input value={form.endereco_bairro} onChange={(e) => setForm({ ...form, endereco_bairro: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Cidade
          <input value={form.endereco_cidade} onChange={(e) => setForm({ ...form, endereco_cidade: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Estado (UF)
          <input value={form.endereco_uf} maxLength={2} onChange={(e) => setForm({ ...form, endereco_uf: e.target.value.toUpperCase() })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
      </div>
      {faltando.length > 0 && (
        <p className="mt-3 rounded-lg border border-amber/50 bg-amber/10 px-4 py-3 text-xs text-charcoal/75">
          Faltam <b>{faltando.length}</b> {faltando.length === 1 ? "informação" : "informações"} para
          completarmos a sua qualificação. Com o cadastro completo, conseguimos preparar
          contrato, procuração e declaração sem precisar te pedir nada depois.
        </p>
      )}
      <div className="mt-3 flex items-center gap-3">
        <button onClick={salvar} disabled={salvando}
          className="rounded-xl bg-gold px-5 py-2 text-sm font-bold text-navy hover:bg-amber disabled:opacity-50">
          {salvando ? "Salvando…" : "Salvar"}
        </button>
        {aviso && <span className="text-xs text-charcoal/60">{aviso}</span>}
      </div>

      {assinados.length > 0 && (
        <div className="mt-8 border-t border-black/5 pt-5">
          <h3 className="text-sm font-semibold text-navy">Documentos que você assinou</h3>
          <ul className="mt-3 space-y-2">
            {assinados.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 rounded-lg border border-black/5 bg-ice px-3 py-2 text-sm">
                <span className="truncate text-charcoal/80">✍ {a.titulo}</span>
                <span className="shrink-0 text-xs text-forest">assinado em {dataHora(a.assinado_em)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

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
                <span className="flex shrink-0 items-center gap-3 text-xs">
                  <span className="text-charcoal/45">
                    {d.enviado_por === "CLIENTE" ? "enviado por você" : "do escritório"}
                  </span>
                  <a href={`${API}/api/v1/documentos/${d.id}/baixar`} target="_blank" rel="noreferrer"
                    className="font-semibold text-gold hover:underline">baixar</a>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
