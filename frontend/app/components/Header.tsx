"use client";
import { useState } from "react";
import Link from "next/link";
import AtendimentoChat from "./AtendimentoChat";

const LINKS = [
  { href: "/", label: "Início" },
  { href: "/#areas", label: "Áreas de Atuação" },
  { href: "/#sobre", label: "Sobre" },
  { href: "/contrato", label: "Elaboração de Contrato" },
  { href: "/#contato", label: "Contato" },
];

export default function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-navy/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-serif text-2xl font-bold tracking-tight text-white">FC</span>
          <span className="text-sm font-semibold uppercase tracking-[0.2em] text-gold">Advocacia</span>
        </Link>

        {/* Desktop */}
        <nav className="hidden items-center gap-7 lg:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="text-sm font-medium text-white/70 transition hover:text-gold">
              {l.label}
            </Link>
          ))}
          <Link href="/entrar?next=/cliente" className="text-sm font-medium text-white/70 transition hover:text-gold">
            Área do Cliente
          </Link>
          <Link href="/entrar?next=/crm" className="text-sm font-medium text-gold/80 transition hover:text-gold">
            Área da Equipe
          </Link>
          <AtendimentoChat variant="inline" label="Tire suas dúvidas"
            className="rounded-full bg-gold px-6 py-2.5 text-sm font-bold text-navy transition hover:bg-amber" />
        </nav>

        {/* Mobile toggle */}
        <button onClick={() => setOpen(!open)} aria-label="Menu" className="lg:hidden text-white">
          <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeWidth={2}
              d={open ? "M6 18L18 6M6 6l12 12" : "M4 7h16M4 12h16M4 17h16"} />
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <nav className="flex flex-col gap-1 border-t border-white/10 bg-navy px-6 py-4 lg:hidden">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)}
              className="py-2 text-sm font-medium text-white/80">
              {l.label}
            </Link>
          ))}
          <Link href="/entrar?next=/cliente" onClick={() => setOpen(false)} className="py-2 text-sm font-medium text-white/80">
            Área do Cliente
          </Link>
          <Link href="/entrar?next=/crm" onClick={() => setOpen(false)} className="py-2 text-sm font-medium text-gold">
            Área da Equipe
          </Link>
          <div className="mt-2">
            <AtendimentoChat variant="inline" label="Tire suas dúvidas agora"
              className="w-full rounded-full bg-gold px-6 py-3 text-center text-sm font-bold text-navy" />
          </div>
        </nav>
      )}
    </header>
  );
}
