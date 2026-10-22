import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--canvas)',
        surface: 'var(--surface)',
        border: 'var(--border)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        primary: 'var(--primary)',
        'primary-hover': 'var(--primary-hover)',
        success: 'var(--success)',
        warning: 'var(--warning)',
        danger: 'var(--danger)',
      },
      borderRadius: { control: 'var(--radius-control)' },
      maxWidth: { form: '48rem' },
    },
  },
  plugins: [],
} satisfies Config;
