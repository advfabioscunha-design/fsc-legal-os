"use client";
import { useEffect } from "react";

/* O LINK DO E-MAIL CAI NA PORTA DA FRENTE, E PRECISA CHEGAR NA SALA CERTA.
 *
 * O Supabase só honra o endereço de retorno que a gente pede se ele
 * estiver na lista de endereços permitidos do projeto. Com a lista
 * vazia, ele ignora o pedido e manda todo mundo para a Site URL, que
 * aqui é a raiz do aplicativo. Era isso que acontecia: a pessoa
 * clicava no e-mail de recuperação, caía na página inicial, e o
 * endereço trazia o token de recuperação que ninguém ali sabia ler.
 *
 * Dá para consertar preenchendo a lista no painel do Supabase, e vale
 * a pena fazer isso também. Mas depender de uma configuração que
 * ninguém vê para uma recuperação de senha funcionar é frágil: um dia
 * alguém limpa a lista, ou cria um domínio novo, e o canal quebra em
 * silêncio. Este componente fecha o buraco do lado de cá.
 *
 * Ele fica no layout, então roda em qualquer página. Se a URL trouxer
 * a marca de recuperação, ele leva para /entrar carregando junto a
 * âncora com o token, que é o que a tela de lá espera. Em qualquer
 * outro caso não faz absolutamente nada.
 */
export default function LevaParaRedefinirSenha() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const caminho = window.location.pathname;
    if (caminho.startsWith("/entrar")) return;   // já está no lugar certo

    const ancora = window.location.hash || "";
    const busca = new URLSearchParams(window.location.search);
    const naAncora = new URLSearchParams(ancora.replace(/^#/, ""));

    // Os dois formatos que o Supabase usa, conforme a versão do fluxo:
    // o token na âncora, e o código na própria URL.
    const ehRecuperacao =
      naAncora.get("type") === "recovery"
      || busca.get("type") === "recovery"
      || (Boolean(busca.get("code")) && busca.get("fluxo") !== "outro");

    if (!ehRecuperacao) return;

    // `replace`, e não `push`: voltar para trás depois de trocar a
    // senha levaria a pessoa a um link já gasto.
    window.location.replace(
      `/entrar?recuperar=1${busca.toString() ? `&${busca.toString()}` : ""}${ancora}`);
  }, []);

  return null;
}
