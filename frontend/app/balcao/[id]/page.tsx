"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import VisualizadorProtegido from "../../components/VisualizadorProtegido";

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
  { id: "REVISAO_ADV", rotulo: "Revisão do advogado" },
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
  const [comoEnviar, setComoEnviar] = useState<"" | "DOCUMENTOS" | "FORMULARIO">("");
  const [comTimbre, setComTimbre] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");
  const arquivoRef = useRef<HTMLInputElement>(null);

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
    finally { setOcupado(false); if (arquivoRef.current) arquivoRef.current.value = ""; }
  }

  async function aprovar() {
    if (!confirm("Aprovar este documento?")) return;
    setOcupado(true);
    try {
      await fetch(`${API}/api/v1/contratos/pedidos/${id}/aprovar`, { method: "POST" });
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

  const obrigatoriosFaltando = (tipo?.campos || [])
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
              Você propôs {brl(pedido.proposta_valor)}. Um advogado do escritório
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
                {(tipo.campos || []).map((c: any) => (
                  <label key={c.campo} className="block">
                    <span className="text-xs text-white/70">
                      {c.rotulo}{c.obrigatorio && <span className="text-[#C0392B]"> *</span>}
                    </span>
                    {c.porque && (
                      <span className="block text-[10px] text-white/35">por que pedimos: {c.porque}</span>
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
                <button onClick={concluirColeta} disabled={ocupado}
                  className="rounded-lg bg-[#C9A84C] px-5 py-2.5 text-sm font-bold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-50">
                  Terminei, pode escrever
                </button>
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
              <button onClick={aprovar} disabled={ocupado}
                className="w-full rounded-lg bg-[#1DB954] py-3 text-sm font-bold text-white hover:bg-[#17a349] disabled:opacity-50">
                {pedido.assinatura_digital === false
                  ? "Aprovar e receber o arquivo"
                  : "Aprovar e seguir para assinatura"}
              </button>

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
            {faseAtual === "REDACAO" && <p>Seu documento está sendo elaborado.</p>}
            {faseAtual === "REVISAO_IA" && <p>O documento está em revisão técnica.</p>}
            {faseAtual === "AJUSTE" && <p>Aplicando os ajustes apontados na revisão.</p>}
            {faseAtual === "REVISAO_ADV" && (
              <p>Na mesa do advogado para revisão final. Nada é enviado a você
                 antes dessa conferência.</p>
            )}
            {faseAtual === "ASSINATURA" && (
              <p>{pedido.assinatura_digital === false
                ? "Preparando o arquivo para você baixar."
                : "Enviado para assinatura eletrônica. Quando todos assinarem, a cópia final vai para o seu e-mail."}</p>
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
      </div>
    </main>
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
