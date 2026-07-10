// ── ScorePill ──
export const SCORE_THRESHOLDS = [
	{ min: 7, color: 'var(--color-score-high)' },
	{ min: 5, color: 'var(--color-score-mid)' },
	{ min: 0, color: 'var(--color-score-low)' },
] as const;

export function scoreColor(score: number): string {
	for (const t of SCORE_THRESHOLDS) {
		if (score >= t.min) return t.color;
	}
	return SCORE_THRESHOLDS[SCORE_THRESHOLDS.length - 1].color;
}

// ── NamespaceDot ──
export const NAMESPACE_COLORS: Record<string, string> = {
	code: 'var(--color-ns-code)',
	user: 'var(--color-ns-user)',
	system: 'var(--color-ns-system)',
	project: 'var(--color-ns-project)',
	concept: 'var(--color-ns-concept)',
};

export const NAMESPACE_DEFAULT_COLOR = 'var(--color-ns-default)';

export function namespaceColor(namespace: string): string {
	return NAMESPACE_COLORS[namespace] ?? NAMESPACE_DEFAULT_COLOR;
}

// ── RelationPill ──
export interface RelationStyle {
	bg: string;
	text: string;
}

export const RELATION_STYLES: Record<string, RelationStyle> = {
	references: { bg: 'var(--color-rel-references-bg)', text: 'var(--color-rel-references-text)' },
	implements: { bg: 'var(--color-rel-implements-bg)', text: 'var(--color-rel-implements-text)' },
	depends_on: { bg: 'var(--color-rel-depends-on-bg)', text: 'var(--color-rel-depends-on-text)' },
	conflicts_with: { bg: 'var(--color-rel-conflicts-with-bg)', text: 'var(--color-rel-conflicts-with-text)' },
	part_of: { bg: 'var(--color-rel-part-of-bg)', text: 'var(--color-rel-part-of-text)' },
};

export const RELATION_FALLBACK_STYLE: RelationStyle = {
	bg: 'var(--color-rel-fallback-bg)',
	text: 'var(--color-rel-fallback-text)',
};

export function readableLabel(type: string): string {
	return type
		.split('_')
		.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
		.join(' ');
}

// ── ToggleSwitch ──
export const TOGGLE_DEFAULTS = {
	trackWidth: 36,
	trackHeight: 20,
	trackRadius: 10,
	thumbSize: 16,
	thumbOffset: 2,
	thumbTranslate: 16,
} as const;

// ── HealthRing ──
export const HEALTH_RING_DEFAULTS = {
	size: 60,
	strokeWidth: 6,
	color: 'var(--color-ring-fg)',
	labelFontSize: 14,
} as const;

// ── HeatmapGrid ──
export const HEATMAP_DEFAULTS = {
	cellSize: 14,
	gap: 2,
	labelFontSize: 11,
	colLabelHeight: 14,
	rowLabelWidth: 60,
	cellRadius: 2,
} as const;

export function defaultColorScale(value: number, max: number): string {
	if (value === 0) return 'var(--color-heatmap-zero)';
	const intensity = value / max;
	if (intensity > 0.66) return 'var(--color-brand)';
	if (intensity > 0.33) return 'var(--color-heatmap-mid)';
	return 'var(--color-heatmap-low)';
}