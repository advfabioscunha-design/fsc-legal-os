"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* A VOLTA DO GOOGLE
 *
 * O Google devolve a pessoa para cá. Esta tela existe porque entre
 * "o Google confirmou quem é" e "a pessoa está na tela certa" há três
 * coisas que ninguém mais faz:
 *
 *   1. fechar a sessão — trocar o código que veio na URL por um login
 *      de verdade;
 *   2. amarrar ao cadastro — se a pessoa chegou por um convite do
 *      WhatsApp, o login novo tem de cair no cadastro que já existe,
 *      senão ela entra e encontra a área vazia;
 *   3. conferir o papel — e só então decidir entre a operação do
 *      escritório e a área do cliente.
 *
 * O item 3 é o que importa mais. Entrar com Google prova quem a pessoa
 * é; não dá a ela permissão nenhuma. Quem não tem papel de OPERADOR ou
 * ADMIN gravado em `perfis` vai para a área do cliente, mesmo que tenha
 * clicado na porta da equipe. Qualquer pessoa do mundo tem um Gmail, e
 * nenhuma delas pode virar operadora do escritório por isso.
 *
 * A tela é quase sempre invisível: dura o tempo de dois pedidos. Ela só
 * aparece de verdade quando algo deu errado, e aí precisa dizer o que
 * foi, porque a alternativa é uma tela branca em cima de um login que a
 * pessoa acabou de fazer.
 */
