/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#14171C",
        panel: "#1B1F26",
        "panel-raised": "#21252D",
        border: "#2A2F3A",
        text: "#E8E6E1",
        "text-muted": "#8B92A0",
        "text-dim": "#5C6270",
        "risk-high": "#C9564A",
        "risk-medium": "#C99A3D",
        "risk-low": "#4A9C7C",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "SF Mono", "monospace"],
      },
    },
  },
  plugins: [],
};