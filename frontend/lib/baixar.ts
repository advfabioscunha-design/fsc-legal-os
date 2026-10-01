const API = process.env.NEXT_PUBLIC_API_URL ?? "https://api.fscadvocaciadigital.com.br";

/* BAIXAR ARQUIVO DE ROTA QUE EXIGE LOGIN
 *
 * Um link comum não serve. O crachá da sessão é posto pelo embrulho do
 * `fetch`, e navegação de link não passa por ele: o navegador sai do
 * site, pede o arquivo sem dizer quem é, e a API responde o que tem de
 * responder a um desconhecido. O advogado clicava em "abrir no Word" e
 * recebia, em letra de máquina, "Faça login para acessar" — estando
 * logado o tempo todo.
 *
 * Aqui o arquivo vem por `fetch`, que leva o crachá, e só depois vira
 * download. O usuário não vê diferença nenhuma, que é o ponto.
 *
 * Por que não deixar a rota pública, como o PDF: o PDF é o que o
 * cliente recebe, e o endereço dele já circula. O Word é o documento em
 * texto, aberto para edição, e enquanto está em conferência ele não é
 * de ninguém fora do escritório.
 */
export async function baixarComToken(caminho: string, nomePadrao: string) {
  const r = await fetch(`${API}${caminho}`);
  if (!r.ok) {
    let motivo = "";
    try { motivo = (await r.json())?.detail || ""; } catch { /* sem corpo */ }
    throw new Error(motivo || (r.status === 401
      ? "Sua sessão expirou. Entre de novo."
      : "Não consegui baixar o arquivo agora."));
  }

  // O nome vem do servidor quando ele manda; é ele que sabe o protocolo
  // do pedido, e arquivo chamado "documento.doc" na pasta de downloads
  // de quem baixa dez por dia não ajuda ninguém.
  const cab = r.headers.get("Content-Disposition") || "";
  const achado = /filename="?([^";]+)"?/i.exec(cab);
  const nome = achado?.[1] || nomePadrao;

  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Esperar antes de soltar: o Firefox cancela o download se o endereço
  // deixar de existir no mesmo instante do clique.
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
