/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#020817',
          900: '#080f1f',
          800: '#0d1526',
          700: '#1a2540',
          600: '#263257',
        },
        indigo: {
          950: '#1a0533',
        },
        accent: {
          DEFAULT: '#6366f1',
          hover:   '#4f46e5',
          muted:   '#3730a3',
          glow:    'rgba(99,102,241,0.35)',
        },
        neon: {
          blue:   '#4f8ef7',
          indigo: '#7c6ef7',
          purple: '#a855f7',
          cyan:   '#22d3ee',
          green:  '#34d399',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        // Layered depth shadows
        card:       '0 4px 24px 0 rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.3)',
        'card-lg':  '0 8px 40px 0 rgba(0,0,0,0.55), 0 2px 4px rgba(0,0,0,0.35)',
        'card-xl':  '0 16px 60px 0 rgba(0,0,0,0.65), 0 4px 8px rgba(0,0,0,0.4)',
        // Glow shadows
        glow:       '0 0 20px rgba(99,102,241,0.25), 0 0 40px rgba(99,102,241,0.10)',
        'glow-sm':  '0 0 12px rgba(99,102,241,0.3)',
        'glow-lg':  '0 0 35px rgba(99,102,241,0.35), 0 0 70px rgba(99,102,241,0.15)',
        'glow-cyan':'0 0 20px rgba(34,211,238,0.25)',
        'glow-green':'0 0 20px rgba(52,211,153,0.25)',
        'glow-purple':'0 0 20px rgba(168,85,247,0.25)',
        // Inner glow
        'inner-glow':'inset 0 1px 0 rgba(255,255,255,0.06)',
      },
      animation: {
        // Existing
        'pulse-slow':    'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':       'fadeIn 0.4s ease-out both',
        'slide-in':      'slideIn 0.3s ease-out both',
        'slide-up':      'slideUp 0.4s ease-out both',
        // New premium animations
        'float':         'float 6s ease-in-out infinite',
        'float-slow':    'float 9s ease-in-out infinite',
        'gradient-shift':'gradientShift 8s ease infinite',
        'glow-pulse':    'glowPulse 2s ease-in-out infinite',
        'shimmer':       'shimmer 1.8s linear infinite',
        'scale-in':      'scaleIn 0.35s cubic-bezier(0.34,1.56,0.64,1) both',
        'slide-right':   'slideRight 0.3s ease-out both',
        'stagger-1':     'fadeIn 0.4s ease-out 0.05s both',
        'stagger-2':     'fadeIn 0.4s ease-out 0.1s both',
        'stagger-3':     'fadeIn 0.4s ease-out 0.15s both',
        'stagger-4':     'fadeIn 0.4s ease-out 0.20s both',
        'stagger-5':     'fadeIn 0.4s ease-out 0.25s both',
        'stagger-6':     'fadeIn 0.4s ease-out 0.30s both',
        'border-glow':   'borderGlow 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:       { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideIn:      { from: { opacity: 0, transform: 'translateX(-14px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
        slideUp:      { from: { opacity: 0, transform: 'translateY(20px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideRight:   { from: { opacity: 0, transform: 'translateX(20px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
        scaleIn:      { from: { opacity: 0, transform: 'scale(0.92)' }, to: { opacity: 1, transform: 'scale(1)' } },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-8px)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%':      { backgroundPosition: '100% 50%' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 12px rgba(99,102,241,0.2), 0 0 30px rgba(99,102,241,0.05)' },
          '50%':      { boxShadow: '0 0 24px rgba(99,102,241,0.45), 0 0 60px rgba(99,102,241,0.15)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        borderGlow: {
          '0%, 100%': { borderColor: 'rgba(99,102,241,0.2)' },
          '50%':      { borderColor: 'rgba(99,102,241,0.55)' },
        },
      },
      backgroundSize: {
        '300%': '300% 300%',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34,1.56,0.64,1)',
      },
    },
  },
  plugins: [],
}
