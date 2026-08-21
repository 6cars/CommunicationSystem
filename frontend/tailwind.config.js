/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f3f6fb",
        ink: "#1c2738",
        muted: "#64748b",
        bubble: {
          user: "#2563eb",
          agent: "#e8eef6",
        },
      },
      boxShadow: {
        panel: "0 20px 50px -24px rgba(28, 39, 56, 0.35)",
      },
    },
  },
  plugins: [],
};
