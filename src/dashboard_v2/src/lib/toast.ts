import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
	id: string;
	message: string;
	type: ToastType;
	duration: number;
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	/** Timer for the current head toast. One active timer at a time. */
	let timerId: ReturnType<typeof setTimeout> | null = null;

	function startTimer(toast: Toast) {
		timerId = setTimeout(() => {
			timerId = null;
			// Dismiss head and start timer for next toast in queue
			let nextHead: Toast | undefined;
			update((queue) => {
				const next = queue.slice(1);
				nextHead = next[0];
				return next;
			});
			if (nextHead) startTimer(nextHead);
		}, toast.duration);
	}

	function showToast(message: string, type: ToastType = 'info', duration = 1800): void {
		const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
		const toast: Toast = { id, message, type, duration };

		let wasEmpty = false;
		update((queue) => {
			wasEmpty = queue.length === 0;
			return [...queue, toast];
		});

		// Start timer only when this toast becomes the head of an empty queue.
		// Queued toasts get their timers started when they reach the front.
		if (wasEmpty) startTimer(toast);
	}

	function dismissToast(id: string): void {
		let headDismissed = false;
		let nextHead: Toast | undefined;

		update((queue) => {
			const idx = queue.findIndex((t) => t.id === id);
			if (idx === -1) return queue;

			headDismissed = idx === 0;
			const newQueue = queue.filter((t) => t.id !== id);
			if (headDismissed) nextHead = newQueue[0];
			return newQueue;
		});

		if (headDismissed) {
			// Cancel the running timer (no orphaned fire) and start the next one
			if (timerId !== null) {
				clearTimeout(timerId);
				timerId = null;
			}
			if (nextHead) startTimer(nextHead);
		}
	}

	return { subscribe, showToast, dismissToast };
}

export const toastStore = createToastStore();

/** Convenience alias — callers import `showToast` directly. */
export const showToast = toastStore.showToast;
export const dismissToast = toastStore.dismissToast;
