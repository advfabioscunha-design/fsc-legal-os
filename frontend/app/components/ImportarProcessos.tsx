"use client";
import { useState } from "react";
import { porOab, porProcesso, FonteOcupada } from "../../lib/cnj";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

// OAB do escritório — usada quando o campo fica em branco.
const OAB_PADRAO = { numero: "10849", uf: "RO" };

/* CARREGAR PROCESSOS DO ACERVO

   Duas portas, as duas gratuitas, lendo o Diário de Justiça Eletrônico
   Nacional do CNJ:

     POR OAB     traz tudo que foi publicado no nome do escritório.
     POR NÚMERO  um processo, com o histórico de publicações dele.

   A tela é de duas etapas de propósito. Primeiro mostra o que achou, o
   que disso já existe aqui e qual cliente cada processo parece ser;
   depois grava só o que foi marcado. Importar acervo inteiro sem olhar
   duplica cliente e enche a esteira de processo que não é do escritório
   — a conferência de um minuto evita a limpeza de uma tarde. */

type Item = {
  numero_processo: string;
  tribunal?: string; orgao?: string; classe?: string;
  ultimo_ato?: string; ultima_data?: string; publicacoes?: number;
  cliente_provavel?: string | null; cliente_cadastrado?: string | null;
  transitou?: boolean; fase_sugerida?: string;
  arquivado?: boolean; motivo_arquivado?: string | null;
  ja_na_plataforma?: boolean; caso_id?: string | null;
  comunicacoes?: any[];
};

/* Períodos. Cinco anos cabem numa consulta só: medido na OAB do
   escritório, 1.161 publicações em 5 anos, resposta em segundos. */
const PERIODOS = [
  { d: 30, l: "30 dias" }, { d: 90, l: "3 meses" }, { d: 180, l: "6 meses" },
  { d: 365, l: "1 ano" }, { d: 730, l: "2 anos" }, { d: 1095, l: "3 anos" },
  { d: 1825, l: "5 anos" },
];

