"use client";
import { useEffect, useState } from "react";

type Props = {
  aberto: boolean;
  onFechar: () => void;
  titulo?: string;
  texto: string;
  onAprovar?: () => void;
};

export default function DocumentoRevisao({ aberto, onFechar, titulo = "Contrato em Revisão", texto, onAprovar }: Props) {
  const [borrado, setBorrado] = useState(false);

  useEffect(() => {
    if (!aberto) return;
    // Borra o conteúdo quando a janela perde o foco (deter screenshot/alt-tab)
    const onBlur = () => setBorrado(true);
    const onFocus = () => setBorrado(false);
    // Bloqueia impressão e PrintScreen (melhor esforço)
    const onKey = (e: KeyboardEvent) => {
      const k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && (k === "p" || k === "s" || k === "c")) { e.preventDefault(); setBorrado(true); }
      if (e.key === "PrintScreen") { setBorrado(true); }
    };
    const beforePrint = () => setBorrado(true);
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    window.addEventListener("keydown", onKey);
    window.addEventListener("beforeprint", beforePrint);
    return () => {
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("beforeprint", beforePrint);
    };
  }, [aberto]);

  if (!aberto) return null;

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-black/80 p-3 sm:p-6">
      {/* CSS de proteção contra impressão */}
      <style>{`
        @media print {
          .doc-protegido { display: none !important; }
          body::after { content: "Documento protegido — visualização apenas em revisão na plataforma."; }
        }
      `}</style>

      <div className="doc-protegido mx-auto flex h-full w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between border-b border-black/10 bg-navy px-5 py-3 text-white">
          <p className="text-sm font-bold">{titulo}</p>
          <button onClick={onFechar} aria-label="Fechar" className="text-white/70 hover:text-white">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Documento com marca d'água REVISÃO */}
        <div
          className={`relative flex-1 overflow-y-auto bg-white p-6 transition ${borrado ? "blur-md" : ""}`}
          style={{ userSelect: "none", WebkitUserSelect: "none" }}
          onContextMenu={(e) => e.preventDefault()}
          onCopy={(e) => e.preventDefault()}
        >
          {/* Marca d'água repetida */}
          <div aria-hidden className="pointer-events-none absolute inset-0 z-0 flex flex-wrap content-center justify-center overflow-hidden opacity-[0.12]">
            {Array.from({ length: 24 }).map((_, i) => (
              <span key={i} className="m-6 -rotate-[30deg] whitespace-nowrap text-4xl font-extrabold tracking-widest text-navy">
                REVISÃO
              </span>
            ))}
          </div>
          {/* Faixa central grande */}
          <div aria-hidden className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
            <span className="-rotate-[18deg] select-none text-6xl font-black tracking-widest text-red-600/25 sm:text-8xl">REVISÃO</span>
          </div>

          <pre className="relative z-[5] whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-charcoal">
{texto}
          </pre>

          {borrado && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/70 text-center">
              <p className="px-6 text-sm font-semibold text-navy">
                Visualização pausada por segurança.<br />Clique aqui para continuar lendo.
              </p>
            </div>
          )}
        </div>

        {/* Rodapé / ações */}
        <div className="border-t border-black/10 bg-ice px-5 py-3">
          <p className="mb-3 text-center text-[11px] text-charcoal/60">
            Documento em <b>revisão</b> — elaborado com base na legislação específica e na jurisprudência aplicável,
            com total segurança jurídica. Cópia, impressão e captura estão protegidas.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
            <button onClick={onFechar} className="rounded-lg border border-black/15 px-5 py-2.5 text-sm font-semibold text-charcoal hover:border-navy">
              Fechar
            </button>
            {onAprovar && (
              <button onClick={onAprovar} className="rounded-lg bg-gold px-6 py-2.5 text-sm font-bold text-navy transition hover:bg-amber">
                Aprovar e receber por WhatsApp/E-mail
              </button>
            )}
          </div>
        </div>
      </div>

      {/* clique no fundo para desfazer o borrão (quando volta o foco) */}
      <button aria-hidden tabIndex={-1} className="absolute inset-0 -z-10" onClick={() => setBorrado(false)} />
    </div>
  );
}
