// Check table enhancement and preservation of existing citation nodes/listeners.
const assert = require('node:assert/strict');
const { runAsset } = require('./helpers.cjs');
function element(tagName = 'SPAN', textContent = '') {
  return {
    tagName, textContent, childNodes: [], attributes: {}, colSpan: 1, rowSpan: 1,
    setAttribute(key, value) { this.attributes[key] = value; },
    append(...children) {
      for (const child of children) {
        if (child.parentNode) child.parentNode.childNodes.splice(child.parentNode.childNodes.indexOf(child), 1);
        this.childNodes.push(child);
        child.parentNode = this;
      }
    },
  };
}
function fixture(columns = 4, comparison = true) {
  const classes = new Set(comparison ? ['report-table--comparison'] : []);
  const headers = Array.from({ length: columns }, (_, i) => element('TH', ['Drug', 'Strategy', 'Half-life', 'Dosing'][i]));
  const cells = headers.map((_, i) => element(i ? 'TD' : 'TH'));
  const row = Object.assign(element('TR'), { cells });
  const headerRow = Object.assign(element('TR'), { cells: headers });
  return Object.assign(element('TABLE'), {
    tHead: Object.assign(element('THEAD'), { rows: [headerRow] }),
    tBodies: [Object.assign(element('TBODY'), { rows: [row] })], rows: [headerRow, row],
    classList: { contains: name => classes.has(name), add: name => classes.add(name) },
  });
}
function run(tables) {
  runAsset('tables.js', { document: { querySelectorAll: () => tables, createElement: () => element() } });
}
const table = fixture();
const cell = table.tBodies[0].rows[0].cells[1];
const citation = element('A', '[8]');
citation.existingClickHandler = () => {};
cell.append(citation);
run([table]);
assert.equal(table.classList.contains('is-stack-ready'), true);
assert.equal(cell.childNodes[0].textContent, 'Strategy');
assert.equal(cell.childNodes[0].attributes['aria-hidden'], 'true');
assert.equal(cell.childNodes[1].childNodes[0], citation);
assert.equal(citation.existingClickHandler instanceof Function, true);
assert.equal(cell.attributes.role, 'cell');
run([table]);
assert.equal(cell.childNodes.length, 2, 'Repeated initialization must not duplicate labels');
const merged = fixture();
merged.tHead.rows[0].cells[0].colSpan = 2;
const wrongWidth = fixture(3);
const noHeading = fixture();
noHeading.tHead = null;
const generic = fixture(3, false);
run([merged, wrongWidth, noHeading, generic]);
for (const unsupported of [merged, wrongWidth, noHeading]) {
  assert.equal(unsupported.classList.contains('is-stack-ready'), false);
}
assert.equal(generic.classList.contains('is-stack-ready'), true);
console.log('PASS: labels, semantic roles, citation node preservation, repeated initialization, generic tables, and unsupported-table fallback.');
