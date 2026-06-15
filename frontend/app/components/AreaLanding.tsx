import Link from "next/link";
import Header from "./Header";
import AtendimentoWhats from "./AtendimentoWhats";

const WHATS = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? "";
const WHATS_LINK = WHATS
  ? `https://wa.me/${WHATS}?text=${encodeURIComponent("Olá! Quero atendimento na FC Advocacia.")}`
  : "/entrar";

export type AreaProps = {
  titulo: string;
  subnichos?: string;
  chamada: string;        // subtítulo de impacto
  dores: string[];        // dores do cliente
  solucoes: string[];     // como o escritório resolve
};

export default function AreaLanding({ titulo, subnichos, chamada, dores, solucoes }: AreaProps) {
  return (
    <main className="bg-white text-charcoal">
      <Header />

      {/* Hero da área */}
      <section className="bg-navy py-28 text-white md:py-36">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <Link href="/#areas" className="mb-6 inline-block text-sm text-gold">← Áreas de atuação</Link>
          <h1 className="font-serif text-4xl font-bold leading-tight md:text-5xl">{titulo}</h1>
          {subnichos && <p className="mt-3 text-sm font-medium uppercase tracking-wide text-gold">{subnichos}</p>}
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-white/75">{chamada}</p>
          <div className="mt-9">
            <AtendimentoWhats variant="inline" label="Analisar meu caso agora"
              className="rounded-full bg-gold px-8 py-4 text-sm font-semibold text-navy transition hover:bg-[#b89971]" />
          </div>
        </div>
      </section>

      {/* A dor do cliente */}
      <section className="py-20">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="font-serif text-3xl font-bold text-navy">Você se identifica com isso?</h2>
          <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {dores.map((d) => (
              <li key={d} className="flex gap-3 rounded-xl border border-black/5 bg-ice p-5 text-charcoal/80">
                <span className="text-gold">●</span>{d}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Como resolvemos */}
      <section className="bg-ice py-20">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="font-serif text-3xl font-bold text-navy">Como o escritório resolve</h2>
          <ul className="mt-8 space-y-4">
            {solucoes.map((s) => (
              <li key={s} className="flex gap-3 text-lg text-charcoal/80">
                <span className="font-semibold text-gold">✓</span>{s}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* CTA final */}
      <section className="py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="font-serif text-3xl font-bold text-navy">Não deixe seu direito esfriar.</h2>
          <p className="mt-4 text-lg text-charcoal/70">
            Estaremos ao seu lado em todo o processo, com atualizações e tirando suas dúvidas.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <AtendimentoWhats variant="inline" label="Falar com um especialista"
              className="rounded-full bg-gold px-8 py-4 text-sm font-semibold text-navy hover:bg-[#b89971]" />
            <Link href="/entrar"
              className="rounded-full border border-navy/15 px-8 py-4 text-sm font-semibold text-navy hover:border-gold">
              Iniciar pela plataforma
            </Link>
          </div>
        </div>
      </section>

      <footer className="bg-navy py-10 text-center text-white/60">
        <p className="text-sm text-white/80">📍 Bases em <b>Porto Velho/RO</b> &nbsp;•&nbsp; <b>Florianópolis/SC</b></p>
        <p className="text-xs text-white/50">Atuação em todo o território nacional</p>
        <p className="mt-4 text-xs text-white/40">© {new Date().getFullYear()} FC Advocacia — Especialistas em Recuperação Patrimonial.</p>
      </footer>
    </main>
  );
}
