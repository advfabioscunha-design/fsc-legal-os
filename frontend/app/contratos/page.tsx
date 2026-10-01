"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import PainelLayout from "../components/PainelLayout";
import VisualizadorProtegido from "../components/VisualizadorProtegido";
import { baixarComToken } from "../../lib/baixar";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* CONTRATOS — o balcão, e só o balcão.

   Esta tela já foi a fase 1 dos casos judiciais. Não é mais: aquilo
   virou "Atendimento". Aqui só existem pedidos de redação de contrato,
   que são outro serviço, com outro rito, outro preço e outro prazo.
   Quem pede um contrato de locação não tem processo, não tem prazo
   processual e não deve aparecer na mesma esteira de quem tem.

   As colunas são as fases do pedido, na ordem em que acontecem. O que
   depende do escritório fica em destaque; o que depende do cliente fica
   apagado, porque não adianta cobrar de quem já fez a sua parte. */

const COLUNAS = [
  { f: "QUALIFICACAO", l: "Qualificação", cor: "#8899AA", cliente: true },
  { f: "PROPOSTA", l: "Proposta", cor: "#C9A24D", cliente: true },
  { f: "PAGAMENTO", l: "Pagamento", cor: "#E5A44C", cliente: true },
  { f: "COLETA", l: "Coleta", cor: "#8899AA", cliente: true },
  { f: "CIENCIA", l: "Ciência", cor: "#E5A44C", cliente: true },
  { f: "REDACAO", l: "Redação", cor: "#2D7DD2", cliente: false },
  { f: "REVISAO_IA", l: "Revisão", cor: "#2D7DD2", cliente: false },
  { f: "AJUSTE", l: "Ajuste", cor: "#2D7DD2", cliente: false },
  { f: "CIENCIA_ALTERACAO", l: "Decisão do cliente", cor: "#E5A44C", cliente: true },
  { f: "REVISAO_2", l: "Conferência", cor: "#2D7DD2", cliente: false },
  { f: "REVISAO_ADV", l: "Revisão do advogado", cor: "#C0392B", cliente: false },
  { f: "APROVACAO", l: "Enviado ao cliente", cor: "#E5A44C", cliente: true },
  { f: "ASSINATURA", l: "Assinatura", cor: "#16A085", cliente: true },
  { f: "ENTREGUE", l: "Concluído", cor: "#1DB954", cliente: false },
];

const btn = "rounded-lg px-3 py-1.5 text-xs font-bold transition disabled:opacity-40";
const inp = "w-full rounded-lg border border-white/15 bg-[#0B1F3B] px-3 py-2 text-sm text-white outline-none focus:border-[#C9A24D]";
const brl = (v: any) => `R$ ${Number(v || 0).toFixed(2)}`;

