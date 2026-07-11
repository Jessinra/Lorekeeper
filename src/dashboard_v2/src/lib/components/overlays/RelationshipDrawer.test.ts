import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import RelationshipDrawer from './RelationshipDrawer.svelte';
import { RELATION_DRAWER_STRINGS as S } from '$lib/constants/strings';

function makeMemory(overrides: Record<string, unknown> = {}) {
	return {
		lore_id: 'mem-1',
		title: 'Test Memory',
		description: 'A test memory for testing',
		content: 'This is some sample content for the test memory card.',
		namespace: 'user',
		source_type: 'observed',
		score: 8,
		confidence: 7,
		usage_count: 5,
		soft_deleted: false,
		created_at: '2026-06-01T00:00:00Z',
		updated_at: '2026-06-15T00:00:00Z',
		...overrides,
	};
}

function baseProps(overrides: Record<string, unknown> = {}) {
	return {
		open: true,
		sourceMemory: makeMemory({ lore_id: 'mem-1', title: 'Source Memory' }),
		targetMemory: makeMemory({ lore_id: 'mem-2', title: 'Target Memory', namespace: 'code' }),
		relationType: 'references',
		linkId: 'link-1',
		suggestionId: null,
		page: 'links' as const,
		onClose: vi.fn(),
		onNavigate: vi.fn(),
		onDelete: vi.fn().mockResolvedValue(true),
		onAccept: vi.fn().mockResolvedValue(true),
		onReject: vi.fn().mockResolvedValue(true),
		onRefresh: vi.fn().mockResolvedValue(true),
		...overrides,
	};
}

