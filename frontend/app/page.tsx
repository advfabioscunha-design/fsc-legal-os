import Link from "next/link";
import Header from "./components/Header";
import AtendimentoChat from "./components/AtendimentoChat";
import AtendimentoWhats from "./components/AtendimentoWhats";

const AREAS = [
  { slug: "direito-bancario", titulo: "Direito Bancário", desc: "Juros abusivos, tarifas indevidas, cartão RMC/RCC, fraudes PIX e busca e apreensão." },
  { slug: "distrato-imobiliario", titulo: "Distrato Imobiliário", desc: "Atraso de obra e retenção abusiva de valores na rescisão." },
  { slug: "execucao-fiscal", titulo: "Execução Fiscal", desc: "Desbloqueio de patrimônio e defesa tributária." },
  { slug: "recuperacao-consumo", titulo: "Recuperação de Consumo de Energia", desc: "Multa e cobrança de recuperação de consumo de energia elétrica." },
];

const DIFERENCIAIS = [
  { t: "Atendimento Especializado", d: "Soluções jurídicas estratégicas e personalizadas." },
  { t: "Experiência e Credibilidade", d: "Atuação sólida e comprometida com resultados." },
  { t: "Transparência e Compromisso", d: "Ética, clareza e dedicação em cada caso." },
  { t: "Atendimento Humanizado", d: "Escuta ativa e foco nas suas necessidades." },
];

