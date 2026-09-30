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

type Msg = { id?: number; autor: "CLIENTE" | "AGENTE" | "HUMANO"; conteudo: string;
             criado_em?: string; canal?: string | null };
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
  endereco_rua?: string | null; endereco_numero?: string | null;
  endereco_complemento?: string | null; endereco_bairro?: string | null;
  endereco_cidade?: string | null; endereco_uf?: string | null; endereco_cep?: string | null;
};
type Vista = "home" | "casos" | "acompanhar" | "atendimento" | "contrato" | "cadastro" | "pedidos";

/* QUEM VÊ O QUÊ

   São dois serviços com ritos diferentes, e o cliente de um não deve ver
   a tela do outro. Quem chegou pelo balcão pedindo um contrato de
   aluguel não tem processo: mostrar "meus processos" e "você ainda não
   tem caso aberto" a essa pessoa é falar de uma coisa que ela nunca
   pediu, e dá a impressão de que algo deu errado.

   Quem tem os dois (pediu um contrato e depois abriu uma ação, ou o
   contrário) vê os dois. O tipo vem do cadastro, e nunca se apaga um
   lado ao acrescentar o outro. */

const WHATS_RO = "5569993225383";
const WHATS_SC = "5548988357992";
const FALLBACK =
  "Recebi sua mensagem e já estou cuidando do seu caso. Me dê só mais um detalhe " +
  "enquanto preparo o próximo passo. Se preferir, fale agora com nossa equipe pelo WhatsApp, " +
  "não vou te deixar sem resposta.";

const dataHora = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "";

/* Os cartões da tela inicial eram emoji dentro de um quadrado colorido.
   Emoji muda de desenho a cada aparelho, não aceita cor e passa ar de
   rascunho justamente na tela em que o cliente decide se confia no
   escritório. Viraram traço, na mesma espessura, com a cor do sistema. */
const ICONES = {
  pasta: "M3 7h6l2 2h10v10H3zM3 7V5h6l2 2",
  documento: "M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5",
  conversa: "M21 12a8 8 0 0 1-8 8H8l-5 2 1.4-4.2A8 8 0 1 1 21 12z",
  caneta: "M4 20h4l10-10a2.8 2.8 0 0 0-4-4L4 16zM14 6l4 4",
  pessoa: "M20 21v-2a5 5 0 0 0-5-5H9a5 5 0 0 0-5 5v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
};

