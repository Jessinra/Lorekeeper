// ── Metrics tab ──
// Activity-box heatmap: rows = local date, columns = local hour (0–23).
// Fixed to last 7 days. Timezone is detected from the browser.

const TOOL_COLORS = {
  lore_search:             { h: 217, s: '90%' },
  lore_insert:             { h: 142, s: '65%' },
  lore_update:             { h:  38, s: '85%' },
  lore_reflect:            { h:   4, s: '75%' },
  lore_processed_sessions: { h: 262, s: '65%' },
};
const COMBINED_COLOR  = { h: 217, s: '85%' };
const DEFAULT_COLOR   = { h: 220, s: '20%' };
const EMPTY_BOX_COLOR = '#ebedf0';
const HOURS           = Array.from({ length: 24 }, (_, i) => i);
const HOURS_WINDOW    = 168; // fixed 7-day window

// Local TZ offset label (e.g. "GMT+8")
const _tzOffsetMin  = -new Date().getTimezoneOffset(); // e.g. +480 for SGT
const _tzOffsetHr   = _tzOffsetMin / 60;
const TZ_LABEL      = `GMT${_tzOffsetHr >= 0 ? '+' : ''}${_tzOffsetHr}`;

// ── Tooltip ───────────────────────────────────────────────────────────────────

let _tooltip = null;
function getTooltip() {
  if (!_tooltip) {
    _tooltip = document.createElement('div');
    _tooltip.className = 'activity-tooltip';
    _tooltip.style.display = 'none';
    document.body.appendChild(_tooltip);
  }
  return _tooltip;
}

function showTooltip(e, html) {
  const t = getTooltip();
  t.innerHTML = html;
  t.style.display = 'block';
  positionTooltip(e);
}

function positionTooltip(e) {
  const t = getTooltip();
  const x = e.clientX + 14;
  const y = e.clientY - 10;
  t.style.left = '-9999px'; // off-screen to measure
  t.style.top  = '0';
  requestAnimationFrame(() => {
    const w = t.offsetWidth;
    t.style.left = (x + w > window.innerWidth ? e.clientX - w - 14 : x) + 'px';
    t.style.top  = Math.max(4, y) + 'px';
  });
}

function hideTooltip() {
  getTooltip().style.display = 'none';
}

// ── UTC bucket → local date + hour ───────────────────────────────────────────

function utcBucketToLocal(bucket) {
  // bucket is always "YYYY-MM-DD HH:00" (UTC, space separator, hourly)
  const d = new Date(bucket.replace(' ', 'T') + ':00Z');
  const localDate = d.toLocaleDateString('en-CA'); // YYYY-MM-DD in local TZ
  const localHour = d.getHours();                  // 0–23 local
  return { localDate, localHour };
}

export async function loadMetrics() {
  const res = await fetch(`/api/metrics?hours=${HOURS_WINDOW}`);
  if (!res.ok) { console.error('metrics fetch failed', res.status); return; }
  renderMetrics(await res.json());
}

