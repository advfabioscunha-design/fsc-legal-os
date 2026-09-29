"use client";
import { useEffect, useState } from "react";

/* VISUALIZAÇÃO DA MINUTA ANTES DA APROVAÇÃO

   O que este componente faz de verdade, para ninguém contar com o que
   ele não faz:

   FAZ  marca d'água grande e repetida por cima do texto, com "REVISÃO —
        NÃO ASSINADO", o nome de quem está vendo e a data/hora. Some o
        conteúdo quando a janela perde o foco. Bloqueia seleção, cópia,
        arrastar e menu de contexto. Impressão sai em branco. Não expõe
        PDF nem link de download nesta fase.

   NÃO FAZ  impedir print de tela. Nenhum navegador dá esse controle:
        não existe API que detecte PrintScreen, e a foto com outro
        celular está fora do alcance de qualquer software. Quem
        promete isso está vendendo o que não entrega.

   Então a estratégia é outra, e é a que funciona: atrapalhar a captura
   e IDENTIFICAR a cópia. A marca d'água carrega o nome e o horário de
   quem viu — uma imagem que vaze aponta para uma pessoa e um momento.
   É o mesmo raciocínio dos screeners de cinema. */

export default function VisualizadorProtegido({
  texto, quemVe, titulo,
}: { texto: string; quemVe: string; titulo?: string }) {
  const [oculto, setOculto] = useState(false);
  const carimbo = new Date().toLocaleString("pt-BR");

  useEffect(() => {
    /* Janela sem foco costuma ser recorte de tela, gravador ou outra
       janela por cima. Esconder nesse momento não impede a captura,
       mas tira o conteúdo de boa parte delas. */
    const esconder = () => setOculto(true);
    const mostrar = () => setOculto(false);
    const visibilidade = () => setOculto(document.hidden);
    window.addEventListener("blur", esconder);
    window.addEventListener("focus", mostrar);
    document.addEventListener("visibilitychange", visibilidade);

    const semMenu = (e: Event) => e.preventDefault();
    const semAtalho = (e: KeyboardEvent) => {
      const k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && ["c", "x", "s", "p", "u"].includes(k)) {
        e.preventDefault();
        setOculto(true);
        setTimeout(() => setOculto(false), 1200);
      }
    };
    document.addEventListener("contextmenu", semMenu);
    document.addEventListener("copy", semMenu);
    document.addEventListener("dragstart", semMenu);
    document.addEventListener("keydown", semAtalho);

    return () => {
      window.removeEventListener("blur", esconder);
      window.removeEventListener("focus", mostrar);
      document.removeEventListener("visibilitychange", visibilidade);
      document.removeEventListener("contextmenu", semMenu);
      document.removeEventListener("copy", semMenu);
      document.removeEventListener("dragstart", semMenu);
      document.removeEventListener("keydown", semAtalho);
    };
  }, []);

  const marca = `REVISÃO — NÃO ASSINADO · ${quemVe} · ${carimbo}`;

  return (
    <div className="relative">
      <style>{`@media print { .minuta-protegida { display: none !important; }
        body::after { content: "Este documento não pode ser impresso nesta etapa."; } }`}</style>

      <div className="mb-2 flex items-center justify-between text-xs text-white/50">
        <span>{titulo || "Minuta para conferência"}</span>
        <span>não disponível para download nesta etapa</span>
      </div>

      <div className="minuta-protegida relative overflow-hidden rounded-xl border border-white/10 bg-[#0A1628]">
        {/* Texto */}
        <div
          className="max-h-[60vh] select-none overflow-y-auto p-6 text-sm leading-relaxed text-white/85"
          style={{
            whiteSpace: "pre-wrap",
            userSelect: "none",
            WebkitUserSelect: "none",
            filter: oculto ? "blur(14px)" : "none",
            transition: "filter .12s",
          }}
        >
          {texto}
        </div>

        {/* Marca d'água: grande, repetida, por cima, e sem capturar o
            clique — atrapalha a foto sem atrapalhar a leitura. */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          {Array.from({ length: 14 }).map((_, i) => (
            <div key={i}
              className="absolute whitespace-nowrap font-bold"
              style={{
                top: `${i * 9 - 10}%`, left: "-20%", right: "-20%",
                transform: "rotate(-24deg)",
                fontSize: "clamp(18px, 3.2vw, 44px)",
                color: "rgba(201,168,76,0.16)",
                letterSpacing: "0.06em",
              }}>
              {`${marca}    ${marca}    ${marca}`}
            </div>
          ))}
        </div>

        {/* Cortina quando a janela perde o foco */}
        {oculto && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A1628]/95">
            <p className="px-6 text-center text-sm text-white/60">
              Conteúdo oculto enquanto esta janela não está em primeiro plano.
              <br />Clique aqui para voltar a ler.
            </p>
          </div>
        )}
      </div>

      <p className="mt-2 text-[11px] leading-relaxed text-white/35">
        Esta é uma versão para conferência, com marca d'água identificando
        quem está visualizando. O documento final, sem marca e assinado
        eletronicamente, é enviado ao seu e-mail depois da aprovação.
      </p>
    </div>
  );
}
