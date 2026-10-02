"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";
import BotaoGoogle from "../components/BotaoGoogle";

/* ÁREA DA EQUIPE
 *
 * A porta de quem trabalha no escritório. Ficava só no rodapé, em uma
 * linha, e quem começava na equipe precisava perguntar a alguém por
 * onde se entra. Porta de serviço não fica na fachada, mas também não
 * pode ser um segredo da casa.
 *
 * A página faz três coisas, nesta ordem, que é a ordem em que as
 * pessoas chegam:
 *
 *   1. quem já trabalha aqui entra
 *   2. quem recebeu convite conclui o cadastro
 *   3. quem não tem convite entende por que não tem
 *
 * O terceiro item existe porque a alternativa é pior: sem explicação,
 * a pessoa tenta criar uma conta, não consegue, e escreve para o
 * escritório perguntando o que fez de errado.
 */
export default function AcessoEquipe() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [link, setLink] = useState("");

  // Quem já está logado como equipe não precisa ver tela de login.
  useEffect(() => {
    (async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) return;
      const { data: perfil } = await supabase
        .from("perfis").select("papel").eq("id", data.session.user.id).maybeSingle();
      if (["OPERADOR", "ADMIN"].includes(perfil?.papel)) router.replace("/inicio");
    })();
  }, [router]);

  async function entrar() {
    setOcupado(true); setErro("");
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(), password: senha,
      });
      if (error) { setErro("E-mail ou senha não conferem."); return; }

      const { data } = await supabase.auth.getUser();
      const { data: perfil } = await supabase
        .from("perfis").select("papel,nome").eq("id", data.user?.id).maybeSingle();

      if (!["OPERADOR", "ADMIN"].includes(perfil?.papel)) {
        // Cliente que entrou por aqui não leva erro na cara: vai para
        // a área dele, que é onde ele queria chegar de qualquer forma.
        router.push("/cliente");
        return;
      }
      router.push("/inicio");
    } catch { setErro("Não foi possível entrar agora."); }
    finally { setOcupado(false); }
  }

  /* O convite chega por e-mail com o link inteiro. Quem copia só o
     código, ou copia o link com espaço no meio, também precisa
     conseguir entrar: por isso aceita os dois e extrai o que interessa. */
  function abrirConvite() {
    const bruto = link.trim();
    if (!bruto) return;
    const token = bruto.includes("/convite/")
      ? bruto.split("/convite/")[1].split(/[?#\s]/)[0]
      : bruto.split(/[?#\s]/)[0];
    if (!token) { setAviso("Cole o link que chegou no seu e-mail."); return; }
    router.push(`/convite/${token}`);
  }

  const campo = "mt-1 w-full rounded-lg border border-white/12 bg-navy px-3.5 py-2.5 text-small text-white placeholder:text-slate/60 outline-none transition focus:border-electric";

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy px-5 py-12 font-sans text-white">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-8 flex items-center gap-2.5">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-electric to-indigo font-display text-body font-bold text-white">
            FC
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-body font-bold text-white">Advocacia</span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate">
              Área da equipe
            </span>
          </span>
        </Link>

        <div className="rounded-xl2 border border-white/10 bg-petrol p-7">
          <h1 className="font-display text-title font-bold">Entrar para trabalhar</h1>
          <p className="mt-1.5 text-small text-slate">
            Acesso à operação do escritório: triagem, prazos, agenda, contratos
            e o acompanhamento dos casos.
          </p>

          {/* ENTRAR COM A CONTA GOOGLE DO TRABALHO

              Quase todo escritório usa Gmail, e quem trabalha aqui já
              está logado nele no navegador: um clique, sem mais uma
              senha para guardar.

              O que o botão NÃO faz é dar acesso. Ele prova quem a
              pessoa é; o que ela pode abrir continua vindo do papel
              gravado na plataforma. Quem entrar com um Google que não
              está na equipe cai na área do cliente — não em erro, e
              nunca na operação. */}
          <div className="mt-6">
            <BotaoGoogle destino="/inicio" tom="escuro"
              rotulo="Entrar com o Google do escritório" />
            <p className="mt-2 text-[11px] leading-relaxed text-slate/70">
              Use a conta Google do seu e-mail de trabalho, o mesmo que recebeu
              o convite. Conta pessoal entra como cliente.
            </p>
            <div className="mt-5 flex items-center gap-3">
              <span className="h-px flex-1 bg-white/10" />
              <span className="text-[10px] uppercase tracking-wider text-slate/60">
                ou com e-mail e senha
              </span>
              <span className="h-px flex-1 bg-white/10" />
            </div>
          </div>

          <div className="mt-5 space-y-4">
            <label className="block">
              <span className="text-caption text-slate">E-mail de trabalho</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)}
                type="email" autoComplete="username" className={campo} />
            </label>
            <label className="block">
              <span className="text-caption text-slate">Senha</span>
              <input value={senha} onChange={(e) => setSenha(e.target.value)}
                type="password" autoComplete="current-password"
                onKeyDown={(e) => e.key === "Enter" && entrar()}
                className={campo} />
            </label>
          </div>

          {erro && (
            <p className="mt-4 rounded-lg border border-crimson/40 bg-crimson/10 px-4 py-2.5 text-small">
              {erro}
            </p>
          )}

          <button onClick={entrar} disabled={ocupado || !email || !senha}
            className="mt-6 w-full rounded-lg bg-electric px-6 py-3.5 text-subtitle font-bold text-white transition hover:bg-indigo disabled:opacity-40">
            {ocupado ? "Entrando…" : "Entrar"}
          </button>

          {/* Levava para a tela de entrada, onde a opção não existia:
              quem esquecia a senha dava a volta e voltava ao mesmo
              lugar. Agora abre direto no modo de recuperação. */}
          <Link href="/entrar?recuperar=1&next=/inicio"
            className="mt-4 block text-center text-small text-slate underline underline-offset-4 transition hover:text-white">
            esqueci a senha
          </Link>
        </div>

        {/* QUEM FOI CONVIDADO */}
        <div className="mt-5 rounded-xl2 border border-white/10 bg-petrol/60 p-6">
          <h2 className="font-display text-body font-bold">
            Recebeu um convite para entrar na equipe?
          </h2>
          <p className="mt-1.5 text-small text-slate">
            Cole aqui o link que chegou no seu e-mail para criar a sua senha e
            concluir o cadastro. O link vale por sete dias.
          </p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input value={link} onChange={(e) => setLink(e.target.value)}
              placeholder="cole o link do convite"
              onKeyDown={(e) => e.key === "Enter" && abrirConvite()}
              className={`${campo} mt-0 flex-1`} />
            <button onClick={abrirConvite}
              className="shrink-0 rounded-lg border border-white/20 px-5 py-2.5 text-small font-semibold text-white transition hover:border-white/45">
              Continuar
            </button>
          </div>
          {aviso && <p className="mt-2 text-caption text-amber">{aviso}</p>}
        </div>

        {/* QUEM NÃO TEM CONVITE */}
        <p className="mt-5 text-center text-caption leading-relaxed text-slate">
          O cadastro de novos membros é feito por dentro da plataforma, por
          quem já é administrador, e chega por e-mail. Não há como criar acesso
          por conta própria: quem dá acesso a um sistema com dados de cliente
          precisa ser alguém, e ficar registrado.
        </p>

        <p className="mt-6 text-center text-caption text-slate/70">
          É cliente do escritório?{" "}
          <Link href="/entrar?next=/cliente" className="text-slate underline underline-offset-4 hover:text-white">
            Sua área fica aqui
          </Link>
        </p>
      </div>
    </main>
  );
}
