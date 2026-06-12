import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Plus Jakarta Sans"', "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ['"Space Grotesk"', "monospace"],
        brand: ["Barlow", "sans-serif"],
      },
      colors: {
        fsc: {
          navy:     "#0A1628",
          blue:     "#1A3A6B",
          electric: "#2D7DD2",
          indigo:   "#4361EE",
          slate:    "#8899AA",
          mist:     "#EBF0F7",
          white:    "#FFFFFF",
          gold:     "#C9A84C",
          emerald:  "#1DB954",
          crimson:  "#C0392B",
          amber:    "#F39C12",
        },
      },
      backgroundImage: {
        "fsc-hero": "linear-gradient(135deg, #0A1628 0%, #1A3A6B 100%)",
        "fsc-card": "linear-gradient(135deg, #1A3A6B 0%, #0A1628 100%)",
      },
    },
  },
  plugins: [],
} satisfies Config;