export default function ImportarProcessos({
  fase, onFechar, onPronto,
}: { fase: "JUDICIAL" | "RECEBIMENTO"; onFechar: () => void; onPronto: () => void }) {
  const [modo, setModo] = useState<"oab" | "numero">("oab");
  const [dias, setDias] = useState(1825);
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [confirmarDatajud, setConfirmarDatajud] = useState(false);
  const [tribunal, setTribunal] = useState("");
  const [progresso, setProgresso] = useState<{lidas:number;total:number}|null>(null);
  const [resumo, setResumo] = useState<any>(null);
  const [numero, setNumero] = useState("");
  const [oab, setOab] = useState("");
  const [uf, setUf] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [erro, setErro] = useState("");
  const [itens, setItens] = useState<Item[]>([]);
  const [marcados, setMarcados] = useState<Record<string, boolean>>({});
  const [nomes, setNomes] = useState<Record<string, string>>({});
  const [gravando, setGravando] = useState(false);
  const [resultado, setResultado] = useState<any>(null);

  async function buscar() {
    setBuscando(true); setErro(""); setItens([]); setResultado(null);
    setProgresso(null); setResumo(null);
    let aviso = "";
    try {
      /* A consulta ao CNJ sai deste navegador (ver lib/cnj.ts): o
         servidor do escritório fica fora do Brasil e o CNJ recusa. */
      let comunicacoes: any[];
      if (modo === "oab") {
        const r = await porOab(oab || OAB_PADRAO.numero, uf || OAB_PADRAO.uf, dias,
          { onProgresso: (lidas, total) => setProgresso({ lidas, total }) });
        comunicacoes = r.itens;
        if (r.falhas.length) {
          aviso = `O Diário não devolveu ${r.falhas.length} página(s) desta consulta — ` +
                  `o que veio está aqui, mas pode faltar processo. Vale repetir a busca.`;
        }
      } else {
        comunicacoes = await porProcesso(numero);
      }
      if (!comunicacoes.length) {
        setErro(modo === "oab"
          ? "Nada publicado para esta OAB no período escolhido."
          : "Nada publicado no DJEN para este número. Confira o número ou cadastre o processo manualmente.");
        return;
      }
      const r = await fetch(`${API}/api/v1/processos/previa-do-navegador`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comunicacoes, confirmar_no_datajud: confirmarDatajud }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(d.detail || `Erro ${r.status}`); return; }
      const lista: Item[] = d.itens || [];
      setItens(lista);
      setResumo(d);
      /* Marcado por padrão: só o que está ATIVO e ainda não está aqui.
         Processo arquivado não entra na esteira sem alguém dizer que
         deve entrar — encher a tela de trabalho com processo morto é o
         jeito mais rápido de fazer a equipe parar de olhar a tela. */
      const m: Record<string, boolean> = {};
      lista.forEach((i) => { m[i.numero_processo] = !i.ja_na_plataforma && !i.arquivado; });
      setMarcados(m);
      if (d.aviso) aviso = d.aviso;
      if (aviso) setErro(aviso);
    } catch (e: any) {
      setErro(e instanceof FonteOcupada
        ? `O Diário do CNJ não respondeu agora (${e.message}). É instabilidade comum da fonte — tente de novo em alguns minutos.`
        : "Não foi possível concluir a consulta.");
    } finally { setBuscando(false); setProgresso(null); }
  }

  async function importar() {
    const escolhidos = itens
      .filter((i) => marcados[i.numero_processo])
      .map((i) => ({
        numero_processo: i.numero_processo,
        comunicacoes: i.comunicacoes,
        caso_id: i.caso_id,
        cliente_nome: nomes[i.numero_processo] ?? i.cliente_provavel ?? null,
        fase: i.fase_sugerida === "RECEBIMENTO" ? "RECEBIMENTO" : fase,
      }));
    if (!escolhidos.length) { setErro("Marque ao menos um processo."); return; }
    setGravando(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/processos/importar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ processos: escolhidos, fase }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(d.detail || `Erro ${r.status}`); return; }
      setResultado(d);
      onPronto();
    } catch {
      setErro("Não foi possível falar com o servidor.");
    } finally { setGravando(false); }
  }

  /* Filtro por tribunal: o escritório atua em onze, de e-SAJ a eproc,
     e a lista de 5 anos vem misturada. A lista de siglas sai do próprio
     resultado — nada de combo fixo que envelhece. */
  const tribunais = Array.from(new Set(itens.map((i) => i.tribunal).filter(Boolean))).sort();
  const visiveis = itens
    .filter((i) => mostrarArquivados || !i.arquivado)
    .filter((i) => !tribunal || i.tribunal === tribunal);
  const marcadosN = itens.filter((i) => marcados[i.numero_processo]).length;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4"
      onClick={onFechar}>
      <div onClick={(e) => e.stopPropagation()}
        className="my-6 w-full max-w-4xl rounded-2xl bg-[#0F2A44] p-6 text-white shadow-2xl">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-lg font-bold">
            Carregar processos — fase {fase === "JUDICIAL" ? "judicializado" : "de execução"}
          </h2>
          <button onClick={onFechar} className="text-white/60 hover:text-white">✕</button>
        </div>
        <p className="mb-4 text-xs text-white/50">
          Fonte: Diário de Justiça Eletrônico Nacional (CNJ) — pública e sem custo.
          Traz o que foi publicado; intimação feita só no portal do tribunal não aparece aqui.
        </p>

        {/* Como buscar */}
        <div className="mb-3 flex gap-2">
          {([["oab", "Pela OAB"], ["numero", "Pelo número do processo"]] as const).map(([k, l]) => (
            <button key={k} onClick={() => { setModo(k); setItens([]); setErro(""); }}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                modo === k ? "bg-[#C9A84C] text-[#0A1628]" : "bg-white/5 text-white/60 hover:text-white"}`}>
              {l}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-2 rounded-xl border border-white/10 bg-[#0A1628]/60 p-3">
          {modo === "oab" ? (
            <>
              <label className="text-xs text-white/50">
                OAB (vazio = a do escritório)
                <input value={oab} onChange={(e) => setOab(e.target.value)} placeholder="10849"
                  className="mt-1 block w-28 rounded-lg border border-white/15 bg-[#0A1628] px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" />
              </label>
              <label className="text-xs text-white/50">
                UF
                <input value={uf} onChange={(e) => setUf(e.target.value.toUpperCase())} placeholder="RO" maxLength={2}
                  className="mt-1 block w-16 rounded-lg border border-white/15 bg-[#0A1628] px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" />
              </label>
              <label className="text-xs text-white/50">
                Período
                <select value={dias} onChange={(e) => setDias(Number(e.target.value))}
                  className="mt-1 block rounded-lg border border-white/15 bg-[#0A1628] px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]">
                  {PERIODOS.map((p) => <option key={p.d} value={p.d}>{p.l}</option>)}
                </select>
              </label>
            </>
          ) : (
            <label className="flex-1 text-xs text-white/50">
              Número do processo (CNJ, 20 dígitos)
              <input value={numero} onChange={(e) => setNumero(e.target.value)}
                placeholder="0000000-00.0000.0.00.0000"
                className="mt-1 block w-full rounded-lg border border-white/15 bg-[#0A1628] px-3 py-1.5 text-sm outline-none focus:border-[#C9A84C]" />
            </label>
          )}
          <button onClick={buscar} disabled={buscando}
            className="rounded-lg bg-[#2D7DD2] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#3a8ae0] disabled:opacity-50">
            {buscando ? "Consultando o CNJ…" : "Buscar"}
          </button>
          {progresso && (
            <span className="text-xs text-white/55">
              {progresso.lidas} de {progresso.total} publicações lidas…
            </span>
          )}
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-white/55"
            title="Confere no DataJud, pelo código do movimento, cada processo que o texto marcou como arquivado. Uma consulta por processo — mais devagar, e mais seguro.">
            <input type="checkbox" checked={confirmarDatajud}
              onChange={(e) => setConfirmarDatajud(e.target.checked)}
              className="h-3.5 w-3.5 accent-[#C9A84C]" />
            conferir arquivados no DataJud
          </label>
        </div>

        {erro && (
          <p className="mt-3 rounded-lg border border-[#E5A44C]/40 bg-[#E5A44C]/10 px-3 py-2 text-xs text-[#E5A44C]">
            {erro}
          </p>
        )}

        {resultado && (
          <div className="mt-3 rounded-lg border border-[#1DB954]/40 bg-[#1DB954]/10 px-3 py-2 text-xs text-[#1DB954]">
            {resultado.criados} processo(s) cadastrado(s), {resultado.atualizados} atualizado(s),{" "}
            {resultado.intimacoes} publicação(ões) e {resultado.prazos} prazo(s) registrados.
            <span className="block text-white/50">
              Os prazos entraram estimados pelo tipo de ato, com a data de trabalho dois dias
              antes do prazo fatal. Confira a contagem antes de trabalhar cada peça.
            </span>
          </div>
        )}

        {/* O que foi encontrado */}
        {itens.length > 0 && (
          <>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-white/55">
              <span>
                {itens.length} processo(s) — <b className="text-white/80">{resumo?.ativos ?? itens.length} ativo(s)</b>
                {resumo?.arquivados ? `, ${resumo.arquivados} arquivado(s)` : ""} · {marcadosN} marcado(s)
              </span>
              <div className="flex items-center gap-3">
                <select value={tribunal} onChange={(e) => setTribunal(e.target.value)}
                  className="rounded border border-white/15 bg-[#0A1628] px-2 py-1 text-xs outline-none focus:border-[#C9A84C]">
                  <option value="">todos os tribunais</option>
                  {tribunais.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <label className="flex cursor-pointer items-center gap-1.5">
                  <input type="checkbox" checked={mostrarArquivados}
                    onChange={(e) => setMostrarArquivados(e.target.checked)}
                    className="h-3.5 w-3.5 accent-[#C9A84C]" />
                  mostrar arquivados
                </label>
                <button onClick={() => setMarcados(Object.fromEntries(
                  visiveis.filter((i) => !i.arquivado).map((i) => [i.numero_processo, true])))}
                  className="hover:text-white">marcar os ativos</button>
                <button onClick={() => setMarcados({})} className="hover:text-white">limpar</button>
              </div>
            </div>
            <div className="mt-2 max-h-[45vh] space-y-2 overflow-y-auto pr-1">
              {visiveis.map((i) => (
                <label key={i.numero_processo}
                  className={`flex cursor-pointer gap-3 rounded-lg border p-3 transition ${
                    marcados[i.numero_processo] ? "border-[#C9A84C]/50 bg-[#C9A84C]/5"
                                               : "border-white/10 bg-[#0A1628]/40"}`}>
                  <input type="checkbox" checked={!!marcados[i.numero_processo]}
                    onChange={(e) => setMarcados({ ...marcados, [i.numero_processo]: e.target.checked })}
                    className="mt-1 h-4 w-4 shrink-0 accent-[#C9A84C]" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm text-white">{i.numero_processo}</span>
                      <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-white/70">{i.tribunal}</span>
                      {i.ja_na_plataforma && (
                        <span className="rounded bg-[#2D7DD2]/20 px-1.5 py-0.5 text-[10px] text-[#2D7DD2]">
                          já na plataforma
                        </span>
                      )}
                      {i.transitou && (
                        <span className="rounded bg-[#C9A84C]/20 px-1.5 py-0.5 text-[10px] text-[#C9A84C]">
                          trânsito em julgado
                        </span>
                      )}
                      {i.fase_sugerida === "RECEBIMENTO" && !i.arquivado && (
                        <span className="rounded bg-[#1DB954]/20 px-1.5 py-0.5 text-[10px] text-[#1DB954]">
                          entra em execução
                        </span>
                      )}
                      {i.arquivado && (
                        <span className="rounded bg-[#5A6B7C]/30 px-1.5 py-0.5 text-[10px] text-white/60"
                          title={i.motivo_arquivado || ""}>
                          arquivado — {i.motivo_arquivado}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 truncate text-xs text-white/55">
                      {i.classe} · {i.orgao} · último ato: {i.ultimo_ato} em{" "}
                      {i.ultima_data ? new Date(i.ultima_data + "T12:00").toLocaleDateString("pt-BR") : "—"}{" "}
                      · {i.publicacoes} publicação(ões)
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <span className="text-[11px] text-white/40">Cliente:</span>
                      <input
                        value={nomes[i.numero_processo] ?? i.cliente_cadastrado ?? i.cliente_provavel ?? ""}
                        onChange={(e) => setNomes({ ...nomes, [i.numero_processo]: e.target.value })}
                        onClick={(e) => e.preventDefault()}
                        placeholder="quem é o cliente neste processo"
                        className="flex-1 rounded border border-white/10 bg-[#0A1628] px-2 py-1 text-xs outline-none focus:border-[#C9A84C]" />
                    </div>
                  </div>
                </label>
              ))}
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <button onClick={onFechar}
                className="rounded-lg border border-white/15 px-4 py-2 text-sm text-white/70 hover:text-white">
                Fechar
              </button>
              <button onClick={importar} disabled={gravando || !marcadosN}
                className="rounded-lg bg-[#C9A84C] px-5 py-2 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e] disabled:opacity-40">
                {gravando ? "Cadastrando…" : `Cadastrar ${marcadosN} processo(s)`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
