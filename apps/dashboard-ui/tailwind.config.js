/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        display: ['"Syne"', 'sans-serif'],
        body: ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        fabric: {
          bg:       '#080c10',
          surface:  '#0d1117',
          border:   '#1c2333',
          muted:    '#1e2a3a',
          text:     '#c9d1d9',
          dim:      '#586069',
          critical: '#ff3b30',
          high:     '#ff9500',
          medium:   '#ffd60a',
          low:      '#30d158',
          info:     '#636366',
          accent:   '#00e5ff',
          pulse:    '#0070f3',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan': 'scan 2s linear infinite',
        'fade-in': 'fadeIn 0.4s ease forwards',
        'slide-up': 'slideUp 0.3s ease forwards',
      },
      keyframes: {
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        fadeIn: {
          from: { opacity: 0 },
          to:   { opacity: 1 },
        },
        slideUp: {
          from: { opacity: 0, transform: 'translateY(8px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
