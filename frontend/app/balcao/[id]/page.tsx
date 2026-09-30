"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import VisualizadorProtegido from "../../components/VisualizadorProtegido";
import { esperarAVez } from "../../components/ritmoDaConversa";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* O PEDIDO, DO LADO DO CLIENTE

   Esta tela não é a área de acompanhamento de processo, é outra coisa,
   e de propósito. Quem pede um contrato de locação não tem processo,
   não tem prazo processual e não precisa ver nada disso.

   Aqui o cliente escolhe COMO quer entregar as informações, mandando
   cópia dos documentos ou digitando ,, acompanha a fase, e no fim lê a
   minuta e aprova ou pede mudança. Uma coluna só, poucas decisões por
   vez.

   Os dois caminhos da coleta são alternativos, não um obrigatório e
   outro opcional: quem tem os documentos à mão manda foto e pronto;
   quem está no ônibus digita. */

/* A ORDEM MUDOU
   O pagamento era a terceira etapa: o cliente preenchia tudo, lia a
   orientação e só então pagava. Isso põe o trabalho antes do sim.
   Agora é a primeira, e a coleta vem depois, quando o escritório já
   está montando o documento daquela pessoa. */
const FASES: { id: string; rotulo: string }[] = [
  { id: "PAGAMENTO", rotulo: "Pagamento" },
  { id: "COLETA", rotulo: "Informações do documento" },
  { id: "CIENCIA", rotulo: "Orientação e ciência" },
  { id: "REDACAO", rotulo: "Elaboração" },
  { id: "REVISAO_IA", rotulo: "Revisão técnica" },
  { id: "AJUSTE", rotulo: "Ajustes" },
  { id: "CIENCIA_ALTERACAO", rotulo: "Sua decisão" },
  { id: "REVISAO_2", rotulo: "Conferência" },
  { id: "REVISAO_ADV", rotulo: "Revisão final" },
  { id: "APROVACAO", rotulo: "Sua aprovação" },
  { id: "ASSINATURA", rotulo: "Assinatura" },
  { id: "ENTREGUE", rotulo: "Entregue" },
];

const cx = "rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm outline-none focus:border-[#C9A84C]";
const brl = (v: any) =>
  Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const brData = (s?: string) =>
  s ? `${String(s).slice(8, 10)}/${String(s).slice(5, 7)}/${String(s).slice(0, 4)}` : "";

