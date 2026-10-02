"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../../../lib/supabaseClient";
import { faltaNoCadastro, marcarConcluido } from "../../../lib/cadastro";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A versão de cada documento é a data que aparece no alto dele. Fica
   gravada junto com o aceite: sem isso, saber que a pessoa aceitou não
   diz O QUE ela aceitou, porque o texto muda. Ao atualizar um dos dois,
   mude a data aqui também — e quem já aceitou a versão anterior passa a
   aparecer como pendente de novo aceite. */
const VERSAO_TERMOS = "2026-10-02";
const VERSAO_PRIVACIDADE = "2026-09-28";

/* CONCLUIR O CADASTRO — DUAS PERGUNTAS, SÓ
 *
 * O Google entrega e-mail e, quase sempre, o nome. Não entrega
 * telefone, e não garante que o nome esteja completo: muita conta é
 * "Fabio" ou "Fabio S.". Faltam exatamente duas coisas para o cadastro
 * servir ao escritório — e são essas duas que esta tela pede.
 *
 * Por que WhatsApp: é por ele que saem o aviso de prazo, o pedido de
 * documento e a cobrança. Cliente sem telefone é cliente que só fica
 * sabendo das coisas se lembrar de entrar na plataforma.
 *
 * Por que nome completo: ele entra no contrato, na procuração e na
 * petição. Documento com nome pela metade não vale, e descobrir isso
 * no dia da assinatura custa caro para todo mundo.
 *
 * E por que NÃO se pede mais nada: cada campo a mais nesta tela é uma
 * chance a mais de a pessoa fechar a página. CPF, endereço e estado
 * civil são perguntados na hora em que forem necessários — na coleta
 * do documento —, quando a pessoa já entendeu para quê.
 */
