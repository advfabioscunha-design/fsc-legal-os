import Link from "next/link";
import Header from "../components/Header";
import AtendimentoChat from "../components/AtendimentoChat";
import AtendimentoWhats from "../components/AtendimentoWhats";

export const metadata = {
  title: "Elaboração de Contrato | FC Advocacia",
  description: "Contratos sob medida, elaborados com base na legislação e na jurisprudência aplicável, com total segurança jurídica.",
};

const PASSOS = [
  { n: 1, t: "Você assina o contrato de serviço", d: "Antes de tudo, você assina o nosso contrato de prestação de serviço — rápido e digital." },
  { n: 2, t: "Conta o que precisa", d: "Você descreve o tipo de contrato que precisa e o objetivo." },
  { n: 3, t: "Definição da complexidade e do valor", d: "Logo na primeira informação, o agente explica a complexidade e o valor correspondente (você pode escolher uma faixa maior, nunca menor que a análise)." },
  { n: 4, t: "Coleta das informações", d: "O agente especialista solicita, passo a passo, os dados necessários para confeccionar o contrato." },
  { n: 5, t: "Elaboração com segurança jurídica", d: "O contrato é elaborado com base na legislação específica e na jurisprudência aplicável." },
  { n: 6, t: "Revisão e orientações", d: "Você recebe o contrato espelhado para conferência, com orientações sobre eventuais cláusulas abusivas." },
  { n: 7, t: "Aprovação e envio", d: "Com a sua aprovação, o contrato final é enviado por WhatsApp ou e-mail." },
];

const COMPLEXIDADE = [
  { nivel: "Baixa", preco: "R$ 69,90", d: "Contratos simples e diretos (ex.: recibos, declarações, acordos básicos)." },
  { nivel: "Média", preco: "R$ 99,90", d: "Contratos com cláusulas específicas e obrigações mais detalhadas." },
  { nivel: "Alta", preco: "R$ 249,90", d: "Contratos complexos, com garantias, múltiplas partes ou alto valor envolvido." },
];

export default function ContratoLanding() {
  return (
    <main className="bg-navy text-white">
      <Header />

      {/* Hero */}
      <section className="px-6 pt-32 pb-16 md:pt-40">
        <div className="mx-auto max-w-4xl text-center">
          <span className="mb-5 inline-block rounded-full border border-gold/40 px-4 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-gold">
            Serviço Jurídico Digital
          </span>
          <h1 className="font-serif text-4xl font-bold leading-tight md:text-5xl">
            Elaboração de Contrato com <span className="text-gold">Segurança Jurídica</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-white/75">
            Seu contrato elaborado sob medida, com base na legislação específica e na jurisprudência
            aplicável — com orientação sobre cláusulas abusivas e total segurança jurídica.
          </p>
          <div className="mt-9 flex flex-col items-center gap-4">
            <AtendimentoChat variant="inline" label="Solicitar meu contrato agora"
              className="w-full max-w-xs rounded-full bg-gold px-10 py-5 text-center text-base font-bold text-navy shadow-xl shadow-gold/20 transition hover:bg-amber sm:w-auto" />
            <AtendimentoWhats variant="inline" label="Tirar dúvidas no WhatsApp"
              className="rounded-full border border-gold/40 bg-white/5 px-8 py-3 text-sm font-semibold text-white transition hover:border-gold hover:bg-white/10" />
          </div>
        </div>
      </section>

      {/* Como funciona */}
      <section className="bg-petrol py-20">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="text-center font-serif text-3xl font-bold">Como funciona</h2>
          <ol className="mt-10 space-y-4">
            {PASSOS.map((p) => (
              <li key={p.n} className="flex gap-4 rounded-xl border border-white/10 bg-navy/50 p-5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gold font-bold text-navy">{p.n}</span>
                <div>
                  <p className="font-semibold text-white">{p.t}</p>
                  <p className="mt-1 text-sm text-white/65">{p.d}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Complexidade e preço */}
      <section className="py-20">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-center font-serif text-3xl font-bold">Valores por complexidade</h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-white/65">
            O valor é definido pela complexidade do contrato. Você pode escolher uma faixa maior, mas nunca menor que a análise do especialista.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-3">
            {COMPLEXIDADE.map((c) => (
              <div key={c.nivel} className="rounded-2xl border border-white/10 bg-petrol p-6 text-center">
                <p className="text-sm font-semibold uppercase tracking-wide text-gold">{c.nivel}</p>
                <p className="mt-2 font-serif text-3xl font-bold">{c.preco}</p>
                <p className="mt-3 text-sm text-white/60">{c.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Segurança jurídica */}
      <section className="bg-petrol py-16">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="font-serif text-2xl font-bold">Total segurança jurídica</h2>
          <p className="mt-4 text-white/70">
            Todo contrato é elaborado com base nas legislações específicas e na jurisprudência aplicável.
            Antes da entrega, você recebe o documento espelhado para conferência, com orientações claras
            sobre eventuais cláusulas abusivas — e só é finalizado com a sua aprovação.
          </p>
        </div>
      </section>

      {/* CTA final */}
      <section className="py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="font-serif text-3xl font-bold">Pronto para começar?</h2>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <AtendimentoChat variant="inline" label="Solicitar meu contrato agora"
              className="rounded-full bg-gold px-10 py-4 text-sm font-bold text-navy hover:bg-amber" />
            <Link href="/entrar?next=/cliente"
              className="rounded-full border border-white/20 px-8 py-4 text-sm font-semibold text-white hover:border-gold">
              Acessar minha área
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-navy py-10 text-center text-white/60">
        <p className="text-sm text-white/80">📍 Bases em <b>Porto Velho/RO</b> &nbsp;•&nbsp; <b>Florianópolis/SC</b></p>
        <p className="text-xs text-white/50">Atuação em todo o território nacional</p>
        <p className="mt-4 text-xs text-white/40">© {new Date().getFullYear()} FC Advocacia. Todos os direitos reservados.</p>
      </footer>
    </main>
  );
}
