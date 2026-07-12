// @ts-check
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import sveltePlugin from 'eslint-plugin-svelte';
import svelteParser from 'svelte-eslint-parser';

export default tseslint.config(
	// Global ignores
	{
		ignores: [
			'node_modules/',
			'.svelte-kit/',
			'build/',
			'.vite/',
			'**/*.test.ts',
			'eslint.config.js',
		],
	},

	// Base recommended rules (no type info needed)
	eslint.configs.recommended,
	...tseslint.configs.recommended,

	// Svelte plugin config
	...sveltePlugin.configs['flat/recommended'],
	{
		files: ['**/*.svelte'],
		languageOptions: {
			parser: svelteParser,
			parserOptions: {
				parser: tseslint.parser,
				extraFileExtensions: ['.svelte'],
			},
		},
		rules: {
			'no-undef': 'off',

			// Trusted SVG icons from constants, never user input
			'svelte/no-at-html-tags': 'off',

			// Static SvelteKit site — no resolve() needed for client-side nav
			'svelte/no-navigation-without-resolve': 'off',

			'@typescript-eslint/no-unused-vars': [
				'warn',
				{
					args: 'after-used',
					argsIgnorePattern: '^_',
					varsIgnorePattern: '^_',
					destructuredArrayIgnorePattern: '^_',
				},
			],
		},
	},
);