function renderMetrics({ buckets, tools, data }) {
  const wrap = document.getElementById('metrics-chart-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  updateSummary(buckets, tools, data);

  if (!buckets.length) {
    wrap.innerHTML = '<p class="metrics-empty">No API calls recorded yet.</p>';
    return;
  }

  // Aggregate into local TZ: grid[localDate][localHour][tool] = count
  const grid = {};
  for (const bucket of buckets) {
    const { localDate, localHour } = utcBucketToLocal(bucket);
    if (!grid[localDate]) grid[localDate] = {};
    if (!grid[localDate][localHour]) grid[localDate][localHour] = {};
    for (const tool of tools) {
      const c = data[bucket]?.[tool] ?? 0;
      if (c) grid[localDate][localHour][tool] = (grid[localDate][localHour][tool] ?? 0) + c;
    }
  }

  const dates = Object.keys(grid).sort();

  // Combined (all tools) — TZ label in card subtitle
  const section = makeCard(`API Activity — All tools`, TZ_LABEL);
  section.appendChild(buildGrid(dates, tools, grid, null));
  section.appendChild(makeLegend(COMBINED_COLOR));
  wrap.appendChild(section);

  // Per-tool grids
  if (tools.length > 1) {
    const perToolCard = makeCard('Per-tool breakdown');
    for (const tool of tools) {
      const label = document.createElement('div');
      label.className = 'activity-tool-label';
      const dot = document.createElement('span');
      dot.className = 'activity-tool-dot';
      const col = TOOL_COLORS[tool] ?? DEFAULT_COLOR;
      dot.style.background = `hsl(${col.h}, ${col.s}, 45%)`;
      label.appendChild(dot);
      label.appendChild(document.createTextNode(tool));
      perToolCard.appendChild(label);
      perToolCard.appendChild(buildGrid(dates, [tool], grid, tool));
    }
    wrap.appendChild(perToolCard);
  }
}

// ── Summary strip ─────────────────────────────────────────────────────────────

function updateSummary(buckets, tools, data) {
  const el = document.getElementById('metrics-total-inline');
  if (!el) return;
  let total = 0;
  for (const b of buckets) for (const t of tools) total += (data[b]?.[t] ?? 0);
  el.textContent = total > 0 ? `Total: ${total.toLocaleString()} calls.` : '';
}

// ── Activity grid ─────────────────────────────────────────────────────────────

function buildGrid(dates, tools, grid, singleTool) {
  const container = document.createElement('div');
  container.className = 'activity-grid-wrap';

  // Max count across all cells (for color scale)
  let maxCount = 1;
  for (const date of dates) {
    for (const hour of HOURS) {
      const sum = tools.reduce((a, t) => a + (grid[date]?.[hour]?.[t] ?? 0), 0);
      if (sum > maxCount) maxCount = sum;
    }
  }

  const col = singleTool ? (TOOL_COLORS[singleTool] ?? DEFAULT_COLOR) : COMBINED_COLOR;

  // ── Hour header row (labels at 00, 06, 12, 18) ──
  const headerWrap = document.createElement('div');
  headerWrap.className = 'activity-row-wrap';
  const headerSpacer = document.createElement('div');
  headerSpacer.className = 'activity-date-label'; // same width spacer
  headerWrap.appendChild(headerSpacer);
  const headerRow = document.createElement('div');
  headerRow.className = 'activity-row activity-header-row';
  for (const hour of HOURS) {
    const lbl = document.createElement('div');
    lbl.className = 'activity-col-label';
    lbl.textContent = hour % 6 === 0 ? String(hour).padStart(2, '0') : '';
    headerRow.appendChild(lbl);
  }
  headerWrap.appendChild(headerRow);
  container.appendChild(headerWrap);

  // ── One data row per local date ──
  for (const date of dates) {
    const rowWrap = document.createElement('div');
    rowWrap.className = 'activity-row-wrap';

    // Date label on the left
    const dateLbl = document.createElement('div');
    dateLbl.className = 'activity-date-label';
    dateLbl.textContent = date.slice(5); // MM-DD
    rowWrap.appendChild(dateLbl);

    const row = document.createElement('div');
    row.className = 'activity-row activity-data-row';

    for (const hour of HOURS) {
      const cell = grid[date]?.[hour] ?? {};
      const sum  = tools.reduce((a, t) => a + (cell[t] ?? 0), 0);

      const box = document.createElement('div');
      box.className = 'activity-box';

      if (sum === 0) {
        box.style.background = EMPTY_BOX_COLOR;
      } else {
        const intensity = Math.max(0.15, sum / maxCount);
        const l = Math.round(92 - intensity * 62); // 92% (lightest) → 30% (darkest)
        box.style.background = `hsl(${col.h}, ${col.s}, ${l}%)`;
      }

      // Tooltip
      const breakdown = tools
        .filter(t => (cell[t] ?? 0) > 0)
        .map(t => `<span class="tt-tool">${t}</span><span class="tt-count">${cell[t]}</span>`)
        .join('');
      const hourLabel = `${date} ${String(hour).padStart(2, '0')}:00 ${TZ_LABEL}`;

      box.addEventListener('mouseenter', e => {
        showTooltip(e, sum
          ? `<div class="tt-header">${hourLabel}</div><div class="tt-total">Total: <strong>${sum}</strong></div><div class="tt-breakdown">${breakdown}</div>`
          : `<div class="tt-header">${hourLabel}</div><div class="tt-empty">No calls</div>`
        );
      });
      box.addEventListener('mousemove', positionTooltip);
      box.addEventListener('mouseleave', hideTooltip);

      row.appendChild(box);
    }

    rowWrap.appendChild(row);
    container.appendChild(rowWrap);
  }

  // ── No date axis — date is shown in the hover tooltip ──

  return container;
}

// ── Legend ────────────────────────────────────────────────────────────────────

function makeLegend(col) {
  const wrap = document.createElement('div');
  wrap.className = 'activity-legend';

  const less = document.createElement('span');
  less.className = 'activity-legend-label';
  less.textContent = 'Fewer';
  wrap.appendChild(less);

  for (const intensity of [0, 0.2, 0.4, 0.65, 1.0]) {
    const box = document.createElement('div');
    box.className = 'activity-box activity-legend-box';
    box.style.background = intensity === 0
      ? EMPTY_BOX_COLOR
      : `hsl(${col.h}, ${col.s}, ${Math.round(92 - intensity * 62)}%)`;
    wrap.appendChild(box);
  }

  const more = document.createElement('span');
  more.className = 'activity-legend-label';
  more.textContent = 'More';
  wrap.appendChild(more);

  return wrap;
}

// ── DOM helpers ───────────────────────────────────────────────────────────────

function makeCard(title, tzLabel) {
  const card = document.createElement('div');
  card.className = 'metrics-card';
  const h = document.createElement('div');
  h.className = 'metrics-card-title';
  h.textContent = title;
  if (tzLabel) {
    const tz = document.createElement('span');
    tz.className = 'tz-label';
    tz.style.marginLeft = '6px';
    tz.style.textTransform = 'none';
    tz.style.letterSpacing = '0';
    tz.textContent = tzLabel;
    h.appendChild(tz);
  }
  card.appendChild(h);
  return card;
}
