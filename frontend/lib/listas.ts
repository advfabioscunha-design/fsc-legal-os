/* O QUE VEM DA API NEM SEMPRE TEM A FORMA QUE DEVERIA.
 *
 * As colunas jsonb guardam o que os agentes devolvem: a revisão, o
 * laudo, o relatório, a lista de apontamentos. O esquema diz que
 * `apontamentos` é uma lista de objetos, e quase sempre é. De vez em
 * quando o modelo manda a mesma informação como texto, ou como um
 * objeto só, ou como JSON escrito dentro de uma string.
 *
 * Numa tela isso não é um detalhe: `.map` numa string não existe, e o
 * React não derruba o componente, derruba a PÁGINA. Foi o que o
 * operador viu ao abrir a aba da minuta — "Application error", tela
 * branca, nada a fazer. O contrato estava certo; o que quebrou foi o
 * formato de um recado sobre ele.
 *
 * Então nenhuma tela percorre lista vinda da API sem passar por aqui.
 * Pior desenho com o dado estranho é melhor do que página que não abre:
 * o advogado ainda consegue ler o documento e seguir o trabalho.
 */

function decodificar(v: any): any {
  if (typeof v !== "string") return v;
  const limpo = v.trim();
  if (!limpo || !"[{\"".includes(limpo[0])) return v;
  try { return JSON.parse(limpo); } catch { return v; }
}

/** Sempre uma lista. Texto solto vira lista de um item, nunca de letras. */
export function comoLista(v: any): any[] {
  const d = decodificar(v);
  if (Array.isArray(d)) return d;
  if (d === null || d === undefined || d === "") return [];
  return [d];
}

/** Sempre um objeto, para quem lê com ponto. */
export function comoObjeto(v: any): any {
  const d = decodificar(v);
  return d && typeof d === "object" && !Array.isArray(d) ? d : {};
}

/** Sempre um texto legível, venha o que vier. */
export function comoTexto(v: any): string {
  const d = decodificar(v);
  if (d === null || d === undefined) return "";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map(comoTexto).filter(Boolean).join(" ");
  if (typeof d === "object") return JSON.stringify(d);
  return String(d);
}
