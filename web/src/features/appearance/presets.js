export function renderPresetList(catalog, active, onSelect) {
  const container = document.querySelector('#preset-list');
  container.replaceChildren();
  for (const [presets, builtin] of [[catalog.builtin, true], [catalog.presets, false]]) {
    for (const preset of presets) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'preset';
      button.setAttribute('aria-pressed', String(preset.id === active));
      const sample = document.createElement('span');
      sample.className = 'preset-sample';
      sample.style.background = preset.theme.background;
      for (const key of ['primary', 'surface', 'text']) {
        const dot = document.createElement('i');
        dot.style.background = preset.theme[key];
        sample.append(dot);
      }
      const name = document.createElement('strong');
      name.textContent = preset.theme.name;
      const label = document.createElement('small');
      label.textContent = builtin ? '内置模板' : '个人预设';
      button.append(sample, name, label);
      button.addEventListener('click', () => onSelect(preset, builtin));
      container.append(button);
    }
  }
}
