"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { baixarComToken } from "../../../lib/baixar";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A MESA DA PEÇA PROCESSUAL
 *
 * É a mesma mesa do contrato, do lado judicial, e a diferença não é de
 * forma: é de consequência. Contrato mal revisado volta do cliente;
 * peça mal revisada é protocolada, e o que foi protocolado não volta.
 *
 * O QUE SAIU DA MESA DO CONTRATO
 *
 *   O timbre. Petição leva endereçamento ao juízo no alto e é
 *   protocolada em sistema próprio: papel do escritório ali não tem
 *   função.
 *
 *   A aprovação do cliente. Ele não aprova peça processual. O que
 *   existe aqui é ciência, que é outra coisa e já tem lugar próprio.
 *
 *   O "aprovar e enviar". Quem libera uma peça é a trava de
 *   peticionamento, com a conferência documental e o override
 *   auditado, e ela continua onde está. Esta tela corrige o texto; não
 *   protocola nada.
 *
 * O QUE ENTROU, E NÃO EXISTE NO CONTRATO
 *
 *   O prazo fatal, no alto, sempre visível. Atraso em contrato é
 *   cliente irritado; aqui é preclusão.
 *
 *   O aviso sobre os precedentes. A injeção de jurisprudência sempre
 *   parte do texto-base, então rodar de novo desfaz o que foi corrigido
 *   à mão. Quem edita precisa saber disso ANTES, e não descobrir
 *   depois de perder uma hora de trabalho.
 */
