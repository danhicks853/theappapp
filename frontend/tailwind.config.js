/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#e6f1ff',
          100: '#cce3ff',
          200: '#99c7ff',
          300: '#66abff',
          400: '#3d8fff',
          500: '#1a73e8',
          600: '#0d5bbd',
          700: '#094791',
          800: '#0a2f5f',
          900: '#0a1f3d',
          950: '#050f1f',
        },
        slate: {
          850: '#1a202e',
          950: '#0f1419',
        }
      },
    },
  },
  plugins: [],
}
