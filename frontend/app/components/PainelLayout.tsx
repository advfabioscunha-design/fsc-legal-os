"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* O menu segue o caminho do caso, na ordem em que ele acontece — e são
   quatro fases, cada uma na sua tela:

     1. CONTRATOS      quem chegou, proposta, assinatura, pagamento
     2. TRIAGEM        documentos, análise, peça, revisão, protocolo
     3. JUDICIALIZADO  protocolado, tramitação, trânsito em julgado
     4. EXECUÇÃO       cumprimento, alvará, prestação de contas

   Depois delas vêm as ferramentas transversais: intimações e prazos,
   agenda, administração. "Início" abre a visão geral. */
const MENU = [
  { href: "/inicio", label: "Início", icone: "🏠" },
  { href: "/contratos", label: "Contratos", icone: "🤝" },
  { href: "/crm", label: "Triagem", icone: "🗂️" },
  { href: "/judicial", label: "Judicializado", icone: "⚖️" },
  { href: "/recebimento", label: "Execução", icone: "💰" },
  { href: "/intimacoes", label: "Intimações e prazos", icone: "🔔" },
  { href: "/processos", label: "Todos os processos", icone: "📁" },
  { href: "/agenda", label: "Agenda", icone: "📅" },
  { href: "/admin", label: "Administração", icone: "📊" },
  { href: "/assistente", label: "Assistente", icone: "💡" },
];

/* Onde mora cada caso, agora que são quatro telas. A busca global
   precisa disso: antes ela mandava todo resultado para a Produção, e um
   processo já em juízo não aparecia lá — quem buscava concluía que o
   caso havia sumido. */
const TELA_POR_ESTADO: Record<string, string> = {
  LEAD: "/contratos", QUALIFICACAO: "/contratos", PROPOSTA: "/contratos",
  CONTRATO: "/contratos", PAGAMENTO: "/contratos", LEAD_FRIO: "/contratos",
  JUDICIAL: "/judicial", PROTOCOLADO: "/judicial", TRANSITO_JULGADO: "/judicial",
  RECEBIMENTO: "/recebimento", CONCLUIDO: "/recebimento",
};
const telaDoCaso = (estado?: string | null) =>
  (estado && TELA_POR_ESTADO[estado]) || "/crm";

export default function PainelLayout({ children, titulo }: { children: React.ReactNode; titulo?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const [autorizado, setAutorizado] = useState(false);
  const [busca, setBusca] = useState("");
  const [resultados, setResultados] = useState<any[]>([]);
  const [buscando, setBuscando] = useState(false);

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.replace("/entrar?next=/crm"); return; }
      const { data: perfil } = await supabase
        .from("perfis").select("papel").eq("id", sess.session.user.id).maybeSingle();
      if (!["OPERADOR", "ADMIN"].includes(perfil?.papel)) { router.replace("/cliente"); return; }
      setAutorizado(true);
    })();
  }, [router]);

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    if (!busca.trim()) { setResultados([]); return; }
    setBuscando(true);
    try {
      const r = await fetch(`${API}/api/v1/buscar?q=${encodeURIComponent(busca)}`);
      const d = await r.json();
      setResultados(d.casos || []);
    } catch { setResultados([]); }
    finally { setBuscando(false); }
  }

  if (!autorizado) {
    return <div className="flex min-h-screen items-center justify-center text-white/60" style={{ background: "#0A1628", fontFamily: "Inter, sans-serif" }}>Verificando acesso...</div>;
  }

  return (
    <div className="flex min-h-screen" style={{ background: "#0A1628", fontFamily: "Inter, sans-serif" }}>
      {/* Menu lateral fixo */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-white/5 bg-[#0B1F3B] md:flex">
        <Link href="/inicio" className="flex flex-col px-5 py-5 leading-none">
          <span className="text-lg font-bold text-white">FC <span className="text-[#C9A24D]">Legal OS</span></span>
          <span className="text-[10px] uppercase tracking-widest text-[#8899AA]">Gestão Interna</span>
        </Link>
        <nav className="flex-1 px-3">
          {MENU.map((m) => {
            const ativo = pathname === m.href || pathname?.startsWith(m.href + "/");
            return (
              <Link key={m.href} href={m.href}
                className={`mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${ativo ? "bg-[#C9A24D] font-bold text-[#0A1628]" : "text-[#8899AA] hover:bg-white/5 hover:text-white"}`}>
                <span>{m.icone}</span>{m.label}
              </Link>
            );
          })}
        </nav>
        <button onClick={async () => { await supabase.auth.signOut(); router.push("/entrar"); }}
          className="m-3 rounded-lg border border-white/10 px-3 py-2 text-sm text-[#8899AA] hover:text-white">Sair</button>
      </aside>

      {/* Conteúdo */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Bar com busca global */}
        <header className="sticky top-0 z-30 border-b border-white/5 bg-[#0A1628]/95 px-5 py-3 backdrop-blur">
          <div className="flex items-center gap-4">
            <h1 className="hidden text-sm font-semibold text-white sm:block">{titulo}</h1>
            <form onSubmit={buscar} className="relative ml-auto w-full max-w-md">
              <input value={busca} onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por Nome, CPF/CNPJ ou Nº do processo…"
                className="w-full rounded-full border border-white/15 bg-[#0B1F3B] px-4 py-2 pr-10 text-sm text-white outline-none focus:border-[#C9A24D]" />
              <button type="submit" className="absolute right-3 top-1.5 text-[#8899AA] hover:text-white">🔍</button>
              {(resultados.length > 0 || buscando) && (
                <div className="absolute left-0 right-0 z-40 mt-2 max-h-80 overflow-y-auto rounded-xl border border-white/10 bg-[#0B1F3B] p-2 shadow-2xl">
                  {buscando ? <p className="px-2 py-1 text-xs text-[#8899AA]">Buscando…</p> :
                    resultados.map((c) => (
                      <Link key={c.id} href={telaDoCaso(c.estado)} onClick={() => setResultados([])}
                        className="block rounded-lg px-3 py-2 text-sm text-white hover:bg-white/5">
                        <span className="font-semibold">{c.clientes?.nome ?? "—"}</span>
                        <span className="ml-2 text-xs text-[#8899AA]">{c.grupo ?? ""} {c.numero_processo ? `· ${c.numero_processo}` : ""} · {c.estado}</span>
                      </Link>
                    ))}
                  {!buscando && resultados.length === 0 && <p className="px-2 py-1 text-xs text-[#8899AA]">Nada encontrado.</p>}
                </div>
              )}
            </form>
          </div>
        </header>

        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
