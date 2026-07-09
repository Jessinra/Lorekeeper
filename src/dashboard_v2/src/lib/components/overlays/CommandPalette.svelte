<script lang="ts">
	import { tick } from 'svelte';
	import { onMount } from 'svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';
	import { filterCommands, GROUP_LABELS, GROUP_ORDER } from '$lib/commands.js';
	import type { Command } from '$lib/commands.js';
	import { ICON_SEARCH } from '$lib/constants/icons.js';
	import { PALETTE_STRINGS } from '$lib/constants/strings.js';

	// ─── Props ────────────────────────────────────────────────────────────────
	// Commands are built and injected by the parent (AppShell) — this component
	// is pure UI: filter, render, navigate with keyboard, emit selection.
	interface Props {
		open: boolean;
		commands: Command[];
		onClose: () => void;
	}

	let { open, commands, onClose }: Props = $props();

	// ─── State ────────────────────────────────────────────────────────────────
	let query = $state('');
	let activeIndex = $state(0);
	let inputEl: HTMLInputElement | null = $state(null);
	let listEl: HTMLUListElement | null = $state(null);

	// ─── Filtered + grouped view ──────────────────────────────────────────────
	let filtered = $derived(filterCommands(commands, query));

	type RenderItem =
		| { kind: 'header'; group: string; label: string }
		| { kind: 'command'; command: Command; flatIndex: number };

	let renderItems = $derived.by(() => {
		const items: RenderItem[] = [];
		let flatIndex = 0;
		for (const group of GROUP_ORDER) {
			const cmds = filtered.filter((c) => c.group === group);
			if (cmds.length === 0) continue;
			items.push({ kind: 'header', group, label: GROUP_LABELS[group] });
			for (const command of cmds) {
				items.push({ kind: 'command', command, flatIndex });
				flatIndex++;
			}
		}
		return items;
	});

	// Command-only list following the same group order as renderItems.
	// Arrow nav, Enter selection, and aria-activedescendant all index into this
	// so keyboard focus and the rendered UI are always aligned — even once the
	// 'recent' group is populated or GROUP_ORDER changes.
	let flatCommands = $derived(
		renderItems
			.filter((item): item is { kind: 'command'; command: Command; flatIndex: number } => item.kind === 'command')
			.map((item) => item.command)
	);

	let commandCount = $derived(flatCommands.length);

	// ─── Focus & reset on open ────────────────────────────────────────────────
	$effect(() => {
		if (open) {
			query = '';
			activeIndex = 0;
			tick().then(() => inputEl?.focus());
		}
	});

	// ─── Reset active index when query changes ────────────────────────────────
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		query; // reactive dependency
		activeIndex = 0;
	});

	// ─── Keyboard nav inside palette ─────────────────────────────────────────
	function handleKeydown(e: KeyboardEvent) {
		if (!open) return;

		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				activeIndex = (activeIndex + 1) % Math.max(commandCount, 1);
				scrollActiveIntoView();
				break;

			case 'ArrowUp':
				e.preventDefault();
				activeIndex = (activeIndex - 1 + Math.max(commandCount, 1)) % Math.max(commandCount, 1);
				scrollActiveIntoView();
				break;

			case 'Enter': {
				e.preventDefault();
				const active = flatCommands[activeIndex];
				if (active) {
					active.action();
					onClose();
				}
				break;
			}

			case 'Escape':
				e.preventDefault();
				onClose();
				break;
		}
	}

	function scrollActiveIntoView() {
		tick().then(() => {
			const active = listEl?.querySelector<HTMLLIElement>('[data-active="true"]');
			active?.scrollIntoView({ block: 'nearest' });
		});
	}

	// ─── Select on click ──────────────────────────────────────────────────────
	function select(cmd: Command) {
		cmd.action();
		onClose();
	}

	onMount(() => {
		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
	});
</script>

