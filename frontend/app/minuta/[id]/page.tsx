"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { baixarComToken } from "../../../lib/baixar";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A MESA DO DOCUMENTO
 *
 * Corrigir contrato numa caixinha dentro do painel não funciona. O
 * texto tem vinte mil caracteres e a caixa mostra quinze linhas: para
 * conferir se a cláusula 12 contradiz a 4, a pessoa rola, perde o
 * lugar, rola de volta. Quem revisa assim revisa mal, e sabe disso, e
 * por isso baixava o Word, corrigia lá e não devolvia nada — o sistema
 * ficava com uma versão e o advogado com outra.
 *
 * Aqui o documento ocupa a página inteira, com a largura e a fonte de
 * uma folha, e as três coisas que se faz depois de corrigir estão à
 * mão: ver como fica em PDF, e aprovar.
 *
 * SALVA SOZINHO, E TEM BOTÃO MESMO ASSIM
 *
 * Dois segundos depois da última tecla o texto sobe. O botão Salvar é
 * redundante de propósito: quem mexe num contrato quer ver confirmado
 * que salvou, e "confie, já salvei" não acalma ninguém. O estado fica
 * escrito ao lado, e sair da página com alteração pendente avisa.
 *
 * TEXTO PURO, E ISSO É ESCOLHA
 *
 * A minuta é texto puro no banco, e o PDF é montado a partir dele. Um
 * editor rico aqui criaria uma formatação que o PDF não leria, e o
 * advogado veria na tela um documento diferente do que o cliente
 * receberia. Negrito e títulos saem do próprio texto, na hora de gerar
 * o documento.
 */
