import { DEFAULT_THEME, BUILTIN_PRESETS } from './generated/theme-data.js';
import { bridge, appearanceAction, showStatus } from './shared/bridge.js';
import { fillEditor, readEditor, syncOutputs } from './features/appearance/editor.js';
import { renderPreview } from './features/appearance/preview.js';
import { renderPresetList } from './features/appearance/presets.js';
import { confirmDiscard } from './shared/confirm.js';

let catalog = { builtin: BUILTIN_PRESETS, presets: [], revision: 0 };
let activeId = 'workbench';
let savedId = '';
let busy = false;
let dirty = false;
let connected = false;
let previewGeneration = 0;

function renderPresets() {
  renderPresetList(catalog, activeId, async (preset, builtin) => {
    if (busy || (dirty && !await confirmDiscard())) return;
    activeId = preset.id;
    savedId = builtin ? '' : preset.id;
    dirty = false;
    fillEditor(preset.theme);
    updatePreview();
    renderPresets();
    document.querySelector('#delete').disabled = builtin || !connected;
  });
}

function updatePreview() {
  syncOutputs();
  try {
    renderPreview(readEditor());
    document.querySelector('#field-error').textContent = '';
  } catch (error) { document.querySelector('#field-error').textContent = error.message; }
}

async function run(operation) {
  if (busy) return;
  busy = true;
  document.querySelector('#editor').inert = true;
  document.querySelector('#preset-list').inert = true;
  document.querySelector('#refresh').disabled = true;
  document.querySelector('#actions').setAttribute('aria-busy', 'true');
  document.querySelectorAll('#actions button').forEach(button => { button.disabled = true; });
  try { await operation(); }
  catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    document.querySelector('#editor').inert = false;
    document.querySelector('#preset-list').inert = false;
    document.querySelector('#refresh').disabled = false;
    document.querySelector('#actions').setAttribute('aria-busy', 'false');
    document.querySelectorAll('#actions button').forEach(button => { button.disabled = !connected; });
    document.querySelector('#delete').disabled = !savedId || !connected;
    for (const id of ['apply', 'preview-site', 'restore']) {
      document.querySelector(`#${id}`).disabled = !catalog.integration?.available;
    }
  }
}

async function refresh() {
  const result = await bridge().query('catalog');
  catalog = result;
  connected = true;
  renderPresets();
  document.querySelector('#integration-note').textContent = catalog.integration?.available
    ? '全站接入已就绪 · 首次启用请刷新整个 Dashboard。应用和预览影响此服务器的所有浏览器，约 2 秒同步。'
    : (catalog.integration?.message || '全站接入状态暂时不可用');
}

document.querySelector('#editor').addEventListener('submit', event => event.preventDefault());
document.querySelector('#editor').addEventListener('input', () => { dirty = true; updatePreview(); });
document.querySelector('#save').onclick = () => run(async () => {
  const state = await bridge().action('save', { theme: readEditor(), preset_id: savedId, revision: catalog.revision });
  catalog = { ...catalog, ...state };
  savedId = savedId || state.presets.at(-1).id;
  activeId = savedId;
  dirty = false;
  renderPresets();
  showStatus('预设已保存。点击“应用到 Dashboard”启用全站风格。');
});
document.querySelector('#save-copy').onclick = () => run(async () => {
  const state = await bridge().action('save', { theme: readEditor(), preset_id: '', revision: catalog.revision });
  catalog = { ...catalog, ...state };
  activeId = savedId = state.presets.at(-1).id;
  dirty = false;
  renderPresets();
  showStatus('已另存为个人预设');
});
document.querySelector('#delete').onclick = () => run(async () => {
  const state = await bridge().action('delete', { preset_id: savedId, revision: catalog.revision });
  catalog = { ...catalog, ...state };
  savedId = '';
  activeId = 'workbench';
  dirty = false;
  fillEditor(DEFAULT_THEME);
  updatePreview();
  renderPresets();
  showStatus('个人预设已删除；已应用的外观可通过“恢复原外观”撤销。');
});
document.querySelector('#preview-site').onclick = () => run(async () => {
  await appearanceAction('preview', readEditor());
  const generation = ++previewGeneration;
  showStatus('全站预览中，所有浏览器将在 20 秒后自动恢复。');
  setTimeout(() => { if (generation === previewGeneration) showStatus('预览结束，已恢复原外观'); }, 20000);
});
document.querySelector('#apply').onclick = () => run(async () => {
  await appearanceAction('apply', readEditor());
  previewGeneration++;
  showStatus('已保存服务器全站外观，约 2 秒同步；首次使用请刷新整个 Dashboard。');
});
document.querySelector('#restore').onclick = () => run(async () => {
  await appearanceAction('reset');
  previewGeneration++;
  showStatus('已恢复 Dashboard 原有外观');
});
document.querySelector('#refresh').onclick = () => run(async () => { await refresh(); showStatus('预设列表已刷新，编辑内容已保留'); });
fillEditor(BUILTIN_PRESETS[0].theme);
renderPresets();
updatePreview();
await run(async () => {
  await bridge().ready;
  await refresh();
  showStatus('工作台已就绪');
});