export default function PedidoDoCliente() {
  const { id } = useParams<{ id: string }>();
  const [pedido, setPedido] = useState<any>(null);
  const [tipo, setTipo] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [pix, setPix] = useState<any>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [observacoes, setObservacoes] = useState("");
  const [clausulas, setClausulas] = useState("");
  const [alteracao, setAlteracao] = useState("");
  const [observacao, setObservacao] = useState("");
  const [comoEnviar, setComoEnviar] = useState<"" | "DOCUMENTOS" | "FORMULARIO">("");
  const [comTimbre, setComTimbre] = useState(true);
  // As partes conferidas. Enquanto faltar alguém, o botão de
  // concluir a coleta fica travado: descobrir a falta na redação
  // custa um dia de prazo.
  const [partesOk, setPartesOk] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");
  const arquivoRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const carregar = useCallback(async () => {
    const p = await fetch(`${API}/api/v1/contratos/pedidos/${id}`).then((r) => r.json());
    setPedido(p);
    setValores(p?.dados || {});
    setObservacoes(p?.observacoes || "");
    setClausulas(p?.clausulas_extras || "");
    if (p?.modo_coleta) setComoEnviar(p.modo_coleta === "FORMULARIO" ? "FORMULARIO" : "DOCUMENTOS");
    if (p?.tipo) {
      const t = await fetch(`${API}/api/v1/contratos/tipos/${p.tipo}`).then((r) => r.json());
      setTipo(t);
    }
    fetch(`${API}/api/v1/contratos/pedidos/${id}/documentos`)
      .then((r) => r.json()).then((d) => setDocs(Array.isArray(d) ? d : [])).catch(() => {});
  }, [id]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    fetch(`${API}/api/v1/contratos/pix`).then((r) => r.json()).then(setPix).catch(() => {});
  }, []);

  const faseAtual = pedido?.fase || "COLETA";
  const indiceFase = Math.max(0, FASES.findIndex((f) => f.id === faseAtual));
  const nomeCliente = pedido?.clientes?.nome || "cliente";

  async function salvarColeta() {
    setOcupado(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/dados`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dados: valores, observacoes }),
      });
      await fetch(`${API}/api/v1/contratos/pedidos/${id}/escolhas`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clausulas_extras: clausulas,
          modo_coleta: docs.length > 0 && comoEnviar === "FORMULARIO"
            ? "MISTO" : comoEnviar || "FORMULARIO",
        }),
      });
      if (r.ok) { setAviso("Informações salvas. Pode continuar depois, se preferir."); carregar(); }
      else setAviso("Não foi possível salvar agora.");
    } finally { setOcupado(false); }
  }

  /* Salvar e terminar são botões diferentes de propósito. Quem está no
     ônibus salva e volta depois; quem terminou avisa, e só esse aviso
     manda o pedido para a redação. Sem a separação, ou o redator
     começava com meia informação, ou o cliente ficava preso numa tela
     que não avançava. */
  async function concluirColeta() {
    setOcupado(true); setAviso("");
    try {
      await fetch(`${API}/api/v1/contratos/pedidos/${id}/dados`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dados: valores, observacoes }),
      });
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/coleta-concluida`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ com_timbre: comTimbre }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setAviso(j?.detail || "Não foi possível concluir agora."); return; }
      setAviso("Recebido. O escritório começa a escrever o seu documento.");
      carregar();
    } catch { setAviso("Não foi possível falar com o servidor."); }
    finally { setOcupado(false); }
  }

  async function enviarArquivos(lista: FileList | null, rotulo = "") {
    if (!lista || lista.length === 0) return;
    setOcupado(true); setAviso("");
    try {
      const fd = new FormData();
      Array.from(lista).forEach((f) => fd.append("arquivos", f));
      const url = `${API}/api/v1/contratos/pedidos/${id}/documentos${rotulo ? `?rotulo=${encodeURIComponent(rotulo)}` : ""}`;
      const r = await fetch(url, { method: "POST", body: fd });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setAviso(j?.detail || "Não consegui receber o arquivo."); return; }
      setAviso(`${j.salvos} arquivo(s) recebido(s).`
        + (j.falhas?.length ? ` ${j.falhas.join("; ")}` : ""));
      carregar();
    } catch { setAviso("Falha ao enviar. Tente de novo."); }
    finally {
      setOcupado(false);
      if (arquivoRef.current) arquivoRef.current.value = "";
      if (cameraRef.current) cameraRef.current.value = "";
    }
  }

  async function aprovar() {
    if (!confirm("Aprovar este documento?")) return;
    setOcupado(true);
    try {
      await fetch(`${API}/api/v1/contratos/pedidos/${id}/aprovar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        // A observação vai junto da aprovação. É o recado de quem
        // aprovou mas quer registrar algo: uma dúvida, um detalhe que
        // percebeu, um aviso para o próximo documento. Não é pedido de
        // alteração, e por isso não devolve a peça para ajuste.
        body: JSON.stringify({ observacao: observacao.trim() || null }),
      });
      carregar();
    } finally { setOcupado(false); }
  }

  async function pedirAlteracao() {
    if (alteracao.trim().length < 10) {
      setAviso("Escreva o que precisa ser alterado, com o máximo de detalhe possível.");
      return;
    }
    setOcupado(true);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/alteracao`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: alteracao }),
      });
      if (r.ok) { setAlteracao(""); setAviso("Pedido de alteração enviado."); carregar(); }
    } finally { setOcupado(false); }
  }

  if (!pedido) {
    return <main className="flex min-h-screen items-center justify-center bg-[#0A1628] text-white/60">Carregando…</main>;
  }

  /* A QUALIFICAÇÃO DAS PARTES NÃO ENTRA AQUI

     `campos` traz a lista inteira do tipo, com locador e locatário
     junto. Como a caixa das partes passou a perguntar isso logo
     acima, usar a lista inteira fazia a mesma pessoa ser pedida duas
     vezes na mesma página. `campos_objeto` é a lista sem as partes,
     separada pelo catálogo, que é quem sabe o que pertence a quem. */
  const camposDoObjeto = (tipo?.campos_objeto || tipo?.campos || []) as any[];
  const obrigatoriosFaltando = camposDoObjeto
    .filter((c: any) => c.obrigatorio && !(valores[c.campo] || "").trim()).length;

  return (
    <main className="min-h-screen bg-[#0A1628] px-4 py-8 text-white">
      <div className="mx-auto max-w-2xl space-y-5">
        <header>
          {/* O protocolo é o que o cliente cita quando liga. Vem antes
              do nome do documento, e em destaque, não como rodapé. */}
          <p className="inline-block rounded-md border border-white/15 bg-white/5 px-2.5 py-1 font-mono text-[11px] tracking-wide text-white/70">
            {pedido.numero}
          </p>
          <h1 className="mt-2 text-xl font-bold">
            {pedido.tipo === "OUTRO" && pedido.servico_livre
              ? "Documento sob medida"
              : tipo?.nome || pedido.tipo}
          </h1>
          {pedido.tipo === "OUTRO" && pedido.servico_livre ? (
            <p className="mt-1 text-xs leading-relaxed text-white/60">
              Seu pedido: {pedido.servico_livre}
            </p>
          ) : (
            <p className="mt-0.5 text-xs text-white/50">{tipo?.base_legal}</p>
          )}
          <p className="mt-1 text-xs text-white/60">
            {brl(pedido.valor)} · entrega em até {pedido.prazo_entrega_horas || 24} horas
            {pedido.assinatura_digital === false && " · sem assinatura eletrônica"}
          </p>
        </header>

        {/* Em que fase está */}
        <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-4">
          <p className="mb-3 text-xs font-bold text-[#C9A24D]">Andamento do pedido</p>
          <div className="space-y-1.5">
            {FASES.map((f, i) => (
              <div key={f.id} className="flex items-center gap-2.5">
                <span className={`h-2 w-2 shrink-0 rounded-full ${
                  i < indiceFase ? "bg-[#1DB954]" : i === indiceFase ? "bg-[#C9A84C]" : "bg-white/15"}`} />
                <span className={`text-xs ${
                  i === indiceFase ? "font-bold text-white" : i < indiceFase ? "text-white/55" : "text-white/30"}`}>
                  {f.rotulo}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* A proposta trava o pedido: enquanto não houver resposta, não
            adianta o cliente preencher nada. Dizer isso evita que ele
            fique tentando avançar numa tela que não vai avançar. */}
        {pedido.proposta_status === "PENDENTE" && (
          <section className="rounded-2xl border border-[#E5A44C]/40 bg-[#E5A44C]/10 p-5">
            <p className="text-sm font-bold text-[#E5A44C]">
              Proposta em análise
            </p>
            <p className="mt-2 text-xs leading-relaxed text-white/75">
              Você propôs {brl(pedido.proposta_valor)}. O escritório
              está analisando e responde pelo seu e-mail em até um dia útil.
            </p>
          </section>
        )}

        {pedido.proposta_status === "CONTRAPROPOSTA" && (
          <section className="rounded-2xl border border-[#2D7DD2]/40 bg-[#2D7DD2]/10 p-5">
            <p className="text-sm font-bold text-[#2D7DD2]">
              O escritório respondeu
            </p>
            <p className="mt-2 text-xs leading-relaxed text-white/75">
              Você propôs {brl(pedido.proposta_valor)} e o escritório pode fazer
              por {brl(pedido.proposta_contra)}.
              {pedido.proposta_resposta ? ` ${pedido.proposta_resposta}` : ""}
            </p>
          </section>
        )}

        {pedido.proposta_status === "RECUSADA" && (
          <section className="rounded-2xl border border-white/15 bg-[#0B1F3B] p-5">
            <p className="text-sm font-bold text-white/85">
              Sobre a sua proposta
            </p>
            <p className="mt-2 text-xs leading-relaxed text-white/70">
              Desta vez o escritório não consegue realizar o serviço pelo valor
              proposto.
              {pedido.proposta_resposta ? ` ${pedido.proposta_resposta}` : ""}
            </p>
          </section>
        )}

        {aviso && (
          <p className="rounded-lg border border-[#2D7DD2]/40 bg-[#2D7DD2]/10 px-3 py-2 text-xs text-white/80">{aviso}</p>
        )}

        {/* COLETA, dois caminhos, o cliente escolhe */}
        {/* As partes vêm antes do resto da coleta. É a informação que,
            faltando, impede o contrato de ser executado depois, e é a
            única que o escritório não tem como adivinhar. */}
        {faseAtual === "COLETA" && (
          <JaTemosSeuCadastro pedidoId={String(id)} />
        )}

        {faseAtual === "COLETA" && (
          <CaixaDasPartes pedidoId={String(id)} aoCompletar={setPartesOk} />
        )}

        {faseAtual === "COLETA" && tipo && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <h2 className="text-sm font-bold text-[#C9A24D]">Informações do contrato</h2>
            <p className="mt-1 text-xs leading-relaxed text-white/50">
              Você escolhe como prefere. Os dois caminhos servem, e dá para
              misturar: mandar o que tiver em foto e digitar o resto.
            </p>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button onClick={() => setComoEnviar("DOCUMENTOS")}
                className={`rounded-xl border p-3 text-left text-xs transition ${comoEnviar === "DOCUMENTOS"
                  ? "border-[#C9A84C] bg-[#C9A84C]/10" : "border-white/15 hover:border-white/30"}`}>
                <b className="block text-white">Enviar documentos</b>
                <span className="text-white/50">PDF ou foto. Extraímos os dados.</span>
              </button>
              <button onClick={() => setComoEnviar("FORMULARIO")}
                className={`rounded-xl border p-3 text-left text-xs transition ${comoEnviar === "FORMULARIO"
                  ? "border-[#C9A84C] bg-[#C9A84C]/10" : "border-white/15 hover:border-white/30"}`}>
                <b className="block text-white">Digitar aqui</b>
                <span className="text-white/50">Sem precisar de cópia de nada.</span>
              </button>
            </div>

            {/* Caminho 1: documentos */}
            {comoEnviar === "DOCUMENTOS" && (
              <div className="mt-4 space-y-3">
                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <p className="text-xs font-bold text-white/80">O que precisamos ver</p>
                  <ul className="mt-1 space-y-0.5">
                    {(tipo.documentos || []).map((d: string, i: number) => (
                      <li key={i} className="text-[11px] text-white/55">· {d}</li>
                    ))}
                  </ul>
                </div>

                <input ref={arquivoRef} type="file" multiple
                  accept="image/*,application/pdf"
                  onChange={(e) => enviarArquivos(e.target.files)}
                  className="block w-full text-xs text-white/60 file:mr-3 file:rounded-lg file:border-0 file:bg-[#C9A84C] file:px-4 file:py-2 file:text-sm file:font-bold file:text-[#0A1628]" />

                {/* A CÂMERA TEM BOTÃO PRÓPRIO
                    O seletor acima já aceita foto, mas no celular ele
                    abre a galeria, e quem está com o papel na mão
                    precisa abrir a câmera. O `capture` faz isso. */}
                <input ref={cameraRef} type="file" multiple
                  accept="image/*" capture="environment" className="hidden"
                  onChange={(e) => enviarArquivos(e.target.files)} />
                <button type="button" onClick={() => cameraRef.current?.click()}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-2 text-xs text-white/75 transition hover:border-white/45">
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none"
                    stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                    <path d="M3 8.5A1.5 1.5 0 014.5 7h2L8 5h8l1.5 2h2A1.5 1.5 0 0121 8.5v9A1.5 1.5 0 0119.5 19h-15A1.5 1.5 0 013 17.5v-9z" />
                    <circle cx="12" cy="13" r="3.2" />
                  </svg>
                  Tirar foto agora
                </button>

                <p className="text-[10px] text-white/35">
                  Até 25 MB por arquivo. Foto tirada na hora serve.
                </p>

                {docs.length > 0 && (
                  <div className="rounded-xl border border-white/10 p-3">
                    <p className="mb-1 text-xs font-bold text-white/70">
                      Recebidos ({docs.length})
                    </p>
                    {docs.map((d) => (
                      <p key={d.id} className="truncate text-[11px] text-white/55">✓ {d.nome}</p>
                    ))}
                  </div>
                )}

                <label className="block">
                  <span className="text-xs text-white/70">
                    Como as partes combinaram? Escreva com suas palavras
                  </span>
                  <span className="block text-[10px] text-white/35">
                    valor, prazo, quem paga o quê, isso não está no documento e muda o contrato
                  </span>
                  <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)}
                    rows={4} className={`mt-1 w-full ${cx}`} />
                </label>
              </div>
            )}

            {/* Caminho 2: digitar */}
            {comoEnviar === "FORMULARIO" && (
              <div className="mt-4 space-y-3">
                {camposDoObjeto.map((c: any) => (
                  <label key={c.campo} className="block">
                    <span className="text-xs text-white/70">
                      {c.rotulo}{c.obrigatorio && <span className="text-[#C0392B]"> *</span>}
                    </span>
                    {c.porque && (
                      <span className="block text-[10px] text-white/35">por que pedimos: {c.porque}</span>
                    )}

                    {/* A ESCOLHA MAIS COMUM, DITA EM VOZ ALTA

                        Campos como índice de reajuste, prazo e garantia
                        são onde quem não é do ramo trava: a pergunta é
                        clara e a resposta não. Dizer qual é a prática
                        do mercado, e por quê, resolve em um clique o
                        que antes virava uma pergunta no chat.

                        É sugestão, não imposição: o campo continua
                        aberto, e quem tem o próprio combinado digita o
                        dele. */}
                    {c.sugestao && (
                      <span className="mt-1 block rounded-lg border border-[#2D7DD2]/30 bg-[#2D7DD2]/10 px-3 py-2">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="text-[11px] text-white/70">
                            Mais usado no mercado:
                          </span>
                          <button type="button"
                            onClick={() => setValores({ ...valores, [c.campo]: c.sugestao })}
                            className="rounded-md bg-[#2D7DD2] px-2.5 py-1 text-[11px] font-bold text-white hover:bg-[#4361EE]">
                            {c.sugestao}
                          </button>
                          {(c.opcoes || []).filter((o: string) => o !== c.sugestao).map((o: string) => (
                            <button key={o} type="button"
                              onClick={() => setValores({ ...valores, [c.campo]: o })}
                              className="rounded-md border border-white/20 px-2.5 py-1 text-[11px] text-white/70 hover:border-white/45">
                              {o}
                            </button>
                          ))}
                        </span>
                        {c.porque_sugestao && (
                          <span className="mt-1.5 block text-[10px] leading-relaxed text-white/45">
                            {c.porque_sugestao}
                          </span>
                        )}
                      </span>
                    )}

                    <input value={valores[c.campo] || ""}
                      onChange={(e) => setValores({ ...valores, [c.campo]: e.target.value })}
                      className={`mt-1 w-full ${cx}`} />
                  </label>
                ))}
                <label className="block">
                  <span className="text-xs text-white/70">
                    Como as partes combinaram? Escreva com suas palavras
                  </span>
                  <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)}
                    rows={4} className={`mt-1 w-full ${cx}`} />
                </label>
              </div>
            )}

            {/* Cláusula específica, vale nos dois caminhos */}
            {comoEnviar && (
              <label className="mt-4 block">
                <span className="text-xs text-white/70">
                  Alguma cláusula específica que você quer incluir?
                </span>
                <span className="block text-[10px] text-white/35">
                  opcional, se for algo que a lei não permita, o escritório te
                  explica antes de escrever, e você decide
                </span>
                <textarea value={clausulas} onChange={(e) => setClausulas(e.target.value)}
                  rows={3} className={`mt-1 w-full ${cx}`}
                  placeholder="Ex.: que o inquilino não pode ter animais; que a multa é reduzida se avisar com 60 dias…" />
              </label>
            )}

            {/* A ESCOLHA DO PAPEL, AGORA QUE ELA SIGNIFICA ALGO

                Esta pergunta ficava na primeira tela, ao lado da lista
                de documentos. Ali a pessoa ainda não sabia quanto
                custava nem se ia contratar, e escolher o papel de um
                documento que talvez nem exista é decisão sem contexto.
                Aqui o documento é dela e está sendo montado. */}
            {comoEnviar && (
              <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs font-bold text-white/80">
                  Como você quer o documento
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-white/50">
                  Os dois têm exatamente o mesmo valor jurídico. O timbre
                  mostra quem redigiu, e isso costuma pesar quando a outra
                  parte lê.
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <button onClick={() => setComTimbre(true)}
                    className={`rounded-xl border p-3 text-left text-xs transition ${comTimbre
                      ? "border-[#C9A84C] bg-[#C9A84C]/10" : "border-white/15 hover:border-white/30"}`}>
                    <b className="block text-white">Papel timbrado</b>
                    <span className="text-white/50">Com a identificação do escritório.</span>
                  </button>
                  <button onClick={() => setComTimbre(false)}
                    className={`rounded-xl border p-3 text-left text-xs transition ${!comTimbre
                      ? "border-[#C9A84C] bg-[#C9A84C]/10" : "border-white/15 hover:border-white/30"}`}>
                    <b className="block text-white">Folha branca</b>
                    <span className="text-white/50">Sem nenhuma identificação.</span>
                  </button>
                </div>
              </div>
            )}

            {comoEnviar && (
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button onClick={salvarColeta} disabled={ocupado}
                  className="rounded-lg border border-white/20 px-5 py-2.5 text-sm font-semibold text-white/80 hover:border-white/40 disabled:opacity-50">
                  {ocupado ? "Salvando…" : "Salvar e continuar depois"}
                </button>
                {/* O botão não trava mais por falta de informação.
                    O trabalho começa, e o que falta é cobrado depois:
                    a maior parte do contrato não depende daquele dado,
                    e segurar tudo por causa de um campo faz o cliente
                    esperar por nada. */}
                <button onClick={concluirColeta} disabled={ocupado}
                  className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-40">
                  Terminei, pode escrever
                </button>
                {!partesOk && (
                  <span className="text-xs text-white/45">
                    o escritório começa e avisa o que ainda falta
                  </span>
                )}
                {comoEnviar === "FORMULARIO" && (
                  <span className="text-xs text-white/45">
                    {obrigatoriosFaltando > 0
                      ? `${obrigatoriosFaltando} campo(s) obrigatório(s) em aberto`
                      : "todos os campos obrigatórios preenchidos"}
                  </span>
                )}
              </div>
            )}
          </section>
        )}

        {/* PAGAMENTO, a chave de verdade, não "o escritório manda depois" */}
        {faseAtual === "PAGAMENTO" && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <h2 className="text-sm font-bold text-[#C9A24D]">Pagamento por PIX</h2>
            <p className="mt-1 text-2xl font-bold text-white">{brl(pedido.valor)}</p>

            {pix && (
              <div className="mt-4 space-y-2 rounded-xl border border-white/10 bg-black/25 p-4">
                <Dado rotulo={`Chave (${pix.tipo})`} valor={pix.chave} copiavel />
                <Dado rotulo="Favorecido" valor={pix.favorecido} />
                <Dado rotulo="Banco" valor={pix.banco} />
                {pix.observacao && (
                  <p className="pt-1 text-[10px] text-white/35">{pix.observacao}</p>
                )}
              </div>
            )}

            <p className="mt-4 text-xs leading-relaxed text-white/55">
              Assim que o pagamento for confirmado, o atendimento volta a falar
              com você para pedir as informações do documento, e o prazo de{" "}
              {pedido.prazo_entrega_horas || 24} horas passa a contar dali. Você
              recebe aviso por e-mail, então pode fechar esta página.
            </p>
            <p className="mt-2 text-xs leading-relaxed text-white/40">
              Se tiver feito o PIX e a tela não mudar em algumas horas, fale com
              o escritório: a conferência do extrato é feita por uma pessoa.
            </p>
          </section>
        )}

        {/* APROVAÇÃO, minuta com marca d'água */}
        {faseAtual === "APROVACAO" && pedido.minuta && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
            <h2 className="mb-3 text-sm font-bold text-[#C9A24D]">
              Seu documento, para conferência
            </h2>
            <VisualizadorProtegido texto={pedido.minuta} quemVe={nomeCliente}
              titulo={tipo?.nome} />

            <div className="mt-5 space-y-3">
              {/* A OBSERVAÇÃO DE QUEM APROVA

                  Nem tudo o que o cliente quer dizer sobre o documento
                  é pedido de mudança. Às vezes é uma dúvida que ficou,
                  um detalhe que ele notou, um aviso para o próximo
                  contrato. Sem este campo, isso virava pedido de
                  alteração, o documento voltava para ajuste e os dois
                  lados perdiam um dia. */}
              <label className="block rounded-xl border border-white/10 p-3">
                <span className="text-xs text-white/70">
                  Quer registrar alguma observação junto com a aprovação?
                </span>
                <span className="block text-[10px] text-white/35">
                  opcional, e não atrasa nada: fica anotada no seu pedido
                </span>
                <textarea value={observacao} onChange={(e) => setObservacao(e.target.value)}
                  rows={2}
                  placeholder="Ex.: conferir o nome da rua na hora de assinar; da próxima vez quero o mesmo modelo…"
                  className={`mt-2 w-full ${cx}`} />
              </label>

              {/* APROVAR É O ÚNICO BOTÃO ATÉ AQUI

                  Antes de aprovar, o documento é só para leitura: não
                  há download, e é de propósito. Arquivo baixado antes
                  da aprovação circula, é assinado e vira contrato sem
                  que ninguém do escritório saiba que virou. Depois do
                  aprovado, o download abre. */}
              <button onClick={aprovar} disabled={ocupado}
                className="w-full rounded-lg bg-[#1DB954] py-3 text-sm font-bold text-white hover:bg-[#17a349] disabled:opacity-50">
                {ocupado ? "Registrando…" : "Aprovar este documento"}
              </button>
              <p className="text-center text-[10px] leading-relaxed text-white/35">
                O arquivo para baixar fica disponível assim que você aprovar.
              </p>

              <div className="rounded-xl border border-white/10 p-3">
                <p className="text-xs font-semibold text-white/70">
                  Precisa de alguma alteração? Escreva exatamente o que mudar:
                </p>
                <textarea value={alteracao} onChange={(e) => setAlteracao(e.target.value)}
                  rows={3} placeholder="Ex.: o prazo é de 30 meses, não 24; incluir que o condomínio é por conta do locatário…"
                  className={`mt-2 w-full ${cx}`} />
                <button onClick={pedirAlteracao} disabled={ocupado}
                  className="mt-2 rounded-lg border border-[#E5A44C]/60 px-4 py-2 text-sm font-semibold text-[#E5A44C] hover:bg-[#E5A44C]/10 disabled:opacity-50">
                  Pedir alteração
                </button>
              </div>
            </div>
          </section>
        )}

        {/* Fases em que a bola está com o escritório */}
        {["REDACAO", "REVISAO_IA", "AJUSTE", "REVISAO_ADV",
          "ASSINATURA", "ENTREGUE", "ARQUIVADO"].includes(faseAtual) && (
          <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5 text-sm text-white/70">
            {faseAtual === "REDACAO" && (
              <>
                <p>Seu documento está em elaboração.</p>
                <Pendencias pedidoId={String(id)} />
                <p className="mt-1 text-[11px] text-white/45">
                  O escritório está escrevendo a partir do que você informou.
                  Assim que a primeira versão ficar pronta, ela segue para
                  revisão e depois para a conferência final. Você é avisado
                  por e-mail quando puder ler e aprovar.
                </p>
              </>
            )}
            {faseAtual === "REVISAO_IA" && <p>O documento está em revisão técnica.</p>}
            {faseAtual === "REVISAO_2" && (
              <p>O documento está na conferência antes da leitura final do
                 escritório.</p>
            )}
            {faseAtual === "AJUSTE" && <p>Aplicando os ajustes apontados na revisão.</p>}
            {faseAtual === "REVISAO_ADV" && (
              <p>O escritório está com o seu documento para a conferência
                 final. Nada é enviado a você antes dela.</p>
            )}
            {faseAtual === "ASSINATURA" && (
              <p>{pedido.assinatura_digital === false
                ? "Preparando o arquivo para você baixar."
                : "Enviado para assinatura eletrônica. Quando todos assinarem, a cópia final vai para o seu e-mail."}</p>
            )}
            {(faseAtual === "ASSINATURA" || faseAtual === "ENTREGUE") && (
              <a href={`${API}/api/v1/contratos/pedidos/${id}/documento.doc`}
                className="mb-3 inline-flex items-center gap-2 rounded-lg bg-[#1DB954] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#17a349]">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none"
                  stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                  <path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16" />
                </svg>
                Baixar o meu documento em Word
              </a>
            )}
            {faseAtual === "ENTREGUE" && (
              <div className="space-y-2">
                <p className="text-[#1DB954]">Documento entregue.</p>
                {pedido.prazo_alteracao_ate && (
                  <p className="text-xs text-white/60">
                    Você pode pedir ajustes sem custo até{" "}
                    <b className="text-white/85">{brData(pedido.prazo_alteracao_ate)}</b>.
                    Depois dessa data o pedido é arquivado.
                  </p>
                )}
                <textarea value={alteracao} onChange={(e) => setAlteracao(e.target.value)}
                  rows={2} placeholder="precisa de algum ajuste?"
                  className={`w-full ${cx}`} />
                <button onClick={pedirAlteracao} disabled={ocupado}
                  className="rounded-lg border border-[#E5A44C]/60 px-4 py-2 text-xs font-semibold text-[#E5A44C] hover:bg-[#E5A44C]/10 disabled:opacity-50">
                  Pedir ajuste
                </button>
              </div>
            )}
            {faseAtual === "ARQUIVADO" && (
              <p>Pedido arquivado. Se precisar de algo, fale com o escritório.</p>
            )}
          </section>
        )}

        {/* A CONVERSA FICA DENTRO DO PEDIDO

            E não numa caixa de mensagens geral. Quem tem três pedidos
            abertos não consegue dizer, numa caixa única, a qual deles
            se refere a foto que acabou de mandar, e o escritório
            perde tempo perguntando. Aqui a pergunta e o anexo já
            nascem amarrados ao protocolo. */}
        {/* A PRESSA QUE APARECE NO MEIO DO CAMINHO

            A urgência era escolha da negociação e morria ali. Só que
            ela quase nunca nasce com o pedido: nasce quando a outra
            parte antecipa a assinatura, quando marcam a entrega das
            chaves, quando surge uma reunião. Sem lugar para isso, o
            cliente perguntava no chat e o atendimento improvisava. */}
        {["COLETA", "CIENCIA", "REDACAO", "REVISAO_IA", "AJUSTE", "REVISAO_ADV"]
          .includes(faseAtual) && (
          <Urgencia pedido={pedido} aoMudar={carregar} />
        )}

        {faseAtual === "CIENCIA_ALTERACAO" && (
          <SuaDecisao pedido={pedido} aoMudar={carregar} />
        )}

        <Conversa pedidoId={String(id)} aoMudar={carregar} />
      </div>
    </main>
  );
}