{#if open}
	<OverlayScrim onclick={onClose} />

	<div
		class="palette-card"
		role="dialog"
		aria-modal="true"
		aria-label={PALETTE_STRINGS.dialogAriaLabel}
	>
		<!-- Search input -->
		<div class="palette-input-row">
			<span class="search-icon" aria-hidden="true">
				<Icon path={ICON_SEARCH} size={16} strokeWidth={2} />
			</span>

			<input
				bind:this={inputEl}
				bind:value={query}
				class="palette-input"
				type="text"
				placeholder={PALETTE_STRINGS.inputPlaceholder}
				autocomplete="off"
				spellcheck="false"
				aria-autocomplete="list"
				aria-controls="palette-results"
				aria-activedescendant={flatCommands[activeIndex]
					? `palette-cmd-${flatCommands[activeIndex].id}`
					: undefined}
			/>

			<button
				class="close-btn"
				type="button"
				aria-label={PALETTE_STRINGS.closeButtonAriaLabel}
				onclick={onClose}
			>
				<kbd>Esc</kbd>
			</button>
		</div>

		<!-- Divider -->
		<div class="palette-divider" aria-hidden="true"></div>

		<!-- Results list -->
		<ul
			bind:this={listEl}
			class="palette-results"
			id="palette-results"
			role="listbox"
			aria-label={PALETTE_STRINGS.resultsListAriaLabel}
		>
			{#each renderItems as item (item.kind === 'header' ? `header-${item.group}` : item.command.id)}
				{#if item.kind === 'header'}
					<li class="group-header" role="presentation">{item.label}</li>
				{:else}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<li
						id="palette-cmd-{item.command.id}"
						class="palette-item"
						class:active={item.flatIndex === activeIndex}
						data-active={item.flatIndex === activeIndex ? 'true' : 'false'}
						role="option"
						aria-selected={item.flatIndex === activeIndex}
						onmouseenter={() => (activeIndex = item.flatIndex)}
						onclick={() => select(item.command)}
					>
						{#if item.command.icon}
							<span class="cmd-icon">
								<Icon path={item.command.icon} size={16} strokeWidth={2} />
							</span>
						{/if}
						<span class="cmd-label">{item.command.label}</span>
						{#if item.command.hint}
							<span class="cmd-hint">{item.command.hint}</span>
						{/if}
					</li>
				{/if}
			{:else}
				<li class="empty-state">
					{PALETTE_STRINGS.emptyStatePreamble} "<strong>{query}</strong>"
				</li>
			{/each}
		</ul>

		<!-- Footer hint -->
		<div class="palette-footer" aria-hidden="true">
			<span class="hint-group">
				<kbd>↑</kbd><kbd>↓</kbd> {PALETTE_STRINGS.footerNavigate}
			</span>
			<span class="hint-group">
				<kbd>↵</kbd> {PALETTE_STRINGS.footerSelect}
			</span>
			<span class="hint-group">
				<kbd>Esc</kbd> {PALETTE_STRINGS.footerClose}
			</span>
		</div>
	</div>
{/if}

<style>
	/* ── Card ─────────────────────────────────────────────────────────────── */
	.palette-card {
		position: fixed;
		top: 20vh;
		left: 50%;
		transform: translateX(-50%);
		z-index: 810;

		width: min(640px, calc(100vw - 32px));
		max-height: 480px;
		display: flex;
		flex-direction: column;

		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-card);
		box-shadow:
			0 4px 6px -1px var(--color-shadow-lg),
			0 24px 48px -8px var(--color-shadow-xl);

		animation: palette-in 160ms ease forwards;
		overflow: hidden;
	}

	@keyframes palette-in {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(-6px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0) scale(1);
		}
	}

	/* ── Input row ────────────────────────────────────────────────────────── */
	.palette-input-row {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 14px 16px;
		flex-shrink: 0;
	}

	.search-icon {
		color: var(--color-text-faint);
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	.palette-input {
		flex: 1;
		border: none;
		outline: none;
		background: transparent;
		font-size: 15px;
		color: var(--color-text-primary);
		caret-color: var(--color-brand);
	}

	.palette-input::placeholder {
		color: var(--color-text-faint);
	}

	.close-btn {
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;
		line-height: 1;
	}

	.close-btn kbd {
		background: var(--color-hover-bg);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-kbd);
		font-size: var(--font-size-label);
		padding: var(--space-kbd-pad);
		color: var(--color-text-muted);
		font-family: inherit;
	}

	/* ── Divider ──────────────────────────────────────────────────────────── */
	.palette-divider {
		height: var(--border-width);
		background: var(--color-border);
		flex-shrink: 0;
	}

	/* ── Results list ─────────────────────────────────────────────────────── */
	.palette-results {
		list-style: none;
		margin: 0;
		padding: 6px 0;
		overflow-y: auto;
		flex: 1;
		min-height: 0;
	}

	.group-header {
		padding: 8px 16px 4px;
		font-size: var(--font-size-label);
		font-weight: 600;
		color: var(--color-text-faint);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		user-select: none;
	}

	.palette-item {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 16px;
		cursor: pointer;
		border-radius: 0;
		transition: background 80ms ease;
		color: var(--color-text-body);
	}

	.palette-item.active,
	.palette-item:hover {
		background: var(--color-hover-bg);
	}

	.cmd-icon {
		color: var(--color-text-muted);
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	.cmd-label {
		flex: 1;
		font-size: var(--font-size-body);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.cmd-hint {
		font-size: var(--font-size-label);
		color: var(--color-text-faint);
		flex-shrink: 0;
	}

	.empty-state {
		padding: 20px 16px;
		color: var(--color-text-faint);
		font-size: var(--font-size-body);
		text-align: center;
	}

	.empty-state strong {
		color: var(--color-text-body);
	}

	/* ── Footer ───────────────────────────────────────────────────────────── */
	.palette-footer {
		display: flex;
		gap: 16px;
		padding: 8px 16px;
		border-top: var(--border-width) solid var(--color-border);
		background: var(--color-background);
		flex-shrink: 0;
	}

	.hint-group {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: var(--font-size-label);
		color: var(--color-text-faint);
	}

	kbd {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-kbd);
		font-size: var(--font-size-label);
		padding: var(--space-kbd-pad);
		color: var(--color-text-muted);
		font-family: inherit;
	}
</style>
