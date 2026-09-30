"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

/* A TELA DE CRIAR A SENHA NOVA, E SÓ ISSO.
 *
 * Antes a recuperação caía na tela de entrada, que tinha de adivinhar
 * pelo endereço se aquilo era uma volta do e-mail ou alguém querendo
 * logar. Adivinhação em tela de senha é o tipo de coisa que funciona
 * nos testes e falha no cliente, porque o link chega de quatro
 * formatos diferentes conforme a versão do fluxo e o cliente de
 * e-mail que o abriu.
 *
 * Agora existe um endereço só para isso, e ele trata os quatro:
 *
 *   #access_token=...&type=recovery   o formato antigo, na âncora
 *   ?code=...                          o formato novo, trocado por sessão
 *   ?token_hash=...&type=recovery      o formato à prova de varredura
 *   #error=...&error_code=otp_expired  o link gasto ou vencido
 *
 * O último importa mais do que parece. Antivírus corporativo e alguns
 * servidores de e-mail ABREM os links da mensagem antes de o
 * destinatário clicar, para conferir se são seguros. O link de
 * recuperação vale uma vez só: quando a pessoa clica, ele já foi
 * gasto pelo robô, e ela recebe uma tela em branco sem entender por
 * quê. Aqui ela recebe a explicação e o botão de pedir outro.
 */
export default function NovaSenha() {
  const [estado, setEstado] = useState<"conferindo" | "pronto" | "expirado">("conferindo");
  const [senha, setSenha] = useState("");
  const [senha2, setSenha2] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [email, setEmail] = useState("");
  const [reenviado, setReenviado] = useState(false);

  useEffect(() => {
    (async () => {
      const busca = new URLSearchParams(window.location.search);
      const ancora = new URLSearchParams(
        (window.location.hash || "").replace(/^#/, ""));

      // 1. O link já vencido, ou aberto antes pelo antivírus do e-mail.
      if (ancora.get("error") || busca.get("error")) {
        setEstado("expirado");
        return;
      }

      // 2. O formato à prova de varredura: a troca acontece aqui, no
      //    navegador de quem clicou, e não no servidor de e-mail.
      const token_hash = busca.get("token_hash") || ancora.get("token_hash");
      if (token_hash) {
        const { error } = await supabase.auth.verifyOtp({
          type: "recovery", token_hash,
        });
        setEstado(error ? "expirado" : "pronto");
        return;
      }

      // 3. O formato novo, com código na própria URL. A biblioteca
      //    troca por sessão sozinha quando a página carrega; aqui só
      //    conferimos se ela conseguiu.
      // 4. E o formato antigo, com o token na âncora, que a
      //    biblioteca também consome sozinha.
      const { data } = await supabase.auth.getSession();
      if (data.session) { setEstado("pronto"); return; }

      // Nada de útil no endereço. Pode ser alguém que abriu a página
      // direto, e nesse caso o caminho é pedir um link novo.
      setEstado("expirado");
    })();
  }, []);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    if (senha.length < 6) {
      setMsg("A senha precisa de pelo menos 6 caracteres.");
      return;
    }
    if (senha !== senha2) {
      setMsg("As duas senhas não são iguais. Confira e tente de novo.");
      return;
    }
    setSalvando(true);
    try {
      const { error } = await supabase.auth.updateUser({ password: senha });
      if (error) throw error;

      /* Sai da sessão de recuperação de propósito, e manda entrar.
         Entrar com a senha nova é a única prova de que ela ficou
         gravada do jeito que a pessoa digitou, e é melhor descobrir
         isso agora do que amanhã, trancado de novo. */
      await supabase.auth.signOut();
      window.location.replace("/entrar?senha=nova");
    } catch (err: any) {
      setMsg(String(err?.message || "").includes("expired")
        ? "Este link expirou. Peça um novo abaixo."
        : (err?.message ?? "Não foi possível alterar a senha agora."));
      setSalvando(false);
    }
  }

  async function pedirOutro(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/nova-senha`,
    });
    setReenviado(true);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy px-4">
      <div className="w-full max-w-md rounded-2xl border border-black/5 bg-white p-8 shadow-2xl">
        <Link href="/" className="mb-6 block text-center text-sm font-medium text-gold">
          ← FC Advocacia e Recuperação Patrimonial
        </Link>

        {estado === "conferindo" && (
          <p className="py-8 text-center text-sm text-charcoal/55">
            Conferindo o seu link…
          </p>
        )}

        {estado === "pronto" && (
          <>
            <h1 className="mb-1 text-center font-display text-2xl font-bold text-navy">
              Criar a sua nova senha
            </h1>
            <p className="mb-6 text-center text-sm leading-relaxed text-charcoal/55">
              Escolha a senha que você vai usar a partir de agora. Digite duas
              vezes para não correr o risco de errar.
            </p>
            <form onSubmit={salvar} className="space-y-4">
              <input
                type="password" autoFocus minLength={6}
                className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
                placeholder="Nova senha, pelo menos 6 caracteres" value={senha}
                onChange={(e) => setSenha(e.target.value)} required
              />
              <input
                type="password" minLength={6}
                className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
                placeholder="Repita a nova senha" value={senha2}
                onChange={(e) => setSenha2(e.target.value)} required
              />
              <button
                type="submit" disabled={salvando || !senha || !senha2}
                className="w-full rounded-lg bg-gold py-3 text-sm font-semibold text-navy transition hover:bg-[#b89971] disabled:opacity-60"
              >
                {salvando ? "Salvando…" : "Salvar a nova senha"}
              </button>
            </form>
          </>
        )}

        {estado === "expirado" && (
          <>
            <h1 className="mb-1 text-center font-display text-2xl font-bold text-navy">
              Este link não vale mais
            </h1>
            <p className="mb-6 text-center text-sm leading-relaxed text-charcoal/55">
              O link de recuperação vale uma vez só e por pouco tempo. Também
              acontece de o próprio serviço de e-mail abrir o link antes de
              você, para conferir se é seguro, e com isso gastá-lo. Informe o
              seu e-mail que enviamos outro agora.
            </p>
            {reenviado ? (
              <p className="rounded-lg bg-gold/10 px-4 py-3 text-center text-sm leading-relaxed text-navy">
                Enviado. Abra o seu e-mail e clique no link mais recente, que é
                o único que vale.
              </p>
            ) : (
              <form onSubmit={pedirOutro} className="space-y-4">
                <input
                  type="email" autoFocus
                  className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
                  placeholder="E-mail cadastrado" value={email}
                  onChange={(e) => setEmail(e.target.value)} required
                />
                <button
                  type="submit" disabled={!email}
                  className="w-full rounded-lg bg-gold py-3 text-sm font-semibold text-navy transition hover:bg-[#b89971] disabled:opacity-60"
                >
                  Enviar um link novo
                </button>
              </form>
            )}
            <Link href="/entrar"
              className="mt-6 block text-center text-sm text-charcoal/50 underline underline-offset-4 hover:text-charcoal">
              voltar para a entrada
            </Link>
          </>
        )}

        {msg && (
          <p className="mt-4 text-center text-sm leading-relaxed text-gold">{msg}</p>
        )}
      </div>
    </main>
  );
}
