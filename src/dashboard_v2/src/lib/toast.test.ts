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

	// ── New tests covering sequential-timer and orphaned-timer fixes ──

	it('queued toasts each get their full duration — not starting early', () => {
		showToast('First', 'info', 1000);
		showToast('Second', 'info', 1000);

		// After 1 000 ms the first is dismissed and second becomes head
		vi.advanceTimersByTime(1000);
		expect(get(toastStore)).toHaveLength(1);
		expect(get(toastStore)[0].message).toBe('Second');

		// Second's 1 000 ms starts only AFTER first dismissed — so at 1 999 ms it is still visible
		vi.advanceTimersByTime(999);
		expect(get(toastStore)).toHaveLength(1);

		// At 2 000 ms total (1 000 for first + 1 000 for second) it finally dismisses
		vi.advanceTimersByTime(1);
		expect(get(toastStore)).toHaveLength(0);
	});

	it('three rapid toasts each shown for their full duration', () => {
		showToast('A', 'info', 500);
		showToast('B', 'info', 500);
		showToast('C', 'info', 500);

		vi.advanceTimersByTime(500);
		expect(get(toastStore)[0].message).toBe('B');

		vi.advanceTimersByTime(500);
		expect(get(toastStore)[0].message).toBe('C');

		vi.advanceTimersByTime(500);
		expect(get(toastStore)).toHaveLength(0);
	});

	it('manual dismiss cancels the running timer — no orphaned fire', () => {
		showToast('Quick', 'info', 1000);
		const [toast] = get(toastStore);

		// Dismiss manually at t=300
		vi.advanceTimersByTime(300);
		dismissToast(toast.id);
		expect(get(toastStore)).toHaveLength(0);

		// Timer was cancelled — still empty at t=1000
		vi.advanceTimersByTime(700);
		expect(get(toastStore)).toHaveLength(0);
	});

	it('manual dismiss of head starts timer for next toast', () => {
		showToast('First', 'info', 2000);
		showToast('Second', 'info', 1000);

		const [first] = get(toastStore);
		dismissToast(first.id);

		// Second now at head — should dismiss after 1 000 ms
		vi.advanceTimersByTime(999);
		expect(get(toastStore)).toHaveLength(1);

		vi.advanceTimersByTime(1);
		expect(get(toastStore)).toHaveLength(0);
	});
});