export default function MesaDaMinuta() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [p, setP] = useState<any>(null);
  const [texto, setTexto] = useState("");
  const [estado, setEstado] = useState<"" | "salvando" | "salvo" | "erro">("");
  const [salvoEm, setSalvoEm] = useState<Date | null>(null);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState("");

  const ultimoSalvo = useRef("");
  const relogio = useRef<any>(null);

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}`);
      const d = await r.json();
      if (!r.ok) { setErro(d?.detail || "Não consegui abrir o pedido."); return; }
      setP(d);
      // Só semeia o texto na primeira carga: sobrescrever o que alguém
      // está digitando é o pior erro que uma tela pode cometer.
      if (!ultimoSalvo.current) {
        setTexto(d.minuta || "");
        ultimoSalvo.current = d.minuta || "";
      }
    } catch { setErro("Falha de conexão."); }
  }, [id]);

  useEffect(() => { carregar(); }, [carregar]);

  const salvar = useCallback(async (conteudo: string) => {
    if (!conteudo.trim() || conteudo === ultimoSalvo.current) return;
    setEstado("salvando"); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/minuta`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: conteudo }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({} as any));
        setEstado("erro");
        setErro([j?.detail || "Não consegui salvar.", j?.tecnico]
                  .filter(Boolean).join("  —  "));
        return;
      }
      ultimoSalvo.current = conteudo;
      setEstado("salvo"); setSalvoEm(new Date());
    } catch { setEstado("erro"); setErro("Falha de conexão ao salvar."); }
  }, [id]);

  function digitou(valor: string) {
    setTexto(valor); setEstado("");
    if (relogio.current) clearTimeout(relogio.current);
    relogio.current = setTimeout(() => salvar(valor), 2000);
  }

  /* Sair com alteração por salvar é perder trabalho, e trabalho perdido
     num contrato é uma hora de leitura jogada fora. */
  const pendente = texto !== ultimoSalvo.current;
  useEffect(() => {
    const avisar = (e: BeforeUnloadEvent) => {
      if (pendente) { e.preventDefault(); e.returnValue = ""; }
    };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [pendente]);

  /* Ctrl+S é o reflexo de quem escreve. Deixar o navegador abrir a
     caixa de salvar página seria responder a coisa errada. */
  useEffect(() => {
    const atalho = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault(); salvar(texto);
      }
    };
    window.addEventListener("keydown", atalho);
    return () => window.removeEventListener("keydown", atalho);
  }, [texto, salvar]);

  /* O PAPEL, DECIDIDO NA HORA DE CONFERIR
   *
   * A escolha é do cliente e é feita na coleta, antes de ele ver
   * qualquer coisa. É aqui, lendo o documento pronto, que se descobre
   * que ela não serve: contrato que vai a cartório ou é juntado a um
   * processo costuma pedir folha branca, e quem percebe isso é o
   * advogado.
   *
   * Sem este botão ele teria de devolver o pedido para a coleta por
   * causa de um cabeçalho, perdendo o lugar na esteira. Fica marcado o
   * que o cliente escolheu, e a troca fica registrada em nome de quem
   * trocou. */
  async function trocarTimbre(comTimbre: boolean) {
    const antes = p.com_timbre;
    setP((x: any) => ({ ...x, com_timbre: comTimbre }));   // responde na hora
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/timbre`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ com_timbre: comTimbre, quem: "advogado" }),
      });
      if (!r.ok) throw new Error();
    } catch {
      setP((x: any) => ({ ...x, com_timbre: antes }));     // desfaz se falhou
      setErro("Não consegui mudar o papel agora.");
    }
  }

  async function verOPdf() {
    // Salva antes: PDF gerado do texto antigo faria o advogado conferir
    // uma versão que já não existe, e aprovar achando que conferiu.
    setOcupado("pdf");
    try {
      await salvar(texto);
      window.open(`${API}/api/v1/contratos/pedidos/${id}/pdf`, "_blank");
      fetch(`${API}/api/v1/contratos/pedidos/${id}/layout-conferido?quem=advogado`,
            { method: "POST" }).then(carregar).catch(() => {});
    } finally { setOcupado(""); }
  }

  async function aprovar() {
    if (pendente) await salvar(texto);
    if (!confirm("Aprovar e enviar ao cliente?\n\n"
                 + "Ele recebe aviso com o link da página dele e passa a ver "
                 + "o documento. Depois disso, mudança só pelo pedido de "
                 + "alteração.")) return;
    setOcupado("aprovar"); setErro("");
    try {
      const r = await fetch(
        `${API}/api/v1/contratos/pedidos/${id}/liberar?quem=advogado`,
        { method: "POST" });
      const j = await r.json().catch(() => ({} as any));
      if (!r.ok) {
        setErro([j?.detail || "Não consegui enviar.", j?.tecnico]
                  .filter(Boolean).join("  —  "));
        return;
      }
      router.push("/contratos");
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(""); }
  }

  if (erro && !p) {
    return <main className="p-8 text-sm text-[#ffb3aa]">{erro}</main>;
  }
  if (!p) {
    return <main className="p-8 text-sm text-white/50">Abrindo o documento…</main>;
  }

  const podeAprovar = p.fase === "REVISAO_ADV";

  return (
    <main className="min-h-screen bg-[#0A1628] text-white">
      {/* A barra acompanha a rolagem: num texto de vinte mil caracteres,
          botão que fica lá em cima é botão que não existe. */}
      <div className="sticky top-0 z-10 border-b border-white/10 bg-[#0A1628]/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-5 py-3">
          <button onClick={() => router.push("/contratos")}
            className="text-sm text-white/50 hover:text-white">
            ← voltar
          </button>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-[#C9A24D]">
              {p.clientes?.nome || "Documento"}
            </p>
            <p className="text-[11px] text-white/40">
              {p.numero} · {p.tipo}
              <span className="ml-2">
                {estado === "salvando" ? "salvando…"
                  : estado === "erro" ? "não consegui salvar"
                  : pendente ? "alterações não salvas"
                  : salvoEm ? `salvo às ${salvoEm.toLocaleTimeString("pt-BR",
                      { hour: "2-digit", minute: "2-digit" })}`
                  : ""}
              </span>
            </p>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <button onClick={() => salvar(texto)} disabled={!pendente || estado === "salvando"}
              className="rounded-lg bg-[#C9A24D] px-4 py-2 text-xs font-bold text-[#0A1628] disabled:opacity-35">
              Salvar
            </button>
            <button onClick={verOPdf} disabled={ocupado === "pdf"}
              className="rounded-lg border border-white/20 px-4 py-2 text-xs font-semibold text-white/85 hover:border-white/45 disabled:opacity-40">
              {ocupado === "pdf" ? "Gerando…" : "Ver em PDF"}
            </button>
            <button
              onClick={() => baixarComToken(
                `/api/v1/contratos/pedidos/${id}/documento.doc`,
                `${p.numero || "contrato"}.doc`)
                .catch((e) => setErro(e.message || "Não consegui baixar."))}
              className="rounded-lg border border-white/20 px-4 py-2 text-xs text-white/70 hover:border-white/45">
              Baixar em Word
            </button>
            {podeAprovar && (
              <button onClick={aprovar} disabled={ocupado === "aprovar"}
                className="rounded-lg bg-[#1DB954] px-4 py-2 text-xs font-bold text-white hover:bg-[#17a349] disabled:opacity-40">
                {ocupado === "aprovar" ? "Enviando…" : "Aprovar e enviar ao cliente"}
              </button>
            )}
          </div>
        </div>
        {erro && (
          <p className="bg-[#C0392B]/20 px-5 py-2 text-center text-[11px] text-[#ffb3aa]">
            {erro}
          </p>
        )}
      </div>

      <div className="mx-auto max-w-5xl px-5 py-6">
        {/* O que a revisão apontou fica ao lado do texto, e não noutra
            aba: o advogado está corrigindo justamente isso, e trocar de
            tela para lembrar o apontamento é como revisar de memória. */}
        {(p.revisao?.apontamentos?.length || p.revisao_2?.apontamentos?.length) ? (
          <details className="mb-4 rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
            <summary className="cursor-pointer text-xs font-bold text-[#C9A24D]">
              O que as revisões apontaram
            </summary>
            <div className="mt-2 space-y-1">
              {(p.revisao?.apontamentos || []).map((a: any, i: number) => (
                <p key={`a${i}`} className="text-[11px] leading-relaxed text-white/60">
                  · {typeof a === "string" ? a
                     : `[${a.gravidade}] ${a.clausula}: ${a.problema}`}
                </p>
              ))}
              {(p.revisao_2?.apontamentos || []).map((a: any, i: number) => (
                <p key={`b${i}`} className="text-[11px] leading-relaxed text-white/60">
                  · {typeof a === "string" ? a : `${a.clausula}: ${a.problema}`}
                </p>
              ))}
            </div>
          </details>
        ) : null}

        {/* O PAPEL EM QUE ISSO VAI SAIR
            Fica junto do documento, e não escondido num menu: é
            decisão que se toma olhando o texto, e que muda o que o
            cliente recebe. */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-white/40">Sai em</span>
          {([[true, "Papel timbrado", "Com a identificação do escritório."],
             [false, "Folha branca", "Sem nenhuma identificação."]] as const)
            .map(([valor, titulo, nota]) => {
              const ativo = (p.com_timbre !== false) === valor;
              return (
                <button key={String(valor)} onClick={() => trocarTimbre(valor)}
                  className={`rounded-xl border px-3 py-2 text-left text-[11px] transition ${ativo
                    ? "border-[#C9A24D] bg-[#C9A24D]/10"
                    : "border-white/15 hover:border-white/35"}`}>
                  <b className="block text-white/90">{titulo}</b>
                  <span className="text-white/45">{nota}</span>
                </button>
              );
            })}
          <span className="text-[11px] text-white/30">
            {p.com_timbre === false
              ? "Foi o que o cliente escolheu, salvo se você tiver mudado agora."
              : "Escolha do cliente na coleta. Você pode trocar antes de aprovar."}
          </span>
        </div>

        <div className="flex flex-col gap-4 lg:flex-row">
          {/* A folha. Fundo claro, serifa e largura de página: o olho lê
              contrato assim, e o contraste do painel escuro cansa em
              dois parágrafos. */}
          <textarea
            value={texto}
            onChange={(e) => digitou(e.target.value)}
            spellCheck
            className="min-h-[70vh] flex-1 resize-y rounded-lg border border-white/10 bg-[#F7F5EF] p-10 font-serif text-[15px] leading-[1.8] text-[#1A1A1A] outline-none focus:border-[#C9A24D]"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          />
          <Especialista id={id} minuta={texto} />
        </div>

        <p className="mt-3 text-[11px] leading-relaxed text-white/35">
          Salva sozinho dois segundos depois que você para de digitar, e
          também no Ctrl+S. Títulos e negrito saem do próprio texto quando o
          documento é gerado: escreva o título em uma linha curta, em
          maiúsculas, sem asterisco nem sustenido.
        </p>
      </div>
    </main>
  );
}

/* O ESPECIALISTA DO CASO, AO LADO DO DOCUMENTO
 *
 * Quem confere um contrato tem dúvida enquanto lê, não depois. "De onde
 * saiu este prazo", "o cliente chegou a pedir isso", "esta cláusula de
 * garantia se sustenta". Guardar a dúvida para procurar a resposta
 * depois é como revisar de memória: ou se perde o lugar no texto, ou se
 * deixa passar.
 *
 * Por isso ele fica na mesma tela, à direita, e enxerga o que importa:
 * todo o registro do pedido e O TEXTO QUE ESTÁ NA TELA AGORA, com as
 * alterações ainda não salvas. Comentar a versão do banco enquanto o
 * advogado edita outra é o jeito mais rápido de perder a confiança de
 * quem está trabalhando.
 *
 * ELE NÃO ESCREVE NO DOCUMENTO
 *
 * Sugere a redação, e quem cola é o advogado. Agente que edita contrato
 * sozinho, enquanto alguém edita o mesmo arquivo, produz duas versões
 * e nenhuma confiável. Além disso a conferência final é ato dele: o que
 * vai para o cliente precisa ter passado pela mão de quem assina.
 */
function Especialista({ id, minuta }: { id: string; minuta: string }) {
  const [conversa, setConversa] = useState<any[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [pensando, setPensando] = useState(false);
  const [erro, setErro] = useState("");
  const [aberto, setAberto] = useState(true);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/consultas`);
        const d = await r.json();
        if (Array.isArray(d)) setConversa(d);
      } catch { /* histórico é conforto, não trava a pergunta */ }
    })();
  }, [id]);

  useEffect(() => {
    // Rola a própria caixa, e não a página: scrollIntoView arrasta a
    // tela inteira e tira o documento da frente de quem está editando.
    const c = fim.current?.parentElement;
    if (c) c.scrollTop = c.scrollHeight;
  }, [conversa, pensando]);

  async function mandar(texto?: string) {
    const q = (texto ?? pergunta).trim();
    if (!q || pensando) return;
    setPergunta(""); setErro(""); setPensando(true);
    const antes = conversa;
    setConversa([...antes, { pergunta: q, resposta: "" }]);
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}/consultar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pergunta: q, quem: "advogado", minuta,
          anteriores: antes.slice(-6).map((c: any) => ({
            pergunta: c.pergunta, resposta: c.resposta })),
        }),
      });
      const j = await r.json().catch(() => ({} as any));
      if (!r.ok) {
        setConversa(antes);
        setErro([j?.detail || "Não consegui responder.", j?.tecnico]
                  .filter(Boolean).join("  —  "));
        return;
      }
      setConversa([...antes, { pergunta: q, resposta: j.resposta }]);
    } catch { setConversa(antes); setErro("Falha de conexão."); }
    finally { setPensando(false); }
  }

  const atalhos = [
    ["Revisar o texto da tela",
     "Leia o contrato que estou editando agora e aponte, em ordem de "
     + "gravidade, o que está nulo, frágil ou ambíguo. Seja específico: "
     + "cláusula, problema e a redação que você usaria."],
    ["O que falta decidir",
     "O que ainda precisa de decisão antes de este documento sair, e o "
     + "que depende do cliente?"],
    ["Confere com o que foi pedido",
     "Compare o contrato com os dados do pedido e com o que o cliente "
     + "escreveu. Tem algo divergente, faltando ou inventado?"],
  ] as const;

  if (!aberto) {
    return (
      <button onClick={() => setAberto(true)}
        className="self-start rounded-lg border border-[#C9A24D]/50 px-3 py-2 text-[11px] font-semibold text-[#C9A24D] hover:bg-[#C9A24D]/10">
        Abrir o especialista
      </button>
    );
  }

  return (
    <aside className="flex w-full flex-col rounded-xl border border-white/10 bg-[#0B1F3B] lg:w-[380px]">
      <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
        <span className="text-[11px] font-bold text-[#C9A24D]">
          Especialista do caso
        </span>
        <button onClick={() => setAberto(false)}
          className="ml-auto text-[11px] text-white/35 hover:text-white">
          ocultar
        </button>
      </div>

      <div className="max-h-[60vh] min-h-[200px] flex-1 space-y-3 overflow-y-auto p-3">
        {conversa.length === 0 && (
          <p className="text-[11px] leading-relaxed text-white/45">
            Ele acompanhou este pedido do começo ao fim: a negociação, a
            coleta, as duas revisões e o que o cliente decidiu. Enxerga o
            texto que você está editando agora, inclusive o que ainda não
            foi salvo. Sugere a redação; quem aplica é você.
          </p>
        )}
        {conversa.map((c, i) => (
          <div key={i} className="space-y-1.5">
            <p className="rounded-lg bg-white/5 px-3 py-2 text-[11px] text-white/75">
              {c.pergunta}
            </p>
            {c.resposta ? (
              <p className="whitespace-pre-line rounded-lg bg-[#2D7DD2]/10 px-3 py-2 text-[11px] leading-relaxed text-white/85">
                {c.resposta}
              </p>
            ) : (
              <p className="px-3 text-[11px] italic text-white/35">lendo o caso…</p>
            )}
          </div>
        ))}
        <div ref={fim} />
      </div>

      {erro && (
        <p className="px-3 pb-2 text-[11px] text-[#ffb3aa]">{erro}</p>
      )}

      <div className="space-y-2 border-t border-white/10 p-3">
        <div className="flex flex-wrap gap-1.5">
          {atalhos.map(([rotulo, texto]) => (
            <button key={rotulo} onClick={() => mandar(texto)} disabled={pensando}
              className="rounded-full border border-white/15 px-2.5 py-1 text-[10px] text-white/55 hover:border-white/40 hover:text-white/85 disabled:opacity-40">
              {rotulo}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={pergunta} onChange={(e) => setPergunta(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") mandar(); }}
            placeholder="pergunte sobre o caso ou o texto…"
            className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-xs text-white outline-none focus:border-[#C9A24D]" />
          <button onClick={() => mandar()} disabled={pensando || !pergunta.trim()}
            className="shrink-0 rounded-lg bg-[#C9A24D] px-3 py-2 text-[11px] font-bold text-[#0A1628] disabled:opacity-40">
            {pensando ? "…" : "Perguntar"}
          </button>
        </div>
      </div>
    </aside>
  );
}
