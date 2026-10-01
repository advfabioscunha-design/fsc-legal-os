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

        {/* A folha. Fundo claro, serifa e largura de página: o olho lê
            contrato assim, e o contraste do painel escuro cansa em dois
            parágrafos. */}
        <textarea
          value={texto}
          onChange={(e) => digitou(e.target.value)}
          spellCheck
          className="min-h-[70vh] w-full resize-y rounded-lg border border-white/10 bg-[#F7F5EF] p-10 font-serif text-[15px] leading-[1.8] text-[#1A1A1A] outline-none focus:border-[#C9A24D]"
          style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
        />

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
