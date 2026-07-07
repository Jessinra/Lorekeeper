// Design tokens from spec §8 — kept as AC stub.
// Primary token source is @theme in src/app.css (Tailwind v4 CSS-first).
import type { Config } from 'tailwindcss';

const config: Config = {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				background: '#f9f9fb',
				'text-primary': '#1a1a2e',
				'text-body': '#3f3f52',
				'text-muted': '#6b7280',
				'text-faint': '#9ca3af',
				border: '#e6e6ee',
				divider: '#eeeef3',
				brand: '#7c5cff',
				'brand-hover': '#6a46f5',
				'brand-tint': '#f1edff',
				'success-bg': '#ecfdf3',
				'success-text': '#16a34a',
				'warning-bg': '#fef6e7',
				'warning-text': '#d97706',
				'danger-bg': '#fef2f2',
				'danger-text': '#dc2626'
			},
			borderRadius: {
				card: '14px',
				control: '9px',
				pill: '999px'
			},
			fontSize: {
				body: '13px',
				micro: '11px'
			},
			fontFamily: {
				sans: ['-apple-system', '"Segoe UI"', 'system-ui', 'sans-serif']
			}
		}
	}
};

export default config;
