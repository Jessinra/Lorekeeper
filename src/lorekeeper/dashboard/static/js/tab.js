// ── Tab switching ──
import * as state from './state.js';

export const TAB_ORDER = ['memories', 'detail', 'links', 'query', 'sessions', 'config', 'backup', 'metrics'];

// Cross-module callbacks — wired up by app.js after all modules are imported.
export let _onTabLinks    = () => {};
export let _onTabConfig   = () => {};
export let _onTabSessions = () => {};
export let _onTabMetrics  = () => {};

export function registerTabCallbacks({ onTabLinks, onTabConfig, onTabSessions, onTabMetrics }) {
  _onTabLinks    = onTabLinks;
  _onTabConfig   = onTabConfig;
  _onTabSessions = onTabSessions;
  _onTabMetrics  = onTabMetrics ?? (() => {});
}

export function switchTab(name) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', TAB_ORDER[i] === name));
  document.getElementById('tab-' + name).classList.add('active');
  if (name === 'links'   && !state.linksLoaded) _onTabLinks();
  if (name === 'config')  _onTabConfig();
  if (name === 'sessions') _onTabSessions();
  if (name === 'metrics')  _onTabMetrics();
}

window.switchTab = switchTab;