function Cartao({
  onClick, icone, titulo, texto, contador = 0,
}: {
  onClick: () => void; icone: string; titulo: string; texto: string; contador?: number;
}) {
  return (
    <button onClick={onClick}
      className="group relative flex flex-col items-start rounded-xl2 border border-black/5 bg-white p-7 text-left shadow-card transition hover:-translate-y-1 hover:border-electric/30 hover:shadow-lift">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl2 bg-mist text-electric transition group-hover:bg-electric group-hover:text-white">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
          strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6" aria-hidden="true">
          <path d={icone} />
        </svg>
      </span>

      {contador > 0 && (
        <span className="absolute right-5 top-5 rounded-full bg-electric px-2 py-0.5 text-caption font-bold text-white">
          {contador}
        </span>
      )}

      <h2 className="mt-5 font-display text-subtitle font-bold text-navy">{titulo}</h2>
      <p className="mt-2 text-small text-charcoal/60">{texto}</p>
      <span className="mt-5 text-small font-semibold text-electric">Abrir</span>
    </button>
  );
}

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
  const [subindoAssinado, setSubindoAssinado] = useState<string | null>(null);
  const assinadoRef = useRef<Record<string, HTMLInputElement | null>>({});

  const [anexos, setAnexos] = useState<File[]>([]);
  const [subindo, setSubindo] = useState(false);
  const [alvoSolicitacao, setAlvoSolicitacao] = useState<string | null>(null);
  const arquivoRef = useRef<HTMLInputElement | null>(null);
  const cameraRef = useRef<HTMLInputElement | null>(null);

  const fimRef = useRef<HTMLDivElement | null>(null);
  const [pedidos, setPedidos] = useState<any[]>([]);
  const tipoCliente = String((cadastro as any)?.tipo || "LITIGIOSO").toUpperCase();
  const veContratos = tipoCliente === "CONTRATOS" || tipoCliente === "AMBOS";
  const veProcessos = tipoCliente !== "CONTRATOS" || casos.length > 0;

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
        `tirar qualquer dúvida sobre o seu processo, um documento ou algo que não entendeu, ` +
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

  const carregarPedidos = useCallback(async (tk: string) => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/meus-pedidos`,
        { headers: { Authorization: `Bearer ${tk}` } });
      setPedidos(r.ok ? await r.json() : []);
    } catch { setPedidos([]); }
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
      carregarPedidos(tk);
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
  }, [router, carregarCasos, carregarCaso, carregarPedidos]);

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

  /* Baixa o documento que o escritório mandou assinar (com o token do login). */
  async function baixarParaAssinar(docId: string, titulo: string) {
    try {
      const r = await fetch(`${API}/api/v1/cliente/documentos-assinatura/${docId}/baixar`, { headers: auth() });
      if (!r.ok) { alert("Não foi possível baixar o documento. Tente novamente."); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const tipo = r.headers.get("content-type") || "";
      a.href = url; a.download = `${titulo}${tipo.includes("pdf") ? ".pdf" : ".docx"}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch { alert("Falha de conexão ao baixar."); }
  }

  /* Devolve o documento já assinado. */
  async function enviarAssinado(docId: string, e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setSubindoAssinado(docId);
    try {
      const fd = new FormData();
      fd.append("arquivo", f);
      const r = await fetch(`${API}/api/v1/cliente/documentos-assinatura/${docId}/assinado`, {
        method: "POST", headers: auth(), body: fd,
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { alert(d.detail || "Não foi possível enviar o documento assinado."); return; }
      setMsgs((m) => [...m, { autor: "AGENTE",
        conteudo: "Recebemos o seu documento assinado. Muito obrigado! Já está arquivado no seu processo." }]);
      if (caso) await carregarCaso(caso.id, token, nome);
      await carregarCasos(token);
      alert("Documento assinado enviado com sucesso. Obrigado!");
    } catch { alert("Falha de conexão ao enviar."); }
    finally { setSubindoAssinado(null); }
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
          : "Recebi os documentos, obrigado! Já estão na sua pasta. Ainda falta um item que pedimos, assim que enviar, o processo volta para a produção.",
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
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-electric to-indigo font-display text-small font-bold text-white">
              FC
            </span>
            <span className="flex flex-col leading-none">
              <span className="font-display text-small font-bold text-navy">Advocacia</span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-charcoal/45">
                Área do cliente
              </span>
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <a href={whatsLink} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-whats px-4 py-2 text-caption font-semibold text-white transition hover:brightness-95">
              <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4" aria-hidden="true">
                <path d="M17.47 14.38c-.3-.15-1.75-.86-2.02-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.64.07-.3-.15-1.25-.46-2.38-1.47-.88-.78-1.47-1.75-1.64-2.05-.17-.3-.02-.46.13-.6.13-.14.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.6-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.22 3.08c.15.2 2.1 3.2 5.08 4.49.71.3 1.26.49 1.7.63.71.22 1.36.19 1.87.12.57-.09 1.75-.72 2-1.41.25-.69.25-1.28.17-1.4-.07-.13-.27-.2-.57-.35M12.04 21.5h-.01a9.4 9.4 0 0 1-4.8-1.32l-.34-.2-3.57.94.95-3.48-.22-.36a9.38 9.38 0 0 1-1.44-5.01c0-5.18 4.22-9.4 9.42-9.4a9.34 9.34 0 0 1 6.65 2.76 9.32 9.32 0 0 1 2.76 6.65c0 5.18-4.23 9.4-9.4 9.42M20.5 3.49A11.78 11.78 0 0 0 12.04 0C5.46 0 .1 5.35.1 11.93c0 2.1.55 4.15 1.6 5.96L0 24l6.26-1.64a11.9 11.9 0 0 0 5.78 1.47h.01c6.58 0 11.93-5.35 11.94-11.93a11.86 11.86 0 0 0-3.49-8.44" />
              </svg>
              WhatsApp
            </a>
            <button onClick={sair} className="text-small text-charcoal/50 transition hover:text-charcoal">Sair</button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-8">
        <h1 className="font-display text-title font-bold text-navy">{primeiroNome}</h1>
        <p className="mb-8 text-body text-charcoal/60">
          {casos.length > 1
            ? `Você tem ${casos.length} atendimentos conosco. Cada um tem o seu próprio número, é por ele que identificamos o seu caso.`
            : tipoCliente === "CONTRATOS" && pedidos.length > 0
            ? `Você tem ${pedidos.length} ${pedidos.length === 1 ? "documento" : "documentos"} conosco.`
            : "Aqui ficam o andamento do seu caso, os seus documentos e o canal direto com o escritório."}
        </p>

        {/* Documentos aguardando a sua assinatura */}
        {!carregando && (caso?.assinaturas || []).some((a) => a.status === "ENVIADO") && (
          <div className="mb-6 rounded-2xl border border-forest/40 bg-forest/10 p-5">
            <p className="text-sm font-bold text-navy">✍ Documento aguardando a sua assinatura</p>
            <ol className="mt-2 space-y-0.5 text-xs text-charcoal/70">
              <li>1. Baixe o documento em PDF e confira o conteúdo</li>
              <li>2. Assine, pode imprimir e assinar à caneta, ou assinar digitalmente no celular</li>
              <li>3. Volte aqui e envie o arquivo assinado</li>
            </ol>
            <ul className="mt-4 space-y-2">
              {(caso!.assinaturas || []).filter((a) => a.status === "ENVIADO").map((a) => (
                <li key={a.id} className="rounded-xl bg-white px-4 py-3">
                  <p className="font-semibold text-navy">{a.titulo}</p>
                  <p className="text-xs text-charcoal/50">Enviado em {dataHora(a.enviado_em)}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button onClick={() => baixarParaAssinar(a.id, a.titulo)}
                      className="rounded-xl bg-navy px-5 py-2 text-sm font-semibold text-white hover:opacity-90">
                      ⬇ Baixar documento
                    </button>
                    <button onClick={() => assinadoRef.current?.[a.id]?.click()} disabled={subindoAssinado === a.id}
                      className="rounded-xl bg-forest px-5 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50">
                      {subindoAssinado === a.id ? "Enviando…" : "Enviar assinado"}
                    </button>
                    <input type="file" className="hidden"
                      accept="image/*,application/pdf,.doc,.docx"
                      ref={(el) => { if (assinadoRef.current) assinadoRef.current[a.id] = el; }}
                      onChange={(e) => enviarAssinado(a.id, e)} />
                  </div>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[11px] text-charcoal/55">
              Pode enviar em PDF, Word ou até uma foto do documento assinado, o que for mais fácil para você.
              Se preferir, <b>responda o e-mail</b> que enviamos com o arquivo assinado em anexo:
              funciona do mesmo jeito e chega direto no seu processo.
            </p>
          </div>
        )}

        {/* Avisos sem ciência, o que o escritório precisa que você veja */}
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
          <p className="text-body text-charcoal/50">Carregando</p>
        ) : vista === "home" ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {/* AS DUAS PASTAS, SEMPRE AS DUAS

                Este cartão só aparecia para quem estava marcado como
                cliente de processo, e o de pedidos só para quem estava
                marcado como cliente de contrato. Quem tinha as duas
                coisas via uma só, e quem mudou de categoria no meio do
                caminho perdia a outra de vista.

                O tipo do cliente decide o que vem primeiro, nunca o que
                existe. Pasta vazia diz "você não tem nada aqui", que é
                uma informação; pasta ausente faz a pessoa achar que
                perdeu o processo. */}
            <Cartao
              onClick={() => setVista(casos.length === 1 ? "acompanhar" : "casos")}
              icone={ICONES.pasta}
              contador={totalPendencias}
              titulo="Meus processos"
              texto={casos.length === 0
                ? "Você ainda não tem processo com o escritório. Quando tiver, ele aparece aqui."
                : casos.length === 1
                ? "Veja em que fase o seu caso está, do primeiro contato ao protocolo, e as movimentações do processo."
                : `Seus ${casos.length} processos, cada um com o próprio número e andamento.`}
            />

            {/* ACOMPANHAR PEDIDO, SEM PORTEIRO

                Este cartão só aparecia para quem estava marcado como
                cliente de contratos. Quem chegou por um processo e
                depois encomendou um documento não via o próprio pedido:
                ele existia, estava pago, e sumia da tela. O tipo do
                cliente decide o que é destaque, nunca o que existe. */}
            <Cartao
              onClick={() => setVista("pedidos")}
              icone={ICONES.documento}
              contador={pedidos.filter((p: any) => !["ENTREGUE", "ARQUIVADO"].includes(p.fase)).length}
              titulo="Meus serviços de contrato"
              texto={pedidos.length === 0
                ? "Você ainda não encomendou documento. Quando pedir, ele aparece aqui com número de protocolo."
                : `Seus ${pedidos.length} ${pedidos.length === 1 ? "pedido" : "pedidos"}, cada um com protocolo próprio, do pedido à entrega.`}
            />

            <Cartao
              onClick={() => setVista("atendimento")}
              icone={ICONES.conversa}
              titulo="Atendimento e envio de documentos"
              texto="Fale com o escritório, tire dúvidas e envie documentos por anexo ou foto, no próprio chat."
            />

            <Cartao
              // Vai para o balcão, que é onde o pedido de verdade
              // acontece: catálogo, negociação, pagamento e coleta. A
              // conversa antiga desta tela era um caminho paralelo que
              // não gerava pedido nenhum.
              onClick={() => { window.location.href = "/balcao"; }}
              icone={ICONES.caneta}
              titulo="Solicitar contrato"
              texto="Escolha aqui o documento que precisa. O pedido nasce com protocolo e fica nesta área, com o andamento e a conversa no mesmo lugar."
            />

            <Cartao
              onClick={() => setVista("cadastro")}
              icone={ICONES.pessoa}
              titulo="Meu cadastro e meus documentos"
              texto="Confira os seus dados de contato e tudo o que você já enviou ao escritório."
            />
          </div>
        ) : vista === "pedidos" ? (
          <div>
            <button onClick={() => setVista("home")}
              className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            <h2 className="mb-1 font-display text-title font-bold text-navy">
              Acompanhar pedido
            </h2>
            <p className="mb-5 text-body text-charcoal/60">
              Cada pedido tem o seu próprio número de protocolo. É por ele que o
              escritório identifica o seu documento, e você pode ter quantos
              quiser ao mesmo tempo.
            </p>

            {/* PEDIR OUTRO, A QUALQUER MOMENTO

                Quem encomendou um contrato costuma encomendar o
                segundo. O botão ficava escondido dentro da tela vazia,
                aparecia só para quem não tinha nenhum pedido, e sumia
                justamente para quem já era cliente. */}
            <div className="mb-5 flex flex-wrap gap-3">
              <a href="/balcao"
                className="inline-flex items-center rounded-lg bg-electric px-5 py-2.5 text-small font-bold text-white shadow-card transition hover:bg-indigo">
                Pedir outro documento
              </a>
              <button onClick={() => setVista("atendimento")}
                className="inline-flex items-center rounded-lg border border-black/10 px-5 py-2.5 text-small font-semibold text-charcoal/75 transition hover:border-black/30">
                Falar com o atendimento
              </button>
            </div>

            {pedidos.length === 0 ? (
              <div className="rounded-xl2 border border-black/5 bg-white p-6 text-body text-charcoal/60 shadow-card">
                Você ainda não encomendou nenhum documento. Quando pedir, ele
                aparece aqui com o número de protocolo e a fase em que está.
              </div>
            ) : (
              <div className="space-y-3">
                {pedidos.map((p: any) => {
                  const entregue = p.fase === "ENTREGUE";
                  const arquivado = p.fase === "ARQUIVADO";
                  const nome = p.tipo === "OUTRO" && p.servico_livre
                    ? p.servico_livre
                    : String(p.tipo || "").replaceAll("_", " ").toLowerCase();
                  if (arquivado) {
                    return <Arquivado key={p.id} pedido={p}
                             aoPedir={() => token && carregarPedidos(token)} />;
                  }
                  return (
                    <a key={p.id} href={`/balcao/${p.id}`}
                      className="block rounded-xl2 border border-black/5 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:border-electric/30 hover:shadow-lift">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* O protocolo vem primeiro: é o que a pessoa
                            cita quando liga ou escreve. */}
                        <span className="rounded-md bg-mist px-2.5 py-1 font-mono text-caption tracking-wide text-navy">
                          {p.numero}
                        </span>
                        <span className={`ml-auto rounded-full px-3 py-0.5 text-caption font-bold ${entregue
                          ? "bg-emerald/15 text-emerald"
                          : arquivado ? "bg-black/5 text-charcoal/50"
                          : "bg-electric/15 text-electric"}`}>
                          {entregue ? "Entregue" : arquivado ? "Arquivado"
                            : String(p.fase || "").replaceAll("_", " ").toLowerCase()}
                        </span>
                      </div>
                      <p className="mt-2 font-display text-subtitle font-bold capitalize text-navy">
                        {nome}
                      </p>
                      <p className="mt-1 text-small text-charcoal/60">
                        {Number(p.valor || 0).toLocaleString("pt-BR",
                          { style: "currency", currency: "BRL" })}
                        {p.prazo_entrega_horas ? ` · entrega em até ${p.prazo_entrega_horas}h` : ""}
                      </p>
                      {entregue && p.prazo_alteracao_ate && (
                        <p className="mt-1 text-small text-charcoal/50">
                          Ajustes sem custo até{" "}
                          {String(p.prazo_alteracao_ate).slice(8, 10)}/
                          {String(p.prazo_alteracao_ate).slice(5, 7)}
                        </p>
                      )}
                    </a>
                  );
                })}
              </div>
            )}
          </div>
        ) : vista === "casos" ? (
          /* ── LISTA DE ATENDIMENTOS ── */
          <section className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
            <button onClick={() => setVista("home")} className="mb-4 text-sm text-charcoal/50 hover:text-charcoal">← Voltar</button>
            <h2 className="font-display text-title font-bold text-navy">Meus processos</h2>
            <p className="mt-1 text-body text-charcoal/60">
              Cada processo tem a sua pasta, com o número de atendimento, o
              andamento, a conversa com o escritório e os documentos daquele
              caso. Clique para abrir.
            </p>
            <ul className="mt-5 space-y-3">
              {casos.map((c) => {
                const pend = (c.avisos_sem_ciencia || 0) + (c.documentos_pendentes || 0);
                return (
                  <li key={c.id}>
                    <button onClick={() => abrirCaso(c)}
                      className="flex w-full items-center justify-between gap-4 rounded-xl border border-black/5 bg-ice px-4 py-4 text-left transition hover:border-gold hover:bg-white">
                      <span className="min-w-0">
                        <span className="flex items-center gap-2">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
                            strokeLinecap="round" strokeLinejoin="round"
                            className="h-4 w-4 shrink-0 text-electric" aria-hidden="true">
                            <path d="M3 7h6l2 2h10v10H3zM3 7V5h6l2 2" />
                          </svg>
                          <span className="font-semibold text-navy">{nomeCaso(c)}</span>
                        </span>
                        <span className="mt-0.5 block font-mono text-xs tracking-wide text-gold">
                          Atendimento nº {c.numero_atendimento || ","}
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

            {/* Barra de andamento: amarela enquanto a bola está com o cliente,
                verde assim que ele envia. É o que responde, sem ele precisar
                perguntar, a pergunta "e o meu processo?". */}
            {caso && (
              caso.aguardando_cliente ? (
                <div className="mt-4 overflow-hidden rounded-xl border border-amber/60 bg-amber/10">
                  <div className="h-1.5 w-full bg-amber/25">
                    <div className="h-full w-1/2 bg-amber" />
                  </div>
                  <div className="p-4">
                    <p className="text-sm font-bold text-navy">⚠ Ação necessária: precisamos de um documento seu</p>
                    <p className="mt-1 text-sm text-charcoal/80">{caso.aguardando_desc}</p>
                    <p className="mt-2 text-xs text-charcoal/60">
                      Enquanto isso, seu processo fica parado aguardando você. Assim que enviar,
                      ele volta na hora para os nossos especialistas.
                    </p>
                    <button onClick={() => setVista("atendimento")}
                      className="mt-3 rounded-xl bg-navy px-5 py-2 text-sm font-semibold text-white transition hover:opacity-90">
                      Enviar documento agora
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-4 overflow-hidden rounded-xl border border-forest/40 bg-forest/10">
                  <div className="h-1.5 w-full bg-forest/25">
                    <div className="h-full w-4/5 bg-forest" />
                  </div>
                  <div className="p-4">
                    <p className="text-sm font-bold text-forest">✓ Em elaboração pelos nossos especialistas</p>
                    <p className="mt-1 text-xs text-charcoal/60">
                      Não há nada pendente do seu lado. Qualquer movimentação aparece aqui e
                      chega também no seu e-mail.
                    </p>
                  </div>
                </div>
              )
            )}

            {!caso ? (
              <p className="mt-3 text-sm text-charcoal/60">
                Você ainda não tem um caso aberto. Use o <b>Atendimento</b> para iniciar, assim que contratar,
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
                      Após o protocolo, cada movimentação ou intimação do processo aparecerá aqui automaticamente ,
                      e avisamos você por e-mail e WhatsApp a cada novo passo.
                    </p>
                  )}
                </div>

                {/* A PASTA DO PROCESSO, COMPLETA

                    A conversa e os documentos existiam, mas em outro
                    lugar: o chat era uma tela à parte e os documentos
                    estavam no cadastro, misturados com os de todos os
                    outros casos. Quem tinha dois processos não
                    conseguia responder "o que eu mandei para aquele?".

                    Agora tudo o que é deste caso está dentro dele, e é
                    a mesma coisa que o escritório vê. */}
                <PastaDoProcesso caso={caso} irParaConversa={() => setVista("atendimento")} />
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
                    : "Tire dúvidas e envie documentos, tudo por aqui."}
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
                // resposta que chegou por e-mail entra na mesma conversa,
                // com uma etiqueta para o cliente reconhecer de onde veio
                const porEmail = m.canal === "EMAIL";
                return (
                  <div key={m.id ?? i} className={`flex flex-col ${meu ? "items-end" : "items-start"}`}>
                    <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      meu ? "rounded-br-md bg-navy text-white" : "rounded-bl-md bg-ice text-charcoal"
                    }`}>{texto}</div>
                    {porEmail && (
                      <span className="mt-0.5 px-1 text-[10px] text-charcoal/45">✉ respondido por e-mail</span>
                    )}
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
    email: cadastro?.email || email,
    nacionalidade: cadastro?.nacionalidade || "brasileiro(a)",
    nascimento: (cadastro as any)?.nascimento || "",
    estado_civil: cadastro?.estado_civil || "", profissao: cadastro?.profissao || "",
    endereco_cep: cadastro?.endereco_cep || "", endereco_rua: cadastro?.endereco_rua || "",
    endereco_numero: cadastro?.endereco_numero || "", endereco_complemento: cadastro?.endereco_complemento || "",
    endereco_bairro: cadastro?.endereco_bairro || "", endereco_cidade: cadastro?.endereco_cidade || "",
    endereco_uf: cadastro?.endereco_uf || "",
    // Bancários. Vêm do cadastro para a pessoa não redigitar tudo a
    // cada visita, que era o que acontecia com a qualificação inteira.
    banco_nome: (cadastro as any)?.banco_nome || "",
    banco_codigo: (cadastro as any)?.banco_codigo || "",
    agencia: (cadastro as any)?.agencia || "",
    conta: (cadastro as any)?.conta || "",
    conta_tipo: (cadastro as any)?.conta_tipo || "",
    pix_tipo: (cadastro as any)?.pix_tipo || "",
    pix_chave: (cadastro as any)?.pix_chave || "",
  });
  const [titular, setTitular] = useState<boolean>(
    Boolean((cadastro as any)?.titular_confirmado));
  const faltando = ["nome", "cpf_cnpj", "estado_civil", "profissao", "endereco_rua",
    "endereco_numero", "endereco_bairro", "endereco_cidade", "endereco_uf", "endereco_cep"]
    .filter((k) => !(form[k] || "").trim());
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [cepStatus, setCepStatus] = useState("");
  const [cpfConf, setCpfConf] = useState<any>(null);

  /* Conferência do CPF na Receita, ao sair do campo. Ao salvar seria
     tarde: a pessoa já teria preenchido a tela inteira antes de
     descobrir que errou um dígito lá em cima. */
  async function conferirCpf() {
    const cpf = (form.cpf_cnpj || "").replace(/\D/g, "");
    if (cpf.length !== 11 && cpf.length !== 14) { setCpfConf(null); return; }
    setCpfConf({ carregando: true });
    try {
      const r = await fetch(`${API}/api/v1/cpf/conferir`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cpf, nome: form.nome, nascimento: form.nascimento }),
      });
      setCpfConf(await r.json());
    } catch { setCpfConf(null); }
  }
  // o último CEP consultado impede que a busca rode de novo ao sair do campo
  // e sobrescreva o endereço que a pessoa ajustou à mão
  const ultimoCep = useRef((cadastro?.endereco_cep || "").replace(/\D/g, ""));

  /* Digitou o CEP, o endereço vem sozinho. Depois é só completar o número. */
  async function buscarCep(valor: string) {
    const n = (valor || "").replace(/\D/g, "");
    if (n.length !== 8) { setCepStatus(""); return; }
    if (n === ultimoCep.current) return;   // mesmo CEP: não mexe no que já está preenchido
    ultimoCep.current = n;
    setCepStatus("buscando seu endereço…");
    try {
      const r = await fetch(`${API}/api/v1/cep/${n}`);
      if (!r.ok) {
        ultimoCep.current = "";
        setCepStatus(r.status === 404 ? "CEP não encontrado" : "não consegui buscar agora");
        return;
      }
      const d = await r.json();
      setForm((f) => ({
        ...f,
        endereco_cep: d.cep,
        endereco_rua: d.endereco_rua || f.endereco_rua,
        endereco_bairro: d.endereco_bairro || f.endereco_bairro,
        endereco_cidade: d.endereco_cidade || f.endereco_cidade,
        endereco_uf: d.endereco_uf || f.endereco_uf,
      }));
      setCepStatus("endereço preenchido, confira o número");
      setTimeout(() => setCepStatus(""), 5000);
    } catch { ultimoCep.current = ""; setCepStatus("não consegui buscar agora"); }
  }

  async function salvar() {
    setSalvando(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/cliente/cadastro`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...form, titular_confirmado: titular }),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { setAviso(d.detail || "Não foi possível salvar."); return; }
      const campos: string[] = d?.contato?.campos || [];
      if (campos.length) {
        const nomes = campos.map((c) => (c === "email" ? "e-mail" : "WhatsApp")).join(" e ");
        const n = d?.contato?.avisos_reenviados || 0;
        setAviso(`Cadastro atualizado. A partir de agora os avisos do seu processo vão para o novo ${nomes}.`
          + (n ? ` Reenviamos ${n} aviso(s) que estavam pendentes.` : ""));
      } else {
        setAviso("Cadastro atualizado.");
      }
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
        É por estes contatos que avisamos você a cada movimentação do seu caso, por e-mail e WhatsApp.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="text-xs font-medium text-charcoal/60">Nome completo
          <input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">E-mail de contato
          <input type="email" value={form.email ?? ""}
            onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, email: v })); }}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
          <span className="mt-1 block text-[10px] font-normal text-charcoal/45">
            É para cá que enviamos os avisos do seu processo. Seu login continua
            sendo {email}.
          </span>
        </label>
        <label className="text-xs font-medium text-charcoal/60">CPF / CNPJ
          <input value={form.cpf_cnpj}
            onChange={(e) => setForm({ ...form, cpf_cnpj: e.target.value })}
            onBlur={conferirCpf} inputMode="numeric"
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-electric" />
          {/* O CPF é conferido quando a pessoa sai do campo, e não ao
              salvar. O aviso precisa chegar enquanto ela ainda está
              olhando para o número que digitou. */}
          {cpfConf?.carregando && (
            <span className="mt-1 block text-[11px] font-normal text-charcoal/45">conferindo…</span>
          )}
          {cpfConf && !cpfConf.carregando && cpfConf.ok === false && (
            <span className="mt-1 block text-[11px] font-normal leading-relaxed text-crimson">
              {cpfConf.erro}
              {cpfConf.nome_receita && (
                <span className="mt-0.5 block text-charcoal/55">
                  Na Receita este CPF está em nome de {cpfConf.nome_receita}.
                </span>
              )}
            </span>
          )}
          {cpfConf && !cpfConf.carregando && cpfConf.ok && cpfConf.conferido && (
            <span className="mt-1 block text-[11px] font-normal text-emerald">
              Conferido na Receita, situação regular.
            </span>
          )}
          {cpfConf && !cpfConf.carregando && cpfConf.ok && !cpfConf.conferido && (
            <span className="mt-1 block text-[11px] font-normal text-charcoal/45">
              {cpfConf.aviso}
            </span>
          )}
        </label>
        <label className="text-xs font-medium text-charcoal/60">Data de nascimento
          <span className="block text-[10px] font-normal text-charcoal/40">
            é o que a Receita pede para confirmar o seu CPF
          </span>
          <input type="date" value={form.nascimento || ""}
            onChange={(e) => setForm({ ...form, nascimento: e.target.value })}
            onBlur={conferirCpf}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm text-charcoal outline-none focus:border-electric" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">WhatsApp
          <input value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} inputMode="tel"
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
          <span className="ml-2 text-[10px] font-normal text-gold">{cepStatus}</span>
          <input value={form.endereco_cep} inputMode="numeric" maxLength={9} placeholder="76801-100"
            onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, endereco_cep: v })); buscarCep(v); }}
            onBlur={(e) => buscarCep(e.target.value)}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60 sm:col-span-2">Endereço
          <input type="text" autoComplete="off" value={form.endereco_rua ?? ""}
            onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, endereco_rua: v })); }}
            placeholder="Avenida Sete de Setembro" className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Número
          <input value={form.endereco_numero} onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, endereco_numero: v })); }}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Complemento
          <input value={form.endereco_complemento} onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, endereco_complemento: v })); }}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Bairro
          <input value={form.endereco_bairro} onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, endereco_bairro: v })); }}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Cidade
          <input value={form.endereco_cidade} onChange={(e) => { const v = e.target.value; setForm((f) => ({ ...f, endereco_cidade: v })); }}
            className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-gold" />
        </label>
        <label className="text-xs font-medium text-charcoal/60">Estado (UF)
          <input value={form.endereco_uf} maxLength={2} onChange={(e) => { const v = e.target.value.toUpperCase(); setForm((f) => ({ ...f, endereco_uf: v })); }}
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

      {/* OS DOCUMENTOS SAÍRAM DAQUI

          Ficavam duas listas no fim do cadastro: o que o cliente
          assinou e o que ele enviou. Só que documento pertence a um
          processo ou a um pedido, não à pessoa. Com dois casos abertos,
          as duas listas viravam uma pilha só, sem dizer o que era de
          qual, e era impossível responder "que documento eu mandei para
          aquele processo?".

          Agora cada pasta guarda os seus. O cadastro voltou a ser o que
          o nome diz: quem a pessoa é, onde mora e para onde vai o
          dinheiro dela. */}

      <DadosBancarios form={form} setForm={setForm} nome={form.nome}
        titular={titular} setTitular={setTitular} />

      <TrocarSenha />
    </section>
  );
}


