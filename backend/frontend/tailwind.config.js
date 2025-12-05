/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#1f2937",
        surface: "#111827",
        primary: "#7c3aed",
        "primary-hover": "#6d28d9",
      },
    },
  },
  plugins: [],
}