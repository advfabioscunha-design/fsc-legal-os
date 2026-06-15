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

// Validação de CPF (dígitos verificadores) — gratuita, no próprio navegador
function cpfValido(valor: string): boolean {
  const c = (valor || "").replace(/\D/g, "");
  if (c.length !== 11 || /^(\d)\1{10}$/.test(c)) return false;
  for (const i of [9, 10]) {
    let soma = 0;
    for (let n = 0; n < i; n++) soma += parseInt(c[n]) * (i + 1 - n);
    let dig = (soma * 10) % 11;
    if (dig === 10) dig = 0;
    if (dig !== parseInt(c[i])) return false;
  }
  return true;
}

export default function AreaCliente() {
  const router = useRouter();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [casos, setCasos] = useState<Caso[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [relato, setRelato] = useState("");
  const [cpf, setCpf] = useState("");
  const [erroCpf, setErroCpf] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.push("/entrar"); return; }
      const token = sess.session.access_token;
      setNome(sess.session.user.user_metadata?.nome || sess.session.user.email || "");
      setEmail(sess.session.user.email || "");
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

  async function enviarTriagem(e: React.FormEvent) {
    e.preventDefault();
    if (!relato.trim()) return;
    if (!cpfValido(cpf)) {
      setErroCpf("CPF inválido — confira os números.");
      return;
    }
    setErroCpf(null);
    setEnviando(true);
    try {
      await fetch(`${API}/api/v1/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome, contato: email, relato, cpf, canal: "PORTAL" }),
      });
      setEnviado(true);
      setRelato("");
    } catch {
      /* mantém na tela; o cliente pode tentar de novo */
    } finally {
      setEnviando(false);
    }
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

      {carregando ? (
        <p className="text-white/50">Carregando seus processos...</p>
      ) : casos.length === 0 ? (
        enviado ? (
          <div className="rounded-xl border border-[#1DB954]/40 bg-[#1DB954]/10 p-6 text-sm text-white/80">
            ✅ <b>Recebemos o seu caso!</b> Nossa equipe (e o assistente digital) vai analisar a
            viabilidade e dar o próximo passo. Em breve sua causa aparecerá aqui com as fases do
            andamento. Você também pode falar com a gente pelo WhatsApp a qualquer momento.
          </div>
        ) : (
          <form onSubmit={enviarTriagem} className="rounded-xl border border-white/10 bg-white/5 p-6">
            <h2 className="mb-1 text-lg font-semibold">Conte o seu caso</h2>
            <p className="mb-4 text-sm text-white/60">
              Descreva com suas palavras o que aconteceu. A partir daqui fazemos a triagem,
              a análise de viabilidade e, se você contratar, você acompanha cada fase aqui mesmo.
            </p>
            <input
              value={cpf}
              onChange={(e) => { setCpf(e.target.value); setErroCpf(null); }}
              inputMode="numeric" required
              placeholder="Seu CPF"
              className="mb-1 w-full rounded-lg border border-white/15 bg-[#0A1628] px-4 py-3 text-sm outline-none focus:border-[#C9A84C]"
            />
            {erroCpf && <p className="mb-3 text-xs text-[#C0392B]">{erroCpf}</p>}
            {!erroCpf && <div className="mb-3" />}
            <textarea
              value={relato}
              onChange={(e) => setRelato(e.target.value)}
              rows={6} required
              placeholder="Ex.: Recebi cobranças que não reconheço no meu cartão / Quero rever um contrato de financiamento / Fui cobrado indevidamente..."
              className="w-full rounded-lg border border-white/15 bg-[#0A1628] px-4 py-3 text-sm outline-none focus:border-[#C9A84C]"
            />
            <button type="submit" disabled={enviando}
              className="mt-4 rounded-lg bg-[#C9A84C] px-5 py-3 text-sm font-semibold text-[#0A1628] hover:bg-[#d8b95e] disabled:opacity-60">
              {enviando ? "Enviando..." : "Enviar para análise"}
            </button>
          </form>
        )
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
