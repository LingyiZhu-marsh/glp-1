// Exercise navigation state and keyboard handlers without installing a DOM library.
const assert = require('node:assert/strict');
const { runAsset } = require('./helpers.cjs');
let document;
function node(parent = null, tag = 'div') {
  const attributes = { 'aria-expanded': 'false' };
  const classes = new Set();
  return {
    parent, tag, handlers: {}, hidden: true,
    getAttribute: key => attributes[key],
    setAttribute: (key, value) => { attributes[key] = value; },
    addEventListener(type, handler) { this.handlers[type] = handler; },
    classList: {
      add: value => classes.add(value),
      toggle(value, enabled) { if (enabled) classes.add(value); else classes.delete(value); },
      contains: value => classes.has(value),
    },
    contains(target) { for (; target; target = target.parent) if (target === this) return true; return false; },
    closest(selector) { return selector === 'a' && this.tag === 'a' ? this : null; },
    focus() { document.activeElement = this; },
  };
}
const nav = node();
const mobileButton = node(nav, 'button');
const links = node(nav);
const home = node(links, 'a');
links.querySelector = () => home;
const groups = Array.from({ length: 2 }, () => {
  const element = node(links);
  const button = node(element, 'button');
  const panel = node(element);
  const link = node(panel, 'a');
  panel.querySelector = () => link;
  element.querySelector = selector => selector === 'button' ? button : panel;
  return { element, button, panel, link };
});
nav.querySelector = selector => selector === '.mobile-menu-toggle' ? mobileButton : links;
nav.querySelectorAll = () => groups.map(group => group.element);
const viewport = { matches: false, addEventListener(type, handler) { this.change = handler; } };
document = node();
document.querySelector = () => nav;
document.activeElement = home;
runAsset('main.js', {
  document, window: { location: { protocol: 'http:' }, matchMedia: () => viewport }, URL,
});
const expanded = button => button.getAttribute('aria-expanded') === 'true';
groups[0].button.handlers.click();
assert.equal(expanded(groups[0].button), true);
assert.equal(groups[0].panel.hidden, false);
groups[1].button.handlers.click();
assert.equal(expanded(groups[0].button), false);
assert.equal(expanded(groups[1].button), true);
let stopped = false;
groups[1].element.handlers.keydown({ key: 'Escape', stopPropagation() { stopped = true; } });
assert.equal(stopped, true);
assert.equal(expanded(groups[1].button), false);
assert.equal(document.activeElement, groups[1].button);
groups[0].element.handlers.keydown({ key: 'ArrowDown', target: groups[0].button, preventDefault() {} });
assert.equal(document.activeElement, groups[0].link);
viewport.matches = true;
viewport.change();
assert.equal(document.activeElement, mobileButton);
mobileButton.handlers.click();
assert.equal(nav.classList.contains('is-open'), true);
assert.equal(expanded(mobileButton), true);
nav.handlers.keydown({ key: 'Escape' });
assert.equal(expanded(mobileButton), false);
mobileButton.handlers.click();
nav.handlers.click({ target: home });
assert.equal(expanded(mobileButton), false);
assert.equal(document.activeElement, mobileButton);
mobileButton.handlers.click();
document.handlers.click({ target: node() });
assert.equal(expanded(mobileButton), false);
viewport.matches = false;
viewport.change();
assert.equal(document.activeElement, home);
viewport.matches = true;
viewport.change();
mobileButton.handlers.click();
groups[0].button.handlers.click();
groups[0].link.focus();
viewport.matches = false;
viewport.change();
assert.equal(expanded(groups[0].button), false);
assert.equal(document.activeElement, groups[0].button, 'Resizing must move focus out of the hidden submenu');
console.log('PASS: mutually exclusive dropdowns, keyboard focus, Escape, mobile selection, outside clicks, and breakpoint changes.');