export default function MesaDaPeca() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [p, setP] = useState<any>(null);
  const [texto, setTexto] = useState("");
  const [estado, setEstado] = useState<"" | "salvando" | "salvo" | "erro">("");
  const [salvoEm, setSalvoEm] = useState<Date | null>(null);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState("");
  const [chegouDeFora, setChegouDeFora] = useState<string | null>(null);

  const ultimoSalvo = useRef("");
  const relogio = useRef<any>(null);

  // O texto que vale é o final, que já tem a jurisprudência injetada.
  // Antes de a injeção rodar, o que existe é a base, com as marcações:
  // mostrar ela é melhor do que mostrar nada, e o advogado vê as tags.
  const textoDaPeca = (d: any) =>
    (d?.markdown_final || d?.markdown_base || "");

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/peticoes/${id}`);
      const d = await r.json();
      if (!r.ok) { setErro(d?.detail || "Não consegui abrir a peça."); return; }
      setP(d);
      if (!ultimoSalvo.current) {
        setTexto(textoDaPeca(d));
        ultimoSalvo.current = textoDaPeca(d);
      }
    } catch { setErro("Falha de conexão."); }
  }, [id]);

  useEffect(() => { carregar(); }, [carregar]);

  const salvar = useCallback(async (conteudo: string) => {
    if (!conteudo.trim() || conteudo === ultimoSalvo.current) return;
    setEstado("salvando"); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/peticoes/${id}/texto`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: conteudo, quem: "advogado" }),
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

  const pendente = texto !== ultimoSalvo.current;

  useEffect(() => {
    const avisar = (e: BeforeUnloadEvent) => {
      if (pendente) { e.preventDefault(); e.returnValue = ""; }
    };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [pendente]);

  useEffect(() => {
    const atalho = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault(); salvar(texto);
      }
    };
    window.addEventListener("keydown", atalho);
    return () => window.removeEventListener("keydown", atalho);
  }, [texto, salvar]);

  /* O texto pode mudar sem ser por você: o cliente responde a uma
     pergunta e o especialista ajusta a peça. Sem alteração pendente, a
     tela se atualiza e avisa; com alteração pendente, não toca em nada
     e pergunta. */
  useEffect(() => {
    async function olhar() {
      if (document.hidden) return;
      try {
        const r = await fetch(`${API}/api/v1/peticoes/${id}`);
        const d = await r.json();
        const nova = textoDaPeca(d);
        if (!nova || nova === ultimoSalvo.current) return;
        if (texto === ultimoSalvo.current) {
          ultimoSalvo.current = nova;
          setTexto(nova); setP(d);
          setChegouDeFora("A peça foi atualizada por fora desta tela. Veja "
                          + "na conversa do especialista o que mudou.");
        } else {
          setChegouDeFora("A peça mudou no servidor e você tem alterações "
                          + "não salvas. Salve as suas ou recarregue a "
                          + "página para ver as de lá.");
        }
      } catch { /* a próxima volta tenta de novo */ }
    }
    const t = setInterval(olhar, 10000);
    document.addEventListener("visibilitychange", olhar);
    return () => {
      clearInterval(t);
      document.removeEventListener("visibilitychange", olhar);
    };
  }, [id, texto]);

  async function verOPdf() {
    // Salva antes de gerar: PDF do texto antigo faria o advogado
    // conferir uma versão que já não existe.
    setOcupado("pdf");
    try {
      await salvar(texto);
      window.open(`${API}/api/v1/peticoes/${id}/pdf`, "_blank");
    } finally { setOcupado(""); }
  }

  if (erro && !p) {
    return <main className="p-8 text-sm text-[#ffb3aa]">{erro}</main>;
  }
  if (!p) {
    return <main className="p-8 text-sm text-white/50">Abrindo a peça…</main>;
  }

  const caso = p.casos || {};
  const dias = caso.prazo_fatal
    ? Math.ceil((new Date(caso.prazo_fatal + "T12:00").getTime() - Date.now())
                / 864e5)
    : null;
  const corDoPrazo = dias === null ? "text-white/40"
    : dias < 0 ? "text-[#C0392B]"
    : dias <= 2 ? "text-[#E5A44C]"
    : "text-white/60";

  return (
    <main className="min-h-screen bg-[#0A1628] text-white">
      <div className="sticky top-0 z-10 border-b border-white/10 bg-[#0A1628]/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-5 py-3">
          <button onClick={() => router.push("/judicial")}
            className="text-sm text-white/50 hover:text-white">
            ← voltar
          </button>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-[#C9A24D]">
              {caso.clientes?.nome || caso.titulo || "Peça"}
            </p>
            <p className="text-[11px] text-white/40">
              {p.titulo}
              {caso.numero_processo ? ` · ${caso.numero_processo}` : ""}
              {p.tribunal ? ` · ${p.tribunal}` : ""}
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
            {/* O PRAZO FICA NA BARRA, E NÃO NUMA ABA
                Atraso em contrato é cliente irritado; aqui é preclusão.
                É a única informação que muda o que fazer com todo o
                resto: perto do fim, a resposta certa deixa de ser
                "melhore a fundamentação" e passa a ser "protocole". */}
            {caso.prazo_fatal && (
              <span className={`rounded-lg border border-white/10 px-3 py-2 text-[11px] font-semibold ${corDoPrazo}`}>
                prazo fatal{" "}
                {String(caso.prazo_fatal).slice(8, 10)}/
                {String(caso.prazo_fatal).slice(5, 7)}
                {dias !== null && (
                  <span className="ml-1 font-normal">
                    ({dias < 0 ? `${Math.abs(dias)}d vencido`
                      : dias === 0 ? "é hoje"
                      : dias === 1 ? "amanhã" : `${dias} dias`})
                  </span>
                )}
              </span>
            )}
            <button onClick={() => salvar(texto)}
              disabled={!pendente || estado === "salvando"}
              className="rounded-lg bg-[#C9A24D] px-4 py-2 text-xs font-bold text-[#0A1628] disabled:opacity-35">
              Salvar
            </button>
            <button onClick={verOPdf} disabled={ocupado === "pdf"}
              className="rounded-lg border border-white/20 px-4 py-2 text-xs font-semibold text-white/85 hover:border-white/45 disabled:opacity-40">
              {ocupado === "pdf" ? "Gerando…" : "Ver em PDF"}
            </button>
            <button
              onClick={() => baixarComToken(
                `/api/v1/peticoes/${id}/documento.doc`,
                `${p.titulo || "peca"}.doc`)
                .catch((e) => setErro(e.message || "Não consegui baixar."))}
              className="rounded-lg border border-white/20 px-4 py-2 text-xs text-white/70 hover:border-white/45">
              Baixar em Word
            </button>
          </div>
        </div>
        {erro && (
          <p className="bg-[#C0392B]/20 px-5 py-2 text-center text-[11px] text-[#ffb3aa]">
            {erro}
          </p>
        )}
        {chegouDeFora && (
          <p className="flex items-center justify-center gap-3 bg-[#2D7DD2]/15 px-5 py-2 text-center text-[11px] text-[#9ec8f0]">
            {chegouDeFora}
            <button onClick={() => setChegouDeFora(null)}
              className="underline decoration-dotted hover:text-white">
              entendi
            </button>
          </p>
        )}
      </div>

      <div className="mx-auto max-w-5xl px-5 py-6">
        {/* O AVISO QUE EVITA PERDER UMA HORA DE TRABALHO
            A injeção de precedentes sempre parte do texto-base, então
            rodar de novo refaz o final e desfaz a correção manual. Quem
            edita precisa saber disso antes, e não depois. */}
        {p.status === "COM_PRECEDENTES" && (
          <p className="mb-4 rounded-lg border border-[#E5A44C]/30 bg-[#E5A44C]/5 px-3 py-2 text-[11px] leading-relaxed text-[#E5A44C]">
            Esta peça já recebeu a jurisprudência do banco de precedentes. Se
            alguém rodar os precedentes de novo no painel do caso, a peça é
            remontada a partir do texto-base e as correções feitas aqui se
            perdem. Rode os precedentes primeiro, corrija depois.
          </p>
        )}

        <div className="flex flex-col gap-4 lg:flex-row">
          <textarea
            value={texto}
            onChange={(e) => digitou(e.target.value)}
            spellCheck
            className="min-h-[70vh] flex-1 resize-y rounded-lg border border-white/10 bg-[#F7F5EF] p-10 font-serif text-[15px] leading-[1.8] text-[#1A1A1A] outline-none focus:border-[#C9A24D]"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          />
          <Especialista id={id} texto={texto}
            aoAlterar={(novo) => digitou(novo)} />
        </div>

        <p className="mt-3 text-[11px] leading-relaxed text-white/35">
          Salva sozinho dois segundos depois que você para de digitar, e
          também no Ctrl+S. Protocolar continua no painel do caso, pela trava
          de peticionamento: esta tela corrige o texto, não protocola.
        </p>
      </div>
    </main>
  );
}

