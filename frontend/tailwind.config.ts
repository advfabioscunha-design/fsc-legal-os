import type { Config } from "tailwindcss";

/* SISTEMA DE CORES FSC ADVOCACIA
 *
 * Antes desta versão o projeto tinha TRÊS dourados diferentes
 * (#C9A24D no Tailwind, #C9A84C escrito à mão no balcão, #C5A880 na
 * barra de rolagem) e DOIS marinhos (#0B1F3B e #0A1628). Cada tela
 * escolhia o seu, e o resultado era aquela sensação de coisa remendada
 * que o olho percebe antes da cabeça explicar.
 *
 * Agora há uma paleta só, e ela tem uma lógica:
 *
 *   navy      autoridade. É o fundo, a base de tudo.
 *   electric  ação. Botão, link, o que se clica.
 *   indigo    o hover do electric. Nunca aparece sozinho.
 *   gold      exclusividade. Reservado a selo e área premium.
 *             Dourado em tudo vira enfeite e deixa de significar algo.
 *   slate     texto secundário. Tudo que explica, não afirma.
 *   mist/ice  respiro. Seções claras, cards, formulários.
 *
 * Semânticas (emerald, crimson, amber) nunca são decoração: cada uma
 * significa uma coisa só, e por isso o usuário aprende a lê-las.
 */
export default {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        serif: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        navy: "#0A1628",
        petrol: "#12243F",
        blue: "#1A3A6B",
        electric: "#2D7DD2",
        indigo: "#4361EE",
        slate: "#8899AA",
        mist: "#EBF0F7",
        ice: "#F7F9FC",
        gold: "#C9A84C",
        amber: "#F39C12",
        emerald: "#1DB954",
        crimson: "#C0392B",
        charcoal: "#1F2933",
        whats: "#25D366",

        /* Herdadas da paleta anterior. Ainda há vinte telas usando
           `forest` e trinta usando `amber`; remover de uma vez faria
           essas classes deixarem de existir e os elementos ficarem sem
           cor nenhuma, o que é pior do que uma cor fora do sistema.
           Saem quando as telas internas passarem pela mesma revisão. */
        forest: "#1E4D3B",
        moss: "#2F5D50",
      },
      fontSize: {
        /* Escala com proporção fixa. O site tinha títulos de 4 tamanhos
           arbitrários na mesma página; isso é o que faz parecer amador
           mesmo quando as cores estão certas. */
        "display-lg": ["clamp(2.75rem, 6vw, 4.5rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "display": ["clamp(2rem, 4.2vw, 3.25rem)", { lineHeight: "1.1", letterSpacing: "-0.018em" }],
        "title": ["clamp(1.5rem, 2.6vw, 2.125rem)", { lineHeight: "1.2", letterSpacing: "-0.012em" }],
        "subtitle": ["1.125rem", { lineHeight: "1.65" }],
        "body": ["1rem", { lineHeight: "1.7" }],
        "small": ["0.875rem", { lineHeight: "1.6" }],
        "caption": ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.02em" }],
      },
      boxShadow: {
        card: "0 1px 2px rgba(10,22,40,.06), 0 8px 24px -8px rgba(10,22,40,.14)",
        lift: "0 2px 4px rgba(10,22,40,.08), 0 20px 40px -12px rgba(10,22,40,.22)",
        glow: "0 0 0 1px rgba(45,125,210,.25), 0 12px 32px -8px rgba(45,125,210,.35)",
      },
      borderRadius: { xl2: "1.25rem" },
      maxWidth: { content: "72rem" },
    },
  },
  plugins: [],
} satisfies Config;
