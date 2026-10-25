export function confirmDiscard() {
  const dialog = document.querySelector('#discard-dialog');
  dialog.showModal();
  return new Promise(resolve => {
    dialog.addEventListener('close', () => resolve(dialog.returnValue === 'discard'), { once: true });
  });
}
