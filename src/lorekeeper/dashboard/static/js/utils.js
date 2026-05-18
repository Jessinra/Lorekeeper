// ── Pure utility functions ── no state, no DOM side-effects ──

export function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function scoreClass(s) {
  if (s >= 6) return 'score-high';
  if (s >= 3) return 'score-mid';
  return 'score-low';
}

export function fmt2(n) { return (n ?? 0).toFixed(2); }

export function fmtDate(iso) {
  if (!iso) return '';
  // "2026-05-18T14:32:00Z" → "2026-05-18 14:32"
  const s = iso.replace('T', ' ');
  return s.slice(0, 16);
}

const _today = new Date().toISOString().slice(0, 10);
export function isToday(iso) { return (iso || '').slice(0, 10) === _today; }

export function clientSort(data, field, dir) {
  return [...data].sort((a, b) => {
    let av = a[field] ?? '', bv = b[field] ?? '';
    if (typeof av === 'string') { av = av.toLowerCase(); bv = String(bv).toLowerCase(); }
    if (av < bv) return dir === 'asc' ? -1 : 1;
    if (av > bv) return dir === 'asc' ?  1 : -1;
    return 0;
  });
}

// Expose on window for any inline onclick that may need it (none currently do,
// but kept for symmetry and future safety).
window.esc        = esc;
window.scoreClass = scoreClass;
window.fmt2       = fmt2;
window.fmtDate    = fmtDate;
window.isToday    = isToday;
window.clientSort = clientSort;
