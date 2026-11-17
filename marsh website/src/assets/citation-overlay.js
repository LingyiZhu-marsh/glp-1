// Reference content is generated into local templates, so no fetch is needed.
(() => {
  const dialog = document.querySelector('.citation-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;

  const title = dialog.querySelector('#citation-dialog-title');
  const content = dialog.querySelector('.citation-sheet-content');
  const fullReference = dialog.querySelector('.citation-full-reference');
  const closeButton = dialog.querySelector('.citation-close');
  if (!title || !content || !fullReference || !closeButton) return;
  let trigger = null;

  for (const link of document.querySelectorAll('a[data-citation]')) {
    link.setAttribute('aria-haspopup', 'dialog');
    link.addEventListener('click', event => {
      // Preserve opening the reference page in a new tab with modified clicks.
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const template = document.getElementById(`citation-content-${link.dataset.citation}`);
      if (!template) return;
      trigger = link;
      title.textContent = `Reference ${link.textContent.trim()}`;
      content.replaceChildren(template.content.cloneNode(true));
      fullReference.href = link.href;
      dialog.showModal();
      dialog.scrollTop = 0;
      document.documentElement.classList.add('citation-is-open');
      event.preventDefault();
    });
  }

  closeButton.addEventListener('click', () => dialog.close());
  // Require both the press and release on the backdrop, not a drag from the text.
  let pressedOutside = false;
  dialog.addEventListener('pointerdown', event => { pressedOutside = event.target === dialog; });
  dialog.addEventListener('pointercancel', () => { pressedOutside = false; });
  dialog.addEventListener('click', event => {
    if (pressedOutside && event.target === dialog) dialog.close();
    pressedOutside = false;
  });
  // Native modal dialogs handle Escape, keyboard focus containment, and inert background.
  dialog.addEventListener('close', () => {
    document.documentElement.classList.remove('citation-is-open');
    trigger?.focus({ preventScroll: true });
    trigger = null;
  });
})();
