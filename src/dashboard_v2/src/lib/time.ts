/**
 * Time formatting utilities.
 */

/**
 * Format an ISO datetime string as a human-readable relative time.
 *
 * Returns strings like "now", "5m ago", "3h ago", "2d ago", or a short date
 * for timestamps older than 7 days.
 *
 * @param iso - ISO 8601 datetime string
 * @returns Human-readable relative time string
 */
export function relativeTime(iso: string): string {
	const d = new Date(iso);
	const now = new Date();
	const diffMs = now.getTime() - d.getTime();
	const diffMin = Math.floor(diffMs / 60000);
	if (diffMin < 1) return 'now';
	if (diffMin < 60) return `${diffMin}m ago`;
	const diffHrs = Math.floor(diffMin / 60);
	if (diffHrs < 24) return `${diffHrs}h ago`;
	const diffDays = Math.floor(diffHrs / 24);
	if (diffDays < 7) return `${diffDays}d ago`;
	return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}