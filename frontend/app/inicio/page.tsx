"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PainelLayout from "../components/PainelLayout";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* INÍCIO — a visão geral do escritório.

   Serve a duas coisas: dizer o que precisa de atenção hoje, e ser o ponto
   de onde se alcança qualquer parte da plataforma. Até aqui a esteira era
   a porta de entrada, e de dentro dela não havia como voltar — era a
   única tela sem o menu lateral. */

/* As quatro fases do caso, na ordem, e depois as ferramentas que
   atravessam todas elas. */
const ATALHOS = [
  { href: "/contratos", icone: "🤝", titulo: "1 · Contratos", chave: "contratos_abertos",
    texto: "Quem chegou, proposta, assinatura e pagamento." },
  { href: "/crm", icone: "🗂️", titulo: "2 · Triagem", chave: "producao",
    texto: "Documentos, análise, peça, revisão e protocolo." },
  { href: "/judicial", icone: "⚖️", titulo: "3 · Judicializado", chave: "judicial",
    texto: "Protocolado e em tramitação, até o trânsito em julgado." },
  { href: "/recebimento", icone: "💰", titulo: "4 · Execução", chave: "recebimento",
    texto: "Cumprimento, alvará, RPV e prestação de contas." },
  { href: "/tarefas", icone: "✅", titulo: "Tarefas", chave: null,
    texto: "O que fazer hoje e o plano da semana, por prioridade." },
  { href: "/pendencias", icone: "📌", titulo: "Pendências", chave: null,
    texto: "Anotações do que precisa ser feito, com data para resolver." },
  { href: "/intimacoes", icone: "🔔", titulo: "Intimações e prazos", chave: "prazos_7_dias",
    texto: "O que o juízo mandou e o que vence primeiro." },
  { href: "/agenda", icone: "📅", titulo: "Agenda", chave: null,
    texto: "Audiências, perícias e prazos de trabalho." },
  { href: "/processos", icone: "📁", titulo: "Todos os processos", chave: null,
    texto: "Busca em qualquer fase, por número, cliente ou tribunal." },
  { href: "/admin", icone: "📊", titulo: "Administração", chave: null,
    texto: "Financeiro, equipe e indicadores." },
];

export default function Inicio() {
  const [resumo, setResumo] = useState<any>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/painel/resumo`);
        if (r.ok) setResumo(await r.json());
      } catch { /* a tela funciona mesmo sem os números */ }
    })();
  }, []);

  const urgentes = resumo?.prazos_proximos || [];

  return (
    <PainelLayout titulo="Início">
      <div className="space-y-6">
        {/* O que precisa de atenção */}
        <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { rotulo: "Aguardando cliente", valor: resumo?.aguardando_cliente, cor: "#E5A44C", href: "/crm" },
            { rotulo: "Contratos em aberto", valor: resumo?.contratos_abertos, cor: "#2D7DD2", href: "/contratos" },
            { rotulo: "Prazos em 7 dias", valor: resumo?.prazos_7_dias, cor: "#C0392B", href: "/intimacoes" },
            { rotulo: "Intimações novas", valor: resumo?.intimacoes_novas, cor: "#1DB954", href: "/intimacoes" },
          ].map((c) => (
            <Link key={c.rotulo} href={c.href}
              className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4 transition hover:border-white/25">
              <p className="text-2xl font-bold" style={{ color: c.cor }}>
                {c.valor ?? "—"}
              </p>
              <p className="mt-0.5 text-xs text-white/55">{c.rotulo}</p>
            </Link>
          ))}
        </section>

        {/* Prazos mais próximos: o que não pode passar */}
        <section className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#C9A24D]">O que vence primeiro</h2>
            <Link href="/intimacoes" className="text-xs text-white/50 hover:text-white">ver todos →</Link>
          </div>
          {urgentes.length === 0 ? (
            <p className="text-xs text-white/40">
              {resumo ? "Nenhum prazo nos próximos dias." : "Carregando…"}
            </p>
          ) : (
            <ul className="space-y-2">
              {urgentes.slice(0, 6).map((p: any, i: number) => {
                const d = p.dias_restantes;
                const cor = d <= 0 ? "#C0392B" : d <= 2 ? "#E5A44C" : "#8899AA";
                return (
                  <li key={i} className="flex items-center gap-3 rounded-lg bg-[#0A1628]/60 px-3 py-2 text-xs">
                    <span className="w-16 shrink-0 font-bold" style={{ color: cor }}>
                      {d < 0 ? "vencido" : d === 0 ? "hoje" : `${d} dia${d > 1 ? "s" : ""}`}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-white/80">
                      {p.cliente ? <b>{p.cliente}</b> : null} {p.descricao}
                    </span>
                    <span className="shrink-0 text-white/35">{p.numero_processo || ""}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Onde ir */}
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {ATALHOS.map((a) => (
            <Link key={a.href} href={a.href}
              className="rounded-xl border border-white/10 bg-[#0B1F3B] p-4 transition hover:border-[#C9A24D]/50">
              <div className="flex items-start justify-between">
                <p className="text-lg">{a.icone}</p>
                {a.chave && resumo?.[a.chave] != null && (
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-bold text-white/80">
                    {resumo[a.chave]}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm font-bold text-white/90">{a.titulo}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-white/50">{a.texto}</p>
            </Link>
          ))}
        </section>
      </div>
    </PainelLayout>
  );
}
