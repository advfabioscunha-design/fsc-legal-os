import Link from "next/link";
import Header from "./Header";
import AtendimentoChat from "./AtendimentoChat";
import AtendimentoWhats from "./AtendimentoWhats";

export type AreaProps = {
  titulo: string;
  subnichos?: string;
  chamada: string;        // subtítulo de impacto
  dores: string[];        // dores do cliente
  solucoes: string[];     // como o escritório resolve
};

export default function AreaLanding({ titulo, subnichos, chamada, dores, solucoes }: AreaProps) {
  return (
    <main className="bg-navy text-white">
      <Header />

      {/* Hero da área */}
      <section className="px-6 pt-32 pb-16 md:pt-40">
        <div className="mx-auto max-w-4xl text-center">
          <Link href="/#areas" className="mb-6 inline-block text-sm text-gold">← Áreas de atuação</Link>
          <h1 className="font-serif text-4xl font-bold leading-tight md:text-5xl">{titulo}</h1>
          {subnichos && <p className="mt-3 text-sm font-medium uppercase tracking-wide text-gold">{subnichos}</p>}
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-white/75">{chamada}</p>

          {/* CTA central — Atendimento */}
          <div className="mt-9 flex flex-col items-center gap-4">
            <AtendimentoChat variant="inline" label="Tire suas dúvidas agora"
              className="w-full max-w-xs rounded-full bg-gold px-10 py-5 text-center text-base font-bold text-navy shadow-xl shadow-gold/20 transition hover:bg-amber sm:w-auto" />
            <AtendimentoWhats variant="inline" label="Falar com um Especialista"
              className="rounded-full border border-gold/40 bg-white/5 px-8 py-3 text-sm font-semibold text-white transition hover:border-gold hover:bg-white/10" />
          </div>
        </div>
      </section>

      {/* A dor do cliente */}
      <section className="bg-petrol py-20">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="font-serif text-3xl font-bold">Você se identifica com isso?</h2>
          <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {dores.map((d) => (
              <li key={d} className="flex gap-3 rounded-xl border border-white/10 bg-navy/50 p-5 text-white/80">
                <span className="text-gold">●</span>{d}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Como resolvemos */}
      <section className="py-20">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="font-serif text-3xl font-bold">Como o escritório resolve</h2>
          <ul className="mt-8 space-y-4">
            {solucoes.map((s) => (
              <li key={s} className="flex gap-3 text-lg text-white/80">
                <span className="font-semibold text-gold">✓</span>{s}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* CTA final */}
      <section className="bg-petrol py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="font-serif text-3xl font-bold">Não deixe seu direito esfriar.</h2>
          <p className="mt-4 text-lg text-white/70">
            Estaremos ao seu lado em todo o processo, com atualizações e tirando suas dúvidas.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <AtendimentoChat variant="inline" label="Tire suas dúvidas agora"
              className="rounded-full bg-gold px-10 py-4 text-sm font-bold text-navy hover:bg-amber" />
            <Link href="/entrar?next=/cliente"
              className="rounded-full border border-white/20 px-8 py-4 text-sm font-semibold text-white hover:border-gold">
              Iniciar pela plataforma
            </Link>
          </div>
          <div className="mt-5">
            <Link href="/contrato" className="text-sm font-semibold text-gold underline-offset-4 hover:underline">
              Precisa de um contrato? Solicitar Elaboração de Contrato →
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-navy py-10 text-center text-white/60">
        <p className="text-sm text-white/80">📍 Bases em <b>Porto Velho/RO</b> &nbsp;•&nbsp; <b>Florianópolis/SC</b></p>
        <p className="text-xs text-white/50">Atuação em todo o território nacional</p>
        <p className="mt-4 text-xs text-white/40">© {new Date().getFullYear()} FC Advocacia — Especialistas em Recuperação Patrimonial.</p>
      </footer>
    </main>
  );
}
