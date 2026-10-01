"use client";
import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* ── O QUE JÁ FOI RESOLVIDO, FORA DO CAMINHO ───────────────────
 *
 * As caixas de tarefa, pendência, intimação e prazo acumulam. O que
 * foi resolvido continua na lista, e depois de alguns meses a tela de
 * trabalho vira arquivo morto com um punhado de itens vivos no meio.
 * Quem abre para ver o que falta fazer gasta o tempo filtrando com os
 * olhos, e é assim que um prazo vivo passa despercebido.
 *
 * O resolvido sai da tela principal e vem para cá, que é um arquivo e
 * não uma lixeira: ele continua existindo, continua pesquisável, e
 * continua servindo à prestação de contas. Apagar é outra coisa, e é
 * escolha de quem olha.
 *
 * DUAS TRAVAS NA LIMPEZA
 *
 * Nada de "limpar tudo". A lista vai marcada item a item, porque quem
 * clica em limpar sempre acha que sabe o que vai embora, e às vezes
 * não sabe. E o servidor confere de novo se o item está mesmo
 * resolvido antes de apagar: a tela some, o servidor fica.
 */

export type ItemArquivado = {
  id: string;
  titulo: string;
  detalhe?: string;
  quando?: string;
  resultado?: string;
};

export default function CaixaArquivada({
  caixa, titulo, buscar, aoLimpar,
}: {
  /** tarefas | anotacoes | intimacoes | prazos */
  caixa: string;
  titulo: string;
  buscar: () => Promise<ItemArquivado[]>;
  aoLimpar?: () => void;
}) {
  const [itens, setItens] = useState<ItemArquivado[]>([]);
  const [marcados, setMarcados] = useState<Set<string>>(new Set());
  const [carregando, setCarregando] = useState(true);
  const [limpando, setLimpando] = useState(false);
  const [aviso, setAviso] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setItens(await buscar());
    } catch {
      setItens([]);
    } finally {
      setCarregando(false);
    }
  }, [buscar]);

  useEffect(() => { carregar(); }, [carregar]);

  function alternar(id: string) {
    setMarcados((m) => {
      const novo = new Set(m);
      if (novo.has(id)) novo.delete(id); else novo.add(id);
      return novo;
    });
  }

  async function limpar() {
    if (marcados.size === 0) return;
    if (!confirm(`Apagar ${marcados.size} ${marcados.size === 1 ? "item" : "itens"} do arquivo? `
                 + "Isso não pode ser desfeito.")) return;
    setLimpando(true); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/caixas/${caixa}/limpar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: [...marcados] }),
      });
      const d = await r.json().catch(() => ({} as any));
      if (!r.ok) { setAviso("Não consegui apagar agora."); return; }
      setAviso(`${d.apagados || 0} apagado(s).${d.aviso ? ` ${d.aviso}` : ""}`);
      setMarcados(new Set());
      await carregar();
      aoLimpar?.();
    } catch { setAviso("Falha de conexão."); }
    finally { setLimpando(false); }
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-bold text-[#C9A24D]">{titulo}</h2>
        <span className="text-[11px] text-white/35">
          {carregando ? "carregando…" : `${itens.length} no arquivo`}
        </span>

        {itens.length > 0 && (
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <button
              onClick={() => setMarcados(
                marcados.size === itens.length
                  ? new Set()
                  : new Set(itens.map((i) => i.id)))}
              className="rounded-lg border border-white/20 px-3 py-1.5 text-[11px] text-white/65 hover:border-white/45">
              {marcados.size === itens.length ? "desmarcar todos" : "marcar todos"}
            </button>
            <button onClick={limpar} disabled={limpando || marcados.size === 0}
              className="rounded-lg border border-[#C0392B]/50 px-3 py-1.5 text-[11px] font-semibold text-[#ff9a8f] transition hover:bg-[#C0392B]/10 disabled:opacity-35">
              {limpando ? "Apagando…"
                : marcados.size === 0 ? "Apagar selecionados"
                : `Apagar ${marcados.size} selecionado${marcados.size > 1 ? "s" : ""}`}
            </button>
          </div>
        )}
      </div>

      {aviso && (
        <p className="mb-3 rounded-lg bg-[#C9A24D]/10 px-3 py-2 text-[11px] text-[#C9A24D]">
          {aviso}
        </p>
      )}

      {!carregando && itens.length === 0 && (
        <p className="rounded-xl border border-white/10 bg-[#0B1F3B] p-5 text-center text-xs text-white/35">
          Nada no arquivo ainda. O que você marcar como resolvido vem para cá.
        </p>
      )}

      <div className="space-y-2">
        {itens.map((i) => (
          <label key={i.id}
            className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${marcados.has(i.id)
              ? "border-[#C0392B]/40 bg-[#C0392B]/5"
              : "border-white/10 bg-[#0B1F3B] hover:border-white/25"}`}>
            <input type="checkbox" checked={marcados.has(i.id)}
              onChange={() => alternar(i.id)} className="mt-1" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-white/80">{i.titulo}</p>
              {i.detalhe && (
                <p className="truncate text-[11px] text-white/40">{i.detalhe}</p>
              )}
              {i.resultado && (
                <p className="mt-1 text-[11px] leading-relaxed text-white/55">
                  {i.resultado}
                </p>
              )}
            </div>
            {i.quando && (
              <span className="shrink-0 text-[10px] text-white/30">{i.quando}</span>
            )}
          </label>
        ))}
      </div>
    </div>
  );
}
