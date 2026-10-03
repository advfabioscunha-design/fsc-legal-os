"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* CASCA DA PLATAFORMA INTERNA
 *
 * O que mudou nesta versão, e por quê:
 *
 * 1. Os ícones eram emoji. Emoji muda de desenho a cada sistema
 *    operacional, não aceita cor e, em tela de trabalho, dá ar de
 *    rascunho. Viraram traço, na mesma espessura, e herdam a cor do
 *    item, então acendem junto com ele.
 *
 * 2. O item ativo era um bloco dourado com texto escuro, que puxava
 *    mais atenção do que o conteúdo da tela. Agora é fundo discreto,
 *    texto branco e uma barra fina em azul elétrico à esquerda. Quem
 *    trabalha oito horas aqui precisa de uma marcação que informe, não
 *    que grite.
 *
 * 3. O menu tinha onze itens soltos em lista única. Passou a ter três
 *    blocos com título: o caminho do caso, o controle do dia e o
 *    balcão. Agrupar é o que transforma lista em mapa.
 *
 * 4. As cores estavam escritas à mão em hexadecimal, tela por tela.
 *    Agora vêm do tema, como no resto do sistema, e mudar a paleta
 *    passa a ser uma edição em um arquivo só.
 */

type Item = { href: string; label: string; icone: JSX.Element };

const I = (d: string) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
    strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px] shrink-0"
    aria-hidden="true">
    <path d={d} />
  </svg>
);

const CAMINHO: Item[] = [
  { href: "/inicio", label: "Início", icone: I("M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5") },
  { href: "/crm", label: "Triagem", icone: I("M3 7h6l2 2h10v10H3zM3 7V5h6l2 2") },
  { href: "/judicial", label: "Judicializado", icone: I("M12 3v18M5 7h14M7 7l-3 6h6zM17 7l-3 6h6zM8 21h8") },
  { href: "/recebimento", label: "Execução", icone: I("M12 3v18M16 7.5c0-1.4-1.8-2.5-4-2.5S8 6.1 8 7.5s1.8 2.2 4 2.5 4 1.1 4 2.5-1.8 2.5-4 2.5-4-1.1-4-2.5") },
];

const CONTROLE: Item[] = [
  { href: "/tarefas", label: "Tarefas", icone: I("M4 7l2 2 4-4M4 15l2 2 4-4M13 7h7M13 17h7") },
  { href: "/pendencias", label: "Pendências", icone: I("M12 8v5m0 3h.01M10.3 3.9 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z") },
  { href: "/intimacoes", label: "Intimações e prazos", icone: I("M18 9a6 6 0 1 0-12 0c0 6-2 7-2 7h16s-2-1-2-7M10.5 20a1.8 1.8 0 0 0 3 0") },
  { href: "/processos", label: "Todos os processos", icone: I("M3 7h6l2 2h10v10H3z") },
  { href: "/agenda", label: "Agenda", icone: I("M7 3v3M17 3v3M3.5 9h17M4.5 6h15v14h-15z") },
  { href: "/clientes", label: "Clientes", icone: I("M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M19 8v6M22 11h-6") },
  { href: "/admin/parceiros", label: "Parceiros", icone: I("M17 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M22 12h-6M19 9v6") },
  { href: "/financeiro", label: "Financeiro", icone: I("M12 3v18M16 7.5c0-1.4-1.8-2.5-4-2.5S8 6.1 8 7.5s1.8 2.2 4 2.5 4 1.1 4 2.5-1.8 2.5-4 2.5-4-1.1-4-2.5") },
  { href: "/equipe", label: "Equipe", icone: I("M17 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M22 20v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8") },
  { href: "/admin", label: "Administração", icone: I("M4 20V10M10 20V4M16 20v-7M22 20H2") },
  { href: "/assistente", label: "Assistente", icone: I("M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z") },
];

/* O balcão não é uma fase do caso: é outro serviço. Fica em bloco
   próprio para ninguém confundir "contrato de honorários do caso" com
   "contrato que o cliente encomendou". */
const BALCAO: Item[] = [
  { href: "/contratos", label: "Contratos", icone: I("M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5") },
];

/* Onde mora cada caso, agora que são quatro telas. A busca global
   precisa disso: antes ela mandava todo resultado para a Produção, e um
   processo já em juízo não aparecia lá. Quem buscava concluía que o
   caso havia sumido. */
const TELA_POR_ESTADO: Record<string, string> = {
  LEAD: "/crm", QUALIFICACAO: "/crm", PROPOSTA: "/crm",
  CONTRATO: "/crm", PAGAMENTO: "/crm", LEAD_FRIO: "/crm",
  JUDICIAL: "/judicial", PROTOCOLADO: "/judicial", TRANSITO_JULGADO: "/judicial",
  RECEBIMENTO: "/recebimento", CONCLUIDO: "/recebimento",
};
const telaDoCaso = (estado?: string | null) =>
  (estado && TELA_POR_ESTADO[estado]) || "/crm";

