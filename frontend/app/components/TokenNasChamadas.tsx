"use client";
import { useEffect } from "react";
import { supabase } from "../../lib/supabaseClient";

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* O CRACHÁ EM TODA CHAMADA À API
 *
 * A plataforma tem mais de duzentas chamadas à API espalhadas por vinte
 * telas, e nenhuma delas mandava quem estava falando. A API, do outro
 * lado, não perguntava. Resultado: quem soubesse o endereço listava
 * pedidos, equipe e prazos sem nunca ter feito login.
 *
 * Havia dois caminhos para corrigir. Um era abrir as vinte telas e
 * acrescentar o cabeçalho em cada chamada, uma por uma. Além do
 * trabalho, o problema é o que vem depois: toda tela nova precisaria
 * lembrar de fazer o mesmo, e a que esquecesse ficaria aberta sem
 * ninguém notar.
 *
 * O outro é este. O componente troca o `fetch` do navegador por uma
 * versão que, antes de sair, olha o endereço: se for para a API do
 * escritório, anexa o token da sessão do Supabase; se for para qualquer
 * outro lugar, passa direto, sem tocar em nada. Um arquivo, e cobre
 * tudo o que existe hoje e tudo o que for escrito amanhã.
 *
 * O token é o mesmo que o Supabase já mantém no navegador de quem fez
 * login. Não se inventa credencial nova, não se guarda nada a mais, e
 * quem não está logado continua navegando: as telas públicas do site e
 * do balcão não precisam de token, e a API sabe quais são.
 *
 * O `fetch` é trocado uma vez só. React em modo estrito monta o
 * componente duas vezes em desenvolvimento, e sem a marca abaixo a
 * segunda montagem empilharia um embrulho sobre o outro.
 */
export default function TokenNasChamadas() {
  useEffect(() => {
    const w = window as any;
    if (w.__fscFetchComToken) return;
    w.__fscFetchComToken = true;

    const original = window.fetch.bind(window);

    window.fetch = async (entrada: any, init?: any) => {
      const url =
        typeof entrada === "string" ? entrada
        : entrada instanceof URL ? entrada.toString()
        : entrada?.url || "";

      if (!url.startsWith(API)) return original(entrada, init);

      try {
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;
        if (!token) return original(entrada, init);

        // Cabeçalho já posto à mão em alguma chamada antiga tem
        // precedência: quem escreveu sabia de algo que este código não
        // sabe.
        const headers = new Headers(
          init?.headers || (entrada instanceof Request ? entrada.headers : undefined));
        if (!headers.has("Authorization")) {
          headers.set("Authorization", `Bearer ${token}`);
        }
        return original(entrada, { ...(init || {}), headers });
      } catch {
        // Sessão indisponível não pode derrubar a chamada: a tela
        // pública tem de continuar funcionando.
        return original(entrada, init);
      }
    };
  }, []);

  return null;
}