describe('RelationshipDrawer', () => {
	describe('render states', () => {
		it('renders when open', () => {
			const { getByRole } = render(RelationshipDrawer, { props: baseProps() });
			const dialog = getByRole('dialog');
			expect(dialog).toBeInTheDocument();
			expect(dialog).toHaveAttribute('aria-modal', 'true');
		});

		it('does not render when open is false', () => {
			const { queryByRole } = render(RelationshipDrawer, {
				props: baseProps({ open: false }),
			});
			expect(queryByRole('dialog')).not.toBeInTheDocument();
		});
	});

	describe('header', () => {
		it('shows Relationship title', () => {
			const { getByText } = render(RelationshipDrawer, { props: baseProps() });
			expect(getByText(S.drawerAriaLabel)).toBeInTheDocument();
		});

		it('shows subtitle with source → target', () => {
			const { getByText } = render(RelationshipDrawer, { props: baseProps() });
			expect(getByText(/Source Memory.*Target Memory/)).toBeInTheDocument();
		});

		it('shows close button with aria-label', () => {
			const { getByLabelText } = render(RelationshipDrawer, { props: baseProps() });
			expect(getByLabelText(S.closeButtonAriaLabel)).toBeInTheDocument();
		});
	});

	describe('memory cards', () => {
		it('renders both memory card titles', () => {
			const { getByText } = render(RelationshipDrawer, { props: baseProps() });
			expect(getByText('Source Memory')).toBeInTheDocument();
			expect(getByText('Target Memory')).toBeInTheDocument();
		});

		it('renders content preview on both cards', () => {
			const { getAllByText } = render(RelationshipDrawer, { props: baseProps() });
			const snippets = getAllByText(/sample content/);
			expect(snippets.length).toBe(2);
		});

		it('shows "No description" when description is empty', () => {
			const { getAllByText } = render(RelationshipDrawer, {
				props: baseProps({
					sourceMemory: makeMemory({ title: 'Src', description: '' }),
				}),
			});
			expect(getAllByText(S.noDescription).length).toBeGreaterThanOrEqual(1);
		});

		it('shows "No content" placeholder when content is empty', () => {
			const { getAllByText } = render(RelationshipDrawer, {
				props: baseProps({
					sourceMemory: makeMemory({ title: 'Src', content: '' }),
				}),
			});
			expect(getAllByText(S.noContent).length).toBeGreaterThanOrEqual(1);
		});

		it('shows strikethrough title and deleted badge for soft-deleted memory', () => {
			const { getByText, container } = render(RelationshipDrawer, {
				props: baseProps({
					sourceMemory: makeMemory({
						title: 'Deleted Mem',
						soft_deleted: true,
					}),
				}),
			});
			const visibleBadges = container.querySelectorAll('.card-badge.visible');
			expect(visibleBadges.length).toBe(1);
			const title = getByText('Deleted Mem');
			expect(container.querySelector('.strikethrough')).toBeInTheDocument();
		});

		it('renders score values for both memories', () => {
			const { getAllByText } = render(RelationshipDrawer, { props: baseProps() });
			// ScorePill shows the numeric score; 8 is the score for both memories
			expect(getAllByText('8').length).toBeGreaterThanOrEqual(2);
		});
	});

	describe('relation center', () => {
		it('renders RelationPill with correct label', () => {
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ relationType: 'depends_on' }),
			});
			expect(getByText('Depends On')).toBeInTheDocument();
		});

		it('shows → for directed relations', () => {
			const { container } = render(RelationshipDrawer, {
				props: baseProps({ relationType: 'references' }),
			});
			expect(container.querySelector('.direction-arrow')?.textContent).toBe('→');
		});

		it('shows ↔ for symmetric relations', () => {
			const { container } = render(RelationshipDrawer, {
				props: baseProps({ relationType: 'conflicts_with' }),
			});
			expect(container.querySelector('.direction-arrow')?.textContent).toBe('↔');
		});
	});

	describe('navigation', () => {
		it('calls onClose then onNavigate when clicking source card', async () => {
			const onClose = vi.fn();
			const onNavigate = vi.fn();
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ onClose, onNavigate }),
			});
			await fireEvent.click(getByText('Source Memory'));
			expect(onClose).toHaveBeenCalledOnce();
			expect(onNavigate).toHaveBeenCalledWith('mem-1');
		});

		it('calls onClose then onNavigate when clicking target card', async () => {
			const onClose = vi.fn();
			const onNavigate = vi.fn();
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ onClose, onNavigate }),
			});
			await fireEvent.click(getByText('Target Memory'));
			expect(onClose).toHaveBeenCalledOnce();
			expect(onNavigate).toHaveBeenCalledWith('mem-2');
		});
	});

	describe('dismissal', () => {
		it('closes on scrim click', async () => {
			const onClose = vi.fn();
			const { container } = render(RelationshipDrawer, {
				props: baseProps({ onClose }),
			});
			const scrim = container.querySelector('.scrim');
			expect(scrim).not.toBeNull();
			await fireEvent.click(scrim!);
			expect(onClose).toHaveBeenCalledOnce();
		});

		it('closes on Escape key', async () => {
			const onClose = vi.fn();
			const { getByRole } = render(RelationshipDrawer, {
				props: baseProps({ onClose }),
			});
			const dialog = getByRole('dialog');
			await fireEvent.keyDown(dialog, { key: 'Escape' });
			expect(onClose).toHaveBeenCalledOnce();
		});

		it('closes on close button click', async () => {
			const onClose = vi.fn();
			const { getByLabelText } = render(RelationshipDrawer, {
				props: baseProps({ onClose }),
			});
			await fireEvent.click(getByLabelText(S.closeButtonAriaLabel));
			expect(onClose).toHaveBeenCalledOnce();
		});
	});

	describe('page: links footer', () => {
		it('shows Delete link button', () => {
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ page: 'links' }),
			});
			expect(getByText(S.deleteLink)).toBeInTheDocument();
		});

		it('shows confirmation before calling onDelete', async () => {
			const onDelete = vi.fn().mockResolvedValue(true);
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ page: 'links', onDelete }),
			});
			await fireEvent.click(getByText(S.deleteLink));
			expect(onDelete).not.toHaveBeenCalled();
			expect(getByText(S.deleteConfirm)).toBeInTheDocument();

			await fireEvent.click(getByText(S.deleteConfirm));
			expect(onDelete).toHaveBeenCalledWith('link-1');
		});

		it('Cancel button exits confirmation mode', async () => {
			const onDelete = vi.fn();
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ page: 'links', onDelete }),
			});
			await fireEvent.click(getByText(S.deleteLink));
			expect(getByText(S.deleteConfirm)).toBeInTheDocument();

			await fireEvent.click(getByText('Cancel'));
			expect(getByText(S.deleteLink)).toBeInTheDocument();
		});
	});

	describe('page: review-suggestions footer', () => {
		it('shows Accept and Reject buttons', () => {
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({
					page: 'review-suggestions',
					suggestionId: 'sug-1',
				}),
			});
			expect(getByText(S.accept)).toBeInTheDocument();
			expect(getByText(S.reject)).toBeInTheDocument();
		});

		it('calls onAccept on accept click', async () => {
			const onAccept = vi.fn().mockResolvedValue(true);
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({
					page: 'review-suggestions',
					suggestionId: 'sug-1',
					onAccept,
				}),
			});
			await fireEvent.click(getByText(S.accept));
			expect(onAccept).toHaveBeenCalledWith('sug-1');
		});

		it('calls onReject on reject click', async () => {
			const onReject = vi.fn().mockResolvedValue(true);
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({
					page: 'review-suggestions',
					suggestionId: 'sug-1',
					onReject,
				}),
			});
			await fireEvent.click(getByText(S.reject));
			expect(onReject).toHaveBeenCalledWith('sug-1');
		});
	});

	describe('page: review-stale footer', () => {
		it('shows Refresh and Delete link buttons', () => {
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ page: 'review-stale' }),
			});
			expect(getByText(S.refresh)).toBeInTheDocument();
			expect(getByText(S.deleteLink)).toBeInTheDocument();
		});

		it('calls onRefresh when Refresh clicked', async () => {
			const onRefresh = vi.fn().mockResolvedValue(true);
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({ page: 'review-stale', onRefresh }),
			});
			await fireEvent.click(getByText(S.refresh));
			expect(onRefresh).toHaveBeenCalledWith('link-1');
		});
	});

	describe('loading state', () => {
		it('shows loading message when both memories are null', () => {
			const { getByText } = render(RelationshipDrawer, {
				props: baseProps({
					sourceMemory: null,
					targetMemory: null,
				}),
			});
			expect(getByText(S.loading)).toBeInTheDocument();
		});
	});
});