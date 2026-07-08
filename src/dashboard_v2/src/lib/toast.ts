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

	function showToast(message: string, type: ToastType = 'info', duration = 1800): void {
		const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
		const toast: Toast = { id, message, type, duration };

		update((queue) => [...queue, toast]);

		setTimeout(() => {
			dismissToast(id);
		}, duration);
	}

	function dismissToast(id: string): void {
		update((queue) => queue.filter((t) => t.id !== id));
	}

	return { subscribe, showToast, dismissToast };
}

export const toastStore = createToastStore();

/** Convenience alias — callers import `showToast` directly. */
export const showToast = toastStore.showToast;
export const dismissToast = toastStore.dismissToast;
