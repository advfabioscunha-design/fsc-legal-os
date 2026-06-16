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
        // Paleta Instagram Jurídico (autoridade & confiança)
        navy: "#0B1F3B",      // Azul Marinho
        petrol: "#0F2A44",    // Azul Petróleo
        forest: "#1E4D3B",    // Verde Escuro (Tributário/Bancário)
        moss: "#2F5D50",      // Verde Musgo
        gold: "#C9A24D",      // Dourado Fosco (conversão & CTA)
        amber: "#D4AF37",     // Âmbar (destaque)
        charcoal: "#2B2B2B",  // Cinza Grafite (texto)
        mist: "#E5E7EB",      // Cinza Claro
        ice: "#F8F9FA",       // Cinza Gelo (seções claras)
      },
    },
  },
  plugins: [],
} satisfies Config;
