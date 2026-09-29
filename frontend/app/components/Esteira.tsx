"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import PainelLayout from "./PainelLayout";
import CasoDetalhe from "./CasoDetalhe";
import ImportarProcessos from "./ImportarProcessos";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A esteira é a mesma peça, usada em duas telas, porque são dois
   trabalhos diferentes com ritmos diferentes.

   CONTRATOS é a fase comercial: quem chegou, o que foi proposto, quem
   assinou e quem pagou. TRIAGEM começa quando o contrato está fechado:
   documento, análise, peça, revisão e protocolo. Depois vêm
   JUDICIALIZADO e EXECUÇÃO, cada uma na sua tela.

   Misturar os dois, como estava, fazia o advogado que ia redigir uma
   petição atravessar dez colunas de negociação para chegar no caso dele. */
/* A ENTRADA DO CASO — do primeiro contato ao protocolo.
   Estas colunas já tiveram tela própria, chamada "Contratos". Eram duas
   esteiras para um caminho só: o caso nascia numa tela e continuava em
   outra, e ninguém via o percurso inteiro. Agora são as primeiras
   colunas da Triagem, e "Contratos" ficou livre para o que de fato é —
   o balcão de contratos de prestação de serviço, que é outro negócio. */
const COLUNAS_ENTRADA = [
  { id: "LEAD",           label: "Chegou agora",       cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "QUALIFICACAO",   label: "Qualificação",       cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "PROPOSTA",       label: "Proposta",           cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "CONTRATO",       label: "Assinatura",         cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "PAGAMENTO",      label: "Pagamento",          cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
];

/* JUDICIALIZADO segue o caminho real do processo, não etapas de
   trabalho interno. A coluna de cada caso sai da leitura das
   publicações (backend/app/agentes/fase_judicial.py) e fica sempre
   visível no card, com o motivo — classificação automática sem
   justificativa ninguém confere.

   As duas colunas de prazo são estados de espera: enquanto há prazo em
   aberto o caso fica nelas, e ao cumprir volta sozinho para a coluna de
   onde veio. */
const COLUNAS_JUDICIAL = [
  { id: "PRIMEIRO_GRAU", label: "1º grau",           cor: "border-[#8899AA]", hdr: "bg-[#8899AA]/10" },
  { id: "PRAZO_1G",      label: "Prazo 1º grau",     cor: "border-[#C0392B]", hdr: "bg-[#C0392B]/15" },
  { id: "AUDIENCIA",     label: "Audiência",         cor: "border-[#E5A44C]", hdr: "bg-[#E5A44C]/15" },
  { id: "PERICIA",       label: "Perícia",           cor: "border-[#E5A44C]", hdr: "bg-[#E5A44C]/10" },
  { id: "CONCLUSO",      label: "Concluso",          cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "JULGADO_1G",    label: "Julgado 1º grau",   cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/15" },
  { id: "SEGUNDO_GRAU",  label: "2º grau",           cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "PRAZO_2G",      label: "Prazo 2º grau",     cor: "border-[#C0392B]", hdr: "bg-[#C0392B]/15" },
  { id: "ACORDAO",       label: "Acórdão",           cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "STJ",           label: "STJ",               cor: "border-[#9B59B6]", hdr: "bg-[#9B59B6]/10" },
  { id: "STF",           label: "STF",               cor: "border-[#9B59B6]", hdr: "bg-[#9B59B6]/15" },
  { id: "TRANSITO",      label: "Trânsito em julgado", cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/15" },
];

const COLUNAS_RECEBIMENTO = [
  { id: "RECEBIMENTO", label: "Em execução",            cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/15" },
  { id: "CONCLUIDO",   label: "Concluído",              cor: "border-[#5A6B7C]", hdr: "bg-[#5A6B7C]/10" },
];

const COLUNAS_PRODUCAO = [
  ...COLUNAS_ENTRADA,
  { id: "COLETA_DOCS",    label: "Coleta Docs",        cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "AGUARDANDO_DOCUMENTOS", label: "Aguardando Cliente", cor: "border-[#E5A44C]", hdr: "bg-[#E5A44C]/15" },
  { id: "PRONTO_PARA_ANALISE",   label: "Pronto p/ Análise",  cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/15" },
  { id: "COLETA_PROVAS",  label: "Coleta Provas",      cor: "border-[#F39C12]", hdr: "bg-[#F39C12]/10" },
  { id: "ANALISE",        label: "Análise",            cor: "border-[#4361EE]", hdr: "bg-[#4361EE]/10" },
  { id: "PETICAO",        label: "Peticionamento",     cor: "border-[#2D7DD2]", hdr: "bg-[#2D7DD2]/10" },
  { id: "REVISAO",        label: "Revisão",            cor: "border-[#C9A84C]", hdr: "bg-[#C9A84C]/10" },
  { id: "PROTOCOLO_RPA",  label: "Protocolo",          cor: "border-[#1DB954]", hdr: "bg-[#1DB954]/10" },
  // Fim da linha da triagem: protocolado, o caso vai para Judicializado.
  { id: "LEAD_FRIO",      label: "Sem retorno",        cor: "border-[#5A6B7C]", hdr: "bg-[#5A6B7C]/10" },
  // Protocolado não fica aqui: protocolar é o fim da produção e o
  // começo do judicial. O card aparece na primeira coluna daquela tela
  // — em duas esteiras ao mesmo tempo, ninguém sabe de quem é a vez.
];

const FASES_FORM = [
  { v: "QUALIFICACAO", l: "Qualificação" },
  { v: "PROPOSTA", l: "Negociação / Proposta" },
  { v: "CONTRATO", l: "Assinatura de Contrato" },
  { v: "PAGAMENTO", l: "Pagamento" },
  { v: "COLETA_DOCS", l: "Coleta de Documentos" },
  { v: "COLETA_PROVAS", l: "Coleta de Provas" },
  { v: "ANALISE", l: "Análise" },
  { v: "PETICAO", l: "Peticionamento" },
  { v: "REVISAO", l: "Revisão" },
];
const GRUPOS_FORM = ["BANCARIO", "IMOBILIARIO", "TRABALHISTA", "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"];

type Caso = {
  id: string; estado: string; grupo: string | null; subtipo: string | null;
  numero_processo?: string | null;
  clientes: { nome: string; origem?: string } | null; tese_id: string | null;
  mensagens_nao_respondidas?: number;
  fase_judicial?: string | null;
  fase_judicial_motivo?: string | null;
  fase_judicial_fonte?: string | null;
  // O prazo aberto mais próximo, anexado pelo backend. O card mostrava
  // cliente, matéria e processo — e não mostrava a única coisa que faz
  // alguém largar tudo e trabalhar naquele caso hoje.
  prazo_aberto?: {
    id: string; titulo?: string | null;
    prazo_fatal?: string | null; data_trabalho?: string | null;
    tipo?: string | null; dias_restantes?: number | null;
    depende_do_cliente?: boolean | null;
  } | null;
};

const formVazio = { nome: "", cpf: "", contato: "", grupo: "", fase: "PETICAO", numero_processo: "", honorarios: "", descricao: "" };

export type ModoEsteira = "producao" | "judicial" | "recebimento";

const POR_MODO: Record<ModoEsteira, { titulo: string; colunas: typeof COLUNAS_ENTRADA }> = {
  producao:    { titulo: "Triagem",      colunas: COLUNAS_PRODUCAO },
  judicial:    { titulo: "Judicializado", colunas: COLUNAS_JUDICIAL },
  recebimento: { titulo: "Execução",     colunas: COLUNAS_RECEBIMENTO },
};

export default function Esteira({ modo }: { modo: ModoEsteira }) {
  const contratos = false;   // a entrada virou parte da Triagem
  const judicial = modo === "judicial";
  const producao = modo === "producao";
  const recebimento = modo === "recebimento";
  const processual = judicial || recebimento;
  const COLUNAS = POR_MODO[modo].colunas;
  /* No judicializado a coluna NÃO é o estado do caso: o estado continua
     sendo JUDICIAL (é o que a máquina de estados protege), e a coluna
     vem de `fase_judicial`, lida das publicações. Por isso a lista de
     estados a buscar e a chave de agrupamento são coisas diferentes
     aqui — e só aqui. */
  const estados = judicial
    ? ["JUDICIAL", "PROTOCOLADO", "TRANSITO_JULGADO"]
    : COLUNAS.map((c) => c.id);
  const colunaDoCaso = (c: Caso) =>
    judicial ? (c.fase_judicial || "PRIMEIRO_GRAU") : c.estado;
  const [casos, setCasos] = useState<Caso[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [aba, setAba] = useState<"esteira" | "suspensos" | "arquivados" | "lixeira">("esteira");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [lixeira, setLixeira] = useState<any[]>([]);
  const [form, setForm] = useState({ ...formVazio });
  const [salvando, setSalvando] = useState(false);
  const [importar, setImportar] = useState(false);
  const [movendo, setMovendo] = useState<string | null>(null);
  /* Seleção em lote. Importar cinco anos de acervo traz processo
     arquivado que não interessa; apagar de um em um é trabalho que
     ninguém faz, e o acervo velho acaba ficando lá atrapalhando. */
  const [selecao, setSelecao] = useState<Record<string, boolean>>({});
  const [excluindo, setExcluindo] = useState(false);
  const [recalculando, setRecalculando] = useState(false);

  function load() {
    setLoading(true);
    if (aba === "lixeira") {
      fetch(`${API}/api/v1/lixeira`).then((r) => r.json())
        .then((d) => setLixeira(Array.isArray(d) ? d : []))
        .catch(() => setLixeira([])).finally(() => setLoading(false));
      return;
    }
    const situ = aba === "esteira" ? "ATIVO" : aba === "suspensos" ? "SUSPENSO" : "ARQUIVADO";
    /* Cada tela carrega só o que é dela. A caixa de "intervenção
       urgente" ficava em todas e repetia os mesmos nove casos em cima
       de qualquer trabalho — quem abria o Judicial via a fila da
       triagem antes do próprio acervo. O caso pede atenção no lugar
       onde ele está: o card fica na coluna dele, com o contador de
       mensagens, e os prazos têm a tela de Intimações. */
    fetch(`${API}/api/v1/casos?situacao=${situ}`)
      .then((r) => r.json()).catch(() => [])
      .then((cs) => {
        const lista = Array.isArray(cs) ? cs : [];
        setCasos(aba === "esteira" ? lista.filter((c: Caso) => estados.includes(c.estado)) : lista);
      }).finally(() => setLoading(false));
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [aba, modo]);

  /* Vir de outra tela com um caso em mente — "abrir caso" na lista de
     prazos, por exemplo — abre a pasta dele direto, em vez de largar a
     pessoa na esteira inteira para procurar o card. Lemos da URL no
     efeito, e não com useSearchParams, para a página não precisar de
     fronteira de Suspense no build. */
  useEffect(() => {
    const alvo = new URLSearchParams(window.location.search).get("caso");
    if (alvo) setSelecionado(alvo);
  }, []);

  async function aprovar(id: string) {
    await fetch(`${API}/api/v1/casos/${id}/aprovar-protocolar`, { method: "POST" });
    load();
  }

  /* Mover de fase pela mão: o automático cobre protocolo e trânsito em
     julgado, mas há caso que anda por fora (acordo, cumprimento
     voluntário, desmembramento). O botão existe para isso. */
  async function moverFase(id: string, destino: "JUDICIAL" | "RECEBIMENTO") {
    const rotulo = destino === "RECEBIMENTO" ? "execução" : "judicializado";
    if (!confirm(`Mover este caso para a fase ${rotulo}?`)) return;
    setMovendo(id);
    try {
      const r = await fetch(`${API}/api/v1/casos/${id}/mover-fase`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destino, motivo: "movido na tela" }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({} as any));
        alert(e.detail || `Não foi possível mover (erro ${r.status}).`);
        return;
      }
      load();
    } finally { setMovendo(null); }
  }

  const selecionados = Object.keys(selecao).filter((k) => selecao[k]);

  function alternar(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setSelecao((s) => ({ ...s, [id]: !s[id] }));
  }

  async function excluirSelecionados() {
    if (!selecionados.length) return;
    const nomes = casos.filter((c) => selecao[c.id]).slice(0, 5)
      .map((c) => `• ${c.clientes?.nome ?? "—"}${c.numero_processo ? ` (${c.numero_processo})` : ""}`)
      .join("\n");
    const resto = selecionados.length > 5 ? `\n… e mais ${selecionados.length - 5}` : "";
    if (!window.confirm(
      `Excluir ${selecionados.length} caso(s)?\n\n${nomes}${resto}\n\n` +
      "Todos vão para a lixeira, onde ficam 6 meses e podem ser restaurados."
    )) return;

    setExcluindo(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/excluir-varios`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: selecionados }),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { alert(d.detail || `Erro ${r.status}`); return; }
      // O que falhou é dito com nome e motivo, não escondido num contador.
      if (d.falhas?.length) {
        alert(`${d.excluidos} excluído(s). ${d.falhas.length} não saiu (saíram):\n\n` +
          d.falhas.slice(0, 5).map((f: any) => `• ${f.erro}`).join("\n"));
      }
      setSelecao({});
      load();
    } catch {
      alert("Não foi possível falar com o servidor.");
    } finally { setExcluindo(false); }
  }

  /* Correção humana da coluna. Fica marcada como manual no servidor e
     a leitura automática para de mexer naquele caso — quem abriu o
     processo sabe mais que a leitura de texto. */
  async function corrigirColuna(id: string, fase: string) {
    await fetch(`${API}/api/v1/casos/${id}/fase-judicial`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fase, motivo: "corrigido na tela" }),
    });
    load();
  }

  async function religarAutomatico(id: string) {
    await fetch(`${API}/api/v1/casos/${id}/fase-judicial/automatico`, { method: "POST" });
    load();
  }

  /* MUDAR DE COLUNA À MÃO.

     O card só tinha "voltar": dava para recuar de fase e não para
     avançar, e o caso ficava preso esperando um automático que nem
     sempre vem — a qualificação que terminou no telefone, a proposta
     aceita no WhatsApp, o pagamento que caiu na conta. Quem está
     olhando a tela sabe o que aconteceu; faltava o botão.

     Fora do judicial a coluna é o `estado` do caso, e é isso que muda
     aqui. No judicial a coluna é lida das publicações, e mexer nela é
     `corrigirColuna`, que marca a correção como MANUAL. */
  async function mudarEstado(id: string, estado: string) {
    setMovendo(id);
    try {
      const r = await fetch(`${API}/api/v1/casos/${id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado }),
      });
      if (!r.ok) { alert("Não consegui mudar a fase."); return; }
      load();
    } catch { alert("Falha de conexão."); }
    finally { setMovendo(null); }
  }

  /* A próxima coluna da esteira. LEAD_FRIO fica de fora do "avançar":
     "sem retorno" não é etapa do caminho, é desvio — se alguém quiser
     mandar o caso para lá, usa o seletor. */
  const proximaColuna = (atual: string) => {
    const fila = POR_MODO[modo].colunas.filter((c) => c.id !== "LEAD_FRIO");
    const i = fila.findIndex((c) => c.id === atual);
    return i >= 0 && i < fila.length - 1 ? fila[i + 1] : null;
  };

  async function reclassificarTudo() {
    setRecalculando(true);
    try {
      const r = await fetch(`${API}/api/v1/judicial/reclassificar`, { method: "POST" });
      const d = await r.json().catch(() => ({} as any));
      if (r.ok) {
        alert(`${d.reavaliados ?? 0} de ${d.casos ?? 0} caso(s) reposicionado(s).` +
          (d.viraram_execucao ? ` ${d.viraram_execucao} passaram para execução.` : ""));
      } else {
        alert(d.detail || `Erro ${r.status}`);
      }
      load();
    } catch {
      alert("Não foi possível falar com o servidor.");
    } finally { setRecalculando(false); }
  }

  async function restaurar(id: string) {
    await fetch(`${API}/api/v1/lixeira/${id}/restaurar`, { method: "POST" });
    load();
  }

  async function criarEscritorio(e: React.FormEvent) {
    e.preventDefault();
    if (!form.nome.trim()) { alert("Informe o nome do cliente."); return; }
    if (!form.contato.trim()) { alert("Informe o contato do cliente (e-mail ou WhatsApp) para acionamento."); return; }
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/escritorio`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: form.nome, cpf: form.cpf || null, contato: form.contato,
          grupo: form.grupo || null, fase: form.fase,
          numero_processo: form.numero_processo || null,
          honorarios: form.honorarios || null, descricao: form.descricao || null,
        }),
      });
      if (!r.ok) {
        const er = await r.json().catch(() => ({} as any));
        alert("Não foi possível cadastrar: " + (er.detail || `erro ${r.status}`));
        return;
      }
      setModal(false); setForm({ ...formVazio }); setAba("esteira"); load();
    } catch {
      alert("Falha de conexão com o servidor. Verifique a internet e tente de novo.");
    } finally { setSalvando(false); }
  }

  const ehEscritorio = (c: Caso) => c.clientes?.origem === "ESCRITORIO";

  return (
    <PainelLayout titulo={POR_MODO[modo].titulo}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm text-[#8899AA]">
          {loading ? "Carregando..." : `${casos.length} caso(s)`}
        </span>
        {processual ? (
          <>
            <button onClick={() => setImportar(true)}
              className="ml-auto rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
              + Carregar processos (OAB ou número)
            </button>
            {judicial && (
              <button onClick={reclassificarTudo} disabled={recalculando}
                title="Relê as publicações de todos os processos e reposiciona os cards"
                className="rounded-md border border-[#2D7DD2]/60 px-3 py-1.5 text-sm font-semibold text-[#2D7DD2] transition hover:bg-[#2D7DD2]/10 disabled:opacity-50">
                {recalculando ? "Relendo…" : "Reavaliar colunas"}
              </button>
            )}
            <Link href="/intimacoes"
              className="rounded-md border border-[#C9A84C]/50 px-3 py-1.5 text-sm font-semibold text-[#C9A84C] transition hover:bg-[#C9A84C]/10">
              Intimações e prazos →
            </Link>
          </>
        ) : contratos ? (
          <button onClick={() => { setForm({ ...formVazio, fase: "QUALIFICACAO" }); setModal(true); }}
            className="ml-auto rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
            + Novo contrato / cliente
          </button>
        ) : (
          <>
            <button onClick={() => { setForm({ ...formVazio }); setModal(true); }}
              className="ml-auto rounded-md bg-[#C9A84C] px-3 py-1.5 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e]">
              + Montar processo do escritório
            </button>
            <Link href="/processos"
              className="rounded-md border border-[#C9A84C]/50 px-3 py-1.5 text-sm font-semibold text-[#C9A84C] transition hover:bg-[#C9A84C]/10">
              Processos em andamento →
            </Link>
          </>
        )}
        <button onClick={load}
          className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8899AA] transition-colors hover:text-white">
          Atualizar
        </button>
      </div>

      {/* Barra da seleção — só aparece quando há algo marcado, para não
          ocupar espaço nem sugerir exclusão o tempo todo. */}
      {selecionados.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-[#C0392B]/40 bg-[#C0392B]/10 px-4 py-2.5">
          <span className="text-sm text-white/85">
            <b>{selecionados.length}</b> caso(s) selecionado(s)
          </span>
          <button onClick={() => setSelecao({})}
            className="text-xs text-white/60 underline hover:text-white">limpar seleção</button>
          <button
            onClick={() => setSelecao(Object.fromEntries(casos.map((c) => [c.id, true])))}
            className="text-xs text-white/60 underline hover:text-white">
            selecionar os {casos.length} desta tela
          </button>
          <button onClick={excluirSelecionados} disabled={excluindo}
            className="ml-auto rounded-md bg-[#C0392B] px-4 py-1.5 text-sm font-bold text-white transition hover:bg-[#d14335] disabled:opacity-50">
            {excluindo ? "Excluindo…" : `Excluir ${selecionados.length} caso(s)`}
          </button>
        </div>
      )}

      {/* Abas */}
      <div className="flex gap-2">
        {([["esteira", "Esteira"], ["suspensos", "Suspensos"], ["arquivados", "Arquivados"], ["lixeira", "Lixeira"]] as const).map(([k, l]) => (
          <button key={k} onClick={() => setAba(k)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${aba === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-[#8899AA] hover:text-white"}`}>
            {l}
          </button>
        ))}
      </div>


      {/* Esteira (aba ativa) ou listas de Suspensos/Arquivados */}
      {aba === "esteira" ? (
      <div className="mt-4 overflow-x-auto">
        <div className="flex gap-3 min-w-max pb-4">
          {COLUNAS.map((col) => {
            const cards = casos.filter((c) => colunaDoCaso(c) === col.id);
            return (
              <div key={col.id} className={`${judicial ? "w-48" : "w-56"} shrink-0 flex flex-col gap-2`}>
                <div className={`rounded-lg px-3 py-2 border-l-4 ${col.cor} ${col.hdr} flex items-center justify-between`}>
                  <h2 className="text-xs font-bold text-white truncate">{col.label}</h2>
                  <span className="text-xs text-[#8899AA] ml-1">{cards.length}</span>
                </div>
                <div className="space-y-2 min-h-[3rem]">
                  {cards.map((c) => (
                    <div key={c.id} onClick={() => setSelecionado(c.id)}
                      className={`cursor-pointer rounded-lg bg-[#1A3A6B]/30 border p-3 transition-colors ${ehEscritorio(c) ? "border-[#C9A84C]/40" : "border-white/5 hover:border-[#2D7DD2]/30"}`}>
                      <div className="flex items-start justify-between gap-1">
                        <input type="checkbox" checked={!!selecao[c.id]}
                          onClick={(e) => alternar(c.id, e)} onChange={() => {}}
                          title="Selecionar para excluir em lote"
                          className="mt-0.5 mr-1 h-3.5 w-3.5 shrink-0 cursor-pointer accent-[#C0392B]" />
                        <p className="font-semibold text-white text-sm truncate flex-1">{c.clientes?.nome ?? "—"}</p>
                        {/* A urgência agora mora no card, na coluna onde o
                            caso está — e não numa caixa que repetia os
                            mesmos casos em cima de todas as telas. */}
                        {(c.mensagens_nao_respondidas ?? 0) > 0 && (
                          <span className="shrink-0 rounded-full bg-[#C0392B] px-2 py-0.5 text-[10px] font-bold text-white">
                            {c.mensagens_nao_respondidas} msg
                          </span>
                        )}
                      </div>
                      {ehEscritorio(c) && (
                        <span className="mt-1 inline-block rounded bg-[#C9A84C]/20 px-2 py-0.5 text-[10px] font-bold text-[#C9A84C]">★ ESCRITÓRIO</span>
                      )}
                      <p className="text-xs text-[#8899AA] mt-1 truncate">
                        {c.grupo}{c.subtipo ? ` > ${c.subtipo}` : ""}
                      </p>
                      {c.numero_processo && (
                        <p className="text-[10px] text-[#8899AA]/70 mt-0.5 truncate">Proc. {c.numero_processo}</p>
                      )}
                      {c.tese_id && (
                        <span className="inline-block mt-1 text-[10px] bg-[#2D7DD2]/15 text-[#2D7DD2] rounded px-2 py-0.5">{c.tese_id}</span>
                      )}
                      {/* Por que este caso está nesta coluna. Sem isso a
                          classificação automática vira caixa-preta. */}
                      {judicial && c.fase_judicial_motivo && (
                        <p className="mt-1 text-[10px] leading-snug text-white/40"
                          title={c.fase_judicial_motivo}>
                          {c.fase_judicial_fonte === "MANUAL" ? "✋ " : ""}
                          {c.fase_judicial_motivo.length > 64
                            ? c.fase_judicial_motivo.slice(0, 64) + "…"
                            : c.fase_judicial_motivo}
                        </p>
                      )}
                      {c.prazo_aberto && (
                        <PrazoNoCard prazo={c.prazo_aberto} aoMudar={load} />
                      )}

                      {/* Avançar uma casa. No judicial a coluna vem das
                          publicações, então avançar ali é correção
                          manual e passa pelo mesmo caminho. */}
                      {(() => {
                        const prox = proximaColuna(colunaDoCaso(c));
                        if (!prox) return null;
                        return (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (!confirm(`Avançar este caso para "${prox.label}"?`)) return;
                              judicial ? corrigirColuna(c.id, prox.id) : mudarEstado(c.id, prox.id);
                            }}
                            disabled={movendo === c.id}
                            className="mt-2 w-full rounded-md bg-[#2D7DD2] py-1.5 text-xs font-bold text-white transition hover:bg-[#2468b0] disabled:opacity-40">
                            {movendo === c.id ? "movendo…" : `Avançar → ${prox.label}`}
                          </button>
                        );
                      })()}

                      {/* Mover para qualquer coluna desta esteira. Antes
                          só o judicial tinha seletor, e as outras telas
                          não tinham como corrigir um card fora de lugar. */}
                      {!judicial && (
                        <select value={colunaDoCaso(c)}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => { e.stopPropagation(); mudarEstado(c.id, e.target.value); }}
                          title="Mover para outra fase"
                          className="mt-1.5 w-full rounded border border-white/10 bg-[#0A1628] px-1.5 py-1 text-[10px] text-white/70 outline-none focus:border-[#C9A84C]">
                          {POR_MODO[modo].colunas.map((k) => (
                            <option key={k.id} value={k.id}>{k.label}</option>
                          ))}
                        </select>
                      )}
                      {judicial && (
                        <select value={colunaDoCaso(c)}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => { e.stopPropagation(); corrigirColuna(c.id, e.target.value); }}
                          title="Corrigir a coluna à mão"
                          className="mt-1.5 w-full rounded border border-white/10 bg-[#0A1628] px-1.5 py-1 text-[10px] text-white/70 outline-none focus:border-[#C9A84C]">
                          {COLUNAS_JUDICIAL.map((k) => (
                            <option key={k.id} value={k.id}>{k.label}</option>
                          ))}
                        </select>
                      )}
                      {judicial && c.fase_judicial_fonte === "MANUAL" && (
                        <button onClick={(e) => { e.stopPropagation(); religarAutomatico(c.id); }}
                          className="mt-1 w-full text-[10px] text-white/35 underline hover:text-white/70">
                          voltar a seguir as publicações
                        </button>
                      )}

                      {/* Mover de fase: do judicial para a execução, e o
                          caminho de volta, se a fase foi virada cedo. */}
                      {judicial && (
                        <button onClick={(e) => { e.stopPropagation(); moverFase(c.id, "RECEBIMENTO"); }}
                          disabled={movendo === c.id}
                          className="mt-2 w-full rounded-md border border-[#C9A84C]/60 py-1.5 text-xs font-bold text-[#C9A84C] transition hover:bg-[#C9A84C]/10 disabled:opacity-40">
                          {movendo === c.id ? "movendo…" : "Mover para execução →"}
                        </button>
                      )}
                      {recebimento && col.id === "RECEBIMENTO" && (
                        <button onClick={(e) => { e.stopPropagation(); moverFase(c.id, "JUDICIAL"); }}
                          disabled={movendo === c.id}
                          className="mt-2 w-full rounded-md border border-white/20 py-1.5 text-xs font-semibold text-white/70 transition hover:bg-white/5 disabled:opacity-40">
                          {movendo === c.id ? "movendo…" : "← Voltar para o judicializado"}
                        </button>
                      )}
                      {/* Protocolado, o caso sai da triagem. */}
                      {producao && col.id === "PROTOCOLO_RPA" && (
                        <button onClick={(e) => { e.stopPropagation(); moverFase(c.id, "JUDICIAL"); }}
                          disabled={movendo === c.id}
                          className="mt-2 w-full rounded-md border border-[#C9A84C]/60 py-1.5 text-xs font-bold text-[#C9A84C] transition hover:bg-[#C9A84C]/10 disabled:opacity-40">
                          {movendo === c.id ? "movendo…" : "Mover para judicializado →"}
                        </button>
                      )}
                      {col.id === "REVISAO" && (
                        <button onClick={(e) => { e.stopPropagation(); aprovar(c.id); }}
                          className="mt-2 w-full rounded-md bg-[#1DB954] hover:bg-[#17a349] py-1.5 text-xs font-bold text-white transition-colors">
                          Aprovar e Protocolar
                        </button>
                      )}
                    </div>
                  ))}
                  {cards.length === 0 && (
                    <div className="rounded-lg border border-dashed border-white/10 p-3 text-center">
                      <p className="text-xs text-[#8899AA]/40">vazio</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      ) : aba === "lixeira" ? (
        <div className="p-4">
          {loading ? (
            <p className="text-[#8899AA]">Carregando...</p>
          ) : lixeira.length === 0 ? (
            <p className="text-[#8899AA]/50">Lixeira vazia.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {lixeira.map((it) => (
                <div key={it.id} className="rounded-lg border border-white/10 bg-[#1A3A6B]/30 p-4">
                  <p className="text-sm font-semibold text-white">{it.rotulo || "—"}</p>
                  <p className="mt-1 text-xs text-[#8899AA]">Excluído: {new Date(it.excluido_em).toLocaleString("pt-BR")}</p>
                  <p className="text-[10px] text-[#8899AA]/60">Guardado até: {new Date(it.expira_em).toLocaleDateString("pt-BR")}</p>
                  <button onClick={() => restaurar(it.id)} className="mt-2 rounded-lg bg-[#1DB954] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#17a349]">Restaurar</button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="p-4">
          {loading ? (
            <p className="text-[#8899AA]">Carregando...</p>
          ) : casos.length === 0 ? (
            <p className="text-[#8899AA]/50">Nenhum caso {aba === "suspensos" ? "suspenso" : "arquivado"}.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {casos.map((c) => (
                <button key={c.id} onClick={() => setSelecionado(c.id)}
                  className="rounded-lg border border-white/10 bg-[#1A3A6B]/30 p-4 text-left transition hover:border-[#C9A84C]/40">
                  <p className="text-sm font-semibold text-white">{c.clientes?.nome ?? "—"}</p>
                  <p className="mt-1 text-xs text-[#8899AA]">{c.grupo ?? "—"} · {c.estado}</p>
                  {ehEscritorio(c) && <span className="mt-1 inline-block text-[10px] text-[#C9A84C]">★ Escritório</span>}
                  <p className="mt-2 text-xs text-[#C9A84C]">Abrir para ativar →</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Montar Processo do Escritório */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setModal(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={criarEscritorio}
            className="w-full max-w-lg rounded-2xl bg-[#0F2A44] p-6 text-white shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">Montar Processo do Escritório</h2>
              <button type="button" onClick={() => setModal(false)} className="text-white/60 hover:text-white">✕</button>
            </div>
            <p className="mb-4 text-xs text-white/55">
              Cadastra o cliente direto na plataforma e insere o processo na fase atual, entrando na esteira de produção.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Nome do cliente *"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C] sm:col-span-2" />
              <input value={form.cpf} onChange={(e) => setForm({ ...form, cpf: e.target.value })} placeholder="CPF/CNPJ"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <input value={form.contato} onChange={(e) => setForm({ ...form, contato: e.target.value })} placeholder="E-mail ou WhatsApp"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <select value={form.grupo} onChange={(e) => setForm({ ...form, grupo: e.target.value })}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]">
                <option value="">Grupo (área)…</option>
                {GRUPOS_FORM.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
              <select value={form.fase} onChange={(e) => setForm({ ...form, fase: e.target.value })}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]">
                {FASES_FORM.map((f) => <option key={f.v} value={f.v}>{f.l}</option>)}
              </select>
              <input value={form.numero_processo} onChange={(e) => setForm({ ...form, numero_processo: e.target.value })} placeholder="Nº do processo (se houver)"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <input value={form.honorarios} onChange={(e) => setForm({ ...form, honorarios: e.target.value })} placeholder="Honorários (ex.: R$ 1.500)"
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]" />
              <textarea value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Descrição / observações" rows={3}
                className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C] sm:col-span-2" />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(false)} className="rounded-lg border border-white/15 px-4 py-2 text-sm text-white/70 hover:text-white">Cancelar</button>
              <button type="submit" disabled={salvando}
                className="rounded-lg bg-[#C9A84C] px-5 py-2 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e] disabled:opacity-50">
                {salvando ? "Cadastrando..." : "Cadastrar na esteira"}
              </button>
            </div>
          </form>
        </div>
      )}

      {importar && (
        <ImportarProcessos
          fase={judicial ? "JUDICIAL" : "RECEBIMENTO"}
          onFechar={() => setImportar(false)}
          onPronto={load}
        />
      )}

      {selecionado && (
        <CasoDetalhe casoId={selecionado} onFechar={() => setSelecionado(null)} onMudou={load} />
      )}
    </PainelLayout>
  );
}


/* ── O prazo no card ───────────────────────────────────────────────

   Mostra o prazo fatal mais próximo e deixa corrigi-lo ali mesmo.

   A correção à mão não é luxo: todo prazo calculado pelo sistema é
   ESTIMADO. A contagem sai da publicação e de um calendário de feriados
   NACIONAIS — que não conhece feriado municipal, ponto facultativo nem
   suspensão de expediente do tribunal. Quem está com o processo aberto
   na tela sabe a data certa; faltava onde escrevê-la. */
function PrazoNoCard({ prazo, aoMudar }: { prazo: any; aoMudar: () => void }) {
  const [abrir, setAbrir] = useState(false);
  const [data, setData] = useState(String(prazo.prazo_fatal || prazo.data_trabalho || "").slice(0, 10));
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);

  const d = prazo.dias_restantes;
  const cor = d == null ? "#8899AA"
    : d < 0 ? "#C0392B" : d <= 2 ? "#E5A44C" : d <= 7 ? "#C9A84C" : "#8899AA";
  const quando = d == null ? "sem data"
    : d < 0 ? `venceu há ${Math.abs(d)} d`
    : d === 0 ? "vence hoje"
    : d === 1 ? "vence amanhã"
    : `${d} dias`;
  const br = (x?: string | null) =>
    x ? `${String(x).slice(8, 10)}/${String(x).slice(5, 7)}` : "—";

  async function salvar(e: React.MouseEvent) {
    e.stopPropagation();
    if (!data) return;
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/v1/prazos/${prazo.id}/ajustar`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prazo_fatal: data, motivo, quem: "escritório" }),
      });
      if (!r.ok) { alert("Não consegui alterar o prazo."); return; }
      setAbrir(false); setMotivo(""); aoMudar();
    } finally { setSalvando(false); }
  }

  async function cumprir(e: React.MouseEvent) {
    e.stopPropagation();
    const feito = prompt("O que foi feito? (vai para o histórico do caso)");
    if (feito === null) return;
    setSalvando(true);
    try {
      await fetch(`${API}/api/v1/prazos/${prazo.id}/cumprir`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ motivo: feito, quem: "escritório" }),
      });
      aoMudar();
    } finally { setSalvando(false); }
  }

  return (
    <div className="mt-2 rounded-md border px-1.5 py-1"
      style={{ borderColor: `${cor}66`, background: `${cor}14` }}>
      <button onClick={(e) => { e.stopPropagation(); setAbrir(!abrir); }}
        className="flex w-full items-center gap-1.5 text-left">
        <span className="text-[10px]">⏳</span>
        <span className="text-[10px] font-bold" style={{ color: cor }}>{quando}</span>
        <span className="truncate text-[10px] text-white/50">
          {br(prazo.prazo_fatal)} · {prazo.titulo || prazo.tipo || "prazo"}
        </span>
        {prazo.depende_do_cliente && (
          <span className="shrink-0 text-[9px] text-white/35" title="Depende do cliente">👤</span>
        )}
      </button>

      {abrir && (
        <div className="mt-1.5 space-y-1" onClick={(e) => e.stopPropagation()}>
          <p className="text-[9px] leading-snug text-white/40">
            Prazo estimado pelo sistema: a contagem usa feriados nacionais e não
            conhece feriado local nem suspensão de expediente. Confira e corrija.
          </p>
          <input type="date" value={data} onChange={(e) => setData(e.target.value)}
            className="w-full rounded border border-white/15 bg-[#0A1628] px-1.5 py-1 text-[10px] text-white outline-none focus:border-[#C9A84C]" />
          <input value={motivo} onChange={(e) => setMotivo(e.target.value)}
            placeholder="motivo da correção"
            className="w-full rounded border border-white/15 bg-[#0A1628] px-1.5 py-1 text-[10px] text-white outline-none focus:border-[#C9A84C]" />
          <div className="flex gap-1">
            <button onClick={salvar} disabled={salvando}
              className="flex-1 rounded bg-[#C9A84C] py-1 text-[10px] font-bold text-[#0A1628] disabled:opacity-40">
              {salvando ? "…" : "Corrigir"}
            </button>
            <button onClick={cumprir} disabled={salvando}
              className="flex-1 rounded bg-[#1DB954] py-1 text-[10px] font-bold text-white disabled:opacity-40">
              Cumprido
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
