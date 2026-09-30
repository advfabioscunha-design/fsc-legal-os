import Link from "next/link";
import Image from "next/image";
import Header from "./components/Header";
import AtendimentoChat from "./components/AtendimentoChat";
import AtendimentoWhats from "./components/AtendimentoWhats";
import {
  IlustraBancario, IlustraImobiliario, IlustraFiscal,
  IlustraEnergia, IlustraContrato, MalhaHero,
} from "./components/ui/Ilustracoes";

/* PÁGINA INICIAL
 *
 * Duas coisas guiaram a reescrita.
 *
 * A primeira: o texto anterior falava do escritório. "Atendimento
 * especializado", "experiência e credibilidade", "soluções jurídicas
 * estratégicas". São frases que qualquer escritório do país poderia
 * assinar sem mudar uma vírgula, e por isso não dizem nada. Quem chega
 * aqui não está procurando um escritório bom em abstrato: está com um
 * problema concreto e quer saber se aquele problema tem solução. O
 * texto agora começa pelo problema dele.
 *
 * A segunda: nada de travessão. É pontuação correta, mas virou marca
 * registrada de texto de máquina, e quem lê percebe. Onde havia
 * travessão agora há ponto, vírgula ou dois pontos, que é como as
 * pessoas escrevem.
 */

const AREAS = [
  {
    slug: "direito-bancario",
    titulo: "Direito bancário",
    gancho: "A parcela não bate com o contrato?",
    desc: "Juros acima do combinado, tarifas que ninguém explicou, cartão consignado que você não pediu, PIX de fraude e busca e apreensão de veículo.",
    Icone: IlustraBancario,
  },
  {
    slug: "distrato-imobiliario",
    titulo: "Distrato imobiliário",
    gancho: "A obra atrasou ou você quer sair do contrato?",
    desc: "Atraso na entrega das chaves e retenção de valores acima do que a lei permite quando o comprador desiste.",
    Icone: IlustraImobiliario,
  },
  {
    slug: "execucao-fiscal",
    titulo: "Execução fiscal",
    gancho: "Bloquearam sua conta por uma dívida antiga?",
    desc: "Defesa em cobrança de tributos, desbloqueio de valores e discussão de débitos já prescritos.",
    Icone: IlustraFiscal,
  },
  {
    slug: "recuperacao-consumo",
    titulo: "Recuperação de consumo",
    gancho: "A concessionária cobrou meses de energia de uma vez?",
    desc: "Defesa contra o TOI e contra a cobrança retroativa de consumo de energia elétrica.",
    Icone: IlustraEnergia,
  },
];

/* O que muda para quem contrata. Nenhum item é adjetivo sobre o
   escritório: todos são fatos verificáveis sobre como o trabalho
   acontece. Adjetivo qualquer um escreve. */
const COMO_TRABALHAMOS = [
  {
    t: "Você acompanha pela internet",
    d: "Uma área só sua, com cada etapa do caso registrada e os documentos guardados no mesmo lugar.",
    n: "01",
  },
  {
    t: "Quem assina responde",
    d: "Advogado inscrito na OAB revisa e assina cada peça antes de ir ao processo.",
    n: "02",
  },
  {
    t: "Prazo controlado todo dia",
    d: "As publicações são lidas diariamente e cada prazo entra na agenda no dia em que precisa ser trabalhado.",
    n: "03",
  },
  {
    t: "Atendimento de onde você estiver",
    d: "Conversa por vídeo, WhatsApp e e-mail. O escritório atende em todo o país sem exigir deslocamento.",
    n: "04",
  },
];

