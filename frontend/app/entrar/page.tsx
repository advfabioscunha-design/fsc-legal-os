"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

export default function Entrar() {
  const router = useRouter();
  const [modo, setModo] = useState<"login" | "cadastro">("login");

  /* Quem chega pelo "Analisar meu caso" ainda não tem conta, e abrir a
     tela em "Entrar" faz essa pessoa procurar o link de cadastro antes
     de conseguir começar. O `novo=1` na URL diz de onde ela veio. */
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("novo") === "1") setModo("cadastro");
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
          {modo === "login" ? "Entrar" : "Criar seu acesso"}
        </h1>
        <p className="mb-6 text-center text-sm leading-relaxed text-charcoal/55">
          {modo === "login"
            ? "Entre para acompanhar o seu caso e retomar a conversa de onde parou."
            : "Com a senha criada, tudo o que você conversar e solicitar fica "
              + "guardado na sua área. Se sair e voltar depois, continua do "
              + "mesmo ponto."}
        </p>

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
            onChange={(e) => setSenha(e.target.value)} required minLength={4}
          />
          <button
            type="submit" disabled={carregando}
            className="w-full rounded-lg bg-gold py-3 text-sm font-semibold text-navy transition hover:bg-[#b89971] disabled:opacity-60"
          >
            {carregando ? "Aguarde..." : modo === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        {msg && <p className="mt-4 text-center text-sm text-gold">{msg}</p>}

        <button
          onClick={() => { setMsg(null); setModo(modo === "login" ? "cadastro" : "login"); }}
          className="mt-6 w-full text-center text-sm text-charcoal/50 hover:text-charcoal"
        >
          {modo === "login"
            ? "Não tem conta? Cadastre-se"
            : "Já tem conta? Entrar"}
        </button>
      </div>
    </main>
  );
}
