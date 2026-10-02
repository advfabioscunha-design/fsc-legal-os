"use client";

import { useEffect, useState } from "react";

/* O BOTÃO DO GOOGLE SÓ APARECE QUANDO FUNCIONA
 *
 * Quando o provedor Google não está ligado no Supabase, clicar no botão
 * leva o navegador para o endereço de autorização, que responde com
 * isto, em texto puro, numa página branca:
 *
 *     {"code":400,"error_code":"validation_failed",
 *      "msg":"Unsupported provider: provider is not enabled"}
 *
 * Quem vê isso não entende que faltou uma configuração nossa: entende
 * que o sistema quebrou — e sai da página. O tratamento de erro dentro
 * do botão não alcança esse caso, porque a falha não acontece aqui; ela
 * acontece depois, já no servidor do Supabase, com o navegador fora da
 * nossa página.
 *
 * Por isso a pergunta é feita ANTES, uma vez, ao abrir a tela. O
 * Supabase publica em `/auth/v1/settings` quais provedores estão
 * ligados. Se o Google não estiver, o botão simplesmente não existe, e
 * a tela mostra só o caminho que funciona.
 *
 * Três respostas possíveis, e por isso o `null`:
 *   true  — ligado, mostra o botão
 *   false — desligado, não mostra
 *   null  — ainda perguntando; também não mostra, para o botão não
 *           piscar na tela e sumir.
 */
export function useGoogleLiberado(): boolean | null {
  const [liberado, setLiberado] = useState<boolean | null>(null);

  useEffect(() => {
    let vivo = true;
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
    const chave = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
    if (!url || !chave) { setLiberado(false); return; }

    (async () => {
      try {
        const r = await fetch(`${url}/auth/v1/settings`, {
          headers: { apikey: chave, Authorization: `Bearer ${chave}` },
        });
        const j = await r.json();
        if (vivo) setLiberado(!!j?.external?.google);
      } catch {
        /* Sem resposta, o botão não aparece. É a escolha menos ruim:
           esconder um caminho que talvez funcionasse incomoda menos do
           que oferecer um que termina em página de erro. */
        if (vivo) setLiberado(false);
      }
    })();

    return () => { vivo = false; };
  }, []);

  return liberado;
}