export default function PainelLayout({
  children, titulo,
}: { children: React.ReactNode; titulo?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const [autorizado, setAutorizado] = useState(false);
  const [quem, setQuem] = useState("");
  const [busca, setBusca] = useState("");
  const [resultados, setResultados] = useState<any[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [menuAberto, setMenuAberto] = useState(false);

  useEffect(() => {
    (async () => {
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) { router.replace("/entrar?next=/crm"); return; }
      const { data: perfil } = await supabase
        .from("perfis").select("papel,nome").eq("id", sess.session.user.id).maybeSingle();
      if (!["OPERADOR", "ADMIN"].includes(perfil?.papel)) { router.replace("/cliente"); return; }
      setQuem(perfil?.nome || sess.session.user.email || "");
      setAutorizado(true);
    })();
  }, [router]);

  useEffect(() => { setMenuAberto(false); }, [pathname]);

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
    return (
      <div className="flex min-h-screen items-center justify-center bg-navy font-sans text-small text-slate">
        Verificando acesso
      </div>
    );
  }

  const ativo = (href: string) =>
    pathname === href || pathname?.startsWith(href + "/");

  const linha = (m: Item) => (
    <Link key={m.href} href={m.href}
      className={`relative mb-0.5 flex items-center gap-3 rounded-lg py-2.5 pl-4 pr-3 text-small transition
        ${ativo(m.href)
          ? "bg-white/[.07] font-semibold text-white"
          : "text-slate hover:bg-white/[.04] hover:text-white"}`}>
      {ativo(m.href) && (
        <span aria-hidden="true"
          className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r bg-electric" />
      )}
      <span className={ativo(m.href) ? "text-electric" : ""}>{m.icone}</span>
      {m.label}
    </Link>
  );

  const bloco = (rotulo: string, itens: Item[]) => (
    <div className="mb-5">
      <p className="mb-2 px-4 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate/60">
        {rotulo}
      </p>
      {itens.map(linha)}
    </div>
  );

  const barra = (
    <>
      <Link href="/inicio" className="flex items-center gap-2.5 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-electric to-indigo font-display text-body font-bold text-white">
          FC
        </span>
        <span className="flex flex-col leading-none">
          <span className="font-display text-body font-bold text-white">Legal OS</span>
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate">
            Gestão interna
          </span>
        </span>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {bloco("Caminho do caso", CAMINHO)}
        {bloco("Controle do dia", CONTROLE)}
        {bloco("Balcão", BALCAO)}
      </nav>

      <div className="border-t border-white/5 p-3">
        <p className="truncate px-1 pb-2 text-caption text-slate">{quem}</p>
        <button
          onClick={async () => { await supabase.auth.signOut(); router.push("/entrar"); }}
          className="w-full rounded-lg border border-white/10 px-3 py-2 text-small text-slate transition hover:border-white/25 hover:text-white">
          Sair
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-navy font-sans">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-white/5 bg-petrol md:flex">
        {barra}
      </aside>

      {menuAberto && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="flex w-64 flex-col border-r border-white/5 bg-petrol">{barra}</div>
          <button aria-label="Fechar menu" onClick={() => setMenuAberto(false)}
            className="flex-1 bg-navy/70 backdrop-blur-sm" />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-white/5 bg-navy/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center gap-4">
            <button onClick={() => setMenuAberto(true)} aria-label="Abrir menu"
              className="rounded-lg p-2 text-slate transition hover:bg-white/5 hover:text-white md:hidden">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>

            {titulo && (
              <h1 className="hidden font-display text-body font-bold text-white sm:block">
                {titulo}
              </h1>
            )}

            <form onSubmit={buscar} className="relative ml-auto w-full max-w-md">
              <svg className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate"
                fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path strokeLinecap="round" d="m20 20-3.5-3.5" />
              </svg>
              <input value={busca} onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por nome, CPF, CNPJ ou número do processo"
                className="w-full rounded-lg border border-white/10 bg-petrol py-2.5 pl-10 pr-4 text-small text-white placeholder:text-slate/70 outline-none transition focus:border-electric focus:shadow-glow" />

              {(resultados.length > 0 || buscando) && (
                <div className="absolute left-0 right-0 z-40 mt-2 max-h-80 overflow-y-auto rounded-xl2 border border-white/10 bg-petrol p-2 shadow-lift">
                  {buscando ? (
                    <p className="px-3 py-2 text-caption text-slate">Buscando</p>
                  ) : (
                    resultados.map((c) => (
                      <Link key={c.id} href={telaDoCaso(c.estado)} onClick={() => setResultados([])}
                        className="block rounded-lg px-3 py-2 text-small text-white transition hover:bg-white/5">
                        <span className="font-semibold">{c.clientes?.nome ?? "sem nome"}</span>
                        <span className="ml-2 text-caption text-slate">
                          {c.grupo ?? ""}{c.numero_processo ? ` · ${c.numero_processo}` : ""} · {c.estado}
                        </span>
                      </Link>
                    ))
                  )}
                  {!buscando && resultados.length === 0 && (
                    <p className="px-3 py-2 text-caption text-slate">Nada encontrado.</p>
                  )}
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
