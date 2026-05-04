/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "rgb(var(--brand-navy) / <alpha-value>)",
          "navy-mid": "rgb(var(--brand-navy-mid) / <alpha-value>)",
          "navy-deep": "rgb(var(--brand-navy-deep) / <alpha-value>)",
          cyan: "rgb(var(--brand-cyan) / <alpha-value>)",
          "cyan-soft": "rgb(var(--brand-cyan-soft) / <alpha-value>)",
          teal: "rgb(var(--brand-teal) / <alpha-value>)",
        },
        canvas: "rgb(var(--canvas) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-2": "rgb(var(--surface-2) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        "ink-muted": "rgb(var(--ink-muted) / <alpha-value>)",
        "ink-subtle": "rgb(var(--ink-subtle) / <alpha-value>)",
        hairline: "rgb(var(--hairline) / <alpha-value>)",
        success: "rgb(var(--success) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",
        danger: "rgb(var(--danger) / <alpha-value>)",
      },
    },
  },
  plugins: [],
}

