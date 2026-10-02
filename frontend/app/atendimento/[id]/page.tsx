"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* ATENDIMENTO POR VÍDEO — a tela do cliente.

   O consentimento não é um checkbox ao lado de um parágrafo. Ele exige
   abrir o Termo, ROLAR ATÉ O FINAL e confirmar a ciência lá dentro: o
   botão de concordar só destrava quando o texto acabou de ser percorrido.

   Isso muda o valor probatório da coisa. Um aceite marcado sem que o
   texto tenha sido exibido é fácil de contestar; um aceite dado ao fim do
   documento, com data, hora, IP e a versão do termo guardada por inteiro,
   é outra conversa.

   Quem tentar entrar autorizando sem ter lido recebe orientação, e o
   servidor recusa de qualquer forma — a tela é a parte fácil de burlar. */

type Entrada = {
  ok: boolean;
  status: string;
  expirado: boolean;
  ja_consentiu: boolean;
  resumo: string;
  termo: string;
  versao_consentimento: string;
};

export default function Atendimento() {
  const { id } = useParams<{ id: string }>();
  const [dados, setDados] = useState<Entrada | null>(null);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [nome, setNome] = useState("");
  const [entrando, setEntrando] = useState(false);
  const [sala, setSala] = useState<
    { url: string; token: string; podeGravar: boolean } | null
  >(null);

  // termo
  const [autorizando, setAutorizando] = useState(false);
  const [autorizadoAgora, setAutorizadoAgora] = useState(false);
  const [termoAberto, setTermoAberto] = useState(false);
  const [chegouAoFim, setChegouAoFim] = useState(false);
  const [aceitouTermo, setAceitouTermo] = useState(false);
  const corpoTermo = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/atendimentos/${id}/entrada`);
        const d = await r.json().catch(() => ({} as any));
        if (!r.ok) {
          /* O QUE O CLIENTE PODE E NÃO PODE LER AQUI

             Mensagem de recusa do servidor é escrita para a equipe. Esta
             tela mostrava o texto cru, e o cliente que clicou no link do
             atendimento lia "Esta área é da equipe do escritório" — uma
             frase que, para ele, significa que foi barrado por engano,
             ou que clicou onde não devia. Ele não tem como saber que é
             uma regra de permissão nossa.

             Para quem está do lado de fora, o que importa é só: o link
             serve ou não serve, e o que fazer agora. */
          setErro(r.status === 401 || r.status === 403
            ? "Este link não pôde ser aberto. Peça ao escritório um link "
              + "novo pelo WhatsApp — leva um instante."
            : (d.detail || "Atendimento não encontrado. Confira o link ou "
                           + "peça um novo ao escritório."));
          return;
        }
        setDados(d);
      } catch {
        setErro("Não foi possível carregar o atendimento. Verifique sua conexão.");
      }
    })();
  }, [id]);

  /* Só considera lido quando o fim do texto aparece na tela. A folga de
     24px evita que arredondamento de pixel impeça alguém de concluir. */
  function aoRolar() {
    const el = corpoTermo.current;
    if (!el) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) setChegouAoFim(true);
  }

  // termo curto em tela grande pode não ter rolagem nenhuma
  useEffect(() => {
    if (!termoAberto) return;
    const t = setTimeout(() => {
      const el = corpoTermo.current;
      if (el && el.scrollHeight <= el.clientHeight + 24) setChegouAoFim(true);
    }, 150);
    return () => clearTimeout(t);
  }, [termoAberto]);

  async function entrar(comGravacao: boolean) {
    if (comGravacao && !aceitouTermo) {
      setAviso(
        "Para autorizar a gravação, abra o Termo de Consentimento, leia até o " +
        "final e confirme a ciência dentro dele. É rápido — o botão de " +
        "concordar aparece ao fim do texto."
      );
      setTermoAberto(true);
      return;
    }
    setEntrando(true);
    setErro(""); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/atendimentos/${id}/entrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: nome.trim() || "Cliente",
          aceita_gravacao: comGravacao,
          leu_termo: aceitouTermo,
        }),
      });
      const d = await r.json();
      if (!r.ok) { setErro(d.detail || "Não foi possível entrar na sala."); return; }
      setSala({ url: d.url, token: d.token, podeGravar: !!d.pode_gravar });
    } catch {
      setErro("Não foi possível entrar na sala. Tente novamente.");
    } finally {
      setEntrando(false);
    }
  }

  /* Autorização durante o atendimento: quem entrou sem autorizar pode
     mudar de ideia depois de conversar um pouco. A exigência de ler o
     termo é a mesma; muda só o momento. */
  async function autorizarAgora() {
    if (!aceitouTermo) {
      setAviso(
        "Abra o Termo de Consentimento e leia até o final para autorizar a " +
        "gravação. O botão de concordar aparece ao fim do texto."
      );
      setTermoAberto(true);
      return;
    }
    setAutorizando(true);
    try {
      const r = await fetch(`${API}/api/v1/atendimentos/${id}/autorizar-gravacao`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ leu_termo: true }),
      });
      const d = await r.json();
      if (!r.ok) { setAviso(d.detail || "Não foi possível registrar a autorização."); return; }
      setAutorizadoAgora(true);
      setAviso("");
    } catch {
      setAviso("Falha de conexão ao registrar a autorização.");
    } finally {
      setAutorizando(false);
    }
  }

  if (sala) {
    const src = `${sala.url}?t=${encodeURIComponent(sala.token)}`;
    const faltaAutorizar = !sala.podeGravar && !autorizadoAgora;
    return (
      <div className="fixed inset-0 flex flex-col bg-black">
        {faltaAutorizar && (
          <div className="flex flex-wrap items-center gap-3 bg-amber-50 px-4 py-2.5">
            <span className="text-sm text-amber-900">
              Você entrou <b>sem autorizar a gravação</b>. Se quiser que o
              escritório registre o áudio desta conversa, pode autorizar agora.
            </span>
            <button
              onClick={autorizarAgora}
              disabled={autorizando}
              className="ml-auto rounded-lg bg-navy px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
            >
              {autorizando ? "Registrando…" : aceitouTermo ? "Autorizar a gravação" : "Ler o termo e autorizar"}
            </button>
          </div>
        )}
        {autorizadoAgora && (
          <div className="bg-forest/10 px-4 py-2 text-center text-sm text-forest">
            ✓ Gravação autorizada. O que foi conversado antes deste momento não
            foi gravado.
          </div>
        )}
        {aviso && faltaAutorizar && (
          <div className="bg-amber-100 px-4 py-2 text-center text-xs text-amber-900">⚠ {aviso}</div>
        )}
        <iframe
          src={src}
          allow="camera; microphone; fullscreen; speaker; display-capture; autoplay"
          className="w-full flex-1 border-0"
          title="Atendimento por vídeo"
        />

        {termoAberto && dados && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3">
            <div className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white">
              <div className="flex items-start justify-between gap-3 border-b border-charcoal/10 px-5 py-4">
                <div>
                  <h2 className="text-base font-bold text-navy">Termo de Consentimento</h2>
                  <p className="text-xs text-charcoal/50">
                    Versão {dados.versao_consentimento} · role até o final para confirmar
                  </p>
                </div>
                <button onClick={() => setTermoAberto(false)} className="text-charcoal/40 hover:text-charcoal">✕</button>
              </div>
              <div ref={corpoTermo} onScroll={aoRolar} className="flex-1 overflow-y-auto px-5 py-4">
                <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-charcoal/85">
                  {dados.termo}
                </pre>
                <div className="h-2" />
              </div>
              <div className="border-t border-charcoal/10 bg-ice/40 px-5 py-4">
                {!chegouAoFim && (
                  <p className="mb-2 text-center text-xs text-charcoal/55">
                    ↓ Continue rolando até o fim do termo para liberar a confirmação
                  </p>
                )}
                <button
                  onClick={() => { setAceitouTermo(true); setTermoAberto(false); setAviso(""); }}
                  disabled={!chegouAoFim}
                  className="w-full rounded-xl bg-navy px-6 py-4 text-base font-semibold text-white disabled:cursor-not-allowed disabled:bg-charcoal/25"
                >
                  {chegouAoFim ? "Li o termo e estou ciente — autorizo a gravação" : "Leia o termo até o final"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-5 py-10">
      <div className="rounded-2xl border border-charcoal/10 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-gold">FC Advocacia</p>
        <h1 className="mt-1 text-2xl font-bold text-navy">Seu atendimento por vídeo</h1>

        {erro && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{erro}</p>}
        {!dados && !erro && <p className="mt-4 text-sm text-charcoal/60">Carregando…</p>}

        {dados?.expirado && (
          <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Este link de atendimento expirou. Peça um novo ao escritório — leva um
            minuto para gerar.
          </p>
        )}

        {dados && !dados.expirado && (
          <>
            <label className="mt-5 block text-sm font-medium text-charcoal/80">
              Como podemos chamar você?
              <input
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Seu nome"
                className="mt-1 w-full rounded-xl border border-charcoal/15 px-4 py-3 text-base outline-none focus:border-navy"
              />
            </label>

            <div className="mt-5 rounded-xl border border-charcoal/10 bg-ice/60 p-4">
              <div className="space-y-2 text-sm leading-relaxed text-charcoal/80">
                {dados.resumo.split("\n\n").map((p, i) => (
                  <p key={i}>{p.replace(/\*\*/g, "")}</p>
                ))}
              </div>

              <button
                onClick={() => { setTermoAberto(true); setAviso(""); }}
                className="mt-3 inline-flex items-center gap-2 rounded-xl border border-navy/25 bg-white px-4 py-3 text-sm font-semibold text-navy transition hover:bg-navy/5"
              >
                📄 Abrir e ler o Termo de Consentimento
              </button>

              <p className={`mt-2 text-sm font-medium ${aceitouTermo ? "text-forest" : "text-charcoal/55"}`}>
                {aceitouTermo
                  ? "✓ Termo lido e ciência confirmada. Você pode entrar."
                  : "Ainda não lido. A leitura é necessária para autorizar a gravação."}
              </p>
            </div>

            {aviso && (
              <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                ⚠ {aviso}
              </p>
            )}

            <button
              onClick={() => entrar(true)}
              disabled={entrando}
              className="mt-4 w-full rounded-xl bg-navy px-6 py-4 text-base font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {entrando ? "Entrando…" : "Entrar no atendimento"}
            </button>

            <button
              onClick={() => entrar(false)}
              disabled={entrando}
              className="mt-2 w-full rounded-xl border border-charcoal/15 px-6 py-3 text-sm font-medium text-charcoal/70 transition hover:bg-charcoal/5 disabled:opacity-50"
            >
              Entrar sem autorizar a gravação
            </button>

            <p className="mt-3 text-center text-xs text-charcoal/50">
              O navegador vai pedir permissão para usar sua câmera e seu microfone.
            </p>
          </>
        )}
      </div>

      {/* Termo em tela cheia: precisa rolar até o fim para concordar */}
      {termoAberto && dados && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3">
          <div className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white">
            <div className="flex items-start justify-between gap-3 border-b border-charcoal/10 px-5 py-4">
              <div>
                <h2 className="text-base font-bold text-navy">Termo de Consentimento</h2>
                <p className="text-xs text-charcoal/50">
                  Versão {dados.versao_consentimento} · role até o final para confirmar
                </p>
              </div>
              <button onClick={() => setTermoAberto(false)} className="text-charcoal/40 hover:text-charcoal">✕</button>
            </div>

            <div
              ref={corpoTermo}
              onScroll={aoRolar}
              className="flex-1 overflow-y-auto px-5 py-4"
            >
              <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-charcoal/85">
                {dados.termo}
              </pre>
              <div className="h-2" />
            </div>

            <div className="border-t border-charcoal/10 bg-ice/40 px-5 py-4">
              {!chegouAoFim && (
                <p className="mb-2 text-center text-xs text-charcoal/55">
                  ↓ Continue rolando até o fim do termo para liberar a confirmação
                </p>
              )}
              <button
                onClick={() => { setAceitouTermo(true); setTermoAberto(false); setAviso(""); }}
                disabled={!chegouAoFim}
                className="w-full rounded-xl bg-navy px-6 py-4 text-base font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-charcoal/25"
              >
                {chegouAoFim
                  ? "Li o termo e estou ciente — autorizo a gravação"
                  : "Leia o termo até o final"}
              </button>
              <button
                onClick={() => setTermoAberto(false)}
                className="mt-2 w-full rounded-xl px-6 py-2 text-sm text-charcoal/55 hover:text-charcoal"
              >
                Fechar sem concordar
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