/* ── CONVERSA DO PEDIDO, COM FOTO E ANEXO ──────────────────────
 *
 * Três botões e nenhum menu: escrever, tirar foto, anexar arquivo.
 *
 * A foto tem entrada própria, separada do anexo, por causa do
 * `capture`: no celular ele abre a câmera direto, sem passar pela
 * galeria. Quem está com o documento na mão fotografa e manda, que é
 * o caminho real de quase todo mundo. No computador o mesmo botão
 * abre o seletor de arquivos, e nada se perde.
 *
 * O arquivo entra pela mesma porta dos documentos da coleta, então
 * aparece na pasta do pedido do lado do escritório, e a linha na
 * conversa registra o que foi mandado. Anexo sem recado vira arquivo
 * órfão que ninguém sabe por que chegou.
 */
function Conversa({ pedidoId, aoMudar }: {
  pedidoId: string; aoMudar?: () => void;
}) {
  const [falas, setFalas] = useState<any[]>([]);
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [pensando, setPensando] = useState(false);
  const [aviso, setAviso] = useState("");
  // O instante da última tecla, para a resposta não interromper quem
  // ainda está escrevendo. Ref, e não estado: muda a cada tecla e não
  // precisa redesenhar nada.
  const ultimaTecla = useRef(0);
  // Enquanto uma resposta está sendo segurada, a recarga automática
  // fica parada: senão ela traria do servidor justamente o texto que
  // estamos esperando para mostrar na hora certa.
  const segurando = useRef(false);
  const camera = useRef<HTMLInputElement>(null);
  const anexo = useRef<HTMLInputElement>(null);
  const caixa = useRef<HTMLDivElement>(null);
  const quantas = useRef(0);

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/conversa`);
      const d = await r.json();
      setFalas(Array.isArray(d) ? d : []);
    } catch { /* silêncio: a conversa não pode derrubar a tela */ }
  }, [pedidoId]);

  useEffect(() => { carregar(); }, [carregar]);
  // Recarrega a cada meio minuto. O escritório responde por aqui e o
  // cliente não deve precisar atualizar a página para ver a resposta.
  useEffect(() => {
    const t = setInterval(() => { if (!segurando.current) carregar(); }, 30000);
    return () => clearInterval(t);
  }, [carregar]);

  /* O ROLAR QUE ARRASTAVA A PÁGINA INTEIRA

     Isto era um `scrollIntoView` numa marca no fim da lista, e ele
     rola todos os ancestrais até o elemento aparecer: como a conversa
     fica no pé da página, a página inteira descia. Pior, a recarga de
     meio em meio minuto criava um array novo mesmo sem mensagem nova,
     então a tela pulava sozinha enquanto a pessoa digitava o endereço
     do imóvel lá em cima.

     Agora quem rola é a caixa da conversa, pelo próprio scrollTop,
     que não toca na página. E só quando o número de mensagens de fato
     aumentou. */
  useEffect(() => {
    if (falas.length <= quantas.current) { quantas.current = falas.length; return; }
    quantas.current = falas.length;
    const c = caixa.current;
    if (c) c.scrollTop = c.scrollHeight;
  }, [falas]);

  async function mandarTexto(msg?: string) {
    const conteudo = (msg ?? texto).trim();
    if (!conteudo) return;
    setOcupado(true); setAviso("");
    if (msg === undefined) setTexto("");

    // A fala do cliente aparece na hora, com marca própria, para ele
    // ver que saiu. A do escritório é que espera a vez.
    const minha = { id: `local-${Date.now()}`, autor: "CLIENTE",
                    texto: conteudo, criado_em: new Date().toISOString() };
    setFalas((f) => [...f, minha]);

    segurando.current = true;
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/mensagem`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ autor: "CLIENTE", texto: conteudo }),
      });
      if (!r.ok) { setAviso("Não consegui enviar. Tente de novo."); return; }
      const d = await r.json().catch(() => ({} as any));

      setOcupado(false);
      if (d?.resposta) {
        // O "digitando" e a espera. O texto já está guardado no
        // servidor; o que se segura aqui é só quando ele aparece.
        setPensando(true);
        await esperarAVez(String(d.resposta).length, ultimaTecla);
        setPensando(false);
      }
      await carregar();
      aoMudar?.();
    } catch { setAviso("Sem conexão com o servidor."); }
    finally { setOcupado(false); setPensando(false); segurando.current = false; }
  }

  async function mandarArquivos(lista: FileList | null, origem: "FOTO" | "ARQUIVO") {
    if (!lista || lista.length === 0) return;
    setOcupado(true); setAviso("");
    try {
      const fd = new FormData();
      Array.from(lista).forEach((f) => fd.append("arquivos", f));
      const r = await fetch(
        `${API}/api/v1/contratos/pedidos/${pedidoId}/documentos?rotulo=${encodeURIComponent("Enviado pela conversa")}`,
        { method: "POST", body: fd });
      const j = await r.json().catch(() => ({} as any));
      if (!r.ok) { setAviso(j?.detail || "Não consegui receber o arquivo."); return; }

      const nomes = Array.from(lista).map((f) => f.name).join(", ");
      // O recado vai junto, e é ele que destrava o relógio quando o
      // pedido está parado esperando informação.
      await mandarTexto(origem === "FOTO"
        ? `Enviei ${lista.length === 1 ? "uma foto" : `${lista.length} fotos`}: ${nomes}`
        : `Enviei ${lista.length === 1 ? "um arquivo" : `${lista.length} arquivos`}: ${nomes}`);
      if (j.falhas?.length) setAviso(j.falhas.join("; "));
      else setAviso(`${j.salvos} arquivo(s) recebido(s).`);
      aoMudar?.();
    } catch { setAviso("Falha ao enviar. Tente de novo."); }
    finally {
      setOcupado(false);
      if (camera.current) camera.current.value = "";
      if (anexo.current) anexo.current.value = "";
    }
  }

  const quando = (s?: string) => {
    if (!s) return "";
    const d = new Date(s);
    return isNaN(d.getTime()) ? "" : d.toLocaleString("pt-BR",
      { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
      <h2 className="text-sm font-bold text-[#C9A24D]">Conversa deste pedido</h2>
      <p className="mt-1 text-xs leading-relaxed text-white/50">
        Tudo o que for tratado aqui fica guardado junto do protocolo. Pode
        escrever, fotografar um documento ou anexar um arquivo.
      </p>

      <div ref={caixa}
        className="mt-4 max-h-[46vh] space-y-2 overflow-y-auto rounded-xl bg-[#0A1628] p-3">
        {falas.length === 0 && (
          <p className="py-6 text-center text-[11px] text-white/35">
            Nenhuma mensagem ainda. Escreva abaixo se precisar de algo.
          </p>
        )}
        {falas.map((f: any) => {
          const meu = String(f.autor).toUpperCase() === "CLIENTE";
          return (
            <div key={f.id}
              className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${meu
                ? "ml-auto bg-[#C9A84C]/15 text-white/90"
                : "bg-white/5 text-white/85"}`}>
              <p className="whitespace-pre-line">{f.texto}</p>
              <p className="mt-1 text-[10px] text-white/35">
                {meu ? "você" : "escritório"} · {quando(f.criado_em)}
              </p>
            </div>
          );
        })}
        {pensando && (
          <p className="text-[11px] text-white/35">digitando…</p>
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <textarea value={texto}
          onChange={(e) => { setTexto(e.target.value); ultimaTecla.current = Date.now(); }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); mandarTexto(); }
          }}
          rows={1} placeholder="escreva aqui"
          className={`flex-1 resize-none ${cx}`} />
        <button onClick={() => mandarTexto()} disabled={ocupado || !texto.trim()}
          className="rounded-lg bg-[#C9A84C] px-4 text-sm font-bold text-[#0A1628] disabled:opacity-40">
          Enviar
        </button>
      </div>

      {/* As entradas de arquivo ficam escondidas: o que a pessoa vê é
          um botão com nome de gente, não o seletor cru do navegador. */}
      <input ref={camera} type="file" accept="image/*" capture="environment"
        multiple className="hidden"
        onChange={(e) => mandarArquivos(e.target.files, "FOTO")} />
      <input ref={anexo} type="file" accept="image/*,application/pdf"
        multiple className="hidden"
        onChange={(e) => mandarArquivos(e.target.files, "ARQUIVO")} />

      <div className="mt-2 flex flex-wrap gap-2">
        <button onClick={() => camera.current?.click()} disabled={ocupado}
          className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-2 text-xs text-white/75 transition hover:border-white/45 disabled:opacity-40">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none"
            stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M3 8.5A1.5 1.5 0 014.5 7h2L8 5h8l1.5 2h2A1.5 1.5 0 0121 8.5v9A1.5 1.5 0 0119.5 19h-15A1.5 1.5 0 013 17.5v-9z" />
            <circle cx="12" cy="13" r="3.2" />
          </svg>
          Tirar foto
        </button>
        <button onClick={() => anexo.current?.click()} disabled={ocupado}
          className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-2 text-xs text-white/75 transition hover:border-white/45 disabled:opacity-40">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none"
            stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M20 11.5l-7.8 7.8a4.5 4.5 0 01-6.4-6.4l8.1-8.1a3 3 0 014.2 4.2l-8.1 8.1a1.5 1.5 0 01-2.1-2.1l7.4-7.4" />
          </svg>
          Anexar documento
        </button>
        <span className="self-center text-[10px] text-white/35">
          PDF ou imagem, até 25 MB por arquivo.
        </span>
      </div>

      {aviso && <p className="mt-2 text-[11px] text-[#E5A44C]">{aviso}</p>}
    </section>
  );
}

function Dado({ rotulo, valor, copiavel }:
  { rotulo: string; valor: string; copiavel?: boolean }) {
  const [copiou, setCopiou] = useState(false);
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 shrink-0 text-[11px] text-white/40">{rotulo}</span>
      <span className="flex-1 truncate text-sm font-semibold text-white">{valor}</span>
      {copiavel && (
        <button
          onClick={() => {
            navigator.clipboard?.writeText(valor);
            setCopiou(true); setTimeout(() => setCopiou(false), 2000);
          }}
          className="shrink-0 rounded-lg border border-white/20 px-2 py-1 text-[10px] text-white/70 hover:border-white/40">
          {copiou ? "copiado" : "copiar"}
        </button>
      )}
    </div>
  );
}


/* ── AS PARTES DO CONTRATO ─────────────────────────────────────
 *
 * Todo contrato tem pelo menos duas partes, e antes só uma era
 * perguntada de verdade: os dados da outra ficavam soltos nos campos
 * livres, cada tipo de contrato com um nome diferente, e a falta só
 * aparecia na hora de redigir.
 *
 * A caixa faz três coisas que a tela antiga não fazia:
 *
 * Preenche sozinha o que já se sabe. A parte do cliente nasce com o
 * cadastro dele. Pedir de novo o que a pessoa já informou é a forma
 * mais rápida de fazê-la desistir no meio.
 *
 * Confere o CPF enquanto ela digita, e não depois de salvar. O aviso
 * chega no momento em que ela ainda está olhando o campo.
 *
 * Diz o que falta, com nome e sobrenome. "Faltam informações" não
 * ajuda ninguém; "falta o CPF do fiador e o endereço do locatário"
 * resolve em um minuto.
 */
function CaixaDasPartes({ pedidoId, aoCompletar }: {
  pedidoId: string; aoCompletar: (completo: boolean) => void;
}) {
  const [estado, setEstado] = useState<any>(null);
  const [partes, setPartes] = useState<any[]>([]);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [cpfs, setCpfs] = useState<Record<number, any>>({});

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/partes`);
      const j = await r.json();
      setEstado(j); setPartes(j.partes || []);
      aoCompletar(Boolean(j.completo));
    } catch { /* a tela continua utilizável sem isto */ }
  }, [pedidoId, aoCompletar]);
  useEffect(() => { carregar(); }, [carregar]);

  function mudar(i: number, campo: string, valor: string) {
    setPartes((ps) => ps.map((p, j) => (j === i ? { ...p, [campo]: valor } : p)));
  }

  /* A conferência sai do campo do CPF, quando a pessoa termina de
     digitar. Fazer a cada tecla seria uma consulta por caractere. */
  async function conferirCpf(i: number) {
    const p = partes[i];
    const cpf = (p?.cpf_cnpj || "").replace(/\D/g, "");
    if (cpf.length !== 11 && cpf.length !== 14) { setCpfs((c) => ({ ...c, [i]: null })); return; }
    setCpfs((c) => ({ ...c, [i]: { carregando: true } }));
    try {
      const r = await fetch(`${API}/api/v1/cpf/conferir`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cpf, nome: p?.nome, nascimento: p?.nascimento }),
      });
      const j = await r.json();
      setCpfs((c) => ({ ...c, [i]: j }));
    } catch { setCpfs((c) => ({ ...c, [i]: null })); }
  }

  async function salvar() {
    setSalvando(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/partes`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ partes }),
      });
      const j = await r.json();
      setEstado(j); setPartes(j.partes || partes);
      aoCompletar(Boolean(j.completo));
      setAviso(j.completo
        ? "Tudo certo com as partes. Pode seguir."
        : j.recado || "Ainda falta informação.");
    } catch { setAviso("Não consegui salvar agora."); }
    finally { setSalvando(false); }
  }

  if (!estado) return null;

  const campos: [string, string, string][] = [
    ["nome", "Nome completo", "como está no documento"],
    ["cpf_cnpj", "CPF ou CNPJ", "só números"],
    ["endereco", "Endereço completo", "rua, número, bairro, cidade e estado"],
    ["estado_civil", "Estado civil", "muda a assinatura exigida"],
    ["profissao", "Profissão", ""],
    ["email", "E-mail", "é para onde vai o contrato assinado"],
    ["telefone", "Telefone", ""],
  ];

  return (
    <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
      <h2 className="text-sm font-bold text-[#C9A24D]">Quem assina o contrato</h2>
      <p className="mt-1 text-xs leading-relaxed text-white/55">
        Um contrato precisa identificar as duas partes com precisão. É isso
        que permite cobrar, executar ou provar o combinado se um dia
        precisar. O que o escritório já sabe está preenchido.
      </p>

      <div className="mt-4 space-y-4">
        {partes.map((p, i) => {
          const conf = cpfs[i];
          return (
            <div key={p.papel || i} className="rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-bold capitalize text-white">
                  {String(p.papel || "parte").replaceAll("_", " ")}
                </p>
                {p.do_cliente && (
                  <span className="rounded-full bg-[#2D7DD2]/20 px-2.5 py-0.5 text-[10px] font-bold text-[#2D7DD2]">
                    você, do seu cadastro
                  </span>
                )}
                {(p.falta || []).length > 0 && (
                  <span className="ml-auto text-[11px] text-[#E5A44C]">
                    falta {(p.falta || []).join(", ")}
                  </span>
                )}
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {campos.map(([campo, rotulo, ajuda]) => (
                  <label key={campo} className={campo === "endereco" ? "sm:col-span-2" : ""}>
                    <span className="text-xs text-white/70">{rotulo}</span>
                    {ajuda && <span className="block text-[10px] text-white/35">{ajuda}</span>}
                    <input
                      value={p[campo] || ""}
                      onChange={(e) => mudar(i, campo, e.target.value)}
                      onBlur={campo === "cpf_cnpj" ? () => conferirCpf(i) : undefined}
                      className={`mt-1 w-full ${cx}`} />
                  </label>
                ))}
              </div>

              {/* O QUE A RECEITA DISSE
                  Três respostas possíveis, e cada uma diz uma coisa
                  diferente. Dizer "conferido na Receita" quando só os
                  dígitos foram conferidos seria mentir para quem vai
                  assinar o documento. */}
              {conf?.carregando && (
                <p className="mt-2 text-[11px] text-white/45">conferindo o CPF…</p>
              )}
              {conf && !conf.carregando && conf.ok === false && (
                <p className="mt-2 rounded-lg border border-[#C0392B]/40 bg-[#C0392B]/10 px-3 py-2 text-[11px] leading-relaxed text-white/85">
                  {conf.erro}
                  {conf.nome_receita && (
                    <span className="mt-1 block text-white/55">
                      Na Receita este CPF está em nome de {conf.nome_receita}.
                    </span>
                  )}
                </p>
              )}
              {conf && !conf.carregando && conf.ok && conf.conferido && (
                <p className="mt-2 text-[11px] text-[#1DB954]">
                  CPF conferido na Receita, situação regular.
                </p>
              )}
              {conf && !conf.carregando && conf.ok && !conf.conferido && (
                <p className="mt-2 text-[11px] text-white/45">{conf.aviso}</p>
              )}
            </div>
          );
        })}
      </div>

      {aviso && (
        <p className={`mt-4 rounded-lg px-3 py-2 text-xs leading-relaxed ${
          estado.completo
            ? "border border-[#1DB954]/40 bg-[#1DB954]/10 text-white/85"
            : "border border-[#E5A44C]/40 bg-[#E5A44C]/10 text-white/85"}`}>
          {aviso}
        </p>
      )}

      <button onClick={salvar} disabled={salvando}
        className="mt-4 rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
        {salvando ? "Salvando…" : "Salvar informações das partes"}
      </button>
      <p className="mt-2 text-[11px] text-white/35">
        Pode salvar incompleto e voltar depois: o que você digitou fica
        guardado.
      </p>
    </section>
  );
}


/* ── O QUE AINDA FALTA ─────────────────────────────────────────
 *
 * Duas listas, e a separação entre elas é o ponto.
 *
 * O que é indispensável segura a entrega e para o relógio. Dizer isso
 * com clareza é mais honesto do que prometer um prazo que depende de
 * algo que o escritório não tem: o cliente entende que a bola está com
 * ele, e entende por quê.
 *
 * O que é complementar aparece em tom menor, com o aviso de que pode
 * chegar depois. Tratar as duas coisas com a mesma urgência faria o
 * cliente ignorar as duas.
 */
function Pendencias({ pedidoId }: { pedidoId: string }) {
  const [pend, setPend] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/pendencias`)
      .then((r) => r.json()).then(setPend).catch(() => {});
  }, [pedidoId]);

  if (!pend || (pend.itens || []).length === 0) return null;

  return (
    <div className="mt-3 space-y-3 text-left">
      {(pend.obrigatorias || []).length > 0 && (
        <div className="rounded-xl border border-[#E5A44C]/40 bg-[#E5A44C]/10 p-4">
          <p className="text-xs font-bold text-[#E5A44C]">
            Falta uma informação para concluir
          </p>
          <ul className="mt-2 space-y-1">
            {pend.obrigatorias.map((i: any, k: number) => (
              <li key={k} className="text-xs text-white/80">
                • {i.rotulo}{i.papel ? ` do ${String(i.papel).replaceAll("_", " ")}` : ""}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] leading-relaxed text-white/60">
            O documento já está sendo escrito, mas a entrega espera por isso.
            Assim que você informar, o prazo volta a correr e o escritório
            complementa o texto.
          </p>
        </div>
      )}

      {(pend.complementares || []).length > 0 && (
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs font-semibold text-white/70">
            Pode enviar depois, sem pressa
          </p>
          <ul className="mt-2 space-y-1">
            {pend.complementares.map((i: any, k: number) => (
              <li key={k} className="text-xs text-white/55">• {i.rotulo}</li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-white/40">
            Isso deixa o documento mais completo e não segura nada. Dá para
            mandar a qualquer momento antes de ele ficar pronto.
          </p>
        </div>
      )}
    </div>
  );
}


/* ── ADIANTAR A ENTREGA ────────────────────────────────────────
 *
 * Três estados, e a diferença entre o segundo e o terceiro é o que
 * protege o escritório de prometer prazo sem ter recebido.
 *
 *   nada pedido        um convite discreto, com o valor calculado no
 *                      servidor. O cliente vê o número antes de
 *                      decidir qualquer coisa.
 *   pedido, não pago   o PIX na tela e um botão de avisar que pagou.
 *                      O prazo continua o mesmo, e a tela diz isso
 *                      com todas as letras.
 *   confirmado         a entrega passa a 6 horas e a caixa some.
 *
 * O botão "já paguei" não muda prazo nenhum, e é de propósito: quem
 * muda é o escritório, depois de olhar o extrato.
 */
function Urgencia({ pedido, aoMudar }: { pedido: any; aoMudar: () => void }) {
  const [orcamento, setOrcamento] = useState<any>(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");
  const [txid, setTxid] = useState("");

  const pedida = Boolean(pedido?.urgencia_pedida_em);
  const jaUrgente = Boolean(pedido?.urgente);

  async function orcar() {
    setOcupado(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedido.id}/urgencia`);
      /* FALHA CALADA É PIOR DO QUE FALHA DITA

         Antes isto lia o corpo da resposta sem olhar o código HTTP.
         Com o servidor respondendo 404, o JSON de erro virava
         "orçamento" e a tela trocava de estado mostrando um valor
         vazio: do lado de quem clicou, o botão simplesmente não fazia
         nada. Agora cada desfecho tem uma frase. */
      if (!r.ok) {
        setAviso(r.status === 404
          ? "Este pedido não foi encontrado. Atualize a página e tente de novo."
          : "Não consegui calcular agora. Tente de novo em instantes, ou peça pela conversa aqui embaixo.");
        return;
      }
      const j = await r.json().catch(() => null);
      if (!j) { setAviso("Não consegui calcular agora. Tente de novo."); return; }
      if (j.ja_e_urgente || j.tarde_demais) { setAviso(j.mensagem); return; }
      if (!j.valor) {
        setAviso("Não consegui calcular agora. Peça pela conversa aqui embaixo que o escritório responde.");
        return;
      }
      setOrcamento(j);
      aoMudar();
    } catch {
      setAviso("Sem conexão com o servidor. Tente de novo em instantes.");
    } finally { setOcupado(false); }
  }

  async function avisarQuePagou() {
    setOcupado(true); setAviso("");
    try {
      const r = await fetch(
        `${API}/api/v1/contratos/pedidos/${pedido.id}/urgencia/paguei`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ txid: txid.trim() }) });
      if (!r.ok) {
        setAviso("Não consegui registrar agora. Avise pela conversa aqui embaixo, que o escritório confere igual.");
        return;
      }
      const j = await r.json().catch(() => ({} as any));
      setAviso(j?.mensagem || "Aviso registrado.");
      aoMudar();
    } catch { setAviso("Sem conexão. Tente de novo em instantes."); }
    finally { setOcupado(false); }
  }

  if (jaUrgente) {
    return (
      <section className="rounded-2xl border border-[#1DB954]/40 bg-[#1DB954]/10 p-5">
        <p className="text-sm font-bold text-[#1DB954]">Entrega acelerada</p>
        <p className="mt-1 text-xs leading-relaxed text-white/70">
          Este pedido está com entrega em até 6 horas. Se as 6 horas já
          passaram desde o pedido, a entrega sai nas próximas 1 a 2 horas.
        </p>
      </section>
    );
  }

  const valor = orcamento?.valor ?? pedido?.urgencia_valor;
  const pix = orcamento?.pix;

  return (
    <section className="rounded-2xl border border-white/10 bg-[#0B1F3B] p-5">
      <h2 className="text-sm font-bold text-[#C9A24D]">Precisa para hoje?</h2>

      {!pedida && !orcamento ? (
        <>
          <p className="mt-1 text-xs leading-relaxed text-white/55">
            Dá para adiantar a entrega para até 6 horas, com um acréscimo.
            Veja o valor antes de decidir, sem compromisso.
          </p>
          <button onClick={orcar} disabled={ocupado}
            className="mt-3 rounded-lg border border-[#C9A84C]/60 px-4 py-2 text-xs font-semibold text-[#C9A84C] hover:bg-[#C9A84C]/10 disabled:opacity-50">
            {ocupado ? "Calculando…" : "Ver quanto custa adiantar"}
          </button>
        </>
      ) : (
        <>
          <p className="mt-1 text-xs leading-relaxed text-white/55">
            Acréscimo de{" "}
            <b className="text-white">{brl(valor)}</b> para a entrega em até 6
            horas. Pague pelo PIX abaixo e avise aqui.
          </p>

          {pix && (
            <div className="mt-3 space-y-2 rounded-xl border border-white/10 bg-black/20 p-4">
              <Dado rotulo="Chave PIX" valor={String(pix.chave || "")} copiavel />
              <Dado rotulo="Favorecido" valor={String(pix.nome || "")} />
              <Dado rotulo="Valor" valor={brl(valor)} />
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input value={txid} onChange={(e) => setTxid(e.target.value)}
              placeholder="código do comprovante, se tiver"
              className={`flex-1 ${cx}`} />
            <button onClick={avisarQuePagou} disabled={ocupado}
              className="rounded-lg bg-[#C9A84C] px-4 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
              {ocupado ? "Registrando…" : "Já paguei"}
            </button>
          </div>

          <p className="mt-2 text-[11px] leading-relaxed text-white/40">
            O prazo muda assim que o escritório conferir o pagamento. Até lá,
            vale o prazo combinado no pedido.
          </p>
        </>
      )}

      {aviso && <p className="mt-3 text-[11px] text-[#E5A44C]">{aviso}</p>}
    </section>
  );
}


/* ── O QUE JÁ ESTÁ GUARDADO ────────────────────────────────────
 *
 * O cliente que volta para o segundo serviço começava do zero: outra
 * vez o nome, o CPF, o endereço, e outra vez o documento de
 * identidade que já estava na plataforma havia meses. Do lado dele
 * isso não parece cuidado, parece que ninguém guardou nada.
 *
 * Esta caixa só aparece para quem já passou por aqui, e ela pede
 * CONFIRMAÇÃO, não digitação. Os documentos reaproveitados aparecem
 * nomeados, com a origem, porque o cliente tem direito de saber o que
 * o escritório está usando do que ele mandou antes, e de dizer que
 * aquele não serve para este caso.
 */
function JaTemosSeuCadastro({ pedidoId }: { pedidoId: string }) {
  const [dados, setDados] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/conhecido`)
      .then((r) => r.json()).then(setDados).catch(() => {});
  }, [pedidoId]);

  if (!dados?.conhecido || !dados?.ja_usou_antes) return null;

  const cad = dados.cadastro || {};
  const docs = (dados.documentos || []) as any[];
  const aproveitados = docs.filter((d) => !d.envelhecido);
  const velhos = docs.filter((d) => d.envelhecido);

  const linhas: [string, string][] = [
    ["Nome", cad.nome], ["CPF ou CNPJ", cad.cpf_cnpj],
    ["Endereço", cad.endereco], ["Estado civil", cad.estado_civil],
    ["Profissão", cad.profissao], ["E-mail", cad.email],
    ["Telefone", cad.telefone],
  ].filter(([, v]) => Boolean(v)) as [string, string][];

  return (
    <section className="rounded-2xl border border-[#2D7DD2]/40 bg-[#2D7DD2]/10 p-5">
      <h2 className="text-sm font-bold text-[#7FB2E5]">
        Você já é cliente, então já temos os seus dados
      </h2>
      <p className="mt-1 text-xs leading-relaxed text-white/60">
        Confira abaixo. Se estiver tudo certo, é só seguir. Se alguma coisa
        mudou, corrija no bloco das partes, logo abaixo, que o cadastro é
        atualizado junto.
      </p>

      {linhas.length > 0 && (
        <div className="mt-3 grid gap-1.5 rounded-xl border border-white/10 bg-black/20 p-4 sm:grid-cols-2">
          {linhas.map(([rotulo, valor]) => (
            <p key={rotulo} className="text-[11px] text-white/55">
              <span className="text-white/35">{rotulo}: </span>
              <span className="text-white/85">{valor}</span>
            </p>
          ))}
        </div>
      )}

      {aproveitados.length > 0 && (
        <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs font-bold text-white/80">
            Documentos que você já enviou, aproveitados neste pedido
          </p>
          <ul className="mt-1.5 space-y-0.5">
            {aproveitados.map((d) => (
              <li key={d.id} className="text-[11px] text-white/55">
                ✓ {d.nome}
                {d.de ? <span className="text-white/30"> · do {d.de}</span> : null}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] leading-relaxed text-white/40">
            Você não precisa mandar de novo. Se algum deles não servir para
            este contrato, é só avisar na conversa aqui embaixo.
          </p>
        </div>
      )}

      {velhos.length > 0 && (
        <div className="mt-3 rounded-xl border border-[#E5A44C]/40 bg-[#E5A44C]/10 p-4">
          <p className="text-xs font-bold text-[#E5A44C]">
            Estes podem estar desatualizados
          </p>
          <ul className="mt-1.5 space-y-0.5">
            {velhos.map((d) => (
              <li key={d.id} className="text-[11px] text-white/70">· {d.nome}</li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] leading-relaxed text-white/50">
            Foram enviados há mais de um ano. Comprovante de endereço e
            certidão costumam pedir versão recente, então não usamos estes
            automaticamente. Se ainda valem, mande de novo pela conversa.
          </p>
        </div>
      )}
    </section>
  );
}


/* ── A DECISÃO QUE É DO CLIENTE ────────────────────────────────
 *
 * A revisão encontrou um ponto em que o que ele pediu contraria a lei
 * ou a jurisprudência. O escritório tem duas saídas honestas, e
 * nenhuma delas é decidir sozinho: escrever do jeito que ele pediu,
 * com a ciência do risco registrada, ou adequar.
 *
 * A tela mostra os dois caminhos lado a lado, com o mesmo peso. Pôr um
 * dos botões em destaque seria escolher por ele com o desenho, que é
 * a forma silenciosa de tirar a decisão de quem a tem.
 */
function SuaDecisao({ pedido, aoMudar }: { pedido: any; aoMudar: () => void }) {
  const [obs, setObs] = useState<Record<string, string>>({});
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");

  const pendentes = (pedido?.decisoes_pendentes || []) as any[];
  if (pendentes.length === 0) return null;

  async function decidir(chave: string, escolha: "MANTER" | "ADEQUAR") {
    setOcupado(chave + escolha); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedido.id}/decisao`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chave, escolha, observacao: obs[chave] || "" }),
      });
      if (!r.ok) { setErro("Não consegui registrar. Tente de novo."); return; }
      aoMudar();
    } catch { setErro("Sem conexão com o servidor."); }
    finally { setOcupado(""); }
  }

  return (
    <section className="rounded-2xl border border-[#E5A44C]/50 bg-[#E5A44C]/10 p-5">
      <h2 className="text-sm font-bold text-[#E5A44C]">
        Precisamos de uma decisão sua
      </h2>
      <p className="mt-1 text-xs leading-relaxed text-white/65">
        Na revisão apareceu {pendentes.length === 1 ? "um ponto" : `${pendentes.length} pontos`}
        {" "}em que o que você pediu vai contra a lei ou contra o entendimento
        dos tribunais. Quem decide é você, e a sua escolha fica registrada.
        O prazo fica parado até você responder.
      </p>

      <div className="mt-4 space-y-4">
        {pendentes.map((d: any) => (
          <div key={d.chave} className="rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-bold text-white">{d.clausula}</p>
            <p className="mt-1.5 text-xs leading-relaxed text-white/70">
              {d.o_que_a_lei_diz}
            </p>
            {d.sugestao && (
              <p className="mt-1.5 text-[11px] leading-relaxed text-white/45">
                Como ficaria adequado: {d.sugestao}
              </p>
            )}

            <textarea value={obs[d.chave] || ""}
              onChange={(e) => setObs({ ...obs, [d.chave]: e.target.value })}
              rows={2} placeholder="quer acrescentar alguma coisa? (opcional)"
              className={`mt-3 w-full ${cx}`} />

            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <button onClick={() => decidir(d.chave, "MANTER")}
                disabled={Boolean(ocupado)}
                className="rounded-lg border border-white/25 px-4 py-2.5 text-xs font-semibold text-white/85 transition hover:border-white/50 disabled:opacity-40">
                {ocupado === d.chave + "MANTER" ? "Registrando…"
                  : "Manter como pedi, ciente do risco"}
              </button>
              <button onClick={() => decidir(d.chave, "ADEQUAR")}
                disabled={Boolean(ocupado)}
                className="rounded-lg border border-white/25 px-4 py-2.5 text-xs font-semibold text-white/85 transition hover:border-white/50 disabled:opacity-40">
                {ocupado === d.chave + "ADEQUAR" ? "Registrando…"
                  : "Adequar à lei"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {erro && <p className="mt-3 text-[11px] text-[#ff9a8f]">{erro}</p>}
    </section>
  );
}
