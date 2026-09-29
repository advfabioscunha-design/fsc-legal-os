"use client";
import { useCallback, useEffect, useState } from "react";
import PainelLayout from "../components/PainelLayout";
import VisualizadorProtegido from "../components/VisualizadorProtegido";

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
  { f: "COLETA", l: "Coleta", cor: "#8899AA", cliente: true },
  { f: "CIENCIA", l: "Ciência", cor: "#E5A44C", cliente: true },
  { f: "PAGAMENTO", l: "Pagamento", cor: "#E5A44C", cliente: true },
  { f: "REDACAO", l: "Redação", cor: "#2D7DD2", cliente: false },
  { f: "REVISAO_IA", l: "Revisão", cor: "#2D7DD2", cliente: false },
  { f: "AJUSTE", l: "Ajuste", cor: "#2D7DD2", cliente: false },
  { f: "REVISAO_ADV", l: "Revisão do advogado", cor: "#C0392B", cliente: false },
  { f: "APROVACAO", l: "Com o cliente", cor: "#E5A44C", cliente: true },
  { f: "ASSINATURA", l: "Assinatura", cor: "#16A085", cliente: true },
  { f: "ENTREGUE", l: "Entregue", cor: "#1DB954", cliente: false },
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
  const [aba, setAba] = useState<"pedido" | "minuta" | "conversa">("pedido");
  const [msg, setMsg] = useState("");
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");

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

  async function acao(caminho: string, corpo: any = {}, rotulo = "") {
    setOcupado(rotulo || caminho); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/pedidos/${id}${caminho}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(j?.detail || "Não deu certo."); return; }
      await carregar(); recarregar();
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
          <button onClick={fechar} className="text-xl text-white/40 hover:text-white">×</button>
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
        <div className="mb-4 rounded-xl border border-[#C9A24D]/30 bg-[#C9A24D]/5 p-3">
          <p className="mb-2 text-[11px] font-bold text-[#C9A24D]">O que fazer agora</p>
          {fase === "PAGAMENTO" && (
            <BaixaPix onConfirmar={(txid) => acao("/pagamento", { txid, quem: "escritório" }, "pago")}
              ocupado={ocupado === "pago"} />
          )}
          {fase === "REDACAO" && (
            <Botao rotulo="Redigir a minuta" ocupado={ocupado === "redigir"}
              onClick={() => acao("/redigir", {}, "redigir")}
              nota="O redator escreve seguindo a legislação do tipo." />
          )}
          {fase === "REVISAO_IA" && (
            <Botao rotulo="Revisar" ocupado={ocupado === "revisar"}
              onClick={() => acao("/revisar", {}, "revisar")}
              nota="O revisor lê a íntegra e anota o que precisa mudar." />
          )}
          {fase === "AJUSTE" && (
            <Botao rotulo="Aplicar os apontamentos" ocupado={ocupado === "ajustar"}
              onClick={() => acao("/ajustar", {}, "ajustar")}
              nota="Reescreve a minuta atendendo a revisão. A anterior fica guardada." />
          )}
          {fase === "REVISAO_ADV" && (
            <div>
              <p className="mb-2 text-[11px] leading-relaxed text-white/60">
                Leia a minuta na aba ao lado. Nada chega ao cliente sem esta leitura.
              </p>
              <Botao rotulo="Aprovar e enviar ao cliente" ocupado={ocupado === "liberar"}
                onClick={() => acao("/liberar?quem=advogado", {}, "liberar")} />
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

        <div className="mb-3 flex gap-2">
          {(["pedido", "minuta", "conversa"] as const).map((a) => (
            <button key={a} onClick={() => setAba(a)}
              className={`${btn} ${aba === a ? "bg-[#C9A24D] text-[#0A1628]" : "border border-white/15 text-white/60"}`}>
              {a === "pedido" ? "Pedido" : a === "minuta" ? "Minuta" : `Conversa (${conversa.length})`}
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
            {p.minuta ? (
              <div className="rounded-xl border border-white/10 bg-[#0B1F3B] p-3">
                <pre className="whitespace-pre-wrap text-[11px] leading-relaxed text-white/80">
                  {p.minuta}
                </pre>
              </div>
            ) : (
              <p className="text-xs text-white/40">A minuta ainda não foi escrita.</p>
            )}
          </div>
        )}

        {aba === "conversa" && (
          <div className="space-y-2">
            {conversa.map((m) => (
              <div key={m.id}
                className={`rounded-lg px-3 py-2 text-[11px] leading-relaxed ${m.autor === "CLIENTE"
                  ? "bg-white/5 text-white/80"
                  : "bg-[#2D7DD2]/15 text-white/80"}`}>
                <p className="mb-0.5 text-[10px] font-bold text-white/40">
                  {m.autor === "CLIENTE" ? "Cliente" : m.autor === "AGENTE" ? "Agente" : "Escritório"}
                </p>
                <p className="whitespace-pre-line">{m.texto}</p>
              </div>
            ))}
            {conversa.length === 0 && (
              <p className="text-xs text-white/40">Sem conversa ainda.</p>
            )}
            <div className="flex gap-2 pt-2">
              <input value={msg} onChange={(e) => setMsg(e.target.value)}
                placeholder="escrever para o cliente…" className={inp} />
              <button
                onClick={async () => {
                  if (!msg.trim()) return;
                  await fetch(`${API}/api/v1/contratos/pedidos/${id}/mensagem`, {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ texto: msg, autor: "ESCRITORIO" }),
                  });
                  setMsg(""); carregar();
                }}
                className={`${btn} shrink-0 bg-[#C9A24D] text-[#0A1628]`}>Enviar</button>
            </div>
          </div>
        )}
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
