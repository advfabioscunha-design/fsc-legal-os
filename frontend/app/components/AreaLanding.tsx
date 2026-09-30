import type { ReactNode } from "react";
import Link from "next/link";
import Header from "./Header";
import AtendimentoChat from "./AtendimentoChat";
import { MalhaHero } from "./ui/Ilustracoes";

/* PÁGINA DE ÁREA DE ATUAÇÃO
 *
 * A versão anterior era da época em que o site inteiro usava dourado em
 * tudo, botão redondo e frase de efeito. Três coisas mudaram aqui:
 *
 * 1. O botão principal agora é azul elétrico, como no resto do site. O
 *    dourado voltou a significar uma coisa só, selo e área premium. Cor
 *    que aparece em tudo deixa de comunicar qualquer coisa.
 *
 * 2. Saiu o par de botões concorrentes no hero. Havia "Tire suas
 *    dúvidas agora" e "Falar com um Especialista" lado a lado, que são
 *    a mesma porta com dois nomes, mais o botão fixo de WhatsApp no
 *    canto da tela. Três portas para a mesma sala fazem a pessoa parar
 *    para escolher em vez de entrar.
 *
 * 3. O texto deixou de prometer sentimento e passou a dizer o que
 *    acontece. "Estaremos ao seu lado em todo o processo" virou o que
 *    a pessoa realmente quer saber antes de falar com advogado: quanto
 *    custa a primeira conversa e quem responde pelo caso.
 *
 * As quatro páginas de área continuam passando as mesmas propriedades.
 * Ilustração, prova e passos são opcionais: quem não passa, não perde
 * nada, a seção simplesmente não aparece.
 */

export type AreaProps = {
  titulo: string;
  subnichos?: string;
  chamada: string;
  dores: string[];
  solucoes: string[];
  ilustracao?: ReactNode;
  /** O que a pessoa precisa ter em mãos para a primeira conversa. */
  documentos?: string[];
};

const PASSOS = [
  {
    n: "01",
    t: "Você conta o que aconteceu",
    d: "Pela plataforma ou pelo WhatsApp, quando for melhor para você. Essa conversa não custa nada.",
  },
  {
    n: "02",
    t: "O escritório analisa os documentos",
    d: "O caso é estudado antes de qualquer proposta. Se não houver tese, você ouve isso com todas as letras.",
  },
  {
    n: "03",
    t: "Você decide com o valor na mão",
    d: "Honorário, prazo e o que esperar do processo ficam combinados por escrito antes de começar.",
  },
];

