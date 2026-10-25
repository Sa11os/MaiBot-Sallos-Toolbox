import { themeCSS, contrast } from '../../shared/theme-contract.js';

export function renderPreview(theme) {
  document.querySelector('#preview-styles').textContent = themeCSS(theme, '#preview');
  const root = document.querySelector('#preview');
  root.style.setProperty('--preview-sidebar-width', `${Math.round(theme.sidebar_width / 1.5)}px`);
  root.dataset.side = theme.sidebar_side;
  root.querySelector('.preview-header').style.height = `${theme.header_height}px`;
  root.querySelector('.preview-main').style.padding = `${theme.gap}px`;
  root.querySelector('.preview-name').textContent = theme.name;
  const pairs = [[theme.text, theme.background], [theme.text, theme.surface], [theme.muted, theme.surface]];
  const ratio = Math.min(...pairs.map(([a, b]) => contrast(a, b)));
  document.querySelector('#contrast').textContent = `最低文字对比度 ${ratio.toFixed(1)}:1${ratio < 4.5 ? ' · 建议调整至 4.5:1 以上' : ' · 清晰可读'}`;
  document.querySelector('#contrast').dataset.warning = String(ratio < 4.5);
}