export default function BalcaoOperador() {
  const [pedidos, setPedidos] = useState<any[]>([]);
  const [aberto, setAberto] = useState<string | null>(null);
  const [verArquivo, setVerArquivo] = useState(false);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos`);
      const d = await r.json();
      setPedidos(Array.isArray(d) ? d : []);
    } catch { setPedidos([]); }
    finally { setCarregando(false); }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const daColuna = (f: string) => pedidos.filter((p) => p.fase === f);
  const arquivados = pedidos.filter((p) => p.fase === "ARQUIVADO");

  return (
    <PainelLayout titulo="Contratos">
      <div className="space-y-4 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-xs text-white/50">
            Pedidos de redação de contrato. Serviço separado dos casos judiciais —
            os casos ficam em <b className="text-white/70">Atendimento</b>.
          </p>
          <div className="ml-auto flex gap-2">
            <button onClick={() => setVerArquivo(!verArquivo)}
              className={`${btn} border border-white/15 text-white/60 hover:text-white`}>
              {verArquivo ? "Ver a esteira" : `Arquivo (${arquivados.length})`}
            </button>
            <button onClick={carregar}
              className={`${btn} border border-white/15 text-white/60 hover:text-white`}>
              Atualizar
            </button>
          </div>
        </div>

        <PropostasPendentes recarregar={carregar} />
        <Desarquivamentos recarregar={carregar} />

        {carregando && <p className="text-xs text-white/40">Carregando…</p>}

        {verArquivo ? (
          <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
            <h3 className="mb-3 text-sm font-bold text-[#C9A24D]">Arquivo</h3>
            {arquivados.length === 0 && (
              <p className="text-xs text-white/40">Nada arquivado ainda.</p>
            )}
            <div className="space-y-1">
              {arquivados.map((p) => (
                <button key={p.id} onClick={() => setAberto(p.id)}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs text-white/70 hover:bg-white/5">
                  <span className="font-mono text-white/40">{p.numero}</span>
                  <span className="flex-1 truncate">{p.clientes?.nome ?? "sem cadastro"}</span>
                  <span className="text-white/35">{p.tipo}</span>
                  <span className="text-white/50">{brl(p.valor)}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-4">
            {COLUNAS.map((c) => {
              const lista = daColuna(c.f);
              return (
                <div key={c.f} className="w-64 shrink-0">
                  <div className="mb-2 flex items-center gap-2">
                    <i className="inline-block h-2 w-2 rounded-full" style={{ background: c.cor }} />
                    <h3 className="text-xs font-bold text-white/80">{c.l}</h3>
                    <span className="ml-auto rounded-full bg-white/10 px-2 text-[10px] font-bold text-white/60">
                      {lista.length}
                    </span>
                  </div>
                  <div className={`min-h-24 space-y-2 rounded-xl border border-white/10 p-2
                    ${c.cliente ? "bg-[#0B1F3B]/50" : "bg-[#0B1F3B]"}`}>
                    {lista.length === 0 && (
                      <p className="px-1 py-3 text-center text-[10px] text-white/25">
                        {c.cliente ? "esperando o cliente" : "vazio"}
                      </p>
                    )}
                    {lista.map((p) => (
                      <button key={p.id} onClick={() => setAberto(p.id)}
                        className="w-full rounded-lg bg-black/25 p-2 text-left transition hover:bg-black/40">
                        <p className="truncate text-xs font-semibold text-white">
                          {p.clientes?.nome ?? <span className="text-[#E5A44C]">sem cadastro</span>}
                        </p>
                        <p className="truncate text-[10px] text-white/45">
                          {p.numero} · {p.tipo}
                        </p>
                        <div className="mt-1 flex items-center gap-2 text-[10px]">
                          <span className="text-white/60">{brl(p.valor)}</span>
                          {Number(p.desconto_pct) > 0 && (
                            <span className="text-[#E5A44C]">−{Number(p.desconto_pct)}%</span>
                          )}
                          {p.urgente && <span className="text-[#C0392B]">urgente</span>}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {aberto && (
        <PainelDoPedido id={aberto} fechar={() => setAberto(null)} recarregar={carregar} />
      )}
    </PainelLayout>
  );
}

/* ── O pedido aberto: tudo o que o operador precisa num lugar ──── */
function PainelDoPedido({ id, fechar, recarregar }:
  { id: string; fechar: () => void; recarregar: () => void }) {
  const [p, setP] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [conversa, setConversa] = useState<any[]>([]);
  const [aba, setAba] = useState<
    "pedido" | "minuta" | "conversa" | "consultar">("pedido");
  const [msg, setMsg] = useState("");
  /* CHAT E WHATSAPP SÃO A MESMA CONVERSA
   *
   * O cliente começa no computador, sai para a rua e continua pelo
   * telefone, e espera encontrar lá o que foi dito aqui. Por isso o
   * WhatsApp nasce marcado: deixá-lo desligado por padrão fazia a
   * conversa existir pela metade em cada lugar, e o cliente perguntar
   * de novo o que já tinha sido respondido.
   *
   * O e-mail nasce desmarcado pelo motivo oposto. Ele tem outro ritmo,
   * e copiar cada linha de um chat para a caixa de entrada de quem
   * está com a tela aberta transforma atendimento em spam do próprio
   * escritório. Ele é para o recado que precisa ficar registrado fora
   * da conversa. */
  const [porEmail, setPorEmail] = useState(false);
  const [porWhats, setPorWhats] = useState(true);
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");

  const [atendimento, setAtendimento] = useState<any>(null);

  const carregar = useCallback(async () => {
    try {
      const [a, b, c] = await Promise.all([
        fetch(`${API}/api/v1/contratos/pedidos/${id}`).then((r) => r.json()),
        fetch(`${API}/api/v1/contratos/pedidos/${id}/documentos`).then((r) => r.json()),
        fetch(`${API}/api/v1/contratos/pedidos/${id}/conversa`).then((r) => r.json()),
      ]);
      setP(a); setDocs(Array.isArray(b) ? b : []);
      setConversa(Array.isArray(c) ? c : []);
    } catch { setErro("Não consegui abrir o pedido."); }
  }, [id]);
  useEffect(() => { carregar(); }, [carregar]);

  /* A CONVERSA AO VIVO, E SÓ ELA
   *
   * Enquanto a aba da conversa está aberta, a tela relê a cada quatro
   * segundos: o que o cliente escreve aparece sozinho, e quem está
   * acompanhando vê a conversa acontecer em vez de descobrir depois.
   *
   * Chat e WhatsApp são conversa de verdade, com alguém do outro lado
   * esperando. E-mail não é: ele tem o ritmo dele, e ninguém fica
   * olhando a tela esperando um e-mail chegar. Por isso a batida só
   * roda nesta aba, e para quando ela fecha. Pesquisar o servidor a
   * cada quatro segundos o dia inteiro, por causa de uma caixa que
   * ninguém está olhando, é desperdício que se paga em conta.
   */
  useEffect(() => {
    if (aba !== "conversa") return;
    let vivo = true;
    async function bater() {
      try {
        const [c, s] = await Promise.all([
          fetch(`${API}/api/v1/contratos/pedidos/${id}/conversa`).then((r) => r.json()),
          fetch(`${API}/api/v1/contratos/pedidos/${id}/atendimento`).then((r) => r.json()),
        ]);
        if (!vivo) return;
        if (Array.isArray(c)) setConversa(c);
        setAtendimento(s);
      } catch { /* uma batida perdida não é erro: a próxima vem em 4s */ }
    }
    bater();
    const t = setInterval(bater, 4000);
    return () => { vivo = false; clearInterval(t); };
  }, [aba, id]);

  async function acao(caminho: string, corpo: any = {}, rotulo = "") {
    setOcupado(rotulo || caminho); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}${caminho}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        // O motivo técnico só vem para quem é da equipe, e vem junto
        // porque sem ele a pessoa não sabe se tenta de novo ou se
        // avisa alguém.
        setErro([j?.detail || "Não deu certo.", j?.tecnico]
                  .filter(Boolean).join("  —  "));
        return;
      }
      await carregar(); recarregar();
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(""); }
  }

  async function excluir() {
    const pago = Boolean(p?.pago_em);
    const aviso = pago
      ? `O pedido ${p?.numero} foi PAGO. Excluir tira ele da esteira e o cliente deixa de ver andamento. Escreva o motivo:`
      : `Excluir o pedido ${p?.numero}? Ele sai da esteira. A conversa e os registros permanecem no banco.`;
    const motivo = pago ? prompt(aviso) : (confirm(aviso) ? "" : null);
    if (motivo === null) return;
    if (pago && !String(motivo).trim()) return;

    setOcupado("excluir"); setErro("");
    try {
      const r = await fetch(
        `${API}/api/v1/contratos/pedidos/${id}?quem=escritório`
        + `&motivo=${encodeURIComponent(String(motivo || ""))}`,
        { method: "DELETE" });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(j?.detail || "Não foi possível excluir."); return; }
      recarregar(); fechar();
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(""); }
  }

  if (!p) {
    return (
      <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={fechar}>
        <div className="h-full w-full max-w-2xl bg-[#0A1628] p-5 text-white/50">Carregando…</div>
      </div>
    );
  }

  const fase = p.fase;
  const revisao = p.revisao || null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={fechar}>
      <div className="h-full w-full max-w-2xl overflow-y-auto border-l border-white/10 bg-[#0A1628] p-5"
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-base font-bold text-white">
              {p.clientes?.nome ?? "Pedido sem cadastro"}
            </h2>
            <p className="text-xs text-white/45">
              {p.numero} · {p.tipo} · {brl(p.valor)}
              {Number(p.desconto_pct) > 0 && ` (−${Number(p.desconto_pct)}%)`}
              {p.urgente && " · urgente"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* EXCLUIR

                Faltava, e a esteira acumulava pedido de teste, pedido
                duplicado e gente que abriu e sumiu. A exclusão é lógica:
                apagar de verdade levaria junto a conversa, o
                comprovante do PIX e a ciência registrada, que são
                exatamente as provas de que o escritório precisaria se o
                cliente reclamasse depois. */}
            <button onClick={excluir} disabled={ocupado === "excluir"}
              className="rounded-lg border border-[#C0392B]/40 px-3 py-1.5 text-[11px] font-semibold text-[#ff9a8f] transition hover:border-[#C0392B] hover:bg-[#C0392B]/10 disabled:opacity-50">
              {ocupado === "excluir" ? "Excluindo…" : "Excluir pedido"}
            </button>
            <button onClick={fechar} className="text-xl text-white/40 hover:text-white">×</button>
          </div>
        </div>

        {/* A régua das fases */}
        <div className="mb-4 flex flex-wrap gap-1">
          {COLUNAS.map((c) => (
            <span key={c.f}
              className={`rounded px-2 py-0.5 text-[10px] ${c.f === fase
                ? "bg-[#C9A24D] font-bold text-[#0A1628]"
                : "bg-white/5 text-white/35"}`}>
              {c.l}
            </span>
          ))}
        </div>

        {erro && <p className="mb-3 rounded-lg bg-[#C0392B]/20 px-3 py-2 text-xs text-[#ffb3aa]">{erro}</p>}

        {/* O que fazer agora — só o botão da fase, para não haver dúvida */}
        {/* URGÊNCIA PAGA ESPERANDO CONFERÊNCIA

            Vem antes do bloco da fase de propósito: é dinheiro que já
            entrou e prazo que só começa a valer depois do clique. Um
            aviso desses no meio da tela seria visto na semana que vem. */}
        {p?.urgencia_pedida_em && !p?.urgencia_confirmada_em && (
          <div className="mb-4 rounded-xl border border-[#E5A44C]/50 bg-[#E5A44C]/10 p-3">
            <p className="text-[11px] font-bold text-[#E5A44C]">
              Urgência pedida pelo cliente
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-white/75">
              Adicional de{" "}
              <b className="text-white">
                {Number(p?.urgencia_valor || 0).toLocaleString("pt-BR",
                  { style: "currency", currency: "BRL" })}
              </b>
              {p?.urgencia_txid
                ? <> . O cliente informou o comprovante{" "}
                    <span className="font-mono text-white/85">{p?.urgencia_txid}</span>.</>
                : ". O cliente ainda não avisou o pagamento."}
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-white/50">
              Confira o extrato antes de confirmar. Ao confirmar, a entrega
              passa a 6 horas, a esteira acelera sozinha e o cliente é avisado
              pelos três canais.
            </p>
            <button
              onClick={() => acao("/urgencia/confirmar",
                { txid: p?.urgencia_txid || "", quem: "escritório" },
                "urgencia")}
              disabled={ocupado === "urgencia"}
              className="mt-2 rounded-lg bg-[#E5A44C] px-4 py-2 text-xs font-bold text-[#0A1628] hover:brightness-110 disabled:opacity-50">
              {ocupado === "urgencia" ? "Confirmando…" : "Confirmei o PIX, acelerar"}
            </button>
          </div>
        )}

        <div className="mb-4 rounded-xl border border-[#C9A24D]/30 bg-[#C9A24D]/5 p-3">
          <p className="mb-2 text-[11px] font-bold text-[#C9A24D]">O que fazer agora</p>
          {fase === "PAGAMENTO" && (
            <BaixaPix onConfirmar={(txid) => acao("/pagamento", { txid, quem: "escritório" }, "pago")}
              ocupado={ocupado === "pago"} />
          )}
          {/* AS TRÊS PRIMEIRAS FASES ANDAM SOZINHAS

              A minuta é escrita assim que a coleta fecha, e o pedido
              fica quatro horas visível como "em elaboração" para o
              cliente. Depois disso vai para revisão sozinho, e de duas
              em duas horas segue, até parar na revisão do advogado.

              O botão continua aqui porque a janela é teto, não piso:
              quem clicar, passa na frente do relógio. O que ele mostra
              agora é se o trabalho daquela fase já está pronto. */}
          {fase === "REDACAO" && (
            <div>
              <p className="mb-2 text-[11px] leading-relaxed text-white/60">
                {p.minuta
                  ? "Minuta já escrita. O cliente vê o pedido em elaboração por 4 horas; depois disso vai para revisão sozinho."
                  : "A minuta está sendo escrita. Se demorar, a esteira tenta de novo a cada 15 minutos."}
              </p>
              <Botao rotulo={p.minuta ? "Mandar para revisão agora" : "Redigir a minuta"}
                ocupado={ocupado === "redigir"}
                onClick={() => acao(p.minuta ? "/revisar" : "/redigir", {},
                                    p.minuta ? "revisar" : "redigir")}
                nota="Passar na frente do relógio é sempre permitido." />
            </div>
          )}
          {fase === "REVISAO_IA" && (
            <div>
              <p className="mb-2 text-[11px] leading-relaxed text-white/60">
                {p.revisao
                  ? "Revisão feita. Em até 2 horas segue para ajuste sozinho."
                  : "O revisor está lendo a íntegra."}
              </p>
              <Botao rotulo="Revisar" ocupado={ocupado === "revisar"}
                onClick={() => acao("/revisar", {}, "revisar")}
                nota="O revisor lê a íntegra e anota o que precisa mudar." />
            </div>
          )}
          {fase === "QUALIFICACAO" && (
            <p className="text-[11px] leading-relaxed text-white/60">
              O atendimento está entendendo o que o cliente precisa. O cartão
              anda sozinho para a proposta assim que o primeiro valor for
              apresentado.
            </p>
          )}
          {fase === "PROPOSTA" && (
            <p className="text-[11px] leading-relaxed text-white/60">
              O valor já foi apresentado e o cliente está decidindo. Aceito,
              o cartão vai para o pagamento.
            </p>
          )}
          {fase === "CIENCIA_ALTERACAO" && (
            <div>
              <p className="mb-2 text-[11px] leading-relaxed text-[#E5A44C]">
                A revisão encontrou pontos que contrariam a lei e o cliente
                precisa decidir entre manter como pediu ou adequar. Ele já foi
                avisado pelos três canais, e o prazo está parado até responder.
              </p>
              <p className="text-[11px] text-white/45">
                Assim que ele decidir, o documento volta a andar sozinho.
              </p>
            </div>
          )}
          {fase === "REVISAO_2" && (
            <div>
              <p className="mb-2 text-[11px] leading-relaxed text-white/60">
                {p.revisao_2
                  ? "Conferência feita. Em até 1 hora chega à sua revisão sozinho."
                  : "Conferindo se o ajuste atendeu ao que foi apontado."}
              </p>
              <Botao rotulo="Enviar para a minha revisão"
                ocupado={ocupado === "revisar2"}
                onClick={() => acao("/revisar-2", {}, "revisar2")}
                nota="Passar na frente do relógio é sempre permitido." />
            </div>
          )}
          {fase === "AJUSTE" && (
            <div>
              {/* O PEDIDO QUE CHEGOU AQUI SEM REVISÃO

                  Acontecia quando a revisão falhava e o pedido avançava
                  assim mesmo: o único botão da fase pedia para "acionar
                  o revisor primeiro", e o botão do revisor só existia na
                  fase anterior. Beco sem saída, e alguém precisava mexer
                  no banco para destravar. Agora a fase mostra o botão
                  que falta, e o próprio ajuste revisa antes se for
                  preciso. */}
              {!p.revisao ? (
                <>
                  <p className="mb-2 text-[11px] leading-relaxed text-[#E5A44C]">
                    Este pedido chegou ao ajuste sem a revisão registrada.
                    Rode o revisor e o ajuste abre em seguida.
                  </p>
                  <Botao rotulo="Revisar agora" ocupado={ocupado === "revisar"}
                    onClick={() => acao("/revisar", {}, "revisar")}
                    nota="O revisor lê a íntegra e anota o que precisa mudar." />
                </>
              ) : (
                <>
                  <p className="mb-2 text-[11px] leading-relaxed text-white/60">
                    Em até 2 horas o pedido chega à sua revisão sozinho. Dali não
                    passa sem você.
                  </p>
                  <Botao rotulo="Aplicar os apontamentos" ocupado={ocupado === "ajustar"}
                    onClick={() => acao("/ajustar", {}, "ajustar")}
                    nota="Reescreve a minuta atendendo a revisão. A anterior fica guardada." />
                </>
              )}
            </div>
          )}
          {/* DOIS PASSOS, NÃO UM

              Aprovar o texto e conferir a página são coisas diferentes.
              O texto pode estar impecável e o PDF sair com a cláusula
              quebrada no meio ou o timbre por cima do primeiro
              parágrafo, e quem recebia isso era o cliente. Agora o
              advogado abre o PDF antes, e o botão de liberar só acende
              depois. */}
          {fase === "REVISAO_ADV" && (
            <div>
              <p className="mb-2 text-[11px] leading-relaxed text-white/60">
                Abra o documento para ler e corrigir. Nada chega ao cliente sem esta leitura.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                {/* A MESA, E NÃO A CAIXINHA

                    Corrigir contrato numa caixa de quinze linhas dentro
                    do painel não funciona: para conferir se a cláusula
                    12 contradiz a 4, a pessoa rola e perde o lugar. Quem
                    revisa assim revisa mal, e por isso baixava o Word,
                    corrigia lá e não devolvia nada — o sistema ficava
                    com uma versão e o advogado com outra.

                    Em página inteira ele corrige, vê em PDF e aprova
                    sem sair do lugar. */}
                <a href={`/minuta/${id}`} target="_blank" rel="noreferrer"
                  className="rounded-lg bg-[#C9A24D] px-4 py-2 text-xs font-bold text-[#0A1628] hover:brightness-110">
                  Abrir o documento para corrigir
                </a>
                {/* LER NO WORD, CONFERIR NO PDF

                    Eram coisas diferentes tratadas como uma só. Ler um
                    contrato de vinte mil caracteres rolando um PDF é
                    pedir leitura ruim: no Word o advogado busca,
                    compara, anota ao lado. O PDF continua, mas para o
                    que ele serve de verdade, que é ver a página exata
                    que o cliente vai receber, com timbre e quebras.

                    A correção não é feita em nenhum dos dois: é na aba
                    Minuta, que salva sozinha. Documento editado em dois
                    lugares vira duas versões, e a que chega ao cliente
                    é sempre a errada. */}
                <button
                  onClick={() => baixarComToken(
                    `/api/v1/contratos/pedidos/${id}/documento.doc`,
                    `${p.numero || "contrato"}.doc`).catch((e) => setErro(String(e.message || e)))}
                  className="rounded-lg border border-[#2D7DD2]/60 px-4 py-2 text-xs font-semibold text-[#2D7DD2] hover:bg-[#2D7DD2]/10">
                  Abrir no Word para ler
                </button>
                <a href={`${API}/api/v1/contratos/pedidos/${id}/pdf`}
                  target="_blank" rel="noreferrer"
                  onClick={() => {
                    fetch(`${API}/api/v1/contratos/pedidos/${id}/layout-conferido?quem=advogado`,
                      { method: "POST" }).then(carregar);
                  }}
                  className="rounded-lg border border-white/20 px-4 py-2 text-xs font-semibold text-white/85 hover:border-white/45">
                  Ver o PDF como o cliente recebe
                </a>
                <Botao rotulo="Aprovar e enviar ao cliente" ocupado={ocupado === "liberar"}
                  onClick={() => acao("/liberar?quem=advogado", {}, "liberar")} />
              </div>
              <p className="mt-2 text-[11px] text-white/45">
                {p.visto_advogado_em
                  ? `Layout conferido em ${new Date(p.visto_advogado_em).toLocaleString("pt-BR")}. O cliente recebe aviso por e-mail e WhatsApp com o link da página dele.`
                  : "O PDF sai no papel que o cliente escolheu, timbrado ou folha branca. Confira antes de liberar."}
              </p>

              {/* AS DUAS SAÍDAS QUE FALTAVAM

                  Lendo o documento, o advogado às vezes precisa de um
                  dado que só o cliente tem, ou conclui que o texto
                  pede reescrita e não emenda. Sem estes dois botões
                  ele tinha de escolher entre perguntar pelo WhatsApp
                  por fora, deixando a resposta fora do registro, e
                  devolver o pedido inteiro por causa de uma linha. */}
              <PerguntarOuDevolver id={id} aoMudar={carregar} />
            </div>
          )}
          {fase === "APROVACAO" && (
            <p className="text-[11px] text-white/60">
              Com o cliente. Ele aprova ou pede alteração pela área dele.
            </p>
          )}
          {fase === "ASSINATURA" && (
            <div className="space-y-2">
              <p className="text-[11px] leading-relaxed text-white/60">
                {p.assinatura_digital
                  ? "Cliente escolheu assinatura eletrônica."
                  : "Cliente dispensou a assinatura eletrônica — entrega o arquivo para baixar."}
              </p>
              <Botao rotulo="Marcar como entregue" ocupado={ocupado === "entregar"}
                onClick={() => acao("/entregar", { quem: "escritório" }, "entregar")}
                nota="Abre os 7 dias de alteração sem custo e avisa o cliente por e-mail." />
            </div>
          )}
          {fase === "ENTREGUE" && (
            <div className="space-y-2">
              <p className="text-[11px] text-white/60">
                Entregue. Alteração sem custo até{" "}
                <b className="text-white/80">
                  {p.prazo_alteracao_ate
                    ? `${String(p.prazo_alteracao_ate).slice(8, 10)}/${String(p.prazo_alteracao_ate).slice(5, 7)}`
                    : "—"}
                </b>. Depois disso arquiva sozinho.
              </p>
              <Botao rotulo="Arquivar agora" ocupado={ocupado === "arquivar"}
                onClick={() => acao("/arquivar?quem=escritório", {}, "arquivar")} />
            </div>
          )}
          {["COLETA", "CIENCIA"].includes(fase) && (
            <p className="text-[11px] text-white/60">
              Esperando o cliente completar as informações.
            </p>
          )}
          {fase === "ARQUIVADO" && (
            <p className="text-[11px] text-white/60">Arquivado.</p>
          )}
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          {(["pedido", "minuta", "conversa", "consultar"] as const).map((a) => (
            <button key={a} onClick={() => setAba(a)}
              className={`${btn} ${aba === a ? "bg-[#C9A24D] text-[#0A1628]" : "border border-white/15 text-white/60"}`}>
              {a === "pedido" ? "Pedido"
                : a === "minuta" ? "Minuta"
                : a === "conversa" ? `Conversa (${conversa.length})`
                : "Perguntar"}
            </button>
          ))}
        </div>

        {aba === "pedido" && (
          <div className="space-y-3">
            <Bloco titulo="Como foi combinado">
              <Linha rotulo="Valor de tabela" valor={brl(p.valor_base ?? p.valor)} />
              {Number(p.desconto_pct) > 0 && (
                <Linha rotulo="Desconto" valor={`${Number(p.desconto_pct)}%`} />
              )}
              <Linha rotulo="Total" valor={brl(p.valor)} />
              <Linha rotulo="Prazo" valor={`${p.prazo_entrega_horas || 24} horas`} />
              <Linha rotulo="Assinatura eletrônica" valor={p.assinatura_digital ? "sim" : "não"} />
              <Linha rotulo="Pago em" valor={p.pago_em ? String(p.pago_em).slice(0, 10) : "—"} />
            </Bloco>

            {p.clausulas_extras && (
              <Bloco titulo="Cláusula pedida pelo cliente">
                <p className="whitespace-pre-line text-[11px] leading-relaxed text-white/70">
                  {p.clausulas_extras}
                </p>
              </Bloco>
            )}

            <Bloco titulo={`Documentos (${docs.length})`}>
              {docs.length === 0 && (
                <p className="text-[11px] text-white/35">
                  Nenhum documento. O cliente pode ter digitado tudo — veja os dados abaixo.
                </p>
              )}
              {docs.map((d) => (
                <div key={d.id} className="flex items-center gap-2 text-[11px] text-white/70">
                  <span className="flex-1 truncate">{d.nome}</span>
                  <span className="text-white/30">{d.rotulo || ""}</span>
                </div>
              ))}
            </Bloco>

            <Bloco titulo="Informações do contrato">
              {Object.keys(p.dados || {}).length === 0 ? (
                <p className="text-[11px] text-white/35">Ainda não preenchido.</p>
              ) : (
                Object.entries(p.dados || {}).map(([k, v]) => (
                  <Linha key={k} rotulo={k} valor={String(v ?? "—")} />
                ))
              )}
            </Bloco>

            {(p.negociacao || []).length > 0 && (
              <Bloco titulo="Como se chegou a esse preço">
                {(p.negociacao || []).map((t: any, i: number) => (
                  <p key={i} className="text-[11px] text-white/55">
                    {t.tipo === "FECHADO" ? "✓" : "·"} {brl(t.total)}
                    {t.desconto ? ` (−${t.desconto}%)` : ""} — {t.porque || t.resumo || ""}
                  </p>
                ))}
              </Bloco>
            )}
          </div>
        )}

        {aba === "minuta" && (
          <div className="space-y-3">
            {revisao && (
              <Bloco titulo="O que a revisão apontou">
                <p className="mb-2 text-[11px] leading-relaxed text-white/70">
                  {revisao.parecer || ""}
                </p>
                {(revisao.apontamentos || []).map((a: any, i: number) => (
                  <p key={i} className="text-[11px] text-white/55">
                    · {typeof a === "string" ? a : a.diz || JSON.stringify(a)}
                  </p>
                ))}
              </Bloco>
            )}
            {p.revisao_2 && (
              <Bloco titulo="O que a conferência apontou">
                <p className="mb-2 text-[11px] leading-relaxed text-white/70">
                  {p.revisao_2.parecer || ""}
                </p>
                {(p.revisao_2.apontamentos || []).map((a: any, i: number) => (
                  <p key={i} className="text-[11px] text-white/55">
                    · {typeof a === "string" ? a : `${a.clausula}: ${a.problema}`}
                  </p>
                ))}
              </Bloco>
            )}
            {p.minuta ? (
              <EditorDaMinuta pedidoId={id} minuta={p.minuta}
                podeEditar={fase === "REVISAO_ADV"} aoSalvar={carregar} />
            ) : (
              <p className="text-xs text-white/40">A minuta ainda não foi escrita.</p>
            )}
          </div>
        )}

        {aba === "conversa" && (
          <div className="space-y-2">
            <FaixaDoAtendimento id={id} estado={atendimento}
              aoMudar={(novo) => setAtendimento(novo)} />
            {conversa.map((m) => (
              <div key={m.id}
                className={`rounded-lg px-3 py-2 text-[11px] leading-relaxed ${m.autor === "CLIENTE"
                  ? "bg-white/5 text-white/80"
                  : "bg-[#2D7DD2]/15 text-white/80"}`}>
                <p className="mb-0.5 text-[10px] font-bold text-white/40">
                  {m.autor === "CLIENTE" ? "Cliente" : m.autor === "AGENTE" ? "Agente" : "Escritório"}
                  {/* DIA E HORA EM TODA MENSAGEM

                      Sem isso não há controle de prazo de resposta:
                      "demorou para responder" vira discussão de
                      memória, e memória de quem estava com pressa não
                      serve de prova. Com o carimbo, a conversa é o
                      próprio registro de quanto se levou. */}
                  {m.criado_em && (
                    <span className="ml-2 font-normal text-white/30">
                      {new Date(m.criado_em).toLocaleString("pt-BR", {
                        day: "2-digit", month: "2-digit",
                        hour: "2-digit", minute: "2-digit" })}
                    </span>
                  )}
                  {/* Por onde saiu. É isto que responde ao "ninguém me
                      avisou", e não a memória de quem atendeu. */}
                  {m.autor !== "CLIENTE" && (m.canais || []).length > 0 && (
                    <span className="ml-2 font-normal text-white/25">
                      {(m.canais || []).map((c: string) =>
                        c === "EMAIL" ? (m.email_em ? "e-mail" : "e-mail (falhou)")
                        : c === "WHATSAPP" ? (m.whatsapp_em ? "WhatsApp" : "WhatsApp (falhou)")
                        : "plataforma").join(" · ")}
                    </span>
                  )}
                </p>
                <p className="whitespace-pre-line">{m.texto}</p>
              </div>
            ))}
            {conversa.length === 0 && (
              <p className="text-xs text-white/40">Sem conversa ainda.</p>
            )}

            {/* O cliente está escrevendo agora. Vale mais do que parece:
                quem vê isso espera a frase inteira em vez de responder
                por cima de uma pergunta que ainda não terminou. */}
            {atendimento?.cliente_digitando && (
              <p className="px-3 text-[11px] italic text-[#1DB954]">
                o cliente está digitando…
              </p>
            )}

            {/* POR ONDE MANDAR

                A plataforma é obrigatória e por isso não tem caixa: ela
                é a própria linha da conversa, e é o único registro que
                fica. Os outros dois são escolha de quem escreve. O
                WhatsApp ainda não está ligado; quando o número for
                aprovado, esta caixa passa a funcionar sozinha. */}
            <div className="space-y-2 pt-3">
              <div className="flex flex-wrap items-center gap-4 text-[11px] text-white/55">
                <span className="text-white/35">Vai pelo chat e também por</span>
                <label className="flex cursor-pointer items-center gap-1.5">
                  <input type="checkbox" checked={porWhats}
                    onChange={(e) => setPorWhats(e.target.checked)}
                    className="h-3.5 w-3.5 accent-[#C9A24D]" />
                  WhatsApp
                </label>
                <label className="flex cursor-pointer items-center gap-1.5">
                  <input type="checkbox" checked={porEmail}
                    onChange={(e) => setPorEmail(e.target.checked)}
                    className="h-3.5 w-3.5 accent-[#C9A24D]" />
                  e-mail
                </label>
              </div>
              <p className="text-[10px] leading-relaxed text-white/30">
                Chat e WhatsApp são a mesma conversa: o cliente começa no
                computador, sai para a rua e continua no telefone. O e-mail
                é para o recado que precisa ficar fora da conversa.
              </p>
              <div className="flex gap-2">
                <input value={msg} onChange={(e) => setMsg(e.target.value)}
                  placeholder="escrever para o cliente…" className={inp} />
                <button
                  onClick={async () => {
                    if (!msg.trim()) return;
                    const canais = ["PLATAFORMA"];
                    if (porEmail) canais.push("EMAIL");
                    if (porWhats) canais.push("WHATSAPP");
                    const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/mensagem`, {
                      method: "POST", headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ texto: msg, autor: "ESCRITORIO", canais }),
                    });
                    const j = await r.json().catch(() => ({}));
                    if (j?.falhas?.length) setErro(`Enviado, mas ${j.falhas.join("; ")}`);
                    setMsg(""); carregar();
                  }}
                  className={`${btn} shrink-0 bg-[#C9A24D] text-[#0A1628]`}>Enviar</button>
              </div>
            </div>
          </div>
        )}

        {aba === "consultar" && <Consultar id={id} />}
      </div>
    </div>
  );
}

