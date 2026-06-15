"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

// Fases visíveis ao cliente (do início ao protocolo)
const FASES = [
  { id: "LEAD", label: "Contato inicial" },
  { id: "QUALIFICACAO", label: "Análise de viabilidade" },
  { id: "PROPOSTA", label: "Proposta" },
  { id: "CONTRATO", label: "Contrato" },
  { id: "PAGAMENTO", label: "Pagamento" },
  { id: "COLETA_DOCS", label: "Coleta de documentos" },
  { id: "COLETA_PROVAS", label: "Coleta de provas" },
  { id: "ANALISE", label: "Análise técnica" },
  { id: "PETICAO", label: "Elaboração da petição" },
  { id: "REVISAO", label: "Revisão do advogado" },
  { id: "PROTOCOLADO", label: "Protocolado" },
];

type Caso = { id: string; estado: string; grupo: string | null; numero_processo?: string | null };

export default function AreaCliente() {
  const router = useRouter();
  const [nome, setNome] = useState("");
  const [casos, setCasos] = useState<Caso[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.push("/entrar"); return; }
      const token = sess.session.access_token;
      setNome(sess.session.user.user_metadata?.nome || sess.session.user.email || "");
      try {
        const r = await fetch(`${API}/api/v1/cliente/meus-casos`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setCasos(r.ok ? await r.json() : []);
      } catch { setCasos([]); }
      finally { setCarregando(false); }
    })();
  }, [router]);

  async function sair() {
    await supabase.auth.signOut();
    router.push("/entrar");
  }

  function idxFase(estado: string) {
    const i = FASES.findIndex((f) => f.id === estado);
    return i < 0 ? 0 : i;
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8 flex items-center justify-between">
        <Link href="/" className="text-sm text-[#C9A84C]">← FSC Advocacia</Link>
        <button onClick={sair} className="text-sm text-white/60 hover:text-white">Sair</button>
      </header>

      <h1 className="mb-1 text-2xl font-bold" style={{ fontFamily: "Plus Jakarta Sans, sans-serif" }}>
        Olá, {nome}
      </h1>
      <p className="mb-8 text-sm text-white/60">Acompanhe aqui o andamento da sua causa.</p>

      <Link
        href="/portal"
        className="mb-10 inline-block rounded-lg bg-[#C9A84C] px-5 py-3 text-sm font-semibold text-[#0A1628] hover:bg-[#d8b95e]"
      >
        + Iniciar nova contratação
      </Link>

      {carregando ? (
        <p className="text-white/50">Carregando seus processos...</p>
      ) : casos.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-sm text-white/70">
          Você ainda não tem um processo em andamento. Clique em
          <b> “Iniciar nova contratação”</b> para começar — ou fale com a gente no WhatsApp.
        </div>
      ) : (
        <div className="space-y-6">
          {casos.map((c) => {
            const atual = idxFase(c.estado);
            return (
              <div key={c.id} className="rounded-xl border border-white/10 bg-white/5 p-6">
                <div className="mb-4 flex items-center justify-between">
                  <span className="font-semibold">{c.grupo ?? "Sua causa"}</span>
                  {c.numero_processo && (
                    <span className="text-xs text-[#C9A84C]">Processo {c.numero_processo}</span>
                  )}
                </div>
                <ol className="space-y-2">
                  {FASES.map((f, i) => (
                    <li key={f.id} className="flex items-center gap-3 text-sm">
                      <span
                        className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                          i < atual ? "bg-[#1DB954] text-white"
                          : i === atual ? "bg-[#C9A84C] text-[#0A1628]"
                          : "bg-white/10 text-white/40"
                        }`}
                      >
                        {i < atual ? "✓" : i + 1}
                      </span>
                      <span className={i <= atual ? "text-white" : "text-white/40"}>{f.label}</span>
                    </li>
                  ))}
                </ol>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
