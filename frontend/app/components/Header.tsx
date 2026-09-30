"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AtendimentoChat from "./AtendimentoChat";

/* NAVEGAÇÃO DO SITE
 *
 * A versão anterior tinha oito destinos no topo, e três deles
 * competiam pela mesma decisão do visitante: Contato, Área do Cliente e
 * o botão de atendimento. Menu cheio não é sinal de site completo, é
 * sinal de que ninguém escolheu o que importa.
 *
 * Quatro itens agora, com papéis distintos:
 *   Áreas     o que o escritório faz
 *   Contratos o serviço que se compra direto
 *   Sobre     quem responde pelo trabalho
 *   Contato   onde falar
 *
 * "Início" saiu porque o logo já leva para a home, e todo mundo sabe
 * disso. "Área da Equipe" saiu do menu público: é porta de serviço, e
 * porta de serviço não fica na fachada. Foi para o rodapé.
 *
 * "Área do Cliente" fica à direita, separada por uma linha vertical.
 * Não é conteúdo de marketing, é acesso a uma conta, e a separação
 * visual diz isso sem precisar de rótulo.
 */

const LINKS = [
  { href: "/#areas", label: "Áreas de atuação" },
  { href: "/contrato", label: "Contratos" },
  { href: "/#sobre", label: "Sobre" },
  { href: "/#contato", label: "Contato" },
];

export default function Header() {
  const [open, setOpen] = useState(false);
  const [rolou, setRolou] = useState(false);
  const pathname = usePathname();

  // O cabeçalho ganha fundo sólido e sombra ao sair do topo. Sobre o
  // hero escuro ele pode ser transparente; sobre o conteúdo, não, ou o
  // texto passa por baixo e fica ilegível.
  useEffect(() => {
    const aoRolar = () => setRolou(window.scrollY > 16);
    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);

  useEffect(() => { setOpen(false); }, [pathname]);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-40 transition-all duration-300 ${
        rolou
          ? "border-b border-white/10 bg-navy/95 py-2 shadow-lift backdrop-blur-lg"
          : "border-b border-transparent bg-navy/70 py-4 backdrop-blur-sm"
      }`}
    >
      <div className="mx-auto flex max-w-content items-center gap-6 px-6">
        <Link href="/" className="group flex items-center gap-2.5" aria-label="FC Advocacia, ir para o início">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-electric to-indigo font-display text-body font-bold text-white shadow-glow">
            FC
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-body font-bold tracking-tight text-white">
              Advocacia
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate">
              OAB/RO 10.849
            </span>
          </span>
        </Link>

        <nav className="ml-auto hidden items-center gap-8 lg:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href}
              className="relative text-small font-medium text-white/75 transition hover:text-white
                         after:absolute after:-bottom-1.5 after:left-0 after:h-px after:w-0
                         after:bg-electric after:transition-all hover:after:w-full">
              {l.label}
            </Link>
          ))}

          <span className="h-5 w-px bg-white/15" aria-hidden="true" />

          <Link href="/entrar?next=/cliente"
            className="text-small font-medium text-slate transition hover:text-white">
            Área do cliente
          </Link>

          {/* A porta de quem trabalha aqui. Fica ao lado da do cliente,
              em tom menor: não é conteúdo de marketing, mas quem
              começa na equipe precisa achar sem perguntar a alguém. */}
          <Link href="/acesso-equipe"
            className="text-small font-medium text-slate/70 transition hover:text-white">
            Área da equipe
          </Link>

          <AtendimentoChat variant="inline" label="Falar com o escritório"
            className="inline-flex items-center justify-center rounded-lg bg-electric px-6 py-2.5 text-small font-semibold text-white shadow-card transition-all hover:bg-indigo hover:shadow-glow" />
        </nav>

        <button onClick={() => setOpen(!open)}
          aria-label={open ? "Fechar menu" : "Abrir menu"} aria-expanded={open}
          className="ml-auto rounded-lg p-2 text-white transition hover:bg-white/10 lg:hidden">
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeWidth={2}
              d={open ? "M6 18L18 6M6 6l12 12" : "M4 7h16M4 12h16M4 17h16"} />
          </svg>
        </button>
      </div>

      {open && (
        <nav className="border-t border-white/10 bg-navy px-6 py-5 lg:hidden">
          <div className="flex flex-col">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href}
                className="border-b border-white/5 py-3.5 text-body font-medium text-white/85">
                {l.label}
              </Link>
            ))}
            <Link href="/entrar?next=/cliente"
              className="py-3.5 text-body font-medium text-slate">
              Área do cliente
            </Link>
            <Link href="/acesso-equipe"
              className="py-3.5 text-body font-medium text-slate/70">
              Área da equipe
            </Link>
          </div>
          <div className="mt-4">
            <AtendimentoChat variant="inline" label="Falar com o escritório"
              className="block w-full rounded-lg bg-electric px-6 py-3.5 text-center text-body font-semibold text-white" />
          </div>
        </nav>
      )}
    </header>
  );
}
