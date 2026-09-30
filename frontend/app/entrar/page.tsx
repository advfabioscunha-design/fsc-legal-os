"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

export default function Entrar() {
  const router = useRouter();
  const [modo, setModo] = useState<"login" | "cadastro" | "recuperar">("login");

  /* Quem chega pelo "Analisar meu caso" ainda não tem conta, e abrir a
     tela em "Entrar" faz essa pessoa procurar o link de cadastro antes
     de conseguir começar. O `novo=1` na URL diz de onde ela veio. */
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("novo") === "1") setModo("cadastro");
    // Quem chega pelo "esqueci a senha" da porta da equipe já cai na
    // tela certa, sem ter de procurar o link de novo aqui dentro.
    if (p.get("recuperar") === "1") setModo("recuperar");
  }, []);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  /* PARA ONDE VAI QUEM ACABOU DE ENTRAR
   *
   * O operador caía direto na Triagem. Faz sentido para quem usa o
   * sistema todo dia e só quer ver a esteira, mas é a tela errada para
   * começar o dia: o Início mostra prazo, tarefa e o que está parado,
   * e é de lá que se decide o que fazer.
   *
   * Qualquer tela interna pedida na URL é respeitada, desde que quem
   * entrou seja da equipe. Cliente que tropeça num link interno vai
   * para a área dele, sem mensagem de erro: não é engano dele. */
  async function redirecionarPorPapel() {
    const { data } = await supabase.auth.getUser();
    if (!data.user) return;
    const { data: perfil } = await supabase
      .from("perfis").select("papel").eq("id", data.user.id).maybeSingle();
    const daEquipe = ["OPERADOR", "ADMIN"].includes(perfil?.papel);
    const next = new URLSearchParams(window.location.search).get("next") || "";

    if (next === "/cliente") { router.push("/cliente"); return; }
    if (next.startsWith("/")) {
      router.push(daEquipe ? next : "/cliente");
      return;
    }
    router.push(daEquipe ? "/inicio" : "/cliente");
  }

  /* RECUPERAR A SENHA, PEDINDO SÓ O E-MAIL
   *
   * A tela de entrada não tinha por onde. A porta da equipe até
   * mostrava "esqueci a senha", mas o link trazia para cá, onde a
   * opção não existia: quem esquecia a senha dava a volta e voltava
   * ao mesmo lugar.
   *
   * O aviso é igual exista ou não a conta. Dizer "este e-mail não
   * está cadastrado" entrega a quem está tentando descobrir quem é
   * cliente do escritório exatamente a informação que ele quer.
   */
  async function recuperar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setCarregando(true);
    try {
      // O limite vive no servidor: sem ele, o "esqueci a senha" vira
      // máquina de encher a caixa de entrada de outra pessoa.
      try {
        const lim = await fetch(`${API}/api/v1/acesso/limite`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        if (lim.status === 429) {
          const d = await lim.json().catch(() => ({} as any));
          setMsg(d.detail || "Muitas tentativas. Aguarde uma hora e tente de novo.");
          return;
        }
      } catch { /* contador fora do ar não pode travar quem precisa */ }

      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/entrar`,
      });
      if (error) console.warn(error.message);
      setMsg("Se houver conta com este e-mail, enviamos agora o link para criar "
             + "uma senha nova. Abra o seu e-mail, defina a senha e volte aqui "
             + "para entrar. O link vale por uma hora.");
    } finally {
      setCarregando(false);
    }
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setCarregando(true);
    try {
      if (modo === "cadastro") {
        const { error } = await supabase.auth.signUp({
          email, password: senha, options: { data: { nome } },
        });
        if (error) throw error;
        // se o projeto exigir confirmação por e-mail, não há sessão ainda
        const { data: sess } = await supabase.auth.getSession();
        if (!sess.session) {
          setMsg("Cadastro criado! Confirme pelo link enviado ao seu e-mail e depois faça login.");
          setModo("login");
          return;
        }
        await redirecionarPorPapel();
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email, password: senha,
        });
        if (error) throw error;
        await redirecionarPorPapel();
      }
    } catch (err: any) {
      setMsg(err?.message ?? "Não foi possível concluir. Tente novamente.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy px-4">
      <div className="w-full max-w-md rounded-2xl border border-black/5 bg-white p-8 shadow-2xl">
        <Link href="/" className="mb-6 block text-center text-sm font-medium text-gold">
          ← FC Advocacia e Recuperação Patrimonial
        </Link>
        <h1 className="mb-1 text-center font-display text-2xl font-bold text-navy">
          {modo === "login" ? "Entrar"
            : modo === "cadastro" ? "Criar seu acesso"
            : "Recuperar a senha"}
        </h1>
        <p className="mb-6 text-center text-sm leading-relaxed text-charcoal/55">
          {modo === "login"
            ? "Entre para acompanhar o seu caso e retomar a conversa de onde parou."
            : modo === "cadastro"
            ? "Com a senha criada, tudo o que você conversar e solicitar fica "
              + "guardado na sua área. Se sair e voltar depois, continua do "
              + "mesmo ponto."
            : "Informe o e-mail cadastrado. Enviamos para ele o link para você "
              + "criar uma senha nova."}
        </p>

        {/* RECUPERAR PEDE UMA COISA SÓ

            Pedir e-mail e mais alguma confirmação aqui não protege
            ninguém: quem recebe o link é o dono da caixa de entrada,
            e é isso que faz a recuperação segura. Campo a mais só
            trava quem já está sem acesso. */}
        {modo === "recuperar" ? (
          <form onSubmit={recuperar} className="space-y-4">
            <input
              type="email" autoFocus
              className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
              placeholder="E-mail cadastrado" value={email}
              onChange={(e) => setEmail(e.target.value)} required
            />
            <button
              type="submit" disabled={carregando || !email}
              className="w-full rounded-lg bg-gold py-3 text-sm font-semibold text-navy transition hover:bg-[#b89971] disabled:opacity-60"
            >
              {carregando ? "Enviando…" : "Enviar o link por e-mail"}
            </button>
          </form>
        ) : (
        <form onSubmit={enviar} className="space-y-4">
          {modo === "cadastro" && (
            <input
              className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
              placeholder="Nome completo" value={nome}
              onChange={(e) => setNome(e.target.value)} required
            />
          )}
          <input
            type="email" className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
            placeholder="E-mail" value={email}
            onChange={(e) => setEmail(e.target.value)} required
          />
          <input
            type="password" className="w-full rounded-lg border border-black/10 bg-white px-4 py-3 text-sm text-charcoal outline-none focus:border-gold"
            placeholder={modo === "cadastro" ? "Crie uma senha" : "Senha"} value={senha}
            onChange={(e) => setSenha(e.target.value)} required minLength={6}
          />
          <button
            type="submit" disabled={carregando}
            className="w-full rounded-lg bg-gold py-3 text-sm font-semibold text-navy transition hover:bg-[#b89971] disabled:opacity-60"
          >
            {carregando ? "Aguarde..." : modo === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>
        )}

        {msg && (
          <p className="mt-4 text-center text-sm leading-relaxed text-gold">{msg}</p>
        )}

        {modo === "login" && (
          <button
            onClick={() => { setMsg(null); setModo("recuperar"); }}
            className="mt-4 w-full text-center text-sm text-charcoal/50 underline underline-offset-4 hover:text-charcoal"
          >
            Esqueci a minha senha
          </button>
        )}

        <button
          onClick={() => {
            setMsg(null);
            setModo(modo === "login" ? "cadastro" : "login");
          }}
          className="mt-4 w-full text-center text-sm text-charcoal/50 hover:text-charcoal"
        >
          {modo === "login"
            ? "Não tem conta? Cadastre-se"
            : modo === "cadastro"
            ? "Já tem conta? Entrar"
            : "Voltar para a entrada"}
        </button>
      </div>
    </main>
  );
}
