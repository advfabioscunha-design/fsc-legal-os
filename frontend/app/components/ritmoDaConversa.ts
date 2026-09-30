/* O TEMPO DE UMA CONVERSA DE GENTE.
 *
 * A resposta chegava em menos de um segundo, às vezes antes de a
 * pessoa terminar de ler o que ela mesma escreveu. Nenhum atendente
 * responde assim, e a velocidade é o detalhe que denuncia a máquina
 * antes de qualquer palavra do texto: quem recebe percebe que do
 * outro lado não tem ninguém lendo.
 *
 * Duas regras, e a segunda importa mais do que a primeira.
 *
 * ESPERAR O TEMPO DE LER E ESCREVER. Uns dez segundos, variando com o
 * tamanho da resposta e com um empurrão aleatório, porque intervalo
 * sempre igual denuncia tanto quanto resposta instantânea.
 *
 * ESPERAR A PESSOA TERMINAR. Se ela voltou a digitar enquanto a
 * resposta estava a caminho, a resposta espera. Ser interrompido no
 * meio da frase é a coisa mais irritante de uma conversa, e é o que
 * acontece quando o outro lado responde ao primeiro parágrafo de algo
 * que ainda está sendo escrito.
 *
 * O texto já está guardado no servidor desde o instante em que foi
 * gerado. O que se segura aqui é só a exibição, então nada se perde
 * se a pessoa fechar a página no meio.
 */

/** Quanto tempo uma resposta deste tamanho levaria para ser escrita. */
export function tempoDeResposta(caracteres: number): number {
  // Seis segundos de base, mais o tempo de digitar, com teto para a
  // resposta longa não virar espera constrangedora.
  const base = 6000 + Math.min(caracteres, 700) * 11;
  const comVariacao = base * (0.85 + Math.random() * 0.35);
  return Math.round(Math.min(Math.max(comVariacao, 6000), 14000));
}

const descansar = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Segura a resposta até o tempo passar E a pessoa parar de digitar.
 *
 * `ultimaTecla` é um ref com o instante da última tecla no campo de
 * mensagem. Enquanto ele for recente, a resposta continua esperando,
 * com um teto para não esperar para sempre quem deixou o cursor no
 * campo e saiu para o almoço.
 */
export async function esperarAVez(
  caracteres: number,
  ultimaTecla: { current: number },
  opcoes: { silencioMs?: number; tetoMs?: number } = {},
): Promise<void> {
  const silencio = opcoes.silencioMs ?? 2500;
  const teto = opcoes.tetoMs ?? 45000;
  const comecou = Date.now();

  await descansar(tempoDeResposta(caracteres));

  while (Date.now() - comecou < teto) {
    const quieto = Date.now() - (ultimaTecla.current || 0);
    if (quieto >= silencio) return;
    await descansar(Math.min(silencio - quieto, 800));
  }
}
