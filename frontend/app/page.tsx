import Link from "next/link";

/* ──────────────────────────────────────────
   Ícones inline (SVG) — sem dependência externa
   ────────────────────────────────────────── */
const IconBank = () => (
  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M12 2L2 7h20L12 2zm0 0v20M2 7v13h20V7M6 11v6m4-6v6m4-6v6m4-6v6" />
  </svg>
);
const IconHouse = () => (
  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);
const IconGavel = () => (
  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
  </svg>
);
const IconCar = () => (
  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10l1 1h1m8-1h1l1-1 1-4H9m4 5V9" />
  </svg>
);
const IconShield = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);
const IconStar = () => (
  <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
  </svg>
);
const IconArrow = () => (
  <svg className="w-5 h-5 inline-block ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

/* ──────────────────────────────────────────
   Dados dos nichos
   ────────────────────────────────────────── */
const NICHOS = [
  {
    icon: <IconBank />,
    titulo: "Direito Bancário",
    cor: "border-[#2D7DD2]",
    badge: "bg-[#2D7DD2]/15 text-[#2D7DD2]",
    descricao:
      "Cobranças indevidas, RMC/RCC, fraudes, venda casada de seguros e irregularidades em contratos de crédito.",
    subs: ["Fila de Banco", "RMC / RCC", "Fraudes Bancárias", "Venda Casada"],
  },
  {
    icon: <IconHouse />,
    titulo: "Distrato Imobiliário",
    cor: "border-[#C9A84C]",
    badge: "bg-[#C9A84C]/15 text-[#C9A84C]",
    descricao:
      "Rescisão de contratos imobiliários, restituição de valores pagos e análise de cláusulas abusivas.",
    subs: ["Rescisão de Contrato", "Restituição de Valores", "Cláusulas Abusivas"],
  },
  {
    icon: <IconGavel />,
    titulo: "Execução Fiscal",
    cor: "border-[#4361EE]",
    badge: "bg-[#4361EE]/15 text-[#4361EE]",
    descricao:
      "Defesa em cobranças fiscais, parcelamentos, prescrição de dívidas tributárias e bloqueio de bens.",
    subs: ["Defesa em Execução", "Prescrição Tributária", "Desbloqueio de Bens"],
  },
  {
    icon: <IconCar />,
    titulo: "Busca e Apreensão",
    cor: "border-[#C0392B]",
    badge: "bg-[#C0392B]/15 text-[#C0392B]",
    descricao:
      "Defesa técnica em ação de busca e apreensão de veículo. Prazos legais, contestação e negociação.",
    subs: ["Defesa do Devedor", "Contestação de Liminar", "Negociação"],
  },
];

/* ──────────────────────────────────────────
   Componente principal
   ────────────────────────────────────────── */
export default function Home() {
  return (
    <div className="min-h-screen" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* ── NAVBAR ── */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-white/5 bg-[#0A1628]/90 backdrop-blur-md">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="FSC Advocacia — Dr. Fábio Cunha, OAB/RO 10.849"
                 className="h-11 w-auto" />
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-[#8899AA]">
            <a href="#areas" className="hover:text-white transition-colors">Áreas</a>
            <a href="#sobre" className="hover:text-white transition-colors">Sobre</a>
            <a href="#contato" className="hover:text-white transition-colors">Contato</a>
          </div>
          <Link
            href="/portal"
            className="rounded-md bg-[#2D7DD2] px-5 py-2 text-sm font-semibold text-white hover:bg-[#4361EE] transition-colors"
          >
            Falar com o Atendimento
          </Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section
        className="min-h-screen flex flex-col justify-center px-6 md:px-16 lg:px-24 pt-24"
        style={{ background: "linear-gradient(135deg, #0A1628 0%, #1A3A6B 60%, #0A1628 100%)" }}
      >
        <div className="mx-auto max-w-6xl w-full">
          {/* Badge de confiança */}
          <div className="inline-flex items-center gap-2 rounded-full border border-[#2D7DD2]/30 bg-[#2D7DD2]/10 px-4 py-1.5 text-sm text-[#2D7DD2] mb-8">
            <IconShield />
            <span>Advocacia Digital · Atendimento Nacional · OAB/RO 10.849</span>
          </div>

          <h1
            className="text-4xl md:text-6xl lg:text-7xl font-extrabold text-white leading-tight max-w-4xl"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Você tem{" "}
            <span
              className="relative inline-block"
              style={{
                background: "linear-gradient(90deg, #2D7DD2, #4361EE)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              direitos.
            </span>
            <br />
            Nós provamos.
          </h1>

          <p className="mt-6 max-w-2xl text-lg md:text-xl text-[#8899AA] leading-relaxed">
            Direito Bancário, Distrato Imobiliário, Execução Fiscal e Defesa em Busca e Apreensão.
            Conheça seus direitos com quem entende da lei.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Link
              href="/portal"
              className="rounded-md bg-[#2D7DD2] hover:bg-[#4361EE] text-white font-semibold px-8 py-4 text-base transition-colors duration-200 text-center"
            >
              Falar com o Atendimento <IconArrow />
            </Link>
            <a
              href="#areas"
              className="rounded-md border border-[#2D7DD2] text-[#2D7DD2] hover:bg-[#2D7DD2]/10 font-medium px-8 py-4 text-base transition-colors duration-200 text-center"
            >
              Conhecer as Áreas
            </a>
          </div>

          {/* Trust signals */}
          <div className="mt-14 flex flex-wrap gap-6 text-sm text-[#8899AA]">
            {[
              "100% Digital",
              "Atendimento Nacional",
              "Consulta Inicial Sem Compromisso",
              "OAB/RO 10.849",
            ].map((s) => (
              <span key={s} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2D7DD2] inline-block" />
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── ÁREAS DE ATUAÇÃO ── */}
      <section id="areas" className="py-24 px-6 md:px-16 lg:px-24 bg-[#0A1628]">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12">
            <p className="text-[#2D7DD2] text-sm font-semibold uppercase tracking-widest mb-3">
              Áreas de Atuação
            </p>
            <h2
              className="text-3xl md:text-4xl font-bold text-white"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Como podemos ajudar?
            </h2>
            <p className="mt-3 text-[#8899AA] max-w-xl">
              Atuamos nas principais causas do consumidor e contribuinte,
              com estratégia técnica e atendimento humanizado.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {NICHOS.map((n) => (
              <div
                key={n.titulo}
                className={`rounded-xl border-l-4 ${n.cor} bg-[#1A3A6B]/20 border border-white/5 p-6 hover:bg-[#1A3A6B]/30 transition-colors`}
              >
                <div className={`inline-flex rounded-lg p-2.5 mb-4 ${n.badge}`}>
                  {n.icon}
                </div>
                <h3
                  className="text-xl font-bold text-white mb-2"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  {n.titulo}
                </h3>
                <p className="text-[#8899AA] text-sm leading-relaxed mb-4">
                  {n.descricao}
                </p>
                <div className="flex flex-wrap gap-2">
                  {n.subs.map((s) => (
                    <span
                      key={s}
                      className={`text-xs rounded-full px-3 py-1 font-medium ${n.badge}`}
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── COMO FUNCIONA ── */}
      <section className="py-24 px-6 md:px-16 lg:px-24 bg-[#1A3A6B]/10">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <p className="text-[#2D7DD2] text-sm font-semibold uppercase tracking-widest mb-3">
              Processo
            </p>
            <h2
              className="text-3xl md:text-4xl font-bold text-white"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Como funciona o atendimento
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { n: "01", t: "Consulta Inicial", d: "Descreva sua situação pelo portal. Analisamos o caso e identificamos se há direito a ser exercido." },
              { n: "02", t: "Análise Jurídica", d: "Nossa equipe avalia o caso com base na legislação, jurisprudência e nos documentos apresentados." },
              { n: "03", t: "Estratégia e Ação", d: "Com o diagnóstico em mãos, traçamos a estratégia jurídica adequada e orientamos cada passo." },
            ].map((step) => (
              <div key={step.n} className="flex flex-col items-start">
                <span
                  className="text-5xl font-extrabold text-[#2D7DD2]/30 mb-4 leading-none"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  {step.n}
                </span>
                <h3 className="text-lg font-bold text-white mb-2">{step.t}</h3>
                <p className="text-[#8899AA] text-sm leading-relaxed">{step.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SOBRE / CREDENCIAIS ── */}
      <section id="sobre" className="py-24 px-6 md:px-16 lg:px-24 bg-[#0A1628]">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            {/* Texto */}
            <div>
              <p className="text-[#2D7DD2] text-sm font-semibold uppercase tracking-widest mb-3">
                O Advogado
              </p>
              <h2
                className="text-3xl md:text-4xl font-bold text-white mb-4"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                Dr. Fábio Silva Cunha
              </h2>
              <p className="text-[#8899AA] leading-relaxed mb-4">
                Advogado inscrito na OAB/RO sob o n.º 10.849, com atuação focada na defesa
                dos direitos do consumidor e do contribuinte. Operação 100% digital,
                atendendo clientes em todo o território nacional.
              </p>
              <p className="text-[#8899AA] leading-relaxed mb-6">
                A FSC Advocacia une rigor técnico jurídico a uma abordagem acessível e
                transparente, garantindo que cada cliente compreenda sua situação e as
                possibilidades legais disponíveis.
              </p>
              <div className="flex flex-wrap gap-3">
                {["OAB/RO 10.849", "Advocacia Digital", "Atendimento Nacional"].map((tag) => (
                  <span
                    key={tag}
                    className="text-xs border border-[#2D7DD2]/30 text-[#2D7DD2] rounded-full px-3 py-1"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            {/* Card de destaque */}
            <div className="rounded-xl bg-[#1A3A6B]/30 border border-[#2D7DD2]/20 p-8">
              <div className="flex mb-4">
                {[...Array(5)].map((_, i) => (
                  <span key={i} className="text-[#C9A84C]"><IconStar /></span>
                ))}
              </div>
              <p className="text-white text-lg leading-relaxed italic mb-6">
                "Recebi todo o suporte necessário para entender meu caso. O atendimento
                foi claro, objetivo e completamente digital — muito prático."
              </p>
              <p className="text-[#8899AA] text-sm">
                Cliente — Direito Bancário — SP
              </p>
              <hr className="border-white/10 my-6" />
              <p className="text-[#8899AA] text-xs">
                Depoimento genérico. Nomes e processos não são divulgados em conformidade
                com o Provimento 205/2021 da OAB.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA FINAL ── */}
      <section
        id="contato"
        className="py-24 px-6 text-center"
        style={{ background: "linear-gradient(135deg, #1A3A6B 0%, #0A1628 100%)" }}
      >
        <div className="mx-auto max-w-2xl">
          <h2
            className="text-3xl md:text-4xl font-bold text-white mb-4"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Tire suas dúvidas
          </h2>
          <p className="text-[#8899AA] mb-8 leading-relaxed">
            Descreva sua situação pelo portal de atendimento. Nossa equipe analisará o caso
            e retornará com as orientações adequadas.
          </p>
          <Link
            href="/portal"
            className="rounded-md bg-[#2D7DD2] hover:bg-[#4361EE] text-white font-bold px-10 py-4 text-base transition-colors duration-200 inline-block"
          >
            Acessar o Portal de Atendimento <IconArrow />
          </Link>
          <p className="mt-6 text-xs text-[#8899AA]">
            Este canal é informativo. Não constitui contratação de serviços jurídicos.
          </p>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-white/5 bg-[#0A1628] py-10 px-6">
        <div className="mx-auto max-w-6xl flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-[#8899AA]">
          <div className="flex flex-col items-center md:items-start gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="FSC Advocacia" className="h-9 w-auto" />
            <span>Dr. Fábio Silva Cunha — OAB/RO 10.849</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <a
              href="mailto:contato@fscadvocaciadigital.com.br"
              className="hover:text-[#2D7DD2] transition-colors"
            >
              contato@fscadvocaciadigital.com.br
            </a>
            <span>Operação 100% digital · Atendimento nacional</span>
          </div>
          <div className="text-xs text-center md:text-right text-[#8899AA]/60">
            <p>Comunicação em conformidade com o Provimento OAB 205/2021.</p>
            <p>© {new Date().getFullYear()} FSC Advocacia. Todos os direitos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
