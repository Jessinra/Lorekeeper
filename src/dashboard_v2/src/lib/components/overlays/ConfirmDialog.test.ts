import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import ConfirmDialog from '$lib/components/overlays/ConfirmDialog.svelte';

const baseProps = {
	open: true,
	title: 'Delete memory',
	message: 'This cannot be undone.',
	onConfirm: vi.fn(),
	onCancel: vi.fn()
};

describe('ConfirmDialog', () => {
	it('renders title and message when open', () => {
		const { getByText } = render(ConfirmDialog, { props: baseProps });
		expect(getByText('Delete memory')).toBeInTheDocument();
		expect(getByText('This cannot be undone.')).toBeInTheDocument();
	});

	it('does not render when open is false', () => {
		const { queryByRole } = render(ConfirmDialog, {
			props: { ...baseProps, open: false }
		});
		expect(queryByRole('dialog')).not.toBeInTheDocument();
	});

	it('calls onConfirm when Confirm button clicked', async () => {
		const onConfirm = vi.fn();
		const { getByText } = render(ConfirmDialog, {
			props: { ...baseProps, onConfirm }
		});
		await fireEvent.click(getByText('Delete'));
		expect(onConfirm).toHaveBeenCalledOnce();
	});

	it('calls onCancel when Cancel button clicked', async () => {
		const onCancel = vi.fn();
		const { getByText } = render(ConfirmDialog, {
			props: { ...baseProps, onCancel }
		});
		await fireEvent.click(getByText('Cancel'));
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('calls onCancel when scrim is clicked', async () => {
		const onCancel = vi.fn();
		const { container } = render(ConfirmDialog, {
			props: { ...baseProps, onCancel }
		});
		const scrim = container.querySelector('.scrim');
		expect(scrim).not.toBeNull();
		await fireEvent.click(scrim!);
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('calls onCancel on Escape key', async () => {
		const onCancel = vi.fn();
		render(ConfirmDialog, { props: { ...baseProps, onCancel } });
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('renders custom confirmLabel', () => {
		const { getByText } = render(ConfirmDialog, {
			props: { ...baseProps, confirmLabel: 'Remove link' }
		});
		expect(getByText('Remove link')).toBeInTheDocument();
	});

	it('renders itemName chip when provided', () => {
		const { getByText } = render(ConfirmDialog, {
			props: { ...baseProps, itemName: 'NavRail bug fix — isActive prefix guard' }
		});
		expect(getByText('NavRail bug fix — isActive prefix guard')).toBeInTheDocument();
	});

	it('does not render chip when itemName is null', () => {
		const { container } = render(ConfirmDialog, {
			props: { ...baseProps, itemName: null }
		});
		expect(container.querySelector('.item-chip')).not.toBeInTheDocument();
	});

	it('has role="dialog" and aria-modal="true"', () => {
		const { getByRole } = render(ConfirmDialog, { props: baseProps });
		const dialog = getByRole('dialog');
		expect(dialog).toHaveAttribute('aria-modal', 'true');
	});

	it('confirm button has .danger class when severity="destructive"', () => {
		const { container } = render(ConfirmDialog, {
			props: { ...baseProps, severity: 'destructive' }
		});
		expect(container.querySelector('.btn-confirm.danger')).toBeInTheDocument();
	});

	it('confirm button lacks .danger class when severity="neutral"', () => {
		const { container } = render(ConfirmDialog, {
			props: { ...baseProps, severity: 'neutral' }
		});
		expect(container.querySelector('.btn-confirm.danger')).not.toBeInTheDocument();
	});
});
