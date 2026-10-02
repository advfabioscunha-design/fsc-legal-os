/* O QUE FALTA NO CADASTRO DO CLIENTE — EM UM LUGAR SÓ
 *
 * Três telas precisam da mesma resposta: a volta do Google, a entrada
 * por senha e o balcão. Se cada uma escrever a sua, uma delas vai
 * esquecer o aceite, e ninguém descobre isso até precisar provar que o
 * cliente aceitou alguma coisa.
 *
 * A TRAVA QUE ESTE ARQUIVO EVITA
 *
 * O aceite é gravado no servidor. Enquanto a migração que criou essas
 * colunas não estiver aplicada, o servidor devolve sempre vazio — e aí
 * o balcão manda para a conclusão, a conclusão salva, volta ao balcão,
 * que manda de novo para a conclusão. A pessoa fica girando entre duas
 * telas sem entender por quê.
 *
 * Por isso existe a marca de sessão: concluído uma vez neste navegador,
 * não se pergunta de novo até fechar a aba. O registro de verdade
 * continua sendo o do servidor; a marca só impede que uma falha de
 * gravação vire uma porta girando.
 */

const MARCA = "fsc.cadastro.concluido";

export function concluiuNestaSessao(): boolean {
  try { return sessionStorage.getItem(MARCA) === "1"; } catch { return false; }
}

export function marcarConcluido() {
  try { sessionStorage.setItem(MARCA, "1"); } catch { /* aba privada */ }
}

export function esquecerConclusao() {
  try { sessionStorage.removeItem(MARCA); } catch { /* idem */ }
}

/* Nome completo: duas palavras de verdade. É o mínimo que um contrato
   ou uma procuração exige, e "Fabio" sozinho não serve.
   WhatsApp: 10 ou 11 dígitos, que é o que existe de número no Brasil.
   Quem tem 9 esqueceu o DDD, e o aviso de prazo não chegaria. */
export function faltaNoCadastro(c: any): boolean {
  if (concluiuNestaSessao()) return false;
  const nome = String(c?.nome || "").trim();
  const zap = String(c?.whatsapp || "").replace(/\D/g, "");
  const inteiro = nome.split(/\s+/).filter((p) => p.length > 1).length >= 2;
  const aceitou = !!c?.aceite_termos_em && !!c?.aceite_privacidade_em;
  return !(inteiro && zap.length >= 10 && aceitou);
}