/* ── PARA ONDE O DINHEIRO VAI ──────────────────────────────────
 *
 * Quando uma ação termina com valor a receber, alguém precisa dizer
 * para qual conta transferir. Hoje isso acontece por WhatsApp, no dia
 * do alvará, com print do aplicativo do banco e alguém digitando à mão.
 * É o momento de maior pressa do processo, que é exatamente quando se
 * erra um dígito.
 *
 * Perguntar antes resolve duas coisas: o dado chega com calma e
 * conferido, e a prestação de contas sai preenchida sozinha.
 *
 * A conta tem de ser do próprio cliente, e a tela diz isso com todas as
 * letras. Transferir alvará para conta de terceiro é o caminho mais
 * curto para uma acusação de apropriação, e não há conveniência que
 * pague esse risco. Sem a confirmação de titularidade, a prestação de
 * contas ignora estes campos e o escritório pergunta na hora, como
 * fazia antes.
 */
function DadosBancarios({ form, setForm, nome, titular, setTitular }: {
  form: Record<string, any>; setForm: (f: any) => void; nome: string;
  titular: boolean; setTitular: (v: boolean) => void;
}) {
  const campo = "mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-electric";
  const rotulo = "text-xs font-medium text-charcoal/60";
  const set = (k: string) => (e: any) =>
    setForm((f: any) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="mt-8 border-t border-black/5 pt-6">
      <h3 className="font-display text-body font-bold text-navy">
        Para onde transferir o seu dinheiro
      </h3>
      <p className="mt-1 max-w-2xl text-small text-charcoal/60">
        Se o seu caso terminar com valor a receber, é para esta conta que ele
        vai. Preencher agora evita a correria do dia do alvará, que é quando
        se erra um dígito. Estes dados aparecem num único documento, a
        prestação de contas, junto do valor transferido: nunca em contrato,
        procuração ou petição.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className={rotulo}>Chave PIX
          <input value={form.pix_chave || ""} onChange={set("pix_chave")}
            placeholder="CPF, e-mail, telefone ou chave aleatória" className={campo} />
        </label>
        <label className={rotulo}>Tipo da chave
          <select value={form.pix_tipo || ""} onChange={set("pix_tipo")} className={campo}>
            <option value="">selecione</option>
            <option value="CPF">CPF</option>
            <option value="CNPJ">CNPJ</option>
            <option value="EMAIL">E-mail</option>
            <option value="TELEFONE">Telefone</option>
            <option value="ALEATORIA">Chave aleatória</option>
          </select>
        </label>
      </div>

      <p className="mt-5 text-caption uppercase tracking-wider text-charcoal/45">
        E a conta, para quando o PIX não servir
      </p>
      <p className="text-caption text-charcoal/45">
        PIX falha, cai fora do horário e tem limite. Ter os dois caminhos evita
        que a transferência pare por causa do meio.
      </p>
      <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className={rotulo}>Banco
          <input value={form.banco_nome || ""} onChange={set("banco_nome")}
            placeholder="Nome do banco" className={campo} />
        </label>
        <label className={rotulo}>Tipo de conta
          <select value={form.conta_tipo || ""} onChange={set("conta_tipo")} className={campo}>
            <option value="">selecione</option>
            <option value="CORRENTE">Conta corrente</option>
            <option value="POUPANCA">Poupança</option>
          </select>
        </label>
        <label className={rotulo}>Agência
          <input value={form.agencia || ""} onChange={set("agencia")}
            placeholder="com dígito, se houver" className={campo} />
        </label>
        <label className={rotulo}>Conta
          <input value={form.conta || ""} onChange={set("conta")}
            placeholder="com dígito" className={campo} />
        </label>
      </div>

      <label className="mt-4 flex cursor-pointer items-start gap-2.5 rounded-xl2 border border-black/10 bg-mist/40 p-4">
        <input type="checkbox" checked={titular}
          onChange={(e) => setTitular(e.target.checked)}
          className="mt-0.5 h-4 w-4 accent-electric" />
        <span className="text-small text-charcoal/75">
          Declaro que a conta e a chave informadas são <b>minhas</b>, em nome de{" "}
          <b>{nome || "mim"}</b>.
          <span className="mt-1 block text-caption text-charcoal/55">
            O escritório não transfere valor de processo para conta de outra
            pessoa, mesmo a pedido do cliente. Sem esta confirmação, a
            transferência é combinada por telefone na hora.
          </span>
        </span>
      </label>

      <p className="mt-3 text-caption text-charcoal/45">
        Pode mudar quando quiser. A partir do momento em que salvar, é a conta
        nova que vale para tudo daí em diante.
      </p>
    </div>
  );
}


