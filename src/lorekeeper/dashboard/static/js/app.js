// ── Entry point ──
// Imports all modules, wires cross-module callbacks, then initialises the app.

import './api.js';
import './utils.js';
import * as state    from './state.js';
import { switchTab, registerTabCallbacks } from './tab.js';
import {
  loadMemories, renderList, updateSortHeaders,
  onFilterInput, clearFilter, toggleShowDeleted, setMemSort, updateHeaderMeta,
  registerSelectMemory,
} from './memories.js';
import {
  selectMemory, registerDetailCallbacks,
} from './detail.js';
import {
  loadLinks, setLinkSort, deleteLinkFromTab,
  registerLinksSelectMemory,
} from './links.js';
import { runQuery, registerQuerySelectMemory } from './query.js';
import { loadConfig, saveConfig, onCfgChange } from './config.js';
import { loadRuns } from './runs.js';

// ── Wire cross-module callbacks to break circular deps ──

// tab.js needs to trigger loadLinks / loadConfig when switching tabs
registerTabCallbacks({
  onTabLinks:  loadLinks,
  onTabConfig: loadConfig,
  onTabRuns:   loadRuns,
});

// detail.js needs loadMemories, renderList, loadLinks
registerDetailCallbacks({
  loadMemories,
  renderList,
  loadLinks,
});

// links.js needs selectMemory
registerLinksSelectMemory(selectMemory);

// query.js needs selectMemory
registerQuerySelectMemory(selectMemory);

// memories.js renderList calls selectMemory via window.selectMemory (already set
// in detail.js window assignments), but we also register it for any internal use.
registerSelectMemory(selectMemory);

// ── Init ──

function init() {
  // Keyboard shortcuts
  document.getElementById('q-text').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) runQuery();
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') clearFilter();
    if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      const tab = document.getElementById('tab-memories');
      if (tab.classList.contains('active')) {
        e.preventDefault();
        document.getElementById('mem-filter').focus();
      }
    }
  });

  // Bootstrap the memories tab sort headers and load data
  updateSortHeaders('th-', state.memSort, ['title', 'score', 'confidence', 'usage_count', 'link_count', 'updated_at']);
  loadMemories();
}

init();