export default function Home() {
  return (
    <main className="bg-navy text-white">
      <Header />

      {/* HERO */}
      <section className="relative overflow-hidden">
        <MalhaHero className="pointer-events-none absolute -right-40 -top-32 h-[680px] w-[680px] opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-navy/40 to-navy" />

        <div className="relative mx-auto grid max-w-content grid-cols-1 items-center gap-14 px-6 pb-24 pt-32 md:grid-cols-[1.1fr_.9fr] md:pt-40">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-electric/30 bg-electric/10 px-4 py-1.5 text-caption font-semibold uppercase tracking-[0.16em] text-electric">
              <span className="h-1.5 w-1.5 rounded-full bg-electric" />
              Advocacia digital, atendimento em todo o Brasil
            </span>

            {/* A ABERTURA

                Era uma pergunta acusatória: "Cobraram de você o que não
                deviam?". Funciona como anúncio e falha como recepção.
                Quem chega a um escritório já sabe que algo deu errado;
                o que ele não sabe é como será atendido, se vai
                conseguir falar com alguém e se vai ficar no escuro.

                A abertura passa a responder isso: quem somos, como
                trabalhamos e o que a pessoa encontra aqui. */}
            <h1 className="mt-6 font-display text-display-lg font-bold">
              Seu caso,
              <br />
              <span className="bg-gradient-to-r from-electric to-indigo bg-clip-text text-transparent">
                acompanhado de perto.
              </span>
            </h1>

            <p className="mt-6 max-w-xl text-subtitle text-white/70">
              Você é recebido, ouvido e acompanha tudo em tempo real. Cada
              movimentação do seu processo aparece na sua área na plataforma, e
              você fala com o escritório por ali, sem intermediário e sem
              esperar retorno de ligação.
            </p>

            <ul className="mt-7 grid max-w-xl gap-2.5">
              {[
                "Sua área na plataforma, com o andamento e os documentos do seu caso",
                "Conversa direta com o escritório, registrada e disponível a qualquer hora",
                "Aviso por e-mail a cada passo, sem você precisar perguntar",
                "A primeira análise do seu caso não custa nada",
              ].map((t) => (
                <li key={t} className="flex gap-3 text-body text-white/75">
                  <svg className="mt-1 h-4 w-4 shrink-0 text-electric" viewBox="0 0 20 20"
                    fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" clipRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 10-1.4 1.4l2 2a1 1 0 001.4 0l4-4z" />
                  </svg>
                  {t}
                </li>
              ))}
            </ul>

            <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
              {/* ANALISAR MEU CASO LEVA AO CADASTRO

                  Antes abria uma janela de conversa que sumia quando a
                  pessoa fechava a aba: nem ela nem o escritório
                  conseguiam retomar do ponto em que pararam. Agora o
                  primeiro passo é criar o acesso com senha, e a partir
                  dali toda conversa e cada solicitação ficam
                  registradas na área dela. Sair e voltar passa a ser
                  continuar, e não recomeçar. */}
              <Link
                href="/entrar?next=/cliente&novo=1"
                className="inline-flex w-full items-center justify-center rounded-lg bg-electric px-8 py-4 text-subtitle font-semibold text-white shadow-glow transition-all hover:bg-indigo sm:w-auto"
              >
                Analisar meu caso
              </Link>
              <Link
                href="#areas"
                className="inline-flex w-full items-center justify-center rounded-lg border border-white/25 px-8 py-4 text-subtitle font-medium text-white transition hover:border-white/60 hover:bg-white/5 sm:w-auto"
              >
                Ver as áreas de atuação
              </Link>
            </div>

            <dl className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-white/10 pt-7">
              {[
                ["Acompanhamento", "Tempo real"],
                ["Atuação", "Todo o Brasil"],
                ["Primeira análise", "Sem custo"],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-caption uppercase tracking-wider text-slate">{k}</dt>
                  <dd className="mt-1 font-display text-body font-bold text-white">{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="relative mx-auto w-full max-w-sm">
            <div className="absolute -inset-3 rounded-xl2 bg-gradient-to-br from-electric/25 to-transparent blur-2xl" />
            {/* A FOTO DENTRO DA PALETA

                O retrato foi feito num ambiente de madeira e luz
                quente, e o site é marinho e azul frio. Lado a lado, as
                duas temperaturas brigam e a página parece montada com
                peças de origens diferentes.

                Em vez de trocar a foto, ela é trazida para a paleta:
                uma camada de marinho em multiply apaga o excesso de
                âmbar do fundo, e uma de azul elétrico em soft-light
                devolve contraste. O rosto continua natural, porque
                essas camadas mordem mais as áreas escuras do fundo do
                que a pele. */}
            <div className="relative overflow-hidden rounded-xl2 border border-white/10 shadow-lift">
              <Image
                src="/dr-fabio-hero.jpg"
                alt="Dr. Fábio Cunha, responsável pelo escritório"
                width={520}
                height={640}
                priority
                className="h-auto w-full object-cover saturate-[0.85] contrast-[1.05]"
              />
              <div className="pointer-events-none absolute inset-0 bg-navy/45 mix-blend-multiply" />
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-electric/25 to-transparent mix-blend-soft-light" />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-navy via-navy/85 to-transparent p-5">
                <p className="font-display text-body font-bold">Dr. Fábio Cunha</p>
                <p className="text-small text-slate">Responsável pelo escritório</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* COMO O ESCRITÓRIO TRABALHA
           Vem antes das áreas de atuação de propósito. Quem chega já
           sabe qual é o problema dele; o que decide se ele fica é
           entender como será atendido. */}
      <section className="border-y border-white/10 bg-petrol py-20">
        <div className="mx-auto max-w-content px-6">
          <span className="text-caption font-semibold uppercase tracking-[0.16em] text-electric">
            Como trabalhamos
          </span>
          <h2 className="mt-3 max-w-2xl font-display text-display font-bold">
            Você não fica no escuro em nenhum momento
          </h2>
          <p className="mt-4 max-w-2xl text-subtitle text-white/65">
            A parte mais desgastante de ter um processo não é a espera: é não
            saber. Aqui cada passo aparece na sua área, no mesmo dia em que
            acontece.
          </p>

          <ol className="mt-12 grid gap-px overflow-hidden rounded-xl2 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["01", "Você cria o seu acesso",
               "Leva um minuto. A partir dali, tudo o que você conversar e enviar fica guardado, e você retoma de onde parou."],
              ["02", "Conta o que aconteceu",
               "Pela plataforma, no seu tempo. O escritório estuda o caso e responde o que dá para fazer, com o custo na mão."],
              ["03", "Acompanha em tempo real",
               "Fase do caso, documentos, prazos e cada movimentação do processo, na sua área e no seu e-mail."],
              ["04", "Fala direto com quem cuida",
               "Sem intermediário e sem esperar retorno de ligação. A conversa fica registrada dentro do seu caso."],
            ].map(([n, t, d]) => (
              <li key={n} className="bg-petrol p-7">
                <span className="font-mono text-caption font-bold text-gold">{n}</span>
                <h3 className="mt-3 font-display text-body font-bold">{t}</h3>
                <p className="mt-2 text-small text-white/65">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ÁREAS */}
      <section id="areas" className="scroll-mt-24 bg-ice py-24 text-charcoal">
        <div className="mx-auto max-w-content px-6">
          <span className="text-caption font-semibold uppercase tracking-[0.16em] text-electric">
            Áreas de atuação
          </span>
          <h2 className="mt-3 max-w-2xl font-display text-display font-bold text-navy">
            Quatro situações em que o dinheiro sai do lugar errado
          </h2>
          <p className="mt-4 max-w-2xl text-subtitle text-charcoal/65">
            Veja em qual delas o seu caso se encaixa. Se não se encaixar em
            nenhuma, fale com o escritório mesmo assim.
          </p>

          <div className="mt-14 grid gap-6 sm:grid-cols-2">
            {AREAS.map(({ slug, titulo, gancho, desc, Icone }) => (
              <Link
                key={slug}
                href={`/areas/${slug}`}
                className="group relative flex gap-5 rounded-xl2 border border-navy/[.07] bg-white p-7 shadow-card transition-all hover:-translate-y-1 hover:border-electric/40 hover:shadow-lift"
              >
                <Icone className="h-14 w-14 shrink-0 text-navy" />
                <div className="min-w-0">
                  <h3 className="font-display text-title font-bold text-navy">{titulo}</h3>
                  <p className="mt-1.5 text-body font-semibold text-electric">{gancho}</p>
                  <p className="mt-2.5 text-body text-charcoal/65">{desc}</p>
                  <span className="mt-4 inline-flex items-center gap-1.5 text-small font-semibold text-navy transition group-hover:gap-2.5 group-hover:text-electric">
                    Entender esse caso
                    <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M6 3l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CONTRATOS */}
      <section className="bg-white py-24 text-charcoal">
        <div className="mx-auto grid max-w-content items-center gap-12 px-6 md:grid-cols-[1fr_auto]">
          <div>
            <span className="text-caption font-semibold uppercase tracking-[0.16em] text-gold">
              Serviço avulso
            </span>
            <h2 className="mt-3 font-display text-display font-bold text-navy">
              Precisa de um contrato, não de um processo?
            </h2>
            <p className="mt-4 max-w-xl text-subtitle text-charcoal/65">
              Aluguel, compra e venda, prestação de serviço, comodato,
              notificação. O escritório redige sob medida para o seu caso,
              revisa e entrega em até 24 horas.
            </p>
            <Link
              href="/contrato"
              className="mt-8 inline-flex items-center justify-center rounded-lg bg-gold px-8 py-4 text-subtitle font-bold text-navy shadow-card transition hover:brightness-95"
            >
              Ver os documentos e valores
            </Link>
          </div>
          <IlustraContrato className="mx-auto hidden h-52 w-52 text-navy md:block" />
        </div>
      </section>

      {/* COMO TRABALHAMOS */}
      <section className="bg-navy py-24">
        <div className="mx-auto max-w-content px-6">
          <span className="text-caption font-semibold uppercase tracking-[0.16em] text-electric">
            Como o escritório trabalha
          </span>
          <h2 className="mt-3 max-w-2xl font-display text-display font-bold">
            Você não precisa ligar para saber do seu processo
          </h2>

          <div className="mt-14 grid gap-px overflow-hidden rounded-xl2 bg-white/10 sm:grid-cols-2">
            {COMO_TRABALHAMOS.map(({ t, d, n }) => (
              <div key={t} className="bg-navy p-8 transition hover:bg-petrol">
                <span className="font-mono text-caption font-bold text-electric">{n}</span>
                <h3 className="mt-3 font-display text-title font-bold">{t}</h3>
                <p className="mt-2.5 text-body text-white/65">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SOBRE */}
      <section id="sobre" className="scroll-mt-24 bg-ice py-24 text-charcoal">
        <div className="mx-auto grid max-w-content items-center gap-14 px-6 md:grid-cols-[.8fr_1.2fr]">
          <div className="relative mx-auto w-full max-w-xs">
            <div className="absolute -inset-2 rounded-xl2 bg-gradient-to-br from-electric/20 to-transparent blur-xl" />
            <Image
              src="/dr-fabio-bio.jpg"
              alt="Dr. Fábio Cunha"
              width={420}
              height={520}
              className="relative h-auto w-full rounded-xl2 object-cover shadow-lift"
            />
          </div>

          <div>
            <span className="text-caption font-semibold uppercase tracking-[0.16em] text-electric">
              Quem responde pelo trabalho
            </span>
            <h2 className="mt-3 font-display text-display font-bold text-navy">
              Dr. Fábio Cunha
            </h2>
            <p className="mt-6 text-subtitle text-charcoal/70">
              Advogado inscrito na OAB de Rondônia sob o número 10.849. Atua em
              direito bancário, imobiliário, tributário e do consumidor,
              defendendo pessoas e empresas contra cobranças que não se
              sustentam.
            </p>
            <p className="mt-4 text-subtitle text-charcoal/70">
              O escritório funciona de forma digital, com bases em Porto Velho e
              Florianópolis e atuação em todo o território nacional. Isso
              significa que o seu caso é acompanhado de perto sem que você
              precise sair de casa, e que você vê cada movimentação assim que
              ela acontece.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <AtendimentoChat
                variant="inline"
                label="Conversar sobre o meu caso"
                className="inline-flex items-center justify-center rounded-lg bg-electric px-7 py-3.5 text-body font-semibold text-white shadow-card transition hover:bg-indigo"
              />
              <AtendimentoWhats
                variant="inline"
                label="Chamar no WhatsApp"
                className="inline-flex items-center justify-center rounded-lg border border-navy/15 px-7 py-3.5 text-body font-semibold text-navy transition hover:border-navy/40 hover:bg-navy/[.03]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* CONTATO */}
      <section id="contato" className="scroll-mt-24 border-t border-white/10 bg-navy py-24">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="font-display text-display font-bold">
            Conte o que aconteceu
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-subtitle text-white/65">
            Descreva a sua situação e receba uma orientação sobre o que pode ser
            feito. Sem compromisso e sem custo para entender o caso.
          </p>

          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <AtendimentoChat
              variant="inline"
              label="Analisar meu caso"
              className="inline-flex items-center justify-center rounded-lg bg-electric px-8 py-4 text-subtitle font-semibold text-white shadow-glow transition hover:bg-indigo"
            />
            <AtendimentoWhats
              variant="inline"
              label="Chamar no WhatsApp"
              className="inline-flex items-center justify-center rounded-lg border border-white/25 px-8 py-4 text-subtitle font-medium text-white transition hover:border-white/60 hover:bg-white/5"
            />
          </div>

          <p className="mt-10 text-small text-slate">
            Porto Velho, Rondônia e Florianópolis, Santa Catarina.
            <br />
            Atendimento em todo o território nacional.
          </p>
        </div>
      </section>

      {/* RODAPÉ */}
      <footer className="border-t border-white/10 bg-navy py-14">
        <div className="mx-auto grid max-w-content gap-10 px-6 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-electric to-indigo font-display text-body font-bold text-white">
                FC
              </span>
              <span className="flex flex-col leading-none">
                <span className="font-display text-body font-bold text-white">Advocacia</span>
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate">
                  Recuperação Patrimonial
                </span>
              </span>
            </div>
            {/* O NÚMERO DA OAB FICA, E FICA AQUI

                Saiu do cabeçalho, do hero e da legenda da foto, que é
                onde ele não ajudava ninguém. Permanece no rodapé
                porque o Provimento 205/2021 da OAB exige que a
                comunicação profissional identifique o advogado
                responsável e o número de inscrição. Tirar de todo
                lugar deixaria o site em desacordo com a norma que ele
                próprio cita no fim da página. */}
            <p className="mt-4 text-small text-slate">
              Dr. Fábio Cunha
              <br />
              OAB/RO 10.849
            </p>
          </div>

          <div>
            <h3 className="text-caption font-semibold uppercase tracking-wider text-white">
              Áreas
            </h3>
            <ul className="mt-4 space-y-2.5">
              {AREAS.map((a) => (
                <li key={a.slug}>
                  <Link href={`/areas/${a.slug}`} className="text-small text-slate transition hover:text-white">
                    {a.titulo}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-caption font-semibold uppercase tracking-wider text-white">
              Serviços
            </h3>
            <ul className="mt-4 space-y-2.5">
              <li><Link href="/contrato" className="text-small text-slate transition hover:text-white">Elaboração de contratos</Link></li>
              <li><Link href="/entrar?next=/cliente" className="text-small text-slate transition hover:text-white">Área do cliente</Link></li>
              <li><Link href="/privacidade" className="text-small text-slate transition hover:text-white">Política de privacidade</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-caption font-semibold uppercase tracking-wider text-white">
              Atendimento
            </h3>
            <ul className="mt-4 space-y-2.5">
              <li className="text-small text-slate">Porto Velho, RO</li>
              <li className="text-small text-slate">Florianópolis, SC</li>
              {/* A porta de serviço. Fica no rodapé porque não é
                  conteúdo de marketing, mas precisa ser encontrável:
                  estava em cinza sobre cinza e quem trabalha aqui não
                  achava. */}
              <li className="pt-2">
                <Link href="/acesso-equipe"
                  className="inline-flex items-center gap-1.5 text-small font-medium text-slate transition hover:text-white">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
                    strokeLinecap="round" className="h-4 w-4" aria-hidden="true">
                    <path d="M15 3h4v18h-4M11 16l4-4-4-4M15 12H3" />
                  </svg>
                  Área da equipe
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mx-auto mt-12 max-w-content border-t border-white/10 px-6 pt-7">
          <p className="text-caption text-slate">
            © {new Date().getFullYear()} FC Advocacia. Conteúdo informativo, nos
            termos do Provimento 205/2021 da OAB. Este site não substitui a
            consulta a um advogado sobre o seu caso concreto.
          </p>
        </div>
      </footer>
    </main>
  );
}
