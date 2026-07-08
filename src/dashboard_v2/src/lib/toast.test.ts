import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import { toastStore, showToast, dismissToast } from '$lib/toast.js';

describe('toast store', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		// Drain any leftover toasts from previous tests
		const current = get(toastStore);
		current.forEach((t) => dismissToast(t.id));
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('adds a toast to the queue', () => {
		showToast('Memory copied');
		expect(get(toastStore)).toHaveLength(1);
		expect(get(toastStore)[0].message).toBe('Memory copied');
	});

	it('defaults to type "info"', () => {
		showToast('Hello');
		expect(get(toastStore)[0].type).toBe('info');
	});

	it('respects explicit type', () => {
		showToast('Saved', 'success');
		expect(get(toastStore)[0].type).toBe('success');
	});

	it('auto-dismisses after duration', () => {
		showToast('Auto gone', 'info', 1800);
		expect(get(toastStore)).toHaveLength(1);

		vi.advanceTimersByTime(1800);
		expect(get(toastStore)).toHaveLength(0);
	});

	it('does not dismiss before duration elapses', () => {
		showToast('Still here', 'info', 1800);
		vi.advanceTimersByTime(1799);
		expect(get(toastStore)).toHaveLength(1);
	});

	it('dismissToast removes a specific toast by id', () => {
		showToast('A');
		showToast('B');
		const [first] = get(toastStore);
		dismissToast(first.id);
		const remaining = get(toastStore);
		expect(remaining).toHaveLength(1);
		expect(remaining[0].message).toBe('B');
	});

	it('queues multiple toasts in insertion order', () => {
		showToast('First');
		showToast('Second');
		showToast('Third');
		const messages = get(toastStore).map((t) => t.message);
		expect(messages).toEqual(['First', 'Second', 'Third']);
	});

	it('revealing next toast: after first auto-dismisses, second is at head', () => {
		showToast('Toast 1', 'info', 1000);
		showToast('Toast 2', 'info', 2000);

		vi.advanceTimersByTime(1000);
		const remaining = get(toastStore);
		expect(remaining[0].message).toBe('Toast 2');
	});

	it('each toast gets a unique id', () => {
		showToast('A');
		showToast('B');
		const [a, b] = get(toastStore);
		expect(a.id).not.toBe(b.id);
	});
});
