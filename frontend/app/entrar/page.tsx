"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

export default function Entrar() {
  const router = useRouter();
  const [modo, setModo] = useState<"login" | "cadastro">("login");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function redirecionarPorPapel() {
    const { data } = await supabase.auth.getUser();
    if (!data.user) return;
    const { data: perfil } = await supabase
      .from("perfis").select("papel").eq("id", data.user.id).maybeSingle();
    router.push(perfil?.papel === "OPERADOR" ? "/crm" : "/cliente");
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
          ← FC Advocacia
        </Link>
        <h1 className="mb-1 text-center font-serif text-2xl font-bold text-navy">
          {modo === "login" ? "Entrar" : "Criar conta"}
        </h1>
        <p className="mb-6 text-center text-sm text-charcoal/55">
          {modo === "login"
            ? "Acesse para acompanhar seu processo."
            : "Cadastre-se para iniciar e acompanhar sua causa."}
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
            placeholder="Senha" value={senha}
            onChange={(e) => setSenha(e.target.value)} required minLength={6}
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