export default function AreaLanding({
  titulo, subnichos, chamada, dores, solucoes, ilustracao, documentos,
}: AreaProps) {
  return (
    <main className="bg-navy text-white">
      <Header />

      {/* HERO */}
      <section className="relative overflow-hidden px-6 pb-20 pt-32 md:pt-40">
        <MalhaHero className="pointer-events-none absolute inset-0 h-full w-full text-white/5" />

        <div className="relative mx-auto grid max-w-content items-center gap-12 md:grid-cols-[1.15fr_.85fr]">
          <div>
            <Link href="/#areas"
              className="text-small font-medium text-slate transition hover:text-white">
              Áreas de atuação
            </Link>

            <h1 className="mt-5 font-display text-display-lg font-bold leading-[1.05]">
              {titulo}
            </h1>

            {subnichos && (
              <p className="mt-4 text-caption font-semibold uppercase tracking-[0.16em] text-electric">
                {subnichos}
              </p>
            )}

            <p className="mt-6 max-w-xl text-subtitle text-white/70">{chamada}</p>

            <div className="mt-10">
              <AtendimentoChat
                variant="inline"
                label="Analisar meu caso"
                className="inline-flex w-full items-center justify-center rounded-lg bg-electric px-9 py-4 text-subtitle font-bold text-white shadow-card transition-all hover:bg-indigo hover:shadow-glow sm:w-auto"
              />
              <p className="mt-3 text-small text-slate">
                A primeira conversa é gratuita e sem compromisso.
              </p>
            </div>
          </div>

          {ilustracao && (
            <div className="mx-auto hidden md:block">{ilustracao}</div>
          )}
        </div>
      </section>

      {/* A SITUAÇÃO */}
      <section className="border-y border-white/10 bg-petrol py-20">
        <div className="mx-auto max-w-content px-6">
          <h2 className="font-display text-display font-bold">
            Alguma destas situações é a sua?
          </h2>
          <p className="mt-3 max-w-xl text-subtitle text-white/65">
            Se você reconhecer o seu problema aqui, ele tem nome jurídico e
            tem caminho.
          </p>

          <ul className="mt-12 grid gap-4 sm:grid-cols-2">
            {dores.map((d) => (
              <li key={d}
                className="flex gap-4 rounded-xl2 border border-white/10 bg-navy/60 p-6 text-body text-white/80 transition hover:border-electric/40">
                <span aria-hidden="true"
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-electric" />
                {d}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* O QUE O ESCRITÓRIO FAZ */}
      <section className="py-20">
        <div className="mx-auto max-w-content px-6">
          <h2 className="font-display text-display font-bold">
            O que o escritório faz no seu caso
          </h2>

          <ul className="mt-12 grid gap-px overflow-hidden rounded-xl2 bg-white/10 sm:grid-cols-2">
            {solucoes.map((s) => (
              <li key={s} className="flex gap-4 bg-navy p-7 text-body text-white/80">
                <svg className="mt-1 h-5 w-5 shrink-0 text-electric" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" clipRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 10-1.4 1.4l2 2a1 1 0 001.4 0l4-4z" />
                </svg>
                {s}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* COMO COMEÇA */}
      <section className="border-y border-white/10 bg-petrol py-20">
        <div className="mx-auto max-w-content px-6">
          <h2 className="font-display text-display font-bold">Como começa</h2>
          <p className="mt-3 max-w-xl text-subtitle text-white/65">
            Três passos até você saber se vale a pena entrar com a ação.
          </p>

          <ol className="mt-12 grid gap-px overflow-hidden rounded-xl2 bg-white/10 sm:grid-cols-3">
            {PASSOS.map((p) => (
              <li key={p.n} className="bg-petrol p-7">
                <span className="font-mono text-caption font-bold text-gold">{p.n}</span>
                <h3 className="mt-3 font-display text-body font-bold">{p.t}</h3>
                <p className="mt-2 text-small text-white/65">{p.d}</p>
              </li>
            ))}
          </ol>

          {documentos && documentos.length > 0 && (
            <div className="mt-10 rounded-xl2 border border-white/10 bg-navy p-7">
              <h3 className="font-display text-body font-bold text-white">
                O que ajuda ter em mãos
              </h3>
              <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                {documentos.map((d) => (
                  <li key={d} className="text-small text-white/65">• {d}</li>
                ))}
              </ul>
              <p className="mt-4 text-small text-slate">
                Se faltar algum documento, o escritório orienta como obter.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* CTA FINAL */}
      <section className="py-20">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="font-display text-display font-bold">
            Todo caso tem prazo
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-subtitle text-white/65">
            Direito que existe hoje pode não existir daqui a um ano. Saber em
            que pé está o seu caso leva uma conversa.
          </p>

          <div className="mt-8">
            <AtendimentoChat
              variant="inline"
              label="Analisar meu caso"
              className="inline-flex w-full items-center justify-center rounded-lg bg-electric px-9 py-4 text-subtitle font-bold text-white shadow-card transition-all hover:bg-indigo hover:shadow-glow sm:w-auto"
            />
          </div>

          <p className="mt-6 text-small text-slate">
            Precisa de um contrato ou notificação?{" "}
            <Link href="/contrato" className="text-white underline underline-offset-4">
              Ver elaboração de documentos
            </Link>
          </p>
          <p className="mt-2 text-small text-slate">
            Já é cliente?{" "}
            <Link href="/entrar?next=/cliente" className="text-white underline underline-offset-4">
              Acesse a sua área
            </Link>
          </p>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-navy py-12">
        <div className="mx-auto max-w-content px-6 text-center">
          <p className="text-small text-slate">
            FC Advocacia. Dr. Fábio Cunha, OAB/RO 10.849.
          </p>
          <p className="mt-2 text-small text-slate">
            Porto Velho, RO e Florianópolis, SC. Atendimento em todo o país.
          </p>
          <p className="mt-5 text-caption text-slate/70">
            © {new Date().getFullYear()} FC Advocacia. Conteúdo informativo, nos
            termos do Provimento 205/2021 da OAB.
          </p>
          <Link href="/acesso-equipe"
            className="mt-4 inline-block text-caption text-slate transition hover:text-white">
            Área da equipe
          </Link>
        </div>
      </footer>
    </main>
  );
}
