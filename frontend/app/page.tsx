import Link from "next/link";
import Header from "./components/Header";
import AtendimentoWhats from "./components/AtendimentoWhats";

const WHATS = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? "";
const WHATS_LINK = WHATS
  ? `https://wa.me/${WHATS}?text=${encodeURIComponent("Olá! Gostaria de atendimento na FC Advocacia.")}`
  : "/entrar";

const AREAS = [
  {
    slug: "distrato-imobiliario",
    titulo: "Distrato Imobiliário",
    desc: "Atraso de obra e retenção abusiva de valores.",
  },
  {
    slug: "execucao-fiscal",
    titulo: "Execução Fiscal",
    desc: "Desbloqueio de patrimônio e defesa tributária.",
  },
  {
    slug: "recuperacao-consumo",
    titulo: "Recuperação de Consumo",
    desc: "Limitação de descontos no superendividamento.",
  },
  {
    slug: "direito-bancario",
    titulo: "Direito Bancário",
    desc: "Defesa do consumidor contra abusos institucionais.",
    subs: "Juros Abusivos • Cartão RMC/RCC • Fraudes PIX • Busca e Apreensão",
  },
];

export default function Home() {
  return (
    <main className="bg-white text-charcoal">
      <Header />

      {/* ── HERO (split-screen) ── */}
      <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 pb-20 pt-36 md:grid-cols-2 md:pt-44">
        <div>
          <span className="mb-4 inline-block text-xs font-semibold uppercase tracking-[0.25em] text-gold">
            Advocacia de Alto Padrão
          </span>
          <h1 className="font-serif text-5xl font-bold leading-[1.05] text-navy md:text-6xl">
            FC Advocacia
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-charcoal/70">
            Especialistas em <span className="font-semibold text-navy">Recuperação Patrimonial</span>.
            Defendemos o seu patrimônio contra abusos institucionais — com técnica, ética e total cuidado com você.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <AtendimentoWhats variant="inline" label="Falar com um especialista"
              className="rounded-full bg-gold px-8 py-4 text-sm font-semibold text-navy transition hover:bg-[#b89971]" />
            <a href="#areas"
              className="rounded-full border border-navy/15 px-8 py-4 text-center text-sm font-semibold text-navy transition hover:border-gold">
              Conhecer as áreas
            </a>
          </div>
          <p className="mt-8 text-sm text-charcoal/60">
            Bases em <span className="font-semibold text-navy">Porto Velho/RO</span> e{" "}
            <span className="font-semibold text-navy">Florianópolis/SC</span> · Atuação em todo o território nacional.
          </p>
        </div>

        {/* Container preparado para a foto de estúdio */}
        <div className="relative mx-auto aspect-[4/5] w-full max-w-sm overflow-hidden rounded-2xl bg-ice shadow-2xl ring-1 ring-black/5">
          <img src="/dr-fabio-hero.jpg" alt="Dr. Fábio Cunha" className="h-full w-full object-cover" />
        </div>
      </section>

      {/* ── AUTORIDADE / BIO ── */}
      <section id="sobre" className="bg-ice py-24">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 md:grid-cols-5">
          <div className="md:col-span-2">
            <div className="relative mx-auto aspect-square w-full max-w-xs overflow-hidden rounded-2xl shadow-xl ring-1 ring-black/5">
              <img src="/dr-fabio-bio.jpg" alt="Dr. Fábio Cunha" className="h-full w-full object-cover" />
            </div>
          </div>
          <div className="md:col-span-3">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-[0.25em] text-gold">
              Quem está à frente da sua defesa
            </span>
            <h2 className="font-serif text-4xl font-bold text-navy">Dr. Fábio Cunha</h2>
            <p className="mt-5 text-lg leading-relaxed text-charcoal/75">
              Especialista em <span className="font-semibold text-navy">Direito Tributário</span> e com
              <span className="font-semibold text-navy"> Curso Prático Avançado em Direito Bancário</span>.
            </p>
            <p className="mt-4 text-lg leading-relaxed text-charcoal/75">
              Ao longo de <span className="font-semibold text-navy">7 anos de prática jurídica</span>, dedica-se a
              combater abusos institucionais e a defender o patrimônio de pessoas e empresas — sempre com
              atendimento humano, ético e próximo do cliente em cada etapa do processo.
            </p>
          </div>
        </div>
      </section>

      {/* ── ÁREAS DE ATUAÇÃO (cards estilo carrossel) ── */}
      <section id="areas" className="py-24">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-[0.25em] text-gold">
              Como podemos te ajudar
            </span>
            <h2 className="font-serif text-4xl font-bold text-navy">Áreas de Atuação</h2>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {AREAS.map((a) => (
              <Link key={a.slug} href={`/areas/${a.slug}`}
                className="group flex flex-col rounded-2xl border border-black/5 bg-white p-8 shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
                <h3 className="font-serif text-2xl font-bold text-navy">{a.titulo}</h3>
                {a.subs && (
                  <p className="mt-1 text-xs font-medium uppercase tracking-wide text-gold">{a.subs}</p>
                )}
                <p className="mt-3 flex-1 text-charcoal/65">{a.desc}</p>
                <span className="mt-6 inline-flex items-center text-sm font-semibold text-navy transition group-hover:text-gold">
                  Ver detalhes →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── RODAPÉ ── */}
      <footer id="contato" className="bg-navy py-14 text-white/80">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <div className="font-serif text-2xl font-bold text-white">FC Advocacia</div>
          <p className="mt-2 text-sm text-white/60">Especialistas em Recuperação Patrimonial</p>
          <p className="mt-5 text-sm text-white/80">
            📍 Bases em <b>Porto Velho/RO</b> &nbsp;•&nbsp; <b>Florianópolis/SC</b>
          </p>
          <p className="text-xs text-white/50">Atuação em todo o território nacional</p>
          <div className="mt-6">
            <AtendimentoWhats variant="inline" label="Falar no WhatsApp"
              className="rounded-full bg-gold px-8 py-3 text-sm font-semibold text-navy hover:bg-[#b89971]" />
          </div>
          <p className="mt-8 text-xs text-white/40">© {new Date().getFullYear()} FC Advocacia. Todos os direitos reservados.</p>
        </div>
      </footer>
    </main>
  );
}
