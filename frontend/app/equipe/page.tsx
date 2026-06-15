"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function CadastroEquipe() {
  const router = useRouter();
  const [modo, setModo] = useState<"cadastro" | "login">("cadastro");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [codigo, setCodigo] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function promover(token: string) {
    const r = await fetch(`${API}/api/v1/equipe/registrar`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ codigo }),
    });
    if (!r.ok) throw new Error("Código de acesso inválido.");
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setCarregando(true);
    try {
      if (modo === "cadastro") {
        const { error } = await supabase.auth.signUp({ email, password: senha, options: { data: { nome } } });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password: senha });
        if (error) throw error;
      }
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) {
        setMsg("Confirme seu e-mail e depois entre aqui novamente com o código.");
        setModo("login");
        return;
      }
      await promover(sess.session.access_token);
      router.push("/crm");
    } catch (err: any) {
      setMsg(err?.message ?? "Não foi possível concluir.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-[#C9A84C]/30 bg-white/5 p-8 shadow-xl">
        <Link href="/" className="mb-6 block text-center text-sm text-[#C9A84C]">← FC Advocacia</Link>
        <div className="mb-1 text-center text-xs font-semibold uppercase tracking-wider text-[#C9A84C]">
          Acesso da Equipe
        </div>
        <h1 className="mb-1 text-center text-2xl font-bold" style={{ fontFamily: "Plus Jakarta Sans, sans-serif" }}>
          {modo === "cadastro" ? "Cadastro de operador" : "Entrar como operador"}
        </h1>
        <p className="mb-6 text-center text-sm text-white/60">
          Exclusivo para a equipe do escritório. Requer o código de acesso interno.
        </p>

        <form onSubmit={enviar} className="space-y-4">
          {modo === "cadastro" && (
            <input className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-4 py-3 text-sm outline-none focus:border-[#C9A84C]"
              placeholder="Nome completo" value={nome} onChange={(e) => setNome(e.target.value)} required />
          )}
          <input type="email" className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-4 py-3 text-sm outline-none focus:border-[#C9A84C]"
            placeholder="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-4 py-3 text-sm outline-none focus:border-[#C9A84C]"
            placeholder="Senha" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={6} />
          <input className="w-full rounded-lg border border-[#C9A84C]/40 bg-[#0A1628] px-4 py-3 text-sm outline-none focus:border-[#C9A84C]"
            placeholder="Código de acesso da equipe" value={codigo} onChange={(e) => setCodigo(e.target.value)} required />
          <button type="submit" disabled={carregando}
            className="w-full rounded-lg bg-[#C9A84C] py-3 text-sm font-semibold text-[#0A1628] transition hover:bg-[#d8b95e] disabled:opacity-60">
            {carregando ? "Aguarde..." : modo === "cadastro" ? "Cadastrar operador" : "Entrar"}
          </button>
        </form>

        {msg && <p className="mt-4 text-center text-sm text-[#C9A84C]">{msg}</p>}

        <button onClick={() => { setMsg(null); setModo(modo === "cadastro" ? "login" : "cadastro"); }}
          className="mt-6 w-full text-center text-sm text-white/60 hover:text-white">
          {modo === "cadastro" ? "Já é operador? Entrar" : "Cadastrar novo operador"}
        </button>
      </div>
    </main>
  );
}
