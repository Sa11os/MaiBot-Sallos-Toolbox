import { DEFAULT_THEME } from '../../generated/theme-data.js';
import { validateTheme } from '../../shared/theme-contract.js';

export function fillEditor(theme) {
  for (const [key, value] of Object.entries(theme)) {
    if (key === 'regions' || key === 'version') continue;
    const control = document.querySelector(`[name="${key}"]`);
    if (control) control.value = value;
    const echo = document.querySelector(`[data-value="${key}"]`);
    if (echo) echo.textContent = value;
  }
  for (const [key, value] of Object.entries(theme.regions)) {
    document.querySelector(`[name="region_${key}"]`).value = value;
  }
  syncOutputs();
}

export function syncOutputs() {
  document.querySelectorAll('input[type="range"]').forEach(input => {
    document.querySelector(`[data-value="${input.name}"]`).textContent = input.value;
  });
  document.querySelectorAll('input[type="color"]').forEach(input => {
    document.querySelector(`[data-value="${input.name}"]`).textContent = input.value.toUpperCase();
  });
}

export function readEditor() {
  const values = new FormData(document.querySelector('#editor'));
  const theme = structuredClone(DEFAULT_THEME);
  for (const key of Object.keys(theme)) {
    if (key === 'regions' || key === 'version') continue;
    theme[key] = typeof theme[key] === 'number' ? Number(values.get(key)) : values.get(key);
  }
  for (const key of Object.keys(theme.regions)) theme.regions[key] = values.get(`region_${key}`);
  return validateTheme(theme);
}
