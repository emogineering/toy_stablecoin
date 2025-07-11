/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        'neon-yellow': '#faff00',
        'neon-green': '#00ffb2',
        'neon-blue': '#00e0ff',
      },
      fontFamily: {
        futuristic: ["'Orbitron'", 'Arial', 'sans-serif'],
        main: ["'Inter'", 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