/* QUEM ESTÁ FALANDO COM O CLIENTE AGORA
 *
 * O agente responde em segundos, o que é bom quase sempre e é péssimo
 * na hora em que alguém do escritório decide assumir. Os dois
 * escrevendo ao mesmo tempo produzem o efeito mais constrangedor que
 * um atendimento pode ter: a pessoa explica o caso com cuidado e, logo
 * abaixo, o agente responde outra coisa.
 *
 * Quem escreve, assume. Não há botão obrigatório, porque quem está com
 * pressa de responder responde, e não clica em "assumir" antes. O
 * botão existe para o outro caso: quando se quer pensar a resposta sem
 * correr o risco de ser atropelado no meio.
 *
 * E devolve sozinho em cinco minutos, porque ninguém lembra de
 * devolver. Quem sai para uma audiência deixaria o cliente sem
 * resposta até alguém notar.
 */
function FaixaDoAtendimento({ id, estado, aoMudar }: {
  id: string; estado: any; aoMudar: (n: any) => void;
}) {
  const [ocupado, setOcupado] = useState(false);
  if (!estado) return null;
  const comHumano = estado.quem === "HUMANO";
  const faltam = Number(estado.segundos_para_o_agente_voltar || 0);

  async function trocar(rota: string, corpo: any = {}) {
    setOcupado(true);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}${rota}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
      aoMudar(await r.json().catch(() => estado));
    } catch { /* a próxima batida corrige */ }
    finally { setOcupado(false); }
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 rounded-lg px-3 py-2 text-[11px] ${
      comHumano ? "bg-[#C9A24D]/10 text-[#C9A24D]" : "bg-white/5 text-white/50"}`}>
      {comHumano ? (
        <>
          <b>Você assumiu esta conversa.</b>
          <span className="text-white/45">
            O agente não responde. Ele volta sozinho em{" "}
            {Math.ceil(faltam / 60)} min, ou a cada mensagem sua o relógio
            recomeça.
          </span>
          <button onClick={() => trocar("/devolver-ao-agente")} disabled={ocupado}
            className="ml-auto underline decoration-dotted hover:text-white">
            devolver ao agente agora
          </button>
        </>
      ) : (
        <>
          <span>O agente está respondendo este cliente.</span>
          <button onClick={() => trocar("/assumir", { quem: "escritório" })}
            disabled={ocupado}
            className="ml-auto underline decoration-dotted hover:text-white">
            assumir a conversa
          </button>
        </>
      )}
    </div>
  );
}

/* PERGUNTAR AO TRABALHO QUE JÁ FOI FEITO
 *
 * Na conferência final o advogado encontra o contrato pronto, os
 * apontamentos das duas revisões e a segunda revisão. O que ele não
 * encontra é o porquê: de onde saiu este prazo, se o cliente chegou a
 * pedir outra coisa, se a revisão viu aquele ponto da fiança.
 *
 * Até aqui a resposta exigia ler tudo — a conversa inteira, os dois
 * pareceres, os dados da coleta. Quinze minutos de leitura para uma
 * dúvida de uma linha, e quem tem pressa não lê: assina confiando, que
 * é o contrário do que a conferência existe para fazer.
 *
 * Aqui ele pergunta em português. Do outro lado responde um agente com
 * o registro inteiro do pedido na frente, que diz o que foi feito, por
 * quem e quando, e que diz "não encontrei" quando o registro não diz.
 *
 * Pergunta e resposta ficam gravadas. A conferência final é ato do
 * advogado, e o que ele consultou antes de aprovar faz parte do que
 * foi conferido. */
function Consultar({ id }: { id: string }) {
  const [historico, setHistorico] = useState<any[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [pensando, setPensando] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/consultas`);
      const d = await r.json();
      setHistorico(Array.isArray(d) ? d : []);
    } catch { /* o histórico é conforto, não pode travar a pergunta */ }
  }, [id]);

  useEffect(() => { carregar(); }, [carregar]);

  async function perguntar() {
    const texto = pergunta.trim();
    if (!texto || pensando) return;
    setPensando(true); setErro("");
    // A pergunta some da caixa e aparece na lista na hora: esperar
    // trinta segundos olhando a própria pergunta parada dá a impressão
    // de que o clique não pegou.
    setHistorico((h) => [...h, { pergunta: texto, resposta: "", em: "agora" }]);
    setPergunta("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/consultar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pergunta: texto, quem: "advogado" }),
      });
      const j = await r.json().catch(() => ({} as any));
      if (!r.ok) {
        setErro([j?.detail || "Não consegui responder.", j?.tecnico]
                  .filter(Boolean).join("  —  "));
        return;
      }
      await carregar();
    } catch { setErro("Falha de conexão."); }
    finally { setPensando(false); }
  }

  const sugestoes = [
    "De onde saiu o prazo deste contrato?",
    "O cliente pediu alguma coisa que a lei não permite?",
    "O que a revisão apontou de mais grave?",
    "Como foi fechado o valor?",
  ];

  return (
    <div className="space-y-3">
      <p className="text-[11px] leading-relaxed text-white/55">
        Pergunte sobre este pedido. Responde quem tem o registro inteiro na
        frente: a coleta, a conversa com o cliente, as duas revisões, as
        decisões dele e o contrato. O que não estiver registrado, a resposta
        diz que não está, em vez de supor.
      </p>

      {erro && (
        <p className="rounded-lg bg-[#C0392B]/20 px-3 py-2 text-[11px] text-[#ffb3aa]">
          {erro}
        </p>
      )}

      <div className="space-y-3">
        {historico.map((c, i) => (
          <div key={i} className="space-y-1.5">
            <p className="rounded-lg bg-white/5 px-3 py-2 text-[11px] text-white/80">
              {c.pergunta}
            </p>
            {c.resposta ? (
              <p className="whitespace-pre-line rounded-lg bg-[#2D7DD2]/10 px-3 py-2 text-[11px] leading-relaxed text-white/85">
                {c.resposta}
              </p>
            ) : (
              <p className="px-3 text-[11px] text-white/35">conferindo os registros…</p>
            )}
          </div>
        ))}
        {historico.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {sugestoes.map((s) => (
              <button key={s} onClick={() => setPergunta(s)}
                className="rounded-full border border-white/15 px-3 py-1.5 text-[11px] text-white/55 hover:border-white/40 hover:text-white/80">
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-2 pt-1">
        <input value={pergunta} onChange={(e) => setPergunta(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") perguntar(); }}
          placeholder="o que você quer saber sobre este pedido…"
          className={inp} />
        <button onClick={perguntar} disabled={pensando || !pergunta.trim()}
          className={`${btn} shrink-0 bg-[#C9A24D] text-[#0A1628] disabled:opacity-40`}>
          {pensando ? "Conferindo…" : "Perguntar"}
        </button>
      </div>
    </div>
  );
}

function Botao({ rotulo, onClick, ocupado, nota }:
  { rotulo: string; onClick: () => void; ocupado?: boolean; nota?: string }) {
  return (
    <div>
      <button onClick={onClick} disabled={ocupado}
        className={`${btn} w-full bg-[#C9A24D] py-2 text-[#0A1628]`}>
        {ocupado ? "Um momento…" : rotulo}
      </button>
      {nota && <p className="mt-1 text-[10px] leading-relaxed text-white/40">{nota}</p>}
    </div>
  );
}

function BaixaPix({ onConfirmar, ocupado }:
  { onConfirmar: (txid: string) => void; ocupado: boolean }) {
  const [txid, setTxid] = useState("");
  return (
    <div className="space-y-2">
      <p className="text-[11px] leading-relaxed text-white/60">
        A baixa é manual, conferindo o extrato. Não há integração com o banco, e
        uma baixa automática inventada faria o escritório escrever o contrato de
        quem não pagou.
      </p>
      <input value={txid} onChange={(e) => setTxid(e.target.value)}
        placeholder="identificador do PIX (opcional)" className={inp} />
      <button onClick={() => onConfirmar(txid)} disabled={ocupado}
        className={`${btn} w-full bg-[#1DB954] py-2 text-[#0A1628]`}>
        {ocupado ? "Um momento…" : "Confirmar o pagamento"}
      </button>
    </div>
  );
}

function Bloco({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
      <h3 className="mb-2 text-[11px] font-bold text-[#C9A24D]">{titulo}</h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline gap-2 text-[11px]">
      <span className="text-white/40">{rotulo}</span>
      <span className="flex-1 border-b border-dotted border-white/10" />
      <span className="text-white/80">{valor}</span>
    </div>
  );
}


/* ── PROPOSTAS ESPERANDO DECISÃO ──────────────────────────────────

   Fica no topo da esteira e só aparece quando há o que decidir. É o
   único ponto da tela em que alguém está do outro lado esperando uma
   resposta que só uma pessoa pode dar: o cliente parou de avançar
   exatamente aqui.

   Por isso mostra o valor de tabela ao lado do proposto e a
   justificativa dele por extenso. Decidir só com o número é decidir no
   escuro: "é o que sobra do aluguel deste mês" e "achei caro" levam a
   respostas diferentes. */
function PropostasPendentes({ recarregar }: { recarregar: () => void }) {
  const [lista, setLista] = useState<any[]>([]);
  const [abertaId, setAbertaId] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/propostas?status=PENDENTE`);
      const d = await r.json();
      setLista(Array.isArray(d) ? d : []);
    } catch { setLista([]); }
  }, []);
  useEffect(() => { carregar(); }, [carregar]);

  if (lista.length === 0) return null;

  return (
    <div className="rounded-xl border border-[#E5A44C]/40 bg-[#E5A44C]/[.07] p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-sm">✋</span>
        <h3 className="text-sm font-bold text-[#E5A44C]">
          {lista.length === 1
            ? "Uma proposta esperando a sua decisão"
            : `${lista.length} propostas esperando a sua decisão`}
        </h3>
        <span className="ml-auto text-[10px] text-white/40">
          o cliente parou o pedido aqui
        </span>
      </div>

      <div className="space-y-2">
        {lista.map((p) => (
          <div key={p.id} className="rounded-lg bg-black/25 p-3">
            <button onClick={() => setAbertaId(abertaId === p.id ? null : p.id)}
              className="flex w-full flex-wrap items-baseline gap-2 text-left">
              <span className="text-xs font-semibold text-white">
                {p.clientes?.nome ?? "sem cadastro"}
              </span>
              <span className="text-[10px] text-white/40">
                {p.numero} · {String(p.tipo || "").replaceAll("_", " ").toLowerCase()}
              </span>
              <span className="ml-auto text-xs">
                <b className="text-[#E5A44C]">{brl(p.proposta_valor)}</b>
                <span className="text-white/35"> de {brl(p.valor)}</span>
              </span>
            </button>

            {p.proposta_motivo && (
              <p className="mt-1.5 text-[11px] italic leading-relaxed text-white/60">
                “{p.proposta_motivo}”
              </p>
            )}

            {abertaId === p.id && (
              <Decisao pedido={p}
                depois={() => { carregar(); recarregar(); setAbertaId(null); }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Decisao({ pedido, depois }: { pedido: any; depois: () => void }) {
  const [resposta, setResposta] = useState("");
  const [contra, setContra] = useState("");
  const [ocupado, setOcupado] = useState("");

  async function responder(decisao: string) {
    if (decisao === "CONTRAPROPOSTA" && !contra) {
      alert("Informe o valor da contraproposta.");
      return;
    }
    setOcupado(decisao);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedido.id}/proposta`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decisao, resposta,
          valor: decisao === "CONTRAPROPOSTA" ? Number(contra) : null,
          quem: "escritório",
        }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { alert(j?.detail || "Não deu certo."); return; }
      depois();
    } finally { setOcupado(""); }
  }

  return (
    <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
      <input value={resposta} onChange={(e) => setResposta(e.target.value)}
        placeholder="o que dizer ao cliente (vai no e-mail)"
        className={inp} />
      <div className="flex flex-wrap gap-2">
        <button onClick={() => responder("ACEITA")} disabled={!!ocupado}
          className={`${btn} bg-[#1DB954] text-[#0A1628]`}>
          {ocupado === "ACEITA" ? "…" : `Aceitar ${brl(pedido.proposta_valor)}`}
        </button>

        <div className="flex gap-1">
          <input value={contra} onChange={(e) => setContra(e.target.value)}
            type="number" placeholder="contraproposta"
            className={`${inp} w-32`} />
          <button onClick={() => responder("CONTRAPROPOSTA")} disabled={!!ocupado}
            className={`${btn} shrink-0 bg-[#E5A44C] text-[#0A1628]`}>
            {ocupado === "CONTRAPROPOSTA" ? "…" : "Contrapropor"}
          </button>
        </div>

        <button onClick={() => responder("RECUSADA")} disabled={!!ocupado}
          className={`${btn} border border-[#C0392B]/50 text-[#ff9c90]`}>
          {ocupado === "RECUSADA" ? "…" : "Recusar"}
        </button>
      </div>
      <p className="text-[10px] text-white/35">
        Aceitar grava o valor proposto como o valor do pedido. O cliente recebe
        a resposta por e-mail nos três casos.
      </p>
    </div>
  );
}


/* ── CHAMADOS DE DESARQUIVAMENTO ──────────────────────────────
 *
 * Pedido que passou dos sete dias sem aprovação arquiva sozinho. O
 * cliente que voltar depois escreve por que precisa do documento, e o
 * chamado cai aqui.
 *
 * Fica no topo da esteira, junto das propostas, porque é gente
 * esperando resposta, e não trabalho na fila. A diferença entre as
 * duas coisas é o que decide a ordem do dia.
 */
function Desarquivamentos({ recarregar }: { recarregar: () => void }) {
  const [lista, setLista] = useState<any[]>([]);
  const [ocupado, setOcupado] = useState("");

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/desarquivamentos`);
      setLista(r.ok ? await r.json() : []);
    } catch { setLista([]); }
  }, []);
  useEffect(() => { carregar(); }, [carregar]);

  async function responder(c: any, aprovado: boolean) {
    const resposta = aprovado
      ? (prompt("Quer dizer algo ao cliente junto com a aprovação? (opcional)") ?? "")
      : (prompt("Explique ao cliente por que não é possível reabrir agora:") || "");
    if (!aprovado && !resposta.trim()) return;

    setOcupado(c.id);
    try {
      const r = await fetch(`${API}/api/v1/contratos/desarquivamentos/${c.id}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aprovado, resposta, quem: "escritório" }),
      });
      if (r.ok) { carregar(); recarregar(); }
    } finally { setOcupado(""); }
  }

  if (lista.length === 0) return null;

  return (
    <section className="mb-5 rounded-2xl border border-[#E5A44C]/40 bg-[#E5A44C]/5 p-5">
      <p className="text-xs font-bold uppercase tracking-wider text-[#E5A44C]">
        {lista.length === 1
          ? "Um cliente pediu para reabrir um documento arquivado"
          : `${lista.length} clientes pediram para reabrir documentos arquivados`}
      </p>

      <div className="mt-4 space-y-3">
        {lista.map((c) => {
          const p = c.pedidos_contrato || {};
          const cli = p.clientes || {};
          return (
            <div key={c.id} className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-[11px] text-white/50">{p.numero}</span>
                <span className="text-sm font-semibold text-white">{cli.nome || "sem cadastro"}</span>
                <span className="text-[11px] text-white/40">
                  {p.tipo === "OUTRO" && p.servico_livre
                    ? p.servico_livre.slice(0, 40)
                    : String(p.tipo || "").replaceAll("_", " ").toLowerCase()}
                </span>
              </div>

              <p className="mt-2 whitespace-pre-line rounded-lg bg-black/25 px-3 py-2 text-[12px] leading-relaxed text-white/75">
                {c.motivo}
              </p>

              <div className="mt-3 flex flex-wrap gap-2">
                <button onClick={() => responder(c, true)} disabled={ocupado === c.id}
                  className="rounded-lg bg-[#1DB954] px-4 py-2 text-xs font-bold text-[#0A1628] disabled:opacity-50">
                  Reabrir com prazo novo
                </button>
                <button onClick={() => responder(c, false)} disabled={ocupado === c.id}
                  className="rounded-lg border border-[#C0392B]/40 px-4 py-2 text-xs font-semibold text-[#ff9a8f]">
                  Recusar
                </button>
                <span className="ml-auto self-center text-[11px] text-white/35">
                  Reabrir devolve o documento à revisão do cliente por mais sete dias.
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}


/* ── O EDITOR DO ADVOGADO ──────────────────────────────────────
 *
 * Até aqui a minuta chegava à conferência final e o advogado só podia
 * aprovar ou devolver para ajuste. Corrigir uma vírgula exigia pedir
 * ao redator que reescrevesse o documento inteiro, o que muda muito
 * mais do que uma vírgula e obriga a reler tudo de novo.
 *
 * Três decisões que não são de estilo:
 *
 * SALVA SOZINHO, E TEM BOTÃO. O automático roda dois segundos depois
 * da última tecla. O botão existe porque salvamento automático falha
 * calado, e quem está com um contrato de meia hora na tela tem direito
 * de ver o "salvo" com os próprios olhos.
 *
 * GUARDA A VERSÃO ANTERIOR. Do lado do servidor, a cada gravação. Uma
 * seleção acidental seguida de uma tecla apaga meia hora de trabalho,
 * e sem histórico não há volta.
 *
 * SÓ EDITA NA FASE DELE. Antes da conferência final o texto ainda vai
 * mudar pela mão dos agentes, e editar ali é escrever por cima de
 * algo que vai ser sobrescrito.
 */
function EditorDaMinuta({ pedidoId, minuta, podeEditar, aoSalvar }: {
  pedidoId: string; minuta: string; podeEditar: boolean; aoSalvar: () => void;
}) {
  const [texto, setTexto] = useState(minuta || "");
  const [estado, setEstado] = useState<"" | "salvando" | "salvo" | "erro">("");
  const [editando, setEditando] = useState(false);
  const relogio = useRef<any>(null);
  const ultimoSalvo = useRef(minuta || "");

  // A minuta muda por fora quando o agente reescreve. Enquanto o
  // advogado não começou a editar, a tela acompanha; depois que ele
  // começou, não: sobrescrever o que alguém está digitando é o pior
  // erro que uma tela pode cometer.
  useEffect(() => {
    if (!editando) { setTexto(minuta || ""); ultimoSalvo.current = minuta || ""; }
  }, [minuta, editando]);

  const salvar = useCallback(async (conteudo: string) => {
    if (!conteudo.trim() || conteudo === ultimoSalvo.current) return;
    setEstado("salvando");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${pedidoId}/minuta`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: conteudo }),
      });
      if (!r.ok) { setEstado("erro"); return; }
      ultimoSalvo.current = conteudo;
      setEstado("salvo");
    } catch { setEstado("erro"); }
  }, [pedidoId]);

  function digitou(valor: string) {
    setTexto(valor); setEditando(true); setEstado("");
    if (relogio.current) clearTimeout(relogio.current);
    relogio.current = setTimeout(() => salvar(valor), 2000);
  }

  // Sair da página com alteração por salvar é perder trabalho.
  useEffect(() => {
    const avisar = (e: BeforeUnloadEvent) => {
      if (texto !== ultimoSalvo.current) { e.preventDefault(); e.returnValue = ""; }
    };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [texto]);

  function baixar() {
    // .doc com conteúdo HTML: o Word abre, o Google Docs abre, e não
    // depende de biblioteca nenhuma no navegador.
    const html = `<html xmlns:w="urn:schemas-microsoft-com:office:word">`
      + `<head><meta charset="utf-8"></head><body>`
      + `<div style="font-family:Times New Roman,serif;font-size:12pt;line-height:1.5">`
      + texto.split("\n").map((l) =>
          `<p>${l.replace(/&/g, "&amp;").replace(/</g, "&lt;") || "&nbsp;"}</p>`).join("")
      + `</div></body></html>`;
    const url = URL.createObjectURL(
      new Blob([html], { type: "application/msword" }));
    const a = document.createElement("a");
    a.href = url; a.download = "contrato.doc"; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-bold text-[#C9A24D]">
          {podeEditar ? "Documento, aberto para edição" : "Documento"}
        </span>
        <span className="text-[10px] text-white/35">
          {estado === "salvando" ? "salvando…"
            : estado === "salvo" ? "salvo"
            : estado === "erro" ? "não consegui salvar"
            : texto !== ultimoSalvo.current ? "alterações não salvas" : ""}
        </span>
        <div className="ml-auto flex flex-wrap gap-2">
          {podeEditar && (
            <button onClick={() => salvar(texto)}
              disabled={estado === "salvando" || texto === ultimoSalvo.current}
              className="rounded-lg bg-[#C9A24D] px-3 py-1.5 text-[11px] font-bold text-[#0A1628] disabled:opacity-40">
              Salvar
            </button>
          )}
          <button onClick={baixar}
            className="rounded-lg border border-white/20 px-3 py-1.5 text-[11px] text-white/70 hover:border-white/45">
            Baixar em Word
          </button>
        </div>
      </div>

      {podeEditar ? (
        <textarea
          value={texto}
          onChange={(e) => digitou(e.target.value)}
          onBlur={() => salvar(texto)}
          spellCheck
          className="h-[58vh] w-full resize-y rounded-lg border border-white/10 bg-white px-6 py-5 font-serif text-[13px] leading-relaxed text-[#111] outline-none focus:border-[#C9A24D]"
        />
      ) : (
        <pre className="whitespace-pre-wrap text-[11px] leading-relaxed text-white/80">
          {texto}
        </pre>
      )}

      {podeEditar && (
        <p className="mt-2 text-[10px] leading-relaxed text-white/35">
          O texto salva sozinho dois segundos depois que você para de
          digitar, e a versão anterior fica guardada a cada gravação. O
          cliente só vê o documento depois que você liberar, e em PDF, sem
          opção de baixar até aprovar.
        </p>
      )}
    </div>
  );
}


/* ── AS DUAS SAÍDAS DO ADVOGADO NA CONFERÊNCIA FINAL ───────────
 *
 * Perguntar sai pelos três canais e a resposta volta pela conversa do
 * pedido, onde fica registrada. Devolver manda para o ajuste, e não
 * para a redação: o texto está quase pronto, e reescrever do zero
 * jogaria fora as duas revisões já feitas.
 *
 * As duas ficam recolhidas atrás de um link, de propósito. O caminho
 * normal desta fase é ler e aprovar; pôr três botões do mesmo tamanho
 * lado a lado faz a pessoa parar para escolher em vez de fazer o que
 * veio fazer.
 */
function PerguntarOuDevolver({ id, aoMudar }: { id: string; aoMudar: () => void }) {
  const [aberto, setAberto] = useState<"" | "perguntar" | "devolver">("");
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");

  async function enviar(rota: string, campo: string) {
    if (texto.trim().length < 5) { setAviso("Escreva o que precisa."); return; }
    setOcupado(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}${rota}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [campo]: texto.trim(), quem: "advogado" }),
      });
      if (!r.ok) { setAviso("Não deu certo. Tente de novo."); return; }
      setTexto(""); setAberto("");
      setAviso(rota === "/perguntar"
        ? "Pergunta enviada pelos três canais. A resposta aparece na conversa."
        : "Devolvido para ajuste com o seu apontamento.");
      aoMudar();
    } catch { setAviso("Falha de conexão."); }
    finally { setOcupado(false); }
  }

  return (
    <div className="mt-3 border-t border-white/10 pt-3">
      {aberto === "" ? (
        <div className="flex flex-wrap gap-4">
          <button onClick={() => { setAberto("perguntar"); setAviso(""); }}
            className="text-[11px] text-white/50 underline underline-offset-4 hover:text-white">
            tirar uma dúvida com o cliente
          </button>
          <button onClick={() => { setAberto("devolver"); setAviso(""); }}
            className="text-[11px] text-white/50 underline underline-offset-4 hover:text-white">
            devolver para ajuste
          </button>
        </div>
      ) : (
        <div>
          <p className="mb-1.5 text-[11px] font-bold text-[#C9A24D]">
            {aberto === "perguntar"
              ? "O que você precisa confirmar com o cliente?"
              : "O que o redator precisa corrigir?"}
          </p>
          <textarea value={texto} onChange={(e) => setTexto(e.target.value)}
            rows={3} autoFocus
            placeholder={aberto === "perguntar"
              ? "Ex.: o aluguel de R$ 2.000 já inclui o condomínio ou é à parte?"
              : "Ex.: a cláusula 6 não traz a fórmula da multa proporcional."}
            className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-xs outline-none focus:border-[#C9A24D]" />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button
              onClick={() => enviar(aberto === "perguntar" ? "/perguntar" : "/devolver",
                                    aberto === "perguntar" ? "pergunta" : "motivo")}
              disabled={ocupado}
              className="rounded-lg bg-[#C9A24D] px-4 py-2 text-[11px] font-bold text-[#0A1628] disabled:opacity-50">
              {ocupado ? "Enviando…"
                : aberto === "perguntar" ? "Perguntar pelos três canais"
                : "Devolver para ajuste"}
            </button>
            <button onClick={() => { setAberto(""); setTexto(""); }}
              className="text-[11px] text-white/45 underline hover:text-white">
              cancelar
            </button>
          </div>
        </div>
      )}
      {aviso && <p className="mt-2 text-[11px] text-[#C9A24D]">{aviso}</p>}
    </div>
  );
}
