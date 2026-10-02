"use client";
import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* O ARQUIVO QUE O CLIENTE MANDOU, ABERTO POR QUEM TEM DIREITO.
 *
 * Até aqui o arquivo era guardado, era lido pelos agentes, e ninguém
 * conseguia abrir: nem o cliente que mandou, nem o operador. A lista
 * trazia o caminho dentro do armazenamento, que não é endereço de nada.
 *
 * Na prática, quem recebia a foto de um RG tinha a transcrição e não
 * tinha a foto. Se o agente lesse um dígito errado, não havia como
 * conferir sem abrir o banco.
 *
 * O MESMO COMPONENTE NOS DOIS LADOS
 *
 * Cliente e operador veem a mesma coisa, de propósito. Quando o cliente
 * liga perguntando "a foto que mandei está legível?", quem atende
 * precisa estar olhando exatamente a mesma imagem.
 *
 * O LINK VENCE
 *
 * O armazenamento é privado e o link é assinado, com uma hora de
 * validade: documento de identidade em endereço público é vazamento
 * esperando acontecer. Por isso o link é pedido na hora do clique, e
 * não guardado na tela.
 */

type Doc = {
  id: string; nome?: string; tipo_mime?: string; tamanho?: number;
  rotulo?: string; enviado_por?: string; criado_em?: string;
  eh_imagem?: boolean; eh_pdf?: boolean; lido?: boolean;
  transcricao?: string | null;
};

function tamanhoLegivel(bytes?: number) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function AnexoDoPedido({ doc, tom = "escuro" }: {
  doc: Doc; tom?: "escuro" | "claro";
}) {
  const [url, setUrl] = useState("");
  const [erro, setErro] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [vendoTexto, setVendoTexto] = useState(false);

  const pegarLink = useCallback(async () => {
    if (url || buscando) return url;
    setBuscando(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/contratos/documentos/${doc.id}/abrir`);
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j?.url) {
        setErro(j?.detail || "Não consegui abrir este arquivo agora.");
        return "";
      }
      setUrl(j.url);
      return j.url as string;
    } catch {
      setErro("Falha de conexão ao abrir o arquivo.");
      return "";
    } finally { setBuscando(false); }
  }, [doc.id, url, buscando]);

  /* A miniatura da imagem é buscada sozinha: ver a foto vale mais que
     economizar uma requisição, e é o que permite perceber de relance
     que o cliente mandou a página errada do documento. */
  useEffect(() => {
    if (doc.eh_imagem) pegarLink();
  }, [doc.eh_imagem, pegarLink]);

  async function abrir() {
    const u = url || (await pegarLink());
    if (u) window.open(u, "_blank", "noopener,noreferrer");
  }

  const claro = tom === "claro";
  const borda = claro ? "border-black/10" : "border-white/10";
  const titulo = claro ? "text-charcoal" : "text-white/80";
  const fraco = claro ? "text-charcoal/50" : "text-white/40";

  return (
    <div className={`rounded-lg border ${borda} p-2`}>
      <div className="flex items-start gap-2">
        {doc.eh_imagem && url ? (
          <button onClick={abrir} className="shrink-0" title="abrir em tamanho real">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={url} alt={doc.nome || "anexo"}
              className="h-14 w-14 rounded object-cover" />
          </button>
        ) : (
          <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded border ${borda} text-[10px] font-bold ${fraco}`}>
            {doc.eh_pdf ? "PDF"
              : (doc.nome || "").split(".").pop()?.slice(0, 4).toUpperCase() || "ARQ"}
          </span>
        )}

        <div className="min-w-0 flex-1">
          <p className={`truncate text-[12px] font-semibold ${titulo}`}>
            {doc.nome || "arquivo"}
          </p>
          <p className={`text-[10px] ${fraco}`}>
            {[doc.rotulo, tamanhoLegivel(doc.tamanho),
              doc.enviado_por === "CLIENTE" ? "enviado por você"
                : doc.enviado_por === "ESCRITORIO" ? "do escritório" : ""]
              .filter(Boolean).join(" · ")}
          </p>

          <div className="mt-1 flex flex-wrap items-center gap-2">
            <button onClick={abrir} disabled={buscando}
              className={`text-[11px] font-semibold underline-offset-2 hover:underline ${claro ? "text-navy" : "text-[#C9A84C]"} disabled:opacity-50`}>
              {buscando ? "abrindo…" : "abrir"}
            </button>

            {/* O QUE O SISTEMA LEU, AO LADO DO ARQUIVO
                Ver a transcrição junto da imagem é o que permite pegar o
                dígito trocado. Separados, ninguém confere. */}
            {doc.lido && doc.transcricao && (
              <button onClick={() => setVendoTexto(!vendoTexto)}
                className={`text-[11px] ${fraco} underline-offset-2 hover:underline`}>
                {vendoTexto ? "esconder o que foi lido" : "ver o que foi lido"}
              </button>
            )}
            {doc.lido && (
              <span className="rounded bg-[#1DB954]/15 px-1.5 py-0.5 text-[9px] font-bold text-[#1DB954]">
                lido pelo sistema
              </span>
            )}
          </div>
        </div>
      </div>

      {erro && <p className="mt-1 text-[11px] text-[#E57373]">{erro}</p>}

      {vendoTexto && doc.transcricao && (
        <pre className={`mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded border ${borda} p-2 text-[11px] leading-relaxed ${fraco}`}>
          {doc.transcricao}
        </pre>
      )}
    </div>
  );
}

/** A lista inteira, do jeito que as duas telas usam. */
export function AnexosDoPedido({ docs, tom = "escuro", vazio }: {
  docs: any[]; tom?: "escuro" | "claro"; vazio?: string;
}) {
  const lista = Array.isArray(docs) ? docs : [];
  if (lista.length === 0) {
    return vazio ? (
      <p className={`text-[11px] ${tom === "claro" ? "text-charcoal/40" : "text-white/35"}`}>
        {vazio}
      </p>
    ) : null;
  }
  return (
    <div className="space-y-2">
      {lista.map((d: any) => (
        <AnexoDoPedido key={d.id} doc={d} tom={tom} />
      ))}
    </div>
  );
}
