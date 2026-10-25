export function bridge() {
  if (!window.maibot) throw new Error('请从 MaiBot 的 Sallos 工具箱入口打开工作台');
  return window.maibot;
}

export async function appearanceAction(name, theme) {
  const api = bridge();
  return api.action(name, theme ? { theme } : {});
}

export function showStatus(message, error = false) {
  const status = document.querySelector('#status');
  status.textContent = message;
  status.dataset.error = String(error);
}