/* ── TROCAR A SENHA ────────────────────────────────────────────
 *
 * Ficava só na tela de entrada, no "esqueci a senha", que é o caminho
 * de quem não consegue entrar. Quem está dentro e quer trocar por
 * cuidado, e não por esquecimento, não tinha por onde.
 */
function TrocarSenha() {
  const [aberto, setAberto] = useState(false);
  const [nova, setNova] = useState("");
  const [repetir, setRepetir] = useState("");
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function trocar() {
    if (nova.length < 6) { setErro("A senha precisa de pelo menos 6 caracteres."); return; }
    if (nova !== repetir) { setErro("As duas senhas não são iguais."); return; }
    setOcupado(true); setErro(""); setAviso("");
    try {
      const { error } = await supabase.auth.updateUser({ password: nova });
      if (error) { setErro(error.message); return; }
      setAviso("Senha trocada. Use a nova na próxima vez que entrar.");
      setNova(""); setRepetir(""); setAberto(false);
    } finally { setOcupado(false); }
  }

  return (
    <div className="mt-8 border-t border-black/5 pt-6">
      <h3 className="font-display text-body font-bold text-navy">Senha de acesso</h3>
      {aviso && (
        <p className="mt-2 rounded-lg border border-emerald/30 bg-emerald/10 px-4 py-2.5 text-small text-charcoal/80">
          {aviso}
        </p>
      )}
      {!aberto ? (
        <button onClick={() => { setAberto(true); setAviso(""); }}
          className="mt-3 rounded-lg border border-black/15 px-5 py-2.5 text-small font-semibold text-charcoal/75 transition hover:border-black/35">
          Trocar a minha senha
        </button>
      ) : (
        <div className="mt-3 max-w-md">
          <label className="block text-xs font-medium text-charcoal/60">Senha nova
            <input type="password" value={nova} onChange={(e) => setNova(e.target.value)}
              placeholder="pelo menos 6 caracteres"
              className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-electric" />
          </label>
          <label className="mt-3 block text-xs font-medium text-charcoal/60">Repita a senha nova
            <input type="password" value={repetir} onChange={(e) => setRepetir(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && trocar()}
              className="mt-1 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-electric" />
          </label>
          {erro && <p className="mt-2 text-small text-crimson">{erro}</p>}
          <div className="mt-3 flex gap-3">
            <button onClick={trocar} disabled={ocupado}
              className="rounded-lg bg-electric px-5 py-2.5 text-small font-bold text-white transition hover:bg-indigo disabled:opacity-50">
              {ocupado ? "Trocando…" : "Trocar senha"}
            </button>
            <button onClick={() => { setAberto(false); setErro(""); }}
              className="text-small text-charcoal/50 underline underline-offset-4">cancelar</button>
          </div>
          <p className="mt-3 text-caption text-charcoal/45">
            Ninguém no escritório vê a sua senha, nem a antiga nem a nova.
          </p>
        </div>
      )}
    </div>
  );
}


/* ── O PEDIDO ARQUIVADO, E COMO PEDIR DE VOLTA ────────────────
 *
 * O termo promete ao cliente que o documento fica sete dias disponível
 * para revisão e que, passado o prazo, a solicitação é arquivada e
 * pode ser retomada por um chamado. O chamado é este.
 *
 * Não é um botão que reabre sozinho, de propósito. Reabertura
 * automática torna o prazo decorativo: quem sabe que basta clicar não
 * revisa no prazo. E há casos em que retomar custa trabalho de
 * verdade, porque o contrato envelheceu ou a outra parte desistiu.
 * Quem decide é quem vai fazer, lendo o motivo escrito aqui.
 *
 * O cartão fica visualmente apagado, mas não escondido. Documento que
 * some da tela faz o cliente achar que o escritório perdeu o trabalho
 * dele.
 */
function Arquivado({ pedido, aoPedir }: { pedido: any; aoPedir: () => void }) {
  const [aberto, setAberto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [enviado, setEnviado] = useState(false);

  const nomeDoc = pedido.tipo === "OUTRO" && pedido.servico_livre
    ? pedido.servico_livre
    : String(pedido.tipo || "").replaceAll("_", " ").toLowerCase();

  async function enviar() {
    if (motivo.trim().length < 15) {
      setErro("Conte com um pouco mais de detalhe. É o que o escritório lê para decidir.");
      return;
    }
    setOcupado(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedido.id}/desarquivar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ motivo }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(j?.detail || "Não foi possível enviar agora."); return; }
      setEnviado(true); setAberto(false); aoPedir();
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(false); }
  }

  return (
    <div className="rounded-xl2 border border-black/10 bg-mist/40 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-white px-2.5 py-1 font-mono text-caption tracking-wide text-charcoal/60">
          {pedido.numero}
        </span>
        <span className="ml-auto rounded-full bg-black/5 px-3 py-0.5 text-caption font-bold text-charcoal/55">
          Arquivado
        </span>
      </div>

      <p className="mt-2 font-display text-subtitle font-bold capitalize text-charcoal/70">
        {nomeDoc}
      </p>
      <p className="mt-1 text-small text-charcoal/55">
        Passaram os sete dias de revisão sem aprovação. O documento não se
        perdeu: o escritório o guarda e pode retomá-lo.
      </p>

      {enviado ? (
        <p className="mt-4 rounded-lg border border-emerald/30 bg-emerald/10 px-4 py-2.5 text-small text-charcoal/80">
          Pedido de desarquivamento enviado. O escritório analisa e responde
          por e-mail.
        </p>
      ) : !aberto ? (
        <button onClick={() => setAberto(true)}
          className="mt-4 rounded-lg border border-charcoal/20 px-5 py-2.5 text-small font-semibold text-charcoal/75 transition hover:border-charcoal/45">
          Pedir desarquivamento
        </button>
      ) : (
        <div className="mt-4">
          <label className="block text-small text-charcoal/70">
            Por que você precisa deste documento de volta?
            <span className="mt-0.5 block text-caption text-charcoal/45">
              Se houve alguma mudança no combinado ou alguma dúvida que travou
              a aprovação, conte aqui: é o que o escritório precisa saber para
              retomar do ponto certo.
            </span>
            <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)}
              rows={4}
              className="mt-2 w-full rounded-lg border border-black/10 bg-white px-3 py-2.5 text-small text-charcoal outline-none focus:border-electric" />
          </label>
          {erro && <p className="mt-2 text-small text-crimson">{erro}</p>}
          <div className="mt-3 flex flex-wrap gap-3">
            <button onClick={enviar} disabled={ocupado}
              className="rounded-lg bg-electric px-5 py-2.5 text-small font-bold text-white transition hover:bg-indigo disabled:opacity-50">
              {ocupado ? "Enviando…" : "Enviar pedido"}
            </button>
            <button onClick={() => { setAberto(false); setErro(""); }}
              className="text-small text-charcoal/50 underline underline-offset-4">
              cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


/* ── A PASTA DO PROCESSO ───────────────────────────────────────
 *
 * Tudo o que é de um caso, dentro dele: a conversa com o escritório, os
 * documentos que o cliente enviou e os que ele assinou.
 *
 * Antes isso estava espalhado. O chat era uma tela à parte, e as duas
 * listas de documentos ficavam no fim do cadastro, misturando o que era
 * de um processo com o que era de outro. Com dois casos abertos, não
 * havia como responder à pergunta mais comum que um cliente faz: "o
 * que eu já mandei para aquele processo?".
 *
 * O que o cliente vê aqui é o mesmo que o escritório vê do outro lado.
 * Não é transparência de enfeite: é o que evita a ligação para
 * confirmar se o documento chegou.
 */
function PastaDoProcesso({ caso, irParaConversa }: {
  caso: Caso; irParaConversa: () => void;
}) {
  const docs = caso.documentos || [];
  const assinados = (caso.assinaturas || []).filter((a: any) => a.status === "ASSINADO");
  const mensagens = (caso as any).mensagens?.length || 0;

  return (
    <div className="mt-7 border-t border-black/5 pt-5">
      <h3 className="font-display text-body font-bold text-navy">
        Conversas e documentos deste processo
      </h3>
      <p className="mt-1 text-small text-charcoal/60">
        Tudo o que foi tratado neste caso fica guardado aqui e continua onde
        você parou, sempre que voltar.
      </p>

      <button onClick={irParaConversa}
        className="mt-4 flex w-full items-center gap-3 rounded-xl2 border border-black/5 bg-mist/50 p-4 text-left transition hover:border-electric/40 hover:bg-white">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl2 bg-white text-electric">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
            strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5" aria-hidden="true">
            <path d="M21 12a8 8 0 0 1-8 8H8l-5 2 1.4-4.2A8 8 0 1 1 21 12z" />
          </svg>
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-small font-semibold text-navy">
            Atendimento deste processo
          </span>
          <span className="block text-caption text-charcoal/55">
            {mensagens > 0
              ? `${mensagens} ${mensagens === 1 ? "mensagem" : "mensagens"} trocadas. Tire dúvidas sobre andamento, despacho ou qualquer ponto do caso.`
              : "Tire dúvidas sobre andamento, despacho ou qualquer ponto do caso, e envie documentos por aqui."}
          </span>
        </span>
        <span className="shrink-0 text-electric">→</span>
      </button>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <div>
          <p className="text-caption font-semibold uppercase tracking-wider text-charcoal/45">
            Documentos deste processo
          </p>
          {docs.length === 0 ? (
            <p className="mt-2 text-small text-charcoal/55">
              Nada enviado ainda. Quando o escritório precisar de algum
              documento, o pedido aparece no atendimento.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {docs.map((d: any) => (
                <li key={d.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-black/5 bg-ice px-3 py-2 text-small">
                  <span className="truncate text-charcoal/80">{d.observacao || d.tipo}</span>
                  <span className="flex shrink-0 items-center gap-3 text-caption">
                    <span className="text-charcoal/45">
                      {d.enviado_por === "CLIENTE" ? "enviado por você" : "do escritório"}
                    </span>
                    <a href={`${API}/api/v1/documentos/${d.id}/baixar`} target="_blank" rel="noreferrer"
                      className="font-semibold text-electric hover:underline">baixar</a>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="text-caption font-semibold uppercase tracking-wider text-charcoal/45">
            Documentos que você assinou
          </p>
          {assinados.length === 0 ? (
            <p className="mt-2 text-small text-charcoal/55">
              Nenhum ainda. Quando houver documento para assinar, ele aparece
              no topo da sua área.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {assinados.map((a: any) => (
                <li key={a.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-black/5 bg-ice px-3 py-2 text-small">
                  <span className="truncate text-charcoal/80">{a.titulo}</span>
                  <span className="shrink-0 text-caption text-emerald">
                    assinado em {dataHora(a.assinado_em)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