export default function Entrada() {
  const router = useRouter();
  const [recado, setRecado] = useState("Confirmando o seu acesso…");
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    let vivo = true;

    (async () => {
      const p = new URLSearchParams(window.location.search);
      const next = p.get("next") || "";
      const convite = p.get("convite") || "";

      /* O Google avisa aqui quando a pessoa desistiu na tela dele —
         fechou, clicou em cancelar, negou a permissão. Não é defeito, e
         tratar como defeito deixa a pessoa achando que o sistema
         quebrou. */
      const recusa = p.get("error") || p.get("error_description")
        || new URLSearchParams((window.location.hash || "").replace(/^#/, "")).get("error");
      if (recusa) {
        if (!vivo) return;
        setFalhou(true);
        setRecado("A entrada pelo Google não foi concluída. Você pode tentar de "
                  + "novo ou entrar com e-mail e senha.");
        return;
      }

      /* 1. A SESSÃO
         A biblioteca do Supabase troca o código da URL por uma sessão
         sozinha, assim que carrega. Mas "assim que carrega" não é
         "agora": por isso espera-se, e só então se faz a troca na mão,
         que é o caminho de quem usa o fluxo novo (PKCE). */
      let sessao = (await supabase.auth.getSession()).data.session;
      if (!sessao) {
        for (let i = 0; i < 12 && !sessao; i++) {
          await new Promise((r) => setTimeout(r, 250));
          sessao = (await supabase.auth.getSession()).data.session;
        }
      }
      if (!sessao && p.get("code")) {
        try {
          const { data } = await supabase.auth.exchangeCodeForSession(p.get("code")!);
          sessao = data.session;
        } catch { /* cai no aviso logo abaixo */ }
      }
      if (!sessao) {
        if (!vivo) return;
        setFalhou(true);
        setRecado("Não consegui concluir a entrada pelo Google. Tente de novo. "
                  + "Se repetir, entre com e-mail e senha.");
        return;
      }

      /* Tira o código da barra de endereço. Recarregar a página com um
         código já usado produz erro, e a pessoa lê isso como se o
         acesso dela tivesse falhado. */
      window.history.replaceState({}, "", window.location.pathname);

      /* 2. O NOME
         O cadastro do cliente é criado pelo servidor com o nome que
         está na conta. O Google guarda isso como `full_name`; o resto
         do sistema lê `nome`. Sem esta cópia o cliente nasce chamado
         pelo pedaço do e-mail antes do arroba, e é assim que ele passa
         a ser tratado nas mensagens. */
      try {
        const m: any = sessao.user.user_metadata || {};
        const nome = (m.nome || m.full_name || m.name || "").trim();
        if (!m.nome && nome) await supabase.auth.updateUser({ data: { nome } });
      } catch { /* nome é melhoria, não pode barrar a entrada */ }

      /* 3. O CONVITE DO WHATSAPP
         Quem veio de lá tem caso aberto no escritório. Falhar aqui em
         silêncio é o pior desfecho possível: a pessoa entra e vê uma
         área vazia, achando que o escritório perdeu o caso dela. */
      if (convite) {
        if (vivo) setRecado("Ligando o seu acesso ao seu cadastro…");
        try {
          const v = await fetch(`${API}/api/v1/cliente/vincular`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${sessao.access_token}`,
            },
            body: JSON.stringify({ codigo: convite }),
          });
          if (!v.ok) {
            const j = await v.json().catch(() => ({} as any));
            if (!vivo) return;
            setFalhou(true);
            setRecado(j?.detail
              || "Você já está dentro, mas não consegui ligar o acesso ao seu "
                 + "cadastro. Entre na sua área e fale com o escritório pelo chat.");
            return;
          }
        } catch {
          if (!vivo) return;
          setFalhou(true);
          setRecado("Você já está dentro, mas a ligação com o seu cadastro não "
                    + "foi concluída. Entre na sua área e avise o escritório.");
          return;
        }
      }

      /* 4. O PAPEL DECIDE O DESTINO
         Sem linha em `perfis`, a pessoa é cliente. É o padrão certo:
         o acesso à operação é concedido de dentro da plataforma, por
         quem já é administrador, e não por quem chegou com um Gmail. */
      let daEquipe = false;
      try {
        const { data: perfil } = await supabase
          .from("perfis").select("papel").eq("id", sessao.user.id).maybeSingle();
        daEquipe = ["OPERADOR", "ADMIN"].includes((perfil as any)?.papel);
      } catch { daEquipe = false; }

      if (!vivo) return;

      /* O destino pedido é respeitado quando é tela de cliente — o
         balcão é o caso que importa: quem foi criar acesso no meio de
         um pedido de contrato tem de voltar para o pedido, e não para a
         lista de casos, senão recomeça tudo. Tela interna só para quem
         é da equipe. Qualquer outra coisa na URL é ignorada: `next` vem
         de fora e não manda ninguém para onde não pode ir. */
      const DO_CLIENTE = ["/cliente", "/balcao", "/contrato", "/privacidade", "/portal"];
      const pedido = next.startsWith("/") && !next.startsWith("//") ? next : "";
      const ehDoCliente = DO_CLIENTE.some(
        (r) => pedido === r || pedido.startsWith(`${r}/`) || pedido.startsWith(`${r}?`));

      const alvo = ehDoCliente ? pedido
        : (pedido && daEquipe) ? pedido
        : daEquipe ? "/inicio" : "/cliente";

      if (!vivo) return;

      /* O QUE O GOOGLE NÃO ENTREGA
         Ele dá e-mail e, às vezes, o nome. Nunca dá telefone, nunca dá
         aceite dos termos, e o nome vem como a pessoa escreveu na conta
         — "Fabio", "Fabio S.". Faltam três coisas para esse cadastro
         servir: o nome inteiro, que vai no contrato e na procuração; o
         WhatsApp, por onde sai o aviso de prazo; e o aceite dos termos
         e da política de privacidade.

         Todo cliente passa pela tela de conclusão, e é ela que decide
         se tem o que perguntar: quem já respondeu atravessa sem ver
         nada. A conferência fica num lugar só de propósito — repetida
         em cada porta, é questão de tempo até faltar em uma delas.

         Quem é da equipe não passa: entrou por convite, com cadastro
         feito por um administrador. */
      if (daEquipe) { router.replace(alvo); return; }
      router.replace(`/entrada/completar?next=${encodeURIComponent(alvo)}`);
    })();

    return () => { vivo = false; };
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0A1628] px-5 py-12 text-white">
      <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-[#0B1F3B] p-7 text-center">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#C9A84C]">
          FC Advocacia
        </p>

        {!falhou && (
          <span
            aria-hidden="true"
            className="mx-auto mt-6 block h-7 w-7 animate-spin rounded-full border-2 border-white/15 border-t-[#C9A84C]"
          />
        )}

        <p className="mt-5 text-sm leading-relaxed text-white/75">{recado}</p>

        {falhou && (
          <div className="mt-6 space-y-2.5">
            <Link href="/entrar"
              className="block rounded-lg bg-[#C9A84C] px-4 py-3 text-sm font-bold text-[#0A1628]">
              Entrar com e-mail e senha
            </Link>
            <Link href="/cliente"
              className="block rounded-lg border border-white/20 px-4 py-3 text-sm font-semibold text-white">
              Ir para a minha área
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
