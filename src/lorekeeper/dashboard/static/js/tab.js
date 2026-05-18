// ── Tab switching ──
import * as state from './state.js';

export const TAB_ORDER = ['memories', 'detail', 'links', 'query', 'runs', 'config'];

// Cross-module callbacks — wired up by app.js after all modules are imported.
export let _onTabLinks  = () => {};
export let _onTabConfig = () => {};
export let _onTabRuns   = () => {};

export function registerTabCallbacks({ onTabLinks, onTabConfig, onTabRuns }) {
  _onTabLinks  = onTabLinks;
  _onTabConfig = onTabConfig;
  _onTabRuns   = onTabRuns;
}

export function switchTab(name) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', TAB_ORDER[i] === name));
  document.getElementById('tab-' + name).classList.add('active');
  if (name === 'links' && !state.linksLoaded) _onTabLinks();
  if (name === 'config') _onTabConfig();
  if (name === 'runs')   _onTabRuns();
}

window.switchTab = switchTab;
