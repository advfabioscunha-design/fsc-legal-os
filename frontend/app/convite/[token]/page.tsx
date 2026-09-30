"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A PÁGINA QUE RECEBE QUEM VAI TRABALHAR AQUI
 *
 * Três telas, nesta ordem, e a ordem importa.
 *
 * 1. Boas-vindas. Antes de pedir qualquer coisa, a pessoa lê por que
 *    está sendo chamada e o que vai poder fazer. Formulário que aparece
 *    antes do motivo trata quem chega como cadastro, não como gente.
 *
 * 2. A senha. Ela escolhe, e ninguém no escritório vê. Senha provisória
 *    mandada por e-mail é senha publicada: fica na caixa de entrada de
 *    quem quiser ler, para sempre.
 *
 * 3. A confirmação, com o endereço de acesso. É o fim do cadastro, e
 *    dizer isso com todas as letras evita a dúvida mais comum depois de
 *    qualquer formulário: "será que salvou?".
 */

export default function Convite() {
  const { token } = useParams<{ token: string }>();
  const [convite, setConvite] = useState<any>(null);
  const [erro, setErro] = useState("");
  const [etapa, setEtapa] = useState<"lendo" | "senha" | "pronto">("lendo");
  const [senha, setSenha] = useState("");
  const [repetir, setRepetir] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [feito, setFeito] = useState<any>(null);

  const carregar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/convites/${token}`);
      const j = await r.json();
      if (!r.ok) { setErro(j?.detail || "Convite inválido."); return; }
      setConvite(j);
    } catch { setErro("Não consegui falar com o servidor."); }
  }, [token]);

  useEffect(() => { carregar(); }, [carregar]);

  async function concluir() {
    if (senha.length < 6) { setErro("A senha precisa de pelo menos 6 caracteres."); return; }
    if (senha !== repetir) { setErro("As duas senhas não são iguais."); return; }
    setOcupado(true); setErro("");
    try {
      const r = await fetch(`${API}/api/v1/convites/${token}/aceitar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ senha }),
      });
      const j = await r.json();
      if (!r.ok) { setErro(j?.detail || "Não foi possível concluir."); return; }
      setFeito(j); setEtapa("pronto");
    } catch { setErro("Falha de conexão."); }
    finally { setOcupado(false); }
  }

  const Moldura = ({ children }: { children: React.ReactNode }) => (
    <main className="flex min-h-screen items-center justify-center bg-navy px-5 py-12 font-sans text-white">
      <div className="w-full max-w-xl">
        <div className="mb-8 flex items-center gap-2.5">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-electric to-indigo font-display text-body font-bold text-white">
            FC
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-body font-bold text-white">Advocacia</span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate">
              Recuperação Patrimonial
            </span>
          </span>
        </div>
        {children}
      </div>
    </main>
  );

  if (erro && !convite) {
    return (
      <Moldura>
        <div className="rounded-xl2 border border-crimson/30 bg-petrol p-8">
          <h1 className="font-display text-title font-bold">Este link não abre</h1>
          <p className="mt-3 text-body text-white/70">{erro}</p>
          <p className="mt-6 text-small text-slate">
            Se você já criou a sua senha, entre normalmente. Se o convite
            venceu, peça ao escritório para reenviar.
          </p>
          <Link href="/entrar?next=/inicio"
            className="mt-6 inline-block rounded-lg bg-electric px-6 py-3 text-small font-bold text-white transition hover:bg-indigo">
            Ir para a entrada
          </Link>
        </div>
      </Moldura>
    );
  }

  if (!convite) {
    return <Moldura><p className="text-small text-slate">Carregando</p></Moldura>;
  }

  const primeiro = String(convite.nome || "").split(" ")[0];

  /* ── 3. Pronto ─────────────────────────────────────────────── */
  if (etapa === "pronto" && feito) {
    return (
      <Moldura>
        <div className="rounded-xl2 border border-emerald/30 bg-petrol p-8">
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald/30 bg-emerald/10 px-4 py-1.5 text-caption font-semibold uppercase tracking-[0.14em] text-emerald">
            Cadastro concluído
          </span>

          <h1 className="mt-5 font-display text-title font-bold">
            Pronto, {primeiro}. Você já faz parte da equipe.
          </h1>

          <div className="mt-6 space-y-2 rounded-xl2 border border-white/10 bg-navy p-5">
            <p className="text-small text-white/80">
              <span className="text-slate">E-mail confirmado:</span> {feito.email}
            </p>
            <p className="text-small text-white/80">
              <span className="text-slate">Função:</span> {feito.nivel_nome}
            </p>
            <p className="text-small text-white/80">
              <span className="text-slate">Senha:</span> a que você acabou de
              criar. Ninguém no escritório a vê.
            </p>
          </div>

          <Link href="/entrar?next=/inicio"
            className="mt-7 inline-block rounded-lg bg-electric px-7 py-3.5 text-subtitle font-bold text-white shadow-card transition hover:bg-indigo hover:shadow-glow">
            Acessar a plataforma
          </Link>

          <p className="mt-6 text-small leading-relaxed text-white/60">
            No primeiro acesso você cai na tela de Início, com os prazos e as
            tarefas do dia. Nos próximos dias alguém da equipe faz a sua
            integração, apresenta os documentos do escritório e acompanha os
            seus primeiros atendimentos.
          </p>
          <p className="mt-3 text-small text-slate">
            A confirmação também foi para o seu e-mail.
          </p>
        </div>
      </Moldura>
    );
  }

  /* ── 2. A senha ────────────────────────────────────────────── */
  if (etapa === "senha") {
    return (
      <Moldura>
        <div className="rounded-xl2 border border-white/10 bg-petrol p-8">
          <h1 className="font-display text-title font-bold">Crie a sua senha</h1>
          <p className="mt-2 text-body text-white/70">
            É com ela que você entra. O escritório não escolhe senha por você
            e não tem como ver a sua.
          </p>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-caption text-slate">
                E-mail de acesso, já confirmado
              </span>
              <input value={convite.email} readOnly
                className="mt-1 w-full cursor-not-allowed rounded-lg border border-white/10 bg-navy px-3 py-2.5 text-small text-white/60" />
            </label>
            <label className="block">
              <span className="text-caption text-slate">Senha</span>
              <input value={senha} onChange={(e) => setSenha(e.target.value)}
                type="password" placeholder="pelo menos 6 caracteres"
                className="mt-1 w-full rounded-lg border border-white/10 bg-navy px-3 py-2.5 text-small text-white placeholder:text-slate/60 outline-none transition focus:border-electric" />
            </label>
            <label className="block">
              <span className="text-caption text-slate">Repita a senha</span>
              <input value={repetir} onChange={(e) => setRepetir(e.target.value)}
                type="password"
                onKeyDown={(e) => e.key === "Enter" && concluir()}
                className="mt-1 w-full rounded-lg border border-white/10 bg-navy px-3 py-2.5 text-small text-white outline-none transition focus:border-electric" />
            </label>
          </div>

          {erro && (
            <p className="mt-4 rounded-lg border border-crimson/40 bg-crimson/10 px-4 py-2.5 text-small text-white">
              {erro}
            </p>
          )}

          <button onClick={concluir} disabled={ocupado}
            className="mt-6 w-full rounded-lg bg-electric px-6 py-3.5 text-subtitle font-bold text-white transition hover:bg-indigo disabled:opacity-50">
            {ocupado ? "Criando o seu acesso…" : "Concluir cadastro"}
          </button>

          <button onClick={() => { setEtapa("lendo"); setErro(""); }}
            className="mt-4 text-small text-slate underline underline-offset-4 transition hover:text-white">
            voltar
          </button>
        </div>
      </Moldura>
    );
  }

  /* ── 1. Boas-vindas ────────────────────────────────────────── */
  return (
    <Moldura>
      <div className="rounded-xl2 border border-white/10 bg-petrol p-8">
        <span className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/10 px-4 py-1.5 text-caption font-semibold uppercase tracking-[0.14em] text-gold">
          Convite para a equipe
        </span>

        <h1 className="mt-5 font-display text-display font-bold leading-tight">
          {primeiro}, seja bem-vindo
          <br />
          <span className="text-electric">à FC Advocacia.</span>
        </h1>

        <div className="mt-6 space-y-4 text-body leading-relaxed text-white/75">
          <p>
            Este convite não é para preencher uma vaga. O escritório trabalha
            com gente que chegou depois de ter sido cobrada a mais, ter tido a
            conta bloqueada, ter comprado um imóvel que não saiu do papel.
            Quase sempre é a primeira vez que alguém senta e explica a elas o
            que está acontecendo. Esse alguém passa a ser você.
          </p>
          <p>
            A advocacia que se faz aqui é digital, e isso não quer dizer
            distante: quer dizer que o cliente acompanha o próprio caso,
            recebe resposta no mesmo dia e sabe por onde anda o dinheiro dele.
            Pouca gente no país trabalha assim. Você está entrando num
            escritório que está construindo esse jeito de advogar, e o que
            você fizer aqui fica: nas pessoas que você atender e no escritório
            que vai existir depois de nós.
          </p>
        </div>

        <div className="mt-7 rounded-xl2 border border-white/10 bg-navy p-6">
          <p className="text-caption font-semibold uppercase tracking-wider text-slate">
            Sua função
          </p>
          <p className="mt-1 font-display text-subtitle font-bold text-white">
            {convite.nivel_nome}
          </p>
          <p className="mt-1 text-small text-white/65">{convite.resumo}</p>

          {(convite.pode || []).length > 0 && (
            <>
              <p className="mt-5 text-caption font-semibold uppercase tracking-wider text-slate">
                O que você vai poder fazer
              </p>
              <ul className="mt-2 space-y-1.5">
                {convite.pode.map((p: string) => (
                  <li key={p} className="flex gap-2.5 text-small text-white/80">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-electric" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" clipRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 10-1.4 1.4l2 2a1 1 0 001.4 0l4-4z" />
                    </svg>
                    {p}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <button onClick={() => setEtapa("senha")}
          className="mt-7 w-full rounded-lg bg-electric px-7 py-4 text-subtitle font-bold text-white shadow-card transition hover:bg-indigo hover:shadow-glow">
          Criar meu acesso
        </button>
        <p className="mt-3 text-small text-slate">
          Leva menos de um minuto. Você escolhe a sua senha na próxima tela.
        </p>
      </div>
    </Moldura>
  );
}
