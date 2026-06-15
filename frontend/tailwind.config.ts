import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Serifada elegante para títulos (Playfair) e sans moderna para o corpo (Inter)
        serif: ["var(--font-playfair)", "Georgia", "serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      colors: {
        // Paleta Legal Premium
        navy: "#0A192F",      // Azul Marinho Profundo (confiança)
        gold: "#C5A880",      // Dourado Champanhe / Cobre (ação/destaque)
        charcoal: "#1A1A1A",  // Cinza Chumbo (texto)
        ice: "#F8F9FA",       // Cinza Gelo (alternância de seções)
      },
    },
  },
  plugins: [],
} satisfies Config;