export default function Home() {
  return (
    <main className="bg-navy text-white">
      <Header />

      {/* ── HERO ── */}
      <section className="relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 pb-20 pt-32 md:grid-cols-2 md:pt-40">
          {/* Texto + CTA central */}
          <div className="text-center md:text-left">
            <span className="mb-5 inline-block rounded-full border border-gold/40 px-4 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-gold">
              Advocacia com Propósito
            </span>
            <h1 className="font-serif text-4xl font-bold leading-[1.1] md:text-6xl">
              Você tem <span className="text-gold">direitos</span>.<br />Nós provamos.
            </h1>
            <p className="mx-auto mt-6 max-w-md text-base leading-relaxed text-white/70 md:mx-0">
              Direito Bancário, Distrato Imobiliário, Execução Fiscal, Recuperação de Consumo de Energia
              e Busca e Apreensão. Conheça seus direitos com quem entende da lei.
            </p>

            {/* CTA principal — Atendimento (centralizado e chamativo) */}
            <div className="mt-9 flex flex-col items-center gap-4 md:items-start">
              <AtendimentoChat variant="inline" label="Tire suas dúvidas agora"
                className="w-full rounded-full bg-gold px-10 py-5 text-center text-base font-bold text-navy shadow-xl shadow-gold/20 transition hover:bg-amber sm:w-auto" />
              <div className="flex flex-wrap items-center justify-center gap-4 md:justify-start">
                <Link href="/contrato" className="text-sm font-semibold text-gold underline-offset-4 hover:underline">
                  Solicitar Elaboração de Contrato →
                </Link>
                <a href="#areas" className="text-sm font-medium text-white/60 hover:text-white">Conhecer as áreas</a>
              </div>
            </div>
          </div>

          {/* Foto + Falar com Especialista abaixo */}
          <div className="flex flex-col items-center gap-5">
            <div className="relative aspect-[4/5] w-full max-w-sm overflow-hidden rounded-2xl bg-petrol shadow-2xl ring-1 ring-white/10">
              <img src="/dr-fabio-hero.jpg" alt="Dr. Fábio Cunha" className="h-full w-full object-cover" />
            </div>
            <AtendimentoWhats variant="inline" label="Falar com um Especialista"
              className="w-full max-w-sm rounded-full border border-gold/40 bg-white/5 px-8 py-3.5 text-center text-sm font-semibold text-white transition hover:border-gold hover:bg-white/10" />
          </div>
        </div>
      </section>

      {/* ── ÁREAS ── */}
      <section id="areas" className="bg-petrol py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-12 text-center">
            <h2 className="font-serif text-3xl font-bold md:text-4xl">Áreas de <span className="text-gold">Atuação</span></h2>
          </div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {AREAS.map((a) => (
              <Link key={a.slug} href={`/areas/${a.slug}`}
                className="group flex flex-col rounded-2xl border border-white/10 bg-navy/60 p-6 transition hover:-translate-y-1 hover:border-gold/40">
                <h3 className="font-serif text-xl font-bold text-white">{a.titulo}</h3>
                <p className="mt-3 flex-1 text-sm text-white/60">{a.desc}</p>
                <span className="mt-5 text-sm font-semibold text-gold transition group-hover:translate-x-1">Saiba mais →</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── DIFERENCIAIS ── */}
      <section className="py-16">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 sm:grid-cols-2 lg:grid-cols-4">
          {DIFERENCIAIS.map((d) => (
            <div key={d.t} className="text-center">
              <h3 className="font-semibold text-gold">{d.t}</h3>
              <p className="mt-2 text-sm text-white/60">{d.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SOBRE ── */}
      <section id="sobre" className="bg-petrol py-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 md:grid-cols-5">
          <div className="md:col-span-2">
            <div className="relative mx-auto aspect-square w-full max-w-xs overflow-hidden rounded-2xl shadow-xl ring-1 ring-white/10">
              <img src="/dr-fabio-bio.jpg" alt="Dr. Fábio Cunha" className="h-full w-full object-cover" />
            </div>
          </div>
          <div className="md:col-span-3">
            <span className="mb-3 inline-block text-xs font-semibold uppercase tracking-[0.2em] text-gold">Quem está à frente da sua defesa</span>
            <h2 className="font-serif text-3xl font-bold md:text-4xl">Dr. Fábio Cunha</h2>
            <p className="mt-5 leading-relaxed text-white/70">
              Especialista em <b className="text-white">Direito Tributário</b> e com
              <b className="text-white"> Curso Prático Avançado em Direito Bancário</b>.
            </p>
            <p className="mt-4 leading-relaxed text-white/70">
              Ao longo de <b className="text-white">7 anos de prática jurídica</b>, dedica-se a combater abusos
              institucionais e a defender o patrimônio de pessoas e empresas — sempre com atendimento humano,
              ético e próximo do cliente em cada etapa.
            </p>
          </div>
        </div>
      </section>

      {/* ── CTA AJUDA ── */}
      <section id="contato" className="py-20">
        <div className="mx-auto max-w-4xl px-6">
          <div className="rounded-3xl border border-gold/30 bg-petrol p-10 text-center">
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Precisa de ajuda?</span>
            <h2 className="mt-3 font-serif text-3xl font-bold">Fale agora com a nossa equipe</h2>
            <p className="mx-auto mt-3 max-w-xl text-white/65">
              Tire suas dúvidas e receba orientação com agilidade, segurança e total cuidado com você.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <AtendimentoChat variant="inline" label="Tire suas dúvidas agora"
                className="rounded-full bg-gold px-10 py-4 text-sm font-bold text-navy shadow-lg transition hover:bg-amber" />
              <AtendimentoWhats variant="inline" label="Falar no WhatsApp"
                className="rounded-full border border-white/20 px-8 py-4 text-sm font-semibold text-white hover:border-gold" />
            </div>
            <p className="mt-6 text-sm text-white/55">
              📍 Bases em <b className="text-white">Porto Velho/RO</b> &nbsp;•&nbsp; <b className="text-white">Florianópolis/SC</b> · Atuação em todo o território nacional
            </p>
          </div>
        </div>
      </section>

      {/* ── RODAPÉ ── */}
      <footer className="border-t border-white/10 bg-navy py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-6 text-center">
          <div className="font-serif text-2xl font-bold">FC <span className="text-gold">Advocacia</span></div>
          <p className="text-sm text-white/55">Dr. Fábio Cunha · OAB/RO 10.849</p>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
            <Link href="/contrato" className="text-gold hover:underline">Elaboração de Contrato</Link>
            <Link href="/entrar?next=/cliente" className="text-white/70 hover:text-white">Área do Cliente</Link>
            <Link href="/entrar?next=/crm" className="text-white/70 hover:text-white">Área da Equipe</Link>
          </div>
          <p className="mt-4 text-xs text-white/40">© {new Date().getFullYear()} FC Advocacia. Todos os direitos reservados.</p>
        </div>
      </footer>
    </main>
  );
}
