"use client";
import { useState } from "react";
import Link from "next/link";
import AtendimentoWhats from "./AtendimentoWhats";

const WHATS = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? "";
const WHATS_LINK = WHATS
  ? `https://wa.me/${WHATS}?text=${encodeURIComponent("Olá! Gostaria de atendimento na FC Advocacia.")}`
  : "#contato";

const LINKS = [
  { href: "/#areas", label: "Áreas de Atuação" },
  { href: "/#sobre", label: "O Advogado" },
  { href: "/entrar", label: "Área do Cliente" },
];

export default function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed inset-x-0 top-0 z-40 border-b border-black/5 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-serif text-2xl font-bold tracking-tight text-navy">FC</span>
          <span className="text-sm font-semibold uppercase tracking-[0.2em] text-gold">Advocacia</span>
        </Link>

        {/* Desktop */}
        <nav className="hidden items-center gap-8 md:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="text-sm font-medium text-charcoal/70 transition hover:text-navy">
              {l.label}
            </Link>
          ))}
          <AtendimentoWhats variant="inline" label="Atendimento"
            className="rounded-full bg-gold px-6 py-2.5 text-sm font-semibold text-navy transition hover:bg-[#b89971]" />
        </nav>

        {/* Mobile toggle */}
        <button onClick={() => setOpen(!open)} aria-label="Menu" className="md:hidden text-navy">
          <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeWidth={2}
              d={open ? "M6 18L18 6M6 6l12 12" : "M4 7h16M4 12h16M4 17h16"} />
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <nav className="flex flex-col gap-1 border-t border-black/5 bg-white px-6 py-4 md:hidden">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)}
              className="py-2 text-sm font-medium text-charcoal/80">
              {l.label}
            </Link>
          ))}
          <div className="mt-2">
            <AtendimentoWhats variant="inline" label="Atendimento"
              className="w-full rounded-full bg-gold px-6 py-3 text-center text-sm font-semibold text-navy" />
          </div>
        </nav>
      )}
    </header>
  );
}
