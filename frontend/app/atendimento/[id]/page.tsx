"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* ATENDIMENTO POR VÍDEO — a tela do cliente.

   O caminho é curto de propósito: ele abre o link, diz o nome, decide sobre
   a gravação e entra. Sem instalar nada, sem criar conta, sem senha.

   O aceite da gravação vem ANTES da sala, e não é pró-forma: o texto diz o
   que é gravado (só o áudio), por quê, onde fica e que os servidores estão
   fora do Brasil. Recusar é uma opção de verdade — o atendimento acontece
   igual, apenas sem gravar. */

type Entrada = {
  ok: boolean;
  status: string;
  expirado: boolean;
  ja_consentiu: boolean;
  texto_consentimento: string;
  versao_consentimento: string;
};

export default function Atendimento() {
  const { id } = useParams<{ id: string }>();
  const [dados, setDados] = useState<Entrada | null>(null);
  const [erro, setErro] = useState("");
  const [nome, setNome] = useState("");
  const [aceita, setAceita] = useState(true);
  const [entrando, setEntrando] = useState(false);
  const [sala, setSala] = useState<{ url: string; token: string } | null>(null);
  const quadro = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/v1/atendimentos/${id}/entrada`);
        const d = await r.json();
        if (!r.ok) { setErro(d.detail || "Atendimento não encontrado."); return; }
        setDados(d);
      } catch {
        setErro("Não foi possível carregar o atendimento. Verifique sua conexão.");
      }
    })();
  }, [id]);

  async function entrar() {
    setEntrando(true);
    setErro("");
    try {
      const r = await fetch(`${API}/api/v1/atendimentos/${id}/entrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: nome.trim() || "Cliente", aceita_gravacao: aceita }),
      });
      const d = await r.json();
      if (!r.ok) { setErro(d.detail || "Não foi possível entrar na sala."); return; }
      setSala({ url: d.url, token: d.token });
    } catch {
      setErro("Não foi possível entrar na sala. Tente novamente.");
    } finally {
      setEntrando(false);
    }
  }

  // já dentro da sala: o Prebuilt do Daily assume a tela inteira
  if (sala) {
    const src = `${sala.url}?t=${encodeURIComponent(sala.token)}`;
    return (
      <div className="fixed inset-0 bg-black" ref={quadro}>
        <iframe
          src={src}
          allow="camera; microphone; fullscreen; speaker; display-capture; autoplay"
          className="h-full w-full border-0"
          title="Atendimento por vídeo"
        />
      </div>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-5 py-10">
      <div className="rounded-2xl border border-charcoal/10 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-gold">
          FC Advocacia
        </p>
        <h1 className="mt-1 text-2xl font-bold text-navy">Seu atendimento por vídeo</h1>

        {erro && (
          <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{erro}</p>
        )}

        {!dados && !erro && (
          <p className="mt-4 text-sm text-charcoal/60">Carregando…</p>
        )}

        {dados?.expirado && (
          <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Este link de atendimento expirou. Peça um novo ao escritório — leva
            um minuto para gerar.
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
              <p className="text-sm font-semibold text-navy">Sobre a gravação</p>
              <div className="mt-2 space-y-2 text-sm leading-relaxed text-charcoal/75">
                {dados.texto_consentimento.split("\n\n").map((p, i) => (
                  <p key={i}>{p.replace(/\*\*/g, "")}</p>
                ))}
              </div>

              <label className="mt-4 flex items-start gap-3 text-sm text-charcoal/85">
                <input
                  type="checkbox"
                  checked={aceita}
                  onChange={(e) => setAceita(e.target.checked)}
                  className="mt-0.5 h-5 w-5 shrink-0 accent-navy"
                />
                <span>
                  Li e <b>autorizo a gravação do áudio</b> deste atendimento.
                </span>
              </label>
              {!aceita && (
                <p className="mt-2 text-xs text-charcoal/55">
                  Sem problema: o atendimento acontece do mesmo jeito, apenas sem
                  gravação.
                </p>
              )}
            </div>

            <button
              onClick={entrar}
              disabled={entrando}
              className="mt-5 w-full rounded-xl bg-navy px-6 py-4 text-base font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {entrando ? "Entrando…" : "Entrar no atendimento"}
            </button>

            <p className="mt-3 text-center text-xs text-charcoal/50">
              O navegador vai pedir permissão para usar sua câmera e seu microfone.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
