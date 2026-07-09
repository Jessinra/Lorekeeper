import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import EmptyState from '$lib/components/ui/EmptyState.svelte';

const ICON_SAMPLE = 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z';

describe('EmptyState', () => {
	it('renders icon and message', () => {
		const { container, getByText } = render(EmptyState, {
			props: { icon: ICON_SAMPLE, message: 'No results' }
		});
		expect(getByText('No results')).toBeInTheDocument();
		expect(container.querySelector('svg')).toBeInTheDocument();
	});

	it('renders description when provided', () => {
		const { getByText } = render(EmptyState, {
			props: { icon: ICON_SAMPLE, message: 'No results', description: 'Try adjusting your filter' }
		});
		expect(getByText('Try adjusting your filter')).toBeInTheDocument();
	});

	it('does not render description when omitted', () => {
		const { container } = render(EmptyState, {
			props: { icon: ICON_SAMPLE, message: 'No results' }
		});
		expect(container.querySelector('.description')).not.toBeInTheDocument();
	});

	it('has role="status"', () => {
		const { container } = render(EmptyState, {
			props: { icon: ICON_SAMPLE, message: 'No results' }
		});
		expect(container.querySelector('.empty-state')).toHaveAttribute('role', 'status');
	});
});