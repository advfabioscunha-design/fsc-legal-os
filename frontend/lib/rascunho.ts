"use client";
import { useCallback, useEffect, useRef, useState } from "react";

/* O QUE A PESSOA ESTAVA ESCREVENDO NÃO SE PERDE.
 *
 * Alguém começa a escrever uma mensagem, o telefone toca, ela troca de
 * aba para conferir um documento, volta — e a caixa está vazia. O que
 * ela escreveu some, e com ele some a vontade de escrever de novo.
 *
 * Num atendimento jurídico isso é pior do que parece: a mensagem que se
 * perde costuma ser a mais difícil de escrever. A pessoa estava
 * contando o problema dela, parou no meio para lembrar uma data, e ao
 * voltar encontra a tela limpa. Da segunda vez ela escreve menos.
 *
 * Este gancho guarda o rascunho no próprio navegador enquanto ela
 * digita, e devolve quando ela volta. Nada vai para o servidor: é texto
 * não enviado, é dela, e não tem por que o escritório ver.
 *
 * O RASCUNHO É POR CONVERSA
 *
 * A chave inclui o pedido ou o caso. Sem isso, o rascunho de um pedido
 * reaparece dentro de outro, e a pessoa manda para o lugar errado uma
 * frase que escreveu para outra coisa.
 *
 * E ELE VENCE
 *
 * Rascunho de três meses atrás reaparecendo não é memória, é assombro:
 * a pessoa abre a conversa e encontra uma frase que não lembra de ter
 * escrito, fora de contexto. Sete dias é tempo de voltar; mais que isso
 * é entulho.
 *
 * POR QUE ENVOLVER TUDO EM try/catch
 *
 * O navegador anônimo, a cota cheia e algumas configurações corporativas
 * fazem localStorage LEVANTAR ERRO em vez de devolver vazio. Sem a
 * proteção, a tela inteira quebra por causa de um recurso de
 * conveniência, e aí o cliente não consegue nem escrever.
 */

const PREFIXO = "fsc.rascunho.";
const VALIDADE_MS = 7 * 24 * 60 * 60 * 1000;

type Guardado = { texto: string; em: number };

function ler(chave: string): string {
  try {
    const cru = window.localStorage.getItem(PREFIXO + chave);
    if (!cru) return "";
    const g = JSON.parse(cru) as Guardado;
    if (!g?.texto) return "";
    if (Date.now() - (g.em || 0) > VALIDADE_MS) {
      window.localStorage.removeItem(PREFIXO + chave);
      return "";
    }
    return String(g.texto);
  } catch {
    return "";
  }
}

function gravar(chave: string, texto: string) {
  try {
    if (!texto) {
      window.localStorage.removeItem(PREFIXO + chave);
      return;
    }
    window.localStorage.setItem(
      PREFIXO + chave,
      JSON.stringify({ texto, em: Date.now() } as Guardado),
    );
  } catch {
    /* cota cheia ou aba anônima: o rascunho é conveniência, não função */
  }
}

/** Limpa rascunhos vencidos de todas as conversas. Barato, roda uma vez. */
function varrerVencidos() {
  try {
    const mortos: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i);
      if (!k || !k.startsWith(PREFIXO)) continue;
      try {
        const g = JSON.parse(window.localStorage.getItem(k) || "{}") as Guardado;
        if (Date.now() - (g.em || 0) > VALIDADE_MS) mortos.push(k);
      } catch {
        mortos.push(k);
      }
    }
    mortos.forEach((k) => window.localStorage.removeItem(k));
  } catch {
    /* sem storage, nada a varrer */
  }
}

/**
 * Texto de caixa de mensagem que sobrevive a sair da página.
 *
 * Devolve [texto, setTexto, limpar]. Use `limpar()` DEPOIS que a
 * mensagem for enviada com sucesso — não antes: se o envio falhar e o
 * rascunho já tiver sido apagado, a pessoa perde o texto justamente no
 * momento em que ela mais precisa dele.
 *
 * `chave` tem de identificar a conversa: `pedido-${id}`, `caso-${id}`.
 */
export function useRascunho(
  chave: string,
): [string, (v: string) => void, () => void] {
  const [texto, definir] = useState("");
  const montado = useRef(false);

  // O servidor não tem localStorage, então a leitura só acontece depois
  // que a tela existe no navegador. Ler antes disso quebraria a página
  // inteira no Next.
  useEffect(() => {
    montado.current = false;
    definir(ler(chave));
    montado.current = true;
    varrerVencidos();
  }, [chave]);

  // Grava enquanto digita, com um respiro: salvar a cada tecla escreve
  // no disco dezenas de vezes por frase, e meio segundo depois da última
  // tecla guarda a mesma coisa sem o custo.
  useEffect(() => {
    if (!montado.current) return;
    const t = setTimeout(() => gravar(chave, texto), 400);
    return () => clearTimeout(t);
  }, [chave, texto]);

  // Fechar a aba no meio da digitação não espera o respiro acima: aqui
  // o texto é gravado na hora, porque não haverá próxima oportunidade.
  useEffect(() => {
    const aoSair = () => gravar(chave, texto);
    window.addEventListener("beforeunload", aoSair);
    window.addEventListener("pagehide", aoSair);
    return () => {
      window.removeEventListener("beforeunload", aoSair);
      window.removeEventListener("pagehide", aoSair);
      aoSair();
    };
  }, [chave, texto]);

  const limpar = useCallback(() => {
    definir("");
    gravar(chave, "");
  }, [chave]);

  return [texto, definir, limpar];
}
