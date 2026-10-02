"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.fscadvocaciadigital.com.br";

/* ATENDIMENTO POR VÍDEO — a tela do cliente.

   Esta tela faz pouca coisa de propósito: pergunta como chamar a pessoa
   e abre a sala. Nada mais.

   Ela já pediu muito mais. Havia um Termo de Consentimento para abrir,
   rolar até o fim e confirmar, e duas opções de entrada — com e sem
   autorizar a gravação. A ideia era dar peso probatório ao aceite. Na
   prática fazia o contrário: a pessoa clicava para destravar a tela, e
   um aceite dado para destravar uma tela não prova entendimento nenhum.
   Pior, parava o atendimento na porta: idoso no celular não achava o
   botão, e o advogado ficava esperando.

   A autorização mudou de lugar. Hoje o advogado pede em voz alta no
   início da gravação, e a resposta do cliente fica DENTRO do áudio,
   junto com a pergunta que a originou. É prova melhor: registra o que
   foi dito, por quem e em que tom.

   O que resta aqui é informar — a faixa no alto da sala diz que, se for
   necessário gravar, o advogado avisa antes. Informar é obrigação; pedir
   clique não é. */

type Entrada = {
  ok: boolean;
  status: string;
  expirado: boolean;
  ja_consentiu: boolean;
  // `resumo`, `termo` e `versao_consentimento` ainda vêm do servidor
  // e deixaram de ser usados aqui quando a autorização saiu da porta.
  // Ficam no tipo porque a resposta continua trazendo-os, e porque o
  // termo segue existindo: ele é o texto que o advogado resume em voz.
  resumo?: string;
  termo?: string;
  versao_consentimento?: string;
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

  /* ENTRAR É SÓ ENTRAR
     Não há mais decisão sobre gravação nesta porta. A pessoa escreve
     como quer ser chamada e entra; o resto acontece na conversa. */
  async function entrar() {
    setEntrando(true);
    setErro(""); setAviso("");
    try {
      const r = await fetch(`${API}/api/v1/atendimentos/${id}/entrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: nome.trim() || "Cliente",
          aceita_gravacao: false,
          leu_termo: false,
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

  /* A função que pedia a autorização durante o atendimento saiu com o
     método antigo. Quem autoriza hoje é a voz do cliente, no início da
     gravação, e quem registra é o servidor quando o advogado aciona o
     gravar. Tela nenhuma participa disso. */

  if (sala) {
    /* A SALA EM PORTUGUÊS
       A Daily abre em inglês por padrão — "Join meeting", "Leave", "Mute".
       Para quem está entrando pelo celular, sem familiaridade com vídeo
       chamada, botão em inglês é botão que não se clica: a pessoa fica
       olhando a tela sem saber por onde entrar. O parâmetro `lang` é o
       que a Daily oferece para isso, e não depende do idioma do
       navegador do cliente, que pode estar em qualquer coisa. */
    const src = `${sala.url}?t=${encodeURIComponent(sala.token)}&lang=pt-BR`;
    return (
      <div className="fixed inset-0 flex flex-col bg-black">
        {/* O QUE O CLIENTE VÊ SOBRE A GRAVAÇÃO

            Não há mais nada a clicar. A faixa existe só para informar, e
            informar é o que a lei exige: a pessoa precisa saber que a
            conversa pode ser gravada e com que finalidade.

            A autorização em si é pedida em voz pelo advogado, no momento
            em que ele aciona a gravação, e a resposta do cliente fica
            dentro do próprio áudio. É consentimento melhor do que uma
            caixa marcada: registra a pergunta, a resposta e o tom em que
            foi dada. */}
        <div className="flex flex-wrap items-center gap-2 bg-[#0B1F3B] px-4 py-2.5">
          <span className="text-sm text-white/80">
            Se for necessário <b>gravar o áudio</b> desta conversa, o advogado
            avisa você em voz alta antes de começar e pede a sua concordância.
            Sua imagem não é gravada em momento algum.
          </span>
        </div>

        <iframe
          src={src}
          allow="camera; microphone; fullscreen; speaker; display-capture; autoplay"
          className="w-full flex-1 border-0"
          title="Atendimento por vídeo"
        />

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

            {/* A ENTRADA NÃO PEDE MAIS AUTORIZAÇÃO DE GRAVAÇÃO

                Antes, a porta da sala era um termo para ler até o fim e
                duas opções de entrada. Quem chegava para uma conversa de
                dez minutos encontrava um documento jurídico e a decisão
                de autorizar algo que ainda não tinha começado — e muita
                gente desistia ali, ou entrava sem entender o que marcou.

                Consentimento pedido antes da conversa também vale pouco:
                a pessoa autoriza a gravação de algo que ela ainda não
                sabe o que é. Agora ele é pedido no momento em que a
                gravação vai acontecer, quando o advogado aciona o botão
                — aí a pergunta tem contexto, e a resposta tem peso.

                Até lá, nada é gravado. A pessoa entra e conversa. */}
            {aviso && (
              <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                ⚠ {aviso}
              </p>
            )}

            <button
              onClick={() => entrar()}
              disabled={entrando}
              className="mt-5 w-full rounded-xl bg-navy px-6 py-4 text-base font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {entrando ? "Entrando…" : "Entrar no atendimento"}
            </button>

            <p className="mt-3 text-center text-xs leading-relaxed text-charcoal/50">
              O navegador vai pedir permissão para usar sua câmera e seu
              microfone. A conversa não é gravada — se for necessário gravar,
              o advogado pede a sua autorização durante o atendimento.
            </p>
          </>
        )}
      </div>

      {/* Termo em tela cheia: precisa rolar até o fim para concordar */}
    </main>
  );
}