export default function Completar() {
  const router = useRouter();

  const [carregando, setCarregando] = useState(true);
  const [nome, setNome] = useState("");
  const [fone, setFone] = useState("");
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [destino, setDestino] = useState("/cliente");
  /* Duas caixas, não uma. São dois documentos, com objetos e datas
     diferentes, e juntá-los numa só esconderia metade do que a pessoa
     está aceitando. */
  const [aceitaTermos, setAceitaTermos] = useState(false);
  const [aceitaPrivacidade, setAceitaPrivacidade] = useState(false);
  const [revalidando, setRevalidando] = useState(false);

  useEffect(() => {
    let vivo = true;
    (async () => {
      const p = new URLSearchParams(window.location.search);
      const n = p.get("next") || "";
      const alvo = n.startsWith("/") && !n.startsWith("//") ? n : "/cliente";
      setDestino(alvo);

      const { data } = await supabase.auth.getSession();
      if (!data.session) { router.replace("/entrar"); return; }

      /* O que a pessoa já tem vem preenchido. Pedir de novo um nome que
         o Google acabou de informar faz a tela parecer burocracia. */
      try {
        const r = await fetch(`${API}/api/v1/cliente/cadastro`, {
          headers: { Authorization: `Bearer ${data.session.access_token}` },
        });
        const c = await r.json().catch(() => ({} as any));
        if (!vivo) return;

        /* QUEM JÁ RESPONDEU NÃO RESPONDE DE NOVO
           Esta tela é a porta de todo cliente que entra, venha pelo
           Google ou por senha. Para quem já tem nome, telefone e o
           aceite registrado, ela some: segue direto para onde ia. É o
           que permite deixar a conferência num lugar só, em vez de
           repetida em cada tela de entrada — e repetida é como ela
           deixa de existir em uma delas. */
        if (!faltaNoCadastro(c)) { router.replace(alvo); return; }

        /* Já aceitou uma versão anterior do texto? As caixas voltam
           desmarcadas, porque o que ela leu não é mais este documento.
           A tela diz isso, senão parece que o sistema esqueceu. */
        if (c?.aceite_termos_em
            && (c?.aceite_termos_versao !== VERSAO_TERMOS
                || c?.aceite_privacidade_versao !== VERSAO_PRIVACIDADE)) {
          setRevalidando(true);
        }

        const m: any = data.session.user.user_metadata || {};
        setNome(melhorNome(
          [c?.nome, m.nome, m.full_name, m.name],
          String(data.session.user.email || "")));
        setFone(mascarar(String(c?.whatsapp || "")));
      } catch { /* sem isso a tela abre em branco, o que ainda funciona */ }
      if (vivo) setCarregando(false);
    })();
    return () => { vivo = false; };
  }, [router]);

  async function concluir() {
    setErro("");
    const limpo = nome.trim().replace(/\s+/g, " ");
    const digitos = fone.replace(/\D/g, "");

    /* Duas conferências, e só as que evitam estrago de verdade.
       "Nome e sobrenome" porque é o mínimo que um documento exige;
       10 ou 11 dígitos porque é o que existe de número no Brasil —
       quem digita 9 esqueceu o DDD, e o aviso não chegaria nunca. */
    if (limpo.split(" ").filter((x) => x.length > 1).length < 2) {
      setErro("Escreva o seu nome completo, como está no seu documento.");
      return;
    }
    if (digitos.length < 10 || digitos.length > 11) {
      setErro("Confira o telefone: são 11 dígitos com o DDD, por exemplo "
              + "(69) 99999-9999.");
      return;
    }
    if (!aceitaTermos || !aceitaPrivacidade) {
      setErro("Para concluir, marque que você aceita os Termos de Uso e a "
              + "Política de Privacidade. Os dois abrem em outra aba, se "
              + "quiser ler antes.");
      return;
    }

    setSalvando(true);
    try {
      const { data } = await supabase.auth.getSession();
      if (!data.session) { router.replace("/entrar"); return; }

      const r = await fetch(`${API}/api/v1/cliente/cadastro`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${data.session.access_token}`,
        },
        body: JSON.stringify({ nome: limpo, whatsapp: digitos }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({} as any));
        setErro(j?.detail || "Não consegui salvar agora. Tente de novo.");
        setSalvando(false);
        return;
      }
      /* O nome também fica na conta: é dele que o sistema parte quando
         cria um cadastro novo, e deixar os dois diferentes é o começo
         de um cliente com dois nomes. */
      try { await supabase.auth.updateUser({ data: { nome: limpo } }); } catch { }

      /* O ACEITE FICA REGISTRADO, COM DATA E VERSÃO
         É o que transforma a caixa marcada em prova. O instante é
         carimbado no servidor; daqui vai só qual versão do texto estava
         no ar quando a pessoa marcou.

         Falhar aqui não tranca a entrada: a pessoa já marcou, e barrá-la
         por causa de um registro que não gravou seria punir quem fez a
         parte dela. O registro é refeito no acesso seguinte. */
      try {
        await fetch(`${API}/api/v1/cliente/aceite`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${data.session.access_token}`,
          },
          body: JSON.stringify({
            termos: true, privacidade: true,
            versao_termos: VERSAO_TERMOS,
            versao_privacidade: VERSAO_PRIVACIDADE,
          }),
        });
      } catch { /* ver acima */ }

      /* A marca de que isto já foi respondido neste navegador. Sem ela,
         uma gravação que falhou faria a próxima tela mandar de volta
         para cá, e a pessoa ficaria girando entre duas telas. */
      marcarConcluido();
      router.replace(destino);
    } catch {
      setErro("Falha de conexão. Tente de novo em instantes.");
      setSalvando(false);
    }
  }

  const campo = "w-full rounded-lg border border-black/10 bg-white px-3.5 py-3 "
    + "text-sm text-[#1C1C1C] outline-none focus:border-[#C9A84C]";

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F6F7F9] px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#C9A84C]">
          FC Advocacia
        </p>

        {carregando ? (
          <p className="mt-5 text-sm text-black/50">Carregando o seu cadastro…</p>
        ) : (
          <>
            <h1 className="mt-2 font-display text-lg font-bold text-[#0A1628]">
              Falta pouco para concluir
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-black/60">
              Seu acesso já está criado. Confirme como você se chama e um
              telefone para o escritório falar com você. São só estes dois.
            </p>

            <div className="mt-5 space-y-3">
              <label className="block">
                <span className="text-xs text-black/50">Nome completo</span>
                <input value={nome} onChange={(e) => setNome(e.target.value)}
                  autoComplete="name" placeholder="Nome e sobrenome"
                  className={`mt-1 ${campo}`} />
              </label>

              <label className="block">
                <span className="text-xs text-black/50">WhatsApp com DDD</span>
                <input value={fone} inputMode="tel" autoComplete="tel"
                  onChange={(e) => setFone(mascarar(e.target.value))}
                  onKeyDown={(e) => e.key === "Enter" && concluir()}
                  placeholder="(69) 99999-9999"
                  className={`mt-1 ${campo}`} />
                <span className="mt-1 block text-[11px] leading-relaxed text-black/45">
                  É por aqui que chegam o aviso de prazo e o pedido de documento.
                </span>
              </label>
            </div>

            {/* O ACEITE, ANTES DO BOTÃO

                Marcar vem antes de concluir, na ordem da leitura: quem
                chega ao botão já passou por aqui. Os links abrem em
                outra aba de propósito — ler os termos não pode custar o
                que a pessoa acabou de digitar.

                O botão fica desligado até as duas estarem marcadas. É
                mais honesto do que deixar clicável e reclamar depois:
                a tela mostra que falta alguma coisa, em vez de contar. */}
            <div className="mt-5 rounded-xl border border-black/10 bg-black/[0.02] p-4">
              <p className="text-xs font-semibold text-[#0A1628]">
                Termos e privacidade
              </p>

              {revalidando && (
                <p className="mt-2 rounded-lg bg-[#E5A44C]/10 px-3 py-2 text-[11px] leading-relaxed text-[#8A5A00]">
                  Atualizamos esses documentos desde o seu último aceite. Por
                  isso pedimos de novo — o que você aceitou antes era outro texto.
                </p>
              )}

              <label className="mt-3 flex cursor-pointer items-start gap-2.5">
                <input type="checkbox" checked={aceitaTermos}
                  onChange={(e) => setAceitaTermos(e.target.checked)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-[#C9A84C]" />
                <span className="text-[12px] leading-relaxed text-black/65">
                  Li e aceito os{" "}
                  <a href="/termos" target="_blank" rel="noopener noreferrer"
                    className="font-semibold text-[#0A1628] underline underline-offset-2">
                    Termos de Uso
                  </a>
                </span>
              </label>

              <label className="mt-2.5 flex cursor-pointer items-start gap-2.5">
                <input type="checkbox" checked={aceitaPrivacidade}
                  onChange={(e) => setAceitaPrivacidade(e.target.checked)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-[#C9A84C]" />
                <span className="text-[12px] leading-relaxed text-black/65">
                  Li e aceito a{" "}
                  <a href="/privacidade" target="_blank" rel="noopener noreferrer"
                    className="font-semibold text-[#0A1628] underline underline-offset-2">
                    Política de Privacidade
                  </a>
                </span>
              </label>
            </div>

            {erro && (
              <p className="mt-3 rounded-lg bg-[#E57373]/10 px-3 py-2 text-[12px] leading-relaxed text-[#B3261E]">
                {erro}
              </p>
            )}

            <button onClick={concluir}
              disabled={salvando || !aceitaTermos || !aceitaPrivacidade}
              className="mt-4 w-full rounded-lg bg-[#C9A84C] px-4 py-3 text-sm font-bold text-[#0A1628] transition hover:bg-[#d8b95e] disabled:cursor-not-allowed disabled:opacity-40">
              {salvando ? "Salvando…" : "Concluir e acessar a plataforma"}
            </button>

            <p className="mt-4 text-[11px] leading-relaxed text-black/40">
              Criar acesso não é contratar o escritório: a contratação tem
              contrato próprio, com o serviço e o valor. Seus dados são usados
              apenas para atender o que você pedir, e o escritório não envia
              propaganda por WhatsApp.
            </p>
          </>
        )}
      </div>
    </main>
  );
}

/* O NOME VEM PRONTO, SEM A PESSOA DIGITAR
 *
 * Há três fontes, e a ordem entre elas importa. Na frente fica o nome
 * com sobrenome, venha de onde vier: é o único que serve para
 * documento. Depois, qualquer nome já gravado. Por último, o próprio
 * e-mail.
 *
 * O e-mail é a parte que salva a tela quando o Google não manda nome
 * nenhum: "adv.fabios.cunha@gmail.com" vira "Fabios Cunha", porque é
 * assim que as pessoas montam o endereço delas. O que vem daí é
 * palpite, e palpite editável — o campo fica aberto justamente para a
 * pessoa corrigir. Mas um campo com quase tudo escrito é respondido;
 * um campo vazio é abandonado.
 */
function melhorNome(fontes: any[], email: string) {
  const limpos = fontes
    .map((x) => String(x || "").trim().replace(/\s+/g, " "))
    .filter(Boolean)
    // "adv.fabios.cunha" gravado como nome é o e-mail disfarçado, e
    // mostrá-lo seria pior do que não mostrar nada.
    .filter((x) => !x.includes("@") && !/[._]/.test(x));

  const completo = limpos.find((x) => x.split(" ").filter((p) => p.length > 1).length >= 2);
  if (completo) return completo;
  if (limpos[0]) return limpos[0];
  return doEmail(email);
}

/* Prefixos profissionais e caixas genéricas não são o nome de ninguém.
   Deixá-los entrar produziria "Adv Fabios Cunha" no contrato. */
const NAO_E_NOME = new Set([
  "adv", "advogado", "advogada", "dr", "dra", "doutor", "doutora",
  "contato", "atendimento", "comercial", "financeiro", "juridico",
  "escritorio", "oab", "email", "meu", "sr", "sra",
]);
const MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e"]);

function doEmail(email: string) {
  const local = String(email || "").split("@")[0] || "";
  const partes = local
    .split(/[._\-+0-9]+/)
    .map((p) => p.trim().toLowerCase())
    .filter((p) => p.length > 1 && !NAO_E_NOME.has(p));
  return partes
    .map((p) => (MINUSCULAS.has(p) ? p : p[0].toUpperCase() + p.slice(1)))
    .join(" ");
}

/* O telefone vai formatado enquanto se digita. Não é enfeite: número
   sem formatação é onde o dígito a mais ou a menos passa despercebido,
   e o aviso vai para outra pessoa. */
function mascarar(v: string) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}
