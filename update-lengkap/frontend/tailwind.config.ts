import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b1020",
        side: "#10162b",
        card: "#151d36",
        card2: "#1c2544",
        line: "#2c3366",
        ink: "#eef0ff",
        mute: "#9ba5c7",
        accent: "#c4b5fd",
        mint: "#6ee7b7",
        coral: "#fb7185",
        sky: "#7dd3fc"
      },
      fontFamily: {
        sans: ["var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"]
      }
    }
  },
  plugins: []
};

export default config;
