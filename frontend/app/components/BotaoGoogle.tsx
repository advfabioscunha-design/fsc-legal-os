"use client";

import { useState } from "react";
import { supabase } from "../../lib/supabaseClient";
import { useGoogleLiberado } from "../../lib/entradaGoogle";

/* ENTRAR COM A CONTA GOOGLE
 *
 * Por que isto existe: a senha é o degrau onde a maior parte das
 * pessoas desiste. Ou ela inventa uma senha na hora e esquece no dia
 * seguinte, ou abandona o cadastro no meio. Quem tem Gmail — e é quase
 * todo mundo — já tem uma conta confirmada, com nome e e-mail
 * verificados pelo próprio Google. Um clique e está dentro, sem
 * formulário, sem confirmar e-mail, sem "esqueci a senha" na semana
 * seguinte.
 *
 * O botão não decide nada sobre permissão. Ele só prova QUEM é a
 * pessoa. O que ela pode ver continua sendo decidido pelo papel
 * gravado em `perfis`, no retorno (/entrada). Quem entra com Google
 * sem ser da equipe cai como cliente — nunca como operador. Isso é
 * dito aqui porque é a parte que, mal feita, abriria a operação do
 * escritório para qualquer pessoa com um Gmail.
 *
 * `destino` é a tela para onde ir depois. `convite` é o código do
 * convite do WhatsApp, quando a pessoa chegou por lá: ele viaja na
 * volta para que o login novo seja amarrado ao cadastro que já existe.
 */
export default function BotaoGoogle({
  destino,
  convite,
  rotulo = "Entrar com o Google",
  tom = "claro",
  nota,
  divisor,
}: {
  destino?: string;
  convite?: string;
  rotulo?: string;
  tom?: "claro" | "escuro";
  nota?: string;
  divisor?: string;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const liberado = useGoogleLiberado();

  async function ir() {
    setErro("");
    setOcupado(true);
    try {
      /* A volta do Google tem de cair numa tela nossa que saiba o que
         fazer com a sessão. Mandar direto para /inicio ou /cliente
         parece mais curto, mas aí ninguém confere o papel, e o convite
         do WhatsApp se perde no caminho. */
      const volta = new URL("/entrada", window.location.origin);
      /* Quando a tela não disser o destino, vale o `next` que já estava
         na URL: é o que faz a sessão vencida no meio do trabalho voltar
         para a tela onde a pessoa parou, e não para o Início. */
      const daUrl = new URLSearchParams(window.location.search).get("next") || "";
      const alvo = destino || daUrl;
      if (alvo) volta.searchParams.set("next", alvo);
      if (convite) volta.searchParams.set("convite", convite);

      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: volta.toString(),
          /* Celular e computador de casa costumam ter mais de uma conta
             Google. Sem isto o Google entra com a última usada, e a
             pessoa descobre depois que criou acesso com o e-mail
             errado — e o caso dela fica no cadastro do outro e-mail. */
          queryParams: { prompt: "select_account" },
        },
      });
      if (error) throw error;
      /* Daqui o navegador sai para o Google. Se voltou a execução para
         cá sem erro, a saída está acontecendo: deixar o botão ocupado
         evita dois cliques e duas idas. */
    } catch (e: any) {
      const m = String(e?.message || "");
      setErro(
        /provider is not enabled|Unsupported provider/i.test(m)
          ? "A entrada pelo Google ainda está sendo liberada. Por enquanto, "
            + "entre com e-mail e senha."
          : "Não consegui abrir o Google agora. Tente de novo, ou entre com "
            + "e-mail e senha."
      );
      setOcupado(false);
    }
  }

  const base =
    "flex w-full items-center justify-center gap-3 rounded-lg px-4 py-3 "
    + "text-sm font-semibold transition disabled:opacity-50";
  const cor =
    tom === "escuro"
      ? "border border-white/20 bg-white/5 text-white hover:border-white/45 hover:bg-white/10"
      : "border border-black/12 bg-white text-charcoal shadow-sm hover:bg-black/[0.03]";

  /* Provedor desligado — ou ainda não sabemos: nada aparece. A nota e o
     divisor vêm junto de propósito. Um "ou com e-mail e senha" sozinho,
     sem nada acima dele, é pior do que não ter divisor nenhum: a pessoa
     procura a outra opção que a frase promete e não encontra. */
  if (liberado !== true) return null;

  const risco = tom === "escuro" ? "bg-white/10" : "bg-black/10";
  const legenda = tom === "escuro" ? "text-white/40" : "text-charcoal/40";

  return (
    <div>
      <button type="button" onClick={ir} disabled={ocupado} className={`${base} ${cor}`}>
        <MarcaGoogle />
        {ocupado ? "Abrindo o Google…" : rotulo}
      </button>

      {nota && (
        <p className={`mt-2 text-[11px] leading-relaxed ${tom === "escuro" ? "text-white/55" : "text-charcoal/50"}`}>
          {nota}
        </p>
      )}

      {erro && (
        <p className={`mt-2 text-xs leading-relaxed ${tom === "escuro" ? "text-[#E5A44C]" : "text-[#B3261E]"}`}>
          {erro}
        </p>
      )}

      {divisor && (
        <div className="mt-5 flex items-center gap-3">
          <span className={`h-px flex-1 ${risco}`} />
          <span className={`text-[10px] uppercase tracking-wider ${legenda}`}>{divisor}</span>
          <span className={`h-px flex-1 ${risco}`} />
        </div>
      )}
    </div>
  );
}

/* O "G" colorido, desenhado aqui dentro em vez de buscado num
   endereço do Google: imagem de fora quebra quando a rede está ruim e
   deixa o botão com um quadrado vazio, justamente na tela de entrada. */
function MarcaGoogle() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62Z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.81.54-1.84.86-3.05.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A9 9 0 0 0 9 18Z" />
      <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.94H.96a9 9 0 0 0 0 8.12l3.01-2.34Z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58Z" />
    </svg>
  );
}
