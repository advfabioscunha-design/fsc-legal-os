"use client";
import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";
const GRUPOS = ["BANCARIO", "IMOBILIARIO", "TRABALHISTA", "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"];

export default function CasoDetalhe({ casoId, onFechar, onMudou }: { casoId: string; onFechar: () => void; onMudou: () => void }) {
  const [caso, setCaso] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [nota, setNota] = useState("");
  const [solicitacao, setSolicitacao] = useState("");
  const [novaFase, setNovaFase] = useState("");
  const [linkNome, setLinkNome] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);

  // campos editáveis
  const [edit, setEdit] = useState({ relato_inicial: "", grupo: "", honorarios: "", numero_processo: "" });

  async function carregar() {
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/v1/casos/${casoId}`);
      const d = await r.json();
      setCaso(d);
      setEdit({
        relato_inicial: d.relato_inicial || "", grupo: d.grupo || "",
        honorarios: d.honorarios_valor || "", numero_processo: d.numero_processo || "",
      });
    } catch { setCaso(null); }
    finally { setCarregando(false); }
  }
  useEffect(() => { carregar(); /* eslint-disable-next-line */ }, [casoId]);

  async function salvarCampos() {
    setSalvando(true);
    try {
      await fetch(`${API}/api/v1/casos/${casoId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(edit),
      });
      await carregar(); onMudou();
    } finally { setSalvando(false); }
  }

  async function addNota() {
    if (!nota.trim()) return;
    await fetch(`${API}/api/v1/casos/${casoId}/nota`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: nota }),
    });
    setNota(""); carregar();
  }

  async function addLink() {
    if (!linkUrl.trim()) return;
    await fetch(`${API}/api/v1/casos/${casoId}/documentos`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: linkNome || linkUrl, url: linkUrl, tipo: "LINK" }),
    });
    setLinkNome(""); setLinkUrl(""); carregar();
  }

  async function enviarArquivo(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("arquivo", f);
    await fetch(`${API}/api/v1/casos/${casoId}/documentos/upload`, { method: "POST", body: fd });
    if (fileRef.current) fileRef.current.value = "";
    carregar();
  }

  async function acao(tipo: "suspender" | "arquivar" | "ativar" | "iniciar") {
    let body: any = undefined;
    if (tipo === "suspender" || tipo === "arquivar") {
      const motivo = window.prompt(tipo === "suspender" ? "Motivo da suspensão:" : "Motivo do arquivamento:");
      if (motivo === null) return;
      body = JSON.stringify({ motivo });
    }
    await fetch(`${API}/api/v1/casos/${casoId}/${tipo}`, {
      method: "POST", headers: body ? { "Content-Type": "application/json" } : undefined, body,
    });
    onMudou();
    if (tipo !== "iniciar") onFechar();
    else carregar();
  }

  async function acionarCliente() {
    if (!solicitacao.trim()) return;
    await fetch(`${API}/api/v1/casos/${casoId}/acionar-cliente`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ solicitacao }),
    });
    setSolicitacao(""); carregar();
  }

  async function aprovarEtapa() {
    const r = await fetch(`${API}/api/v1/casos/${casoId}/aprovar-etapa`, { method: "POST" });
    if (!r.ok) { const e = await r.json().catch(() => ({})); alert(e.detail || "Não foi possível avançar."); return; }
    onMudou(); carregar();
  }

  async function acaoHumana() {
    const r = await fetch(`${API}/api/v1/casos/${casoId}/escalar?motivo=DIFICULDADE&detalhe=${encodeURIComponent("Não resolvido — intervenção direta")}`, { method: "POST" });
    if (!r.ok) { alert("Não foi possível escalar neste estágio. Avance/ajuste a etapa antes."); return; }
    onMudou(); onFechar();
  }

  async function retomar() {
    await fetch(`${API}/api/v1/casos/${casoId}/retomar`, { method: "POST" });
    onMudou(); carregar();
  }

  async function moverFase() {
    if (!novaFase) return;
    await fetch(`${API}/api/v1/casos/${casoId}/mover-fase`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fase: novaFase }),
    });
    setNovaFase(""); onMudou(); carregar();
  }

  function baixar() {
    window.open(`${API}/api/v1/casos/${casoId}/download`, "_blank");
  }

  async function excluir() {
    if (!window.confirm("Excluir DEFINITIVAMENTE este caso? Esta ação não pode ser desfeita.")) return;
    await fetch(`${API}/api/v1/casos/${casoId}`, { method: "DELETE" });
    onMudou(); onFechar();
  }

  const ehEscritorio = caso?.clientes?.origem === "ESCRITORIO";
  const situacao = caso?.situacao || "ATIVO";

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onFechar}>
      <div onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-2xl overflow-y-auto bg-[#0F2A44] text-white shadow-2xl">
        {/* header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0F2A44] px-5 py-3">
          <div>
            <p className="text-lg font-bold">{caso?.clientes?.nome ?? "Caso"}</p>
            <p className="text-xs text-white/55">
              {situacao !== "ATIVO" && <span className="mr-2 rounded bg-white/15 px-1.5 py-0.5">{situacao}</span>}
              {caso?.estado} {ehEscritorio && <span className="text-[#C9A84C]">· ★ Escritório</span>}
            </p>
          </div>
          <button onClick={onFechar} className="text-white/60 hover:text-white">✕</button>
        </div>

        {carregando ? (
          <p className="p-6 text-white/50">Carregando...</p>
        ) : !caso ? (
          <p className="p-6 text-white/50">Não foi possível carregar o caso.</p>
        ) : (
          <div className="space-y-6 p-5">
            {caso.aguardando_cliente && (
              <div className="rounded-lg border border-[#F39C12]/40 bg-[#F39C12]/10 p-3">
                <p className="text-sm font-semibold text-[#F39C12]">⏸ Fora da produção — aguardando o cliente</p>
                <p className="mt-1 text-sm text-white/75">{caso.aguardando_desc}</p>
                <button onClick={retomar} className="mt-2 rounded-lg bg-[#1DB954] px-4 py-1.5 text-sm font-bold text-white hover:bg-[#17a349]">
                  Cliente respondeu — retomar produção
                </button>
              </div>
            )}

            {/* Dados editáveis */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Informações do caso</h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="text-xs text-white/60">Contato
                  <input disabled value={caso.clientes?.email || caso.clientes?.whatsapp || "—"}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-[#0A1628]/60 px-3 py-2 text-sm text-white/70" />
                </label>
                <label className="text-xs text-white/60">CPF/CNPJ
                  <input disabled value={caso.clientes?.cpf_cnpj || "—"}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-[#0A1628]/60 px-3 py-2 text-sm text-white/70" />
                </label>
                <label className="text-xs text-white/60">Grupo
                  <select value={edit.grupo} onChange={(e) => setEdit({ ...edit, grupo: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm">
                    <option value="">—</option>
                    {GRUPOS.map((g) => <option key={g} value={g}>{g}</option>)}
                  </select>
                </label>
                <label className="text-xs text-white/60">Nº do processo
                  <input value={edit.numero_processo} onChange={(e) => setEdit({ ...edit, numero_processo: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
                <label className="text-xs text-white/60">Honorários
                  <input value={edit.honorarios} onChange={(e) => setEdit({ ...edit, honorarios: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                </label>
              </div>
              <label className="mt-3 block text-xs text-white/60">Relato / informações coletadas
                <textarea value={edit.relato_inicial} onChange={(e) => setEdit({ ...edit, relato_inicial: e.target.value })} rows={4}
                  className="mt-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              </label>
              <button onClick={salvarCampos} disabled={salvando}
                className="mt-2 rounded-lg bg-[#C9A84C] px-4 py-2 text-sm font-bold text-[#0A1628] disabled:opacity-50">
                {salvando ? "Salvando..." : "Salvar alterações"}
              </button>
            </section>

            {/* Documentos */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Documentos e provas</h3>
              <ul className="space-y-2">
                {(caso.documentos || []).map((d: any) => {
                  const url = (d.storage_path || "").startsWith("http") ? d.storage_path : null;
                  return (
                    <li key={d.id} className="flex items-center justify-between rounded-lg border border-white/10 bg-[#0A1628]/50 px-3 py-2 text-sm">
                      <span className="truncate">{d.observacao || d.tipo}</span>
                      {url ? <a href={url} target="_blank" rel="noreferrer" className="text-[#C9A84C] hover:underline">abrir</a>
                           : <span className="text-xs text-white/40">{d.tipo}</span>}
                    </li>
                  );
                })}
                {(caso.documentos || []).length === 0 && <li className="text-xs text-white/40">Nenhum documento ainda.</li>}
              </ul>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-dashed border-white/15 p-3">
                  <p className="mb-1 text-xs text-white/60">Anexar do computador</p>
                  <input ref={fileRef} type="file" onChange={enviarArquivo} className="text-xs text-white/70 file:mr-2 file:rounded file:border-0 file:bg-[#C9A84C] file:px-2 file:py-1 file:text-[#0A1628]" />
                </div>
                <div className="rounded-lg border border-dashed border-white/15 p-3">
                  <p className="mb-1 text-xs text-white/60">Anexar link (Drive/nuvem)</p>
                  <input value={linkNome} onChange={(e) => setLinkNome(e.target.value)} placeholder="Nome (opcional)"
                    className="mb-1 w-full rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-xs" />
                  <div className="flex gap-1">
                    <input value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://..."
                      className="flex-1 rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-xs" />
                    <button onClick={addLink} className="rounded bg-[#C9A84C] px-2 py-1 text-xs font-bold text-[#0A1628]">+</button>
                  </div>
                </div>
              </div>
            </section>

            {/* Acionar cliente */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Acionar o cliente (WhatsApp)</h3>
              <p className="mb-2 text-xs text-white/55">Digite o que precisa do cliente (informação, documento, assinatura, pagamento). Vai para o agente de triagem do WhatsApp coletar e devolver à esteira.</p>
              <textarea value={solicitacao} onChange={(e) => setSolicitacao(e.target.value)} rows={2} placeholder="Ex.: Enviar RG e comprovante de residência..."
                className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
              <button onClick={acionarCliente} className="mt-2 rounded-lg bg-[#2D7DD2] px-4 py-2 text-sm font-bold text-white hover:bg-[#256bb3]">Enviar ao cliente</button>
            </section>

            {/* Histórico / notas */}
            <section>
              <h3 className="mb-2 text-sm font-bold text-[#C9A84C]">Histórico do atendimento</h3>
              <div className="max-h-60 space-y-2 overflow-y-auto rounded-lg border border-white/10 bg-[#0A1628]/40 p-3">
                {(caso.mensagens || []).map((m: any) => (
                  <div key={m.id} className="text-sm">
                    <span className={`text-[10px] uppercase ${m.autor === "CLIENTE" ? "text-[#2D7DD2]" : m.autor === "HUMANO" ? "text-[#C9A84C]" : "text-white/40"}`}>{m.autor}</span>
                    <p className="whitespace-pre-wrap text-white/80">{m.conteudo}</p>
                  </div>
                ))}
                {(caso.mensagens || []).length === 0 && <p className="text-xs text-white/40">Sem mensagens.</p>}
              </div>
              <div className="mt-2 flex gap-2">
                <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Acrescentar informação / nota interna"
                  className="flex-1 rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm" />
                <button onClick={addNota} className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold hover:bg-white/20">Adicionar</button>
              </div>
            </section>

            {/* Ações */}
            <section className="border-t border-white/10 pt-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <button onClick={baixar} className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold hover:bg-white/20">⬇ Baixar processo (.zip / Word)</button>
                <select value={novaFase} onChange={(e) => setNovaFase(e.target.value)}
                  className="rounded-lg border border-white/15 bg-[#0A1628] px-3 py-2 text-sm">
                  <option value="">Mover para fase…</option>
                  {["QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO", "COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO", "PROTOCOLADO"].map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
                <button onClick={moverFase} className="rounded-lg bg-[#2D7DD2] px-3 py-2 text-sm font-semibold text-white hover:bg-[#256bb3]">Mover</button>
              </div>
              <div className="flex flex-wrap gap-2">
                {ehEscritorio && situacao === "ATIVO" && (
                  <button onClick={() => acao("iniciar")} className="rounded-lg bg-[#1DB954] px-4 py-2 text-sm font-bold text-white hover:bg-[#17a349]">
                    ▶ Iniciar na Esteira
                  </button>
                )}
                {situacao === "ATIVO" ? (
                  <>
                    <button onClick={() => acao("suspender")} className="rounded-lg bg-[#F39C12]/20 px-4 py-2 text-sm font-semibold text-[#F39C12] hover:bg-[#F39C12]/30">Suspender</button>
                    <button onClick={() => acao("arquivar")} className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white/80 hover:bg-white/20">Arquivar</button>
                  </>
                ) : (
                  <button onClick={() => acao("ativar")} className="rounded-lg bg-[#1DB954] px-4 py-2 text-sm font-bold text-white hover:bg-[#17a349]">Ativar caso (voltar à esteira)</button>
                )}
                {situacao === "ATIVO" && (
                  <>
                    <button onClick={aprovarEtapa} className="rounded-lg bg-[#1DB954]/20 px-4 py-2 text-sm font-semibold text-[#1DB954] hover:bg-[#1DB954]/30">Aprovar para continuar</button>
                    <button onClick={acaoHumana} className="rounded-lg bg-[#C0392B]/15 px-4 py-2 text-sm font-semibold text-[#e07a6f] hover:bg-[#C0392B]/25">Ação humana (não resolvido)</button>
                  </>
                )}
                <button onClick={excluir} className="ml-auto rounded-lg bg-[#C0392B]/20 px-4 py-2 text-sm font-semibold text-[#C0392B] hover:bg-[#C0392B]/30">Excluir</button>
              </div>
              {caso.situacao_motivo && <p className="mt-2 text-xs text-white/50">Motivo: {caso.situacao_motivo}</p>}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
