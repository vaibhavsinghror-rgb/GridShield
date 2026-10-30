/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        grid: {
          900: "#0b0f19",
          800: "#111827",
          700: "#1f2937",
          600: "#374151",
          green: "#10b981",
          blue: "#3b82f6",
          amber: "#f59e0b",
          rose: "#f43f5e",
        }
      }
    },
  },
  plugins: [],
}
