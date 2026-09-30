import Link from "next/link";
import Header from "../components/Header";
import AtendimentoChat from "../components/AtendimentoChat";
import { IlustraContrato } from "../components/ui/Ilustracoes";

/* ELABORAÇÃO DE CONTRATOS
 *
 * Três coisas estavam erradas aqui e nenhuma era de design.
 *
 * 1. O texto contava o bastidor. "O escritório explica a complexidade", "o
 *    agente especialista solicita os dados". Quem contrata um contrato
 *    quer saber que um advogado responde por ele, não como o escritório
 *    organiza o trabalho por dentro. A ferramenta é assunto do
 *    escritório; o cliente contrata o escritório.
 *
 * 2. A página anunciava uma tabela de preços, e ainda por cima uma
 *    tabela que não batia com o que o sistema cobra. Os valores saíram
 *    do site inteiro: anunciar honorário ao público é mercantilização
 *    da advocacia, que o Provimento 205/2021 da OAB não admite. O preço
 *    continua existindo e continua sendo dito com todas as letras, só
 *    que no atendimento, a quem já descreveu o que precisa.
 *
 * 3. Havia dois botões concorrendo no mesmo lugar, e um deles era de
 *    WhatsApp, que já existe fixo no canto da tela. Duas portas para a
 *    mesma sala fazem a pessoa parar para escolher em vez de entrar.
 *
 * O texto também encolheu. O passo a passo tinha sete etapas escritas em
 * parágrafo; virou quatro, na linguagem de quem está contratando.
 */

export const metadata = {
  title: "Elaboração de contratos | FC Advocacia",
  description:
    "Contrato sob medida para o seu caso, com revisão e ajustes antes da entrega, pronto em até 24 horas.",
};

const PASSOS = [
  {
    n: "01",
    t: "Você escolhe o documento",
    d: "Aluguel, compra e venda, prestação de serviço, comodato, notificação. Cada tipo tem uma lista do que precisa ser informado.",
  },
  {
    n: "02",
    t: "Conta como ficou combinado",
    d: "Envie os documentos por foto ou PDF, ou preencha os campos na tela. Os dois caminhos servem, e dá para misturar.",
  },
  {
    n: "03",
    t: "O escritório redige e revisa",
    d: "O texto segue a lei que rege aquele tipo de contrato e passa por revisão e conferência antes de chegar até você.",
  },
  {
    n: "04",
    t: "Você aprova e assina",
    d: "Leia com calma, peça ajustes se precisar e só então aprove. A assinatura é eletrônica, ou o arquivo vem para baixar.",
  },
];

const DOCUMENTOS = [
  { t: "Locação de imóvel", d: "Residencial ou comercial, com garantia, reajuste e encargos definidos." },
  { t: "Compra e venda", d: "Bem móvel ou imóvel, com prazo, forma de pagamento e posse." },
  { t: "Prestação de serviço", d: "Objeto, prazo, valor e as regras do conselho profissional quando houver." },
  { t: "Comodato", d: "Empréstimo gratuito de bem, com prazo e responsabilidade por despesas." },
  { t: "Confissão de dívida", d: "Valor, origem, parcelamento e garantia." },
  { t: "Notificação extrajudicial", d: "Cobrança, rescisão ou aviso formal, com prazo e consequência." },
  { t: "Contrato de trabalho", d: "Função, salário, jornada e período de experiência." },
  { t: "Rescisão e distrato", d: "Encerramento de contrato em vigor, com acerto e quitação." },
];

export default function ContratoLanding() {
  return (
    <main className="bg-navy text-white">
      <Header />

      {/* HERO */}
      <section className="px-6 pb-20 pt-32 md:pt-40">
        <div className="mx-auto grid max-w-content items-center gap-12 md:grid-cols-[1.15fr_.85fr]">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/10 px-4 py-1.5 text-caption font-semibold uppercase tracking-[0.16em] text-gold">
              <span className="h-1.5 w-1.5 rounded-full bg-gold" />
              Sem processo, sem audiência
            </span>

            <h1 className="mt-6 font-display text-display-lg font-bold">
              Seu contrato escrito
              <br />
              <span className="text-gold">sob medida</span>
            </h1>

            <p className="mt-6 max-w-xl text-subtitle text-white/70">
              Modelo baixado da internet não conhece o seu imóvel, o seu
              inquilino nem o que vocês combinaram. Aqui o texto é feito para o
              seu caso, segue a lei daquele tipo de contrato e passa por
              revisão antes de chegar até você.
            </p>

            <div className="mt-10">
              <Link
                href="/entrar?novo=1&next=/cliente"
                className="inline-flex w-full items-center justify-center rounded-lg bg-gold px-9 py-4 text-subtitle font-bold text-navy shadow-card transition hover:brightness-95 sm:w-auto"
              >
                Pedir meu contrato
              </Link>
              <p className="mt-3 text-small text-slate">
                Pronto em até 24 horas. Se precisar para hoje, há entrega em
                até 6 horas.
              </p>
              {/* UMA PORTA SÓ

                  Este botão levava direto ao catálogo, e quem pede a
                  análise de um caso passava antes pelo cadastro. Eram
                  duas entradas diferentes para a mesma casa, e a
                  segunda deixava o pedido do lado de fora da conta.

                  Agora as duas levam ao mesmo cadastro. Feito o acesso,
                  a pessoa cai na área dela e escolhe ali o serviço, no
                  mesmo lugar onde depois acompanha o andamento e
                  conversa com o escritório. */}
              <p className="mt-2 text-small text-slate/80">
                O primeiro passo é criar o seu acesso com senha. Feito isso,
                você escolhe o documento dentro da sua área, e é lá que fica a
                conversa e o andamento do pedido, sempre no mesmo lugar.
              </p>
            </div>
          </div>

          <IlustraContrato className="mx-auto hidden h-64 w-64 text-white/70 md:block" />
        </div>
      </section>

      {/* COMO FUNCIONA */}
      <section className="border-y border-white/10 bg-petrol py-20">
        <div className="mx-auto max-w-content px-6">
          <h2 className="font-display text-display font-bold">Como funciona</h2>
          <p className="mt-3 max-w-xl text-subtitle text-white/65">
            Quatro passos. Você só precisa do primeiro para saber quanto custa.
          </p>

          <ol className="mt-12 grid gap-px overflow-hidden rounded-xl2 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
            {PASSOS.map((p) => (
              <li key={p.n} className="bg-petrol p-7">
                <span className="font-mono text-caption font-bold text-gold">{p.n}</span>
                <h3 className="mt-3 font-display text-body font-bold">{p.t}</h3>
                <p className="mt-2 text-small text-white/65">{p.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* DOCUMENTOS */}
      <section className="py-20">
        <div className="mx-auto max-w-content px-6">
          <h2 className="font-display text-display font-bold">
            O que o escritório escreve
          </h2>
          <p className="mt-3 max-w-xl text-subtitle text-white/65">
            Se o documento que você precisa não estiver na lista, fale com o
            escritório antes de contratar.
          </p>

          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {DOCUMENTOS.map((d) => (
              <div key={d.t} className="rounded-xl2 border border-white/10 bg-petrol/60 p-6 transition hover:border-gold/40">
                <h3 className="font-display text-body font-bold">{d.t}</h3>
                <p className="mt-2 text-small text-white/60">{d.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PRAZO E CUIDADO
           Esta secao ficava com a tabela de valores. Saiu: anunciar
           honorario ao publico e o tipo de mercantilizacao que o
           Provimento 205/2021 da OAB nao admite, e um site de
           escritorio nao e vitrine de loja. O valor existe, e dito com
           clareza, mas no atendimento, para a pessoa que ja descreveu o
           que precisa. Ali ele e resposta a uma pergunta concreta, nao
           preco em prateleira. */}
      <section className="border-y border-white/10 bg-petrol py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="font-display text-display font-bold">
            Quanto tempo leva
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-subtitle text-white/65">
            O documento fica pronto em até 24 horas depois que você enviar as
            informações. Se precisar para hoje, há entrega em até 6 horas.
          </p>

          <div className="mt-10 grid gap-5 sm:grid-cols-3 text-left">
            {[
              ["Você descreve", "Conta o que precisa e o escritório informa as condições do serviço."],
              ["O escritório escreve", "Texto conforme a lei daquele contrato, revisado e ajustado antes de sair."],
              ["Você aprova", "Lê com calma, pede ajuste se precisar e só então assina."],
            ].map(([t, d]) => (
              <div key={t} className="rounded-xl2 border border-white/10 bg-navy p-6">
                <h3 className="font-display text-body font-bold text-white">{t}</h3>
                <p className="mt-2 text-small text-white/60">{d}</p>
              </div>
            ))}
          </div>

          <p className="mt-8 text-small text-slate">
            As condições do serviço são apresentadas no atendimento, antes de
            você informar qualquer dado pessoal.
          </p>
        </div>
      </section>

      {/* GARANTIA */}
      <section className="py-20">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="font-display text-title font-bold">
            Você lê antes de aprovar
          </h2>
          <p className="mt-4 text-subtitle text-white/70">
            O documento chega para conferência com marca d’água. Se alguma
            cláusula não refletir o que foi combinado, é só apontar e o texto
            volta corrigido. Depois da entrega você ainda tem sete dias para
            pedir ajuste sem custo.
          </p>
          <p className="mt-4 text-subtitle text-white/70">
            Quando o negócio exigir escritura pública ou registro em cartório,
            o escritório avisa antes do pagamento e explica o que fazer.
            Contrato particular resolve muita coisa, mas não resolve tudo, e
            você tem direito de saber disso antes e não depois.
          </p>
        </div>
      </section>

      {/* CTA FINAL */}
      <section className="border-t border-white/10 bg-petrol py-20">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="font-display text-display font-bold">
            Vamos começar pelo seu documento
          </h2>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/entrar?novo=1&next=/cliente"
              className="inline-flex items-center justify-center rounded-lg bg-gold px-9 py-4 text-subtitle font-bold text-navy shadow-card transition hover:brightness-95"
            >
              Pedir meu contrato
            </Link>
            <AtendimentoChat
              variant="inline"
              label="Tenho uma dúvida antes"
              className="inline-flex items-center justify-center rounded-lg border border-white/25 px-9 py-4 text-subtitle font-medium text-white transition hover:border-white/60 hover:bg-white/5"
            />
          </div>
          <p className="mt-6 text-small text-slate">
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
            FC Advocacia e Recuperação Patrimonial. Dr. Fábio Cunha,
            OAB/RO 10.849.
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
