"use client";
import { useState } from "react";
import { usePathname } from "next/navigation";

// Contatos por estado (DDI 55 + DDD + número)
const CONTATOS = [
  { uf: "Porto Velho / RO", num: "5569993225383", label: "(69) 99322-5383" },
  { uf: "Florianópolis / SC", num: "5548988357992", label: "(48) 98835-7992" },
];
const MSG = "Olá! Vim pelo site da FC Advocacia e gostaria de atendimento.";
const waLink = (n: string) => `https://wa.me/${n}?text=${encodeURIComponent(MSG)}`;

// Telas internas/equipe/cliente: sem botão flutuante
const OCULTAR_EM = ["/entrar", "/equipe", "/crm", "/cliente", "/portal"];

function Opcoes() {
  return (
    <div className="flex flex-col gap-2">
      <p className="px-1 pb-1 text-xs font-semibold uppercase tracking-wide text-charcoal/50">
        Escolha a unidade
      </p>
      {CONTATOS.map((c) => (
        <a key={c.num} href={waLink(c.num)} target="_blank" rel="noopener noreferrer"
          className="flex items-center justify-between gap-3 rounded-lg border border-black/5 bg-white px-4 py-3 text-left transition hover:border-[#25D366] hover:bg-[#25D366]/5">
          <span>
            <span className="block text-sm font-semibold text-navy">{c.uf}</span>
            <span className="block text-xs text-charcoal/60">{c.label}</span>
          </span>
          <span className="text-[#25D366]">›</span>
        </a>
      ))}
    </div>
  );
}

export default function AtendimentoWhats({
  variant = "inline",
  label = "Atendimento",
  className = "",
}: { variant?: "inline" | "floating"; label?: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  if (variant === "floating" && OCULTAR_EM.some((p) => pathname?.startsWith(p))) return null;

  if (variant === "floating") {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        {open && (
          <div className="absolute bottom-16 right-0 w-72 rounded-2xl bg-white p-3 shadow-2xl ring-1 ring-black/10">
            <Opcoes />
          </div>
        )}
        <button onClick={() => setOpen(!open)} aria-label="Atendimento no WhatsApp"
          className="flex items-center gap-2 rounded-full bg-[#25D366] px-5 py-4 text-white shadow-xl transition hover:scale-105">
          <svg viewBox="0 0 24 24" className="h-6 w-6 fill-current" aria-hidden="true">
            <path d="M.057 24l1.687-6.163a11.867 11.867 0 01-1.587-5.945C.16 5.335 5.495 0 12.05 0a11.82 11.82 0 018.413 3.488 11.82 11.82 0 013.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 01-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 001.51 5.26l-.999 3.648 3.748-.985a9.864 9.864 0 005.392 1.592zm5.913-7.43c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.71.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413z" />
          </svg>
          <span className="hidden text-sm font-semibold sm:inline">Atendimento</span>
        </button>
      </div>
    );
  }

  // inline (CTA) — abre um modal central (nunca é cortado pela seção)
  return (
    <>
      <button onClick={() => setOpen(true)} className={className}>{label}</button>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
          onClick={() => setOpen(false)}>
          <div onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-t-2xl bg-white p-4 text-left shadow-2xl sm:rounded-2xl">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-bold text-navy">Falar no WhatsApp</p>
              <button onClick={() => setOpen(false)} aria-label="Fechar" className="text-charcoal/50 hover:text-charcoal">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <Opcoes />
          </div>
        </div>
      )}
    </>
  );
}
