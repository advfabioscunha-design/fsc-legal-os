/* CONSULTA AO DIÁRIO DE JUSTIÇA ELETRÔNICO NACIONAL (CNJ)

   Por que esta consulta roda no navegador, e não no servidor:

   O Comunica CNJ (comunicaapi.pje.jus.br) responde 403 para o nosso
   servidor — ele fica nos Estados Unidos, e o CNJ recusa requisição de
   fora do país. Do navegador do escritório, que está no Brasil, a mesma
   consulta responde normalmente, e a API permite CORS. Então quem
   pergunta ao CNJ é esta tela; o servidor recebe o resultado já lido e
   cuida do resto (cruzar com o acervo, gravar, criar prazos).

   O efeito prático: a varredura acontece quando alguém do escritório
   abre a tela e manda atualizar. Para a varredura virar rotina noturna
   sem ninguém presente, seria preciso um ponto de saída no Brasil. */

const BASE = "https://comunicaapi.pje.jus.br/api/v1/comunicacao";

export type Comunicacao = {
  fonte: string;
  evento_id: string;
  numero_processo: string | null;
  numero_sem_mascara: string | null;
  tribunal: string | null;
  orgao: string | null;
  tipo: string | null;
  tipo_documento: string | null;
  classe: string | null;
  data: string | null;
  link: string | null;
  texto: string;
  partes: { nome: string; polo: string }[];
  advogado: string;
  cliente_provavel: string | null;
};

export class FonteOcupada extends Error {}

/* "O sistema está muito ocupado. Tente novamente mais tarde." é resposta
   do PRÓPRIO CNJ — vem no campo `message` do JSON dele, com HTTP 200, e
   aparece até numa consulta de um único item. Medido: a mesma consulta
   que falha volta a funcionar segundos depois. Então insistir com uma
   pausa crescente resolve a maioria dos casos; desistir na primeira
   negativa seria transformar soluço da fonte em erro nosso. */
async function pedir(params: Record<string, string | number>, tentativas = 4): Promise<any> {
  const url = new URL(BASE);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  let ultimo = "";
  for (let i = 0; i < tentativas; i++) {
    if (i > 0) await new Promise((r) => setTimeout(r, 900 * i));   // 0,9s, 1,8s, 2,7s
    try {
      const r = await fetch(url.toString());
      const d = await r.json();
      if ((d.status || "").toLowerCase() === "success") return d;
      ultimo = d.message || `HTTP ${r.status}`;
    } catch (e: any) {
      ultimo = e?.message || "falha de rede";
    }
  }
  throw new FonteOcupada(ultimo);
}

/* O campo `texto` vem como HTML de editor. Aqui fica só o que se lê —
   mesma limpeza que o backend faz, para que os dois lados enxerguem o
   mesmo conteúdo. */
export function textoLimpo(html?: string | null): string {
  if (!html) return "";
  let t = html.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, " ");
  t = t.replace(/<br\s*\/?>|<\/p>|<\/tr>|<\/section>|<\/div>/gi, "\n");
  t = t.replace(/<[^>]+>/g, " ");
  const ta = document.createElement("textarea");
  ta.innerHTML = t;
  t = ta.value;
  t = t.replace(/[ \t ]+/g, " ").replace(/ +([,.;:)])/g, "$1").replace(/\( +/g, "(");
  t = t.split("\n").map((l) => l.trim()).join("\n");
  return t.replace(/\n{3,}/g, "\n\n").trim();
}

/* Qual das partes é o nosso cliente: na publicação, o advogado aparece
   logo depois da parte que representa. Se o texto não permitir essa
   leitura, devolve null em vez de chutar. */
function clienteProvavel(item: any, texto: string): string | null {
  const advogado: string =
    item?.destinatarioadvogados?.[0]?.advogado?.nome || "";
  const partes: string[] = (item?.destinatarios || [])
    .map((p: any) => p?.nome).filter(Boolean);
  if (!advogado || !partes.length) return null;
  const alvo = texto.toUpperCase().indexOf(advogado.toUpperCase());
  if (alvo < 0) return null;
  let melhor: string | null = null, melhorPos = -1;
  for (const nome of partes) {
    const pos = texto.toUpperCase().lastIndexOf(nome.toUpperCase(), alvo);
    if (pos > melhorPos) { melhor = nome; melhorPos = pos; }
  }
  return melhor;
}

function normalizar(item: any): Comunicacao {
  const texto = textoLimpo(item?.texto);
  return {
    fonte: "COMUNICA_CNJ",
    evento_id: `cnj-${item?.id}`,
    numero_processo: (item?.numeroprocessocommascara || item?.numero_processo || "").trim() || null,
    numero_sem_mascara: (item?.numero_processo || "").trim() || null,
    tribunal: item?.siglaTribunal ?? null,
    orgao: item?.nomeOrgao ?? null,
    tipo: item?.tipoComunicacao ?? null,
    tipo_documento: item?.tipoDocumento ?? null,
    classe: item?.nomeClasse ?? null,
    data: item?.data_disponibilizacao ?? null,
    link: item?.link ?? null,
    texto,
    partes: (item?.destinatarios || [])
      .filter((p: any) => p?.nome)
      .map((p: any) => ({ nome: p.nome, polo: p.polo })),
    advogado: item?.destinatarioadvogados?.[0]?.advogado?.nome || "",
    cliente_provavel: clienteProvavel(item, texto),
  };
}

function isoMenosDias(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() - Math.max(dias, 1));
  return d.toISOString().slice(0, 10);
}

export async function porOab(
  numero: string, uf: string, dias = 60,
  opcoes: {
    porPagina?: number;
    paginasMax?: number;
    onProgresso?: (lidas: number, total: number) => void;
  } = {},
): Promise<{
  itens: Comunicacao[];
  falhas: { pagina: number; erro: string }[];
  total: number;
}> {
  const porPagina = opcoes.porPagina ?? 100;
  const paginasMax = opcoes.paginasMax ?? 60;   // 6.000 publicações

  /* Cinco anos cabem numa consulta só — medido: a OAB 10.849/RO tem
     1.161 publicações em 5 anos, e o CNJ devolve a contagem em menos de
     três segundos. O que a fonte faz, de vez em quando, é responder
     "sistema está muito ocupado" mesmo numa consulta mínima. Isso é
     instabilidade dela, não tamanho de janela — por isso a estratégia
     aqui é PAGINAR com poucas requisições e insistir em cada página,
     em vez de fatiar o período em muitos pedaços (mais pedaços = mais
     requisições = mais chances de topar com a fonte ocupada).

     Uma página que não vem nem depois das tentativas entra em `falhas`
     e a busca CONTINUA: melhor trazer 90% do acervo e dizer o que
     faltou do que voltar de mãos vazias. */

  const hoje = new Date().toISOString().slice(0, 10);
  const inicio = isoMenosDias(dias);
  const base = {
    numeroOab: numero.replace(/\D/g, ""),
    ufOab: uf.toUpperCase(),
    dataDisponibilizacaoInicio: inicio,
    dataDisponibilizacaoFim: hoje,
    itensPorPagina: porPagina,
  };

  const vistos = new Set<string>();
  const saida: Comunicacao[] = [];
  const falhas: { pagina: number; erro: string }[] = [];
  let total: number | null = null;

  for (let pagina = 1; pagina <= paginasMax; pagina++) {
    let dados: any;
    try {
      dados = await pedir({ ...base, pagina });
    } catch (e: any) {
      falhas.push({ pagina, erro: e?.message || "falhou" });
      if (pagina === 1) throw e;          // nem a primeira veio: não há o que salvar
      continue;
    }
    if (total === null) total = dados.count ?? null;
    const itens = dados.items || [];
    for (const i of itens) {
      const c = normalizar(i);
      if (!vistos.has(c.evento_id)) { vistos.add(c.evento_id); saida.push(c); }
    }
    opcoes.onProgresso?.(saida.length, total ?? saida.length);
    if (itens.length < porPagina) break;
  }
  return { itens: saida, falhas, total: total ?? saida.length };
}

export async function porProcesso(numero: string, porPagina = 100): Promise<Comunicacao[]> {
  const d = await pedir({
    numeroProcesso: numero.replace(/\D/g, ""),
    itensPorPagina: porPagina, pagina: 1,
  });
  return (d.items || []).map(normalizar)
    .sort((a: Comunicacao, b: Comunicacao) => (a.data || "").localeCompare(b.data || ""));
}