/* O ESPECIALISTA DO CASO JUDICIAL
 *
 * O mesmo da mesa do contrato, com outro dossiê e outra régua. Ele lê o
 * processo inteiro: a última publicação, o prazo, a fase judicial, as
 * peças anteriores, os documentos e o que a trava de peticionamento já
 * apontou. E enxerga o texto que está na tela agora, inclusive o que
 * ainda não foi salvo.
 *
 * A trava que mais importa aqui: ele não cita julgado que não tenha
 * vindo do banco de precedentes. Jurisprudência inventada em petição
 * não é erro de redação, é o fim da credibilidade da peça.
 */
function Especialista({ id, texto: naTela, aoAlterar }: {
  id: string; texto: string; aoAlterar: (novo: string) => void;
}) {
  const [antes, setAntes] = useState<string | null>(null);
  const [aplicadas, setAplicadas] = useState<Set<string>>(new Set());
  const [aplicando, setAplicando] = useState(false);

  async function aplicar(lista: any[], marca: string) {
    if (aplicando) return;
    setAplicando(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/alteracoes/aplicar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: naTela, alteracoes: lista }),
      });
      const j = await r.json().catch(() => ({} as any));
      if (!r.ok) { setErro(j?.detail || "Não consegui aplicar."); return; }
      if (j.aplicadas > 0) {
        setAntes(naTela);
        aoAlterar(j.texto);
        setAplicadas((s) => new Set([...s, marca]));
      }
      if ((j.recusadas || []).length > 0) {
        setErro("Não consegui aplicar: "
          + j.recusadas.map((x: any) => x.porque).join("; ")
          + ". O trecho mudou depois da proposta; peça de novo.");
      }
    } catch { setErro("Falha de conexão."); }
    finally { setAplicando(false); }
  }


  const [conversa, setConversa] = useState<any[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [pensando, setPensando] = useState(false);
  const [erro, setErro] = useState("");
  const [aberto, setAberto] = useState(true);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/peticoes/${id}/consultas`);
        const d = await r.json();
        if (Array.isArray(d)) setConversa(d);
      } catch { /* histórico é conforto, não trava a pergunta */ }
    })();
  }, [id]);

  useEffect(() => {
    const c = fim.current?.parentElement;
    if (c) c.scrollTop = c.scrollHeight;
  }, [conversa, pensando]);

  async function mandar(t?: string) {
    const q = (t ?? pergunta).trim();
    if (!q || pensando) return;
    setPergunta(""); setErro(""); setPensando(true);
    const anteriores = conversa;
    setConversa([...anteriores, { pergunta: q, resposta: "",
                                  quem_rotulo: "Advogado",
                                  em: new Date().toISOString() }]);
    try {
      const r = await fetch(`${API}/api/v1/peticoes/${id}/consultar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pergunta: q, quem: "advogado", texto: naTela,
          anteriores: anteriores.slice(-6).map((c: any) => ({
            pergunta: c.pergunta, resposta: c.resposta })),
        }),
      });
      const j = await r.json().catch(() => ({} as any));
      if (!r.ok) {
        setConversa(anteriores);
        setErro([j?.detail || "Não consegui responder.", j?.tecnico]
                  .filter(Boolean).join("  —  "));
        return;
      }
      setConversa([...anteriores, {
        pergunta: q, resposta: j.resposta, propostas: j.propostas,
        ao_cliente: j.ao_cliente, quem_rotulo: "Advogado", em: j.em }]);
    } catch { setConversa(anteriores); setErro("Falha de conexão."); }
    finally { setPensando(false); }
  }

  const atalhos = [
    ["Revisar a peça",
     "Leia a peça que estou editando agora e aponte, em ordem de "
     + "gravidade, o que pode gerar inépcia, nulidade ou perda de "
     + "argumento. Cite trecho, problema e a redação que você usaria."],
    ["Cabe neste momento processual?",
     "Confira esta peça contra o último andamento do processo: ela cabe "
     + "agora, o prazo está de pé, e não há duplicidade?"],
    ["Corrigir o que estiver errado",
     "Corrija no texto o que estiver tecnicamente errado. Aplique as "
     + "alterações e me diga, em uma linha cada, o que mudou e por quê. "
     + "Não mexa no que eu não pedi e não toque nas citações de julgado."],
    ["O que falta no kit documental",
     "O que ainda falta de documento ou informação para esta peça ser "
     + "protocolada com segurança?"],
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
            Ele lê o processo inteiro: a última publicação, o prazo, a fase
            judicial, as peças anteriores, os documentos da pasta e o que a
            trava de peticionamento já apontou. Enxerga o texto que você está
            editando, inclusive o que ainda não foi salvo. Não cita julgado
            que não tenha vindo do banco de precedentes.
          </p>
        )}
        {conversa.map((c, i) => (
          <div key={i} className="space-y-1.5">
            <div>
              <p className="mb-0.5 px-1 text-[10px] font-bold text-white/35">
                {c.quem_rotulo || "Advogado"}
                {c.em && (
                  <span className="ml-2 font-normal text-white/25">
                    {new Date(c.em).toLocaleString("pt-BR", {
                      day: "2-digit", month: "2-digit",
                      hour: "2-digit", minute: "2-digit" })}
                  </span>
                )}
              </p>
              <p className="rounded-lg bg-white/5 px-3 py-2 text-[11px] text-white/75">
                {c.pergunta}
              </p>
            </div>
            {c.resposta ? (
              <div>
                <p className="mb-0.5 px-1 text-[10px] font-bold text-[#2D7DD2]">
                  Especialista do caso
                </p>
                <p className="whitespace-pre-line rounded-lg bg-[#2D7DD2]/10 px-3 py-2 text-[11px] leading-relaxed text-white/85">
                  {c.resposta}
                </p>
              </div>
            ) : (
              <p className="px-3 text-[11px] italic text-white/35">lendo o processo…</p>
            )}

            {(c.ao_cliente || []).length > 0 && (
              <div className="rounded-lg border border-[#E5A44C]/30 bg-[#E5A44C]/5 px-3 py-2">
                <p className="text-[10px] font-bold text-[#E5A44C]">
                  Pergunta enviada ao cliente
                </p>
                {c.ao_cliente.map((q: any, k: number) => (
                  <p key={k} className="mt-1 text-[10px] leading-relaxed text-white/60">
                    · {q.assunto ? <b>{q.assunto}: </b> : null}{q.pergunta}
                  </p>
                ))}
              </div>
            )}

            {/* A PROPOSTA ESPERA O ACEITE

                O especialista não mexe no texto sozinho. Ele mostra o
                que sai e o que entra, e o documento só muda quando o
                advogado clica. Quem assina decide o que entra, e
                autorizar com um clique é mais rápido do que conferir
                depois o que mudou sem aviso.

                A conferência do trecho é refeita no servidor na hora de
                aplicar: entre a proposta e o aceite, o advogado pode ter
                editado justamente aquele parágrafo. */}
            {(c.propostas || []).length > 0 && (
              <div className="space-y-2 rounded-lg border border-[#C9A24D]/30 bg-[#C9A24D]/5 p-2">
                <p className="text-[10px] font-bold text-[#C9A24D]">
                  {c.propostas.length === 1
                    ? "1 alteração proposta, esperando você"
                    : `${c.propostas.length} alterações propostas, esperando você`}
                </p>
                {c.propostas.map((a: any, k: number) => {
                  const feito = aplicadas.has(`${i}-${k}`);
                  return (
                    <div key={k} className="rounded border border-white/10 bg-[#0A1628] p-2">
                      <p className="text-[10px] leading-relaxed text-white/60">
                        {a.motivo}
                      </p>
                      {a.procurar && (
                        <p className="mt-1 whitespace-pre-line break-words text-[10px] leading-relaxed text-[#ff9a8f] line-through">
                          {String(a.procurar).slice(0, 300)}
                        </p>
                      )}
                      <p className="mt-0.5 whitespace-pre-line break-words text-[10px] leading-relaxed text-[#9ae6a4]">
                        {String(a.substituir || "").slice(0, 300)
                          || "(o trecho sai do documento)"}
                      </p>
                      <button
                        onClick={() => aplicar([a], `${i}-${k}`)}
                        disabled={feito || aplicando}
                        className="mt-1.5 rounded bg-[#1DB954] px-2.5 py-1 text-[10px] font-bold text-white disabled:opacity-40">
                        {feito ? "aplicada" : "Aplicar esta"}
                      </button>
                    </div>
                  );
                })}
                {c.propostas.length > 1 && (
                  <button
                    onClick={() => aplicar(c.propostas, `${i}-todas`)}
                    disabled={aplicando}
                    className="w-full rounded bg-[#C9A24D] px-3 py-1.5 text-[10px] font-bold text-[#0A1628] disabled:opacity-40">
                    Aplicar todas
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={fim} />
      </div>

      {antes !== null && (
        <button onClick={() => { aoAlterar(antes); setAntes(null); }}
          className="px-3 pb-2 text-left text-[10px] text-white/45 underline decoration-dotted hover:text-white">
          desfazer a última alteração aplicada
        </button>
      )}
      {erro && <p className="px-3 pb-2 text-[11px] text-[#ffb3aa]">{erro}</p>}

      <div className="space-y-2 border-t border-white/10 p-3">
        <div className="flex flex-wrap gap-1.5">
          {atalhos.map(([rotulo, t]) => (
            <button key={rotulo} onClick={() => mandar(t)} disabled={pensando}
              className="rounded-full border border-white/15 px-2.5 py-1 text-[10px] text-white/55 hover:border-white/40 hover:text-white/85 disabled:opacity-40">
              {rotulo}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={pergunta} onChange={(e) => setPergunta(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") mandar(); }}
            placeholder="pergunte sobre o processo ou a peça…"
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
