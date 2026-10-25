// Executed in the Dashboard document; consumes only validated, public appearance data.
import { validateTheme, themeCSS } from '../../shared/theme-contract.js';

const root = document.documentElement;
const style = document.createElement('style');
style.id = 'sallos-toolbox-global-appearance';
let lease = '';
let expires = 0;
let previewEnds = 0;
let state = null;
let healthy = false;
let stopped = false;
let originalStyle;
new MutationObserver(records => {
  if (originalStyle !== undefined && records.some(record => record.oldValue === 'modern')) {
    originalStyle = root.getAttribute('data-dashboard-style');
  }
}).observe(root, { attributes: true, attributeOldValue: true, attributeFilter: ['data-dashboard-style'] });
const parameter = new URLSearchParams(location.search).get('sallosAppearance');
try {
  if (parameter === 'off') sessionStorage.setItem('sallos-appearance-off', '1');
  if (parameter === 'on') sessionStorage.removeItem('sallos-appearance-off');
  stopped = sessionStorage.getItem('sallos-appearance-off') === '1';
} catch { stopped = parameter === 'off'; }

function clearAppearance() {
  root.removeAttribute('data-plugin-appearance');
  style.remove();
  if (originalStyle !== undefined) {
    if (root.dataset.dashboardStyle === 'modern') {
      if (originalStyle === null) root.removeAttribute('data-dashboard-style');
      else root.dataset.dashboardStyle = originalStyle;
    }
    originalStyle = undefined;
  }
}

function paint() {
  if (stopped || !healthy || !state || performance.now() > expires || !document.querySelector('[data-dashboard-shell]')) {
    clearAppearance();
    return;
  }
  const theme = previewEnds && performance.now() > previewEnds ? state.fallback : state.theme;
  if (!theme) { clearAppearance(); return; }
  const css = themeCSS(theme);
  if (originalStyle === undefined || root.dataset.dashboardStyle !== 'modern') {
    originalStyle = root.getAttribute('data-dashboard-style');
    root.dataset.dashboardStyle = 'modern';
  }
  if (root.dataset.pluginAppearance !== 'sallos.toolbox') root.dataset.pluginAppearance = 'sallos.toolbox';
  if (style.textContent !== css) style.textContent = css;
  if (!style.isConnected) document.head.append(style);
}

async function synchronize() {
  if (stopped) return;
  try {
    const response = await fetch('/sallos-toolbox-appearance-v1/state.json', {
      cache: 'no-store', credentials: 'same-origin', signal: AbortSignal.timeout(4000),
    });
    if (!response.ok) throw new Error('Appearance state unavailable');
    const next = await response.json();
    if (next.schema !== 1 || typeof next.lease !== 'string' || next.ttl !== 30
      || !Number.isFinite(next.preview_seconds) || next.preview_seconds < 0 || next.preview_seconds > 20) {
      throw new Error('Appearance state invalid');
    }
    if (next.theme) next.theme = validateTheme(next.theme);
    if (next.fallback) next.fallback = validateTheme(next.fallback);
    healthy = true;
    if (lease !== next.lease) {
      lease = next.lease;
      expires = performance.now() + next.ttl * 1000;
      previewEnds = next.preview_seconds ? performance.now() + next.preview_seconds * 1000 : 0;
      state = next;
    }
    paint();
  } catch { healthy = false; clearAppearance(); }
}

addEventListener('keydown', event => {
  if (event.ctrlKey && event.shiftKey && event.key === 'Backspace') {
    stopped = true;
    try { sessionStorage.setItem('sallos-appearance-off', '1'); } catch { /* tab-only fallback */ }
    clearAppearance();
  }
});
// Independent paint tick makes preview expiry and runner lease expiry work during network failure.
setInterval(paint, 500);
async function loop() {
  await synchronize();
  setTimeout(loop, 2000);
}
void loop();
