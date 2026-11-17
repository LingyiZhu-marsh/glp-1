// Exercise overlay handlers with a small stand-in for the browser APIs.
const assert = require('node:assert/strict');
const { runAsset } = require('./helpers.cjs');
function element(extra = {}) {
  return Object.assign({ handlers: {}, addEventListener(type, fn) { this.handlers[type] = fn; } }, extra);
}
const classes = new Set();
const close = element();
const title = {};
const content = { replaceChildren(value) { this.value = value; } };
const fullReference = {};
const trigger = element({
  dataset: { citation: 'example' }, textContent: '[7]', href: 'file:///project/references/index.html#ref-example',
  setAttribute() {}, focus(options) { this.focusOptions = options; },
});
const dialog = element({
  open: false,
  showModal() { this.open = true; },
  close() { this.open = false; this.handlers.close(); },
  querySelector(selector) {
    return { '#citation-dialog-title': title, '.citation-sheet-content': content,
      '.citation-full-reference': fullReference, '.citation-close': close }[selector];
  },
});
const document = {
  querySelector: () => dialog, querySelectorAll: () => [trigger],
  getElementById: () => ({ content: { cloneNode: () => 'reference markup' } }),
  documentElement: { classList: { add: x => classes.add(x), remove: x => classes.delete(x) } },
};
runAsset('citation-overlay.js', { document });
const click = (extra = {}) => ({ button: 0, preventDefault() { this.prevented = true; }, ...extra });
let event = click({ ctrlKey: true });
trigger.handlers.click(event);
assert.equal(dialog.open, false);
assert.equal(event.prevented, undefined);
event = click();
dialog.scrollTop = 200;
trigger.handlers.click(event);
assert.equal(dialog.open, true);
assert.equal(dialog.scrollTop, 0);
assert.equal(event.prevented, true);
assert.equal(title.textContent, 'Reference [7]');
assert.equal(content.value, 'reference markup');
assert.equal(fullReference.href, trigger.href);
assert.equal(classes.has('citation-is-open'), true);
dialog.handlers.pointerdown({ target: content });
dialog.handlers.click({ target: dialog });
assert.equal(dialog.open, true, 'Dragging from text should not dismiss the sheet');
dialog.handlers.pointerdown({ target: dialog });
dialog.handlers.click({ target: dialog });
assert.equal(dialog.open, false);
assert.equal(classes.has('citation-is-open'), false);
assert.equal(trigger.focusOptions.preventScroll, true);
trigger.handlers.click(click());
close.handlers.click();
assert.equal(dialog.open, false);
console.log('PASS: opening, content, modified clicks, outside dismissal, close button, scroll lock, and focus restoration.');
