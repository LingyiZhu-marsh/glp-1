// Derive mobile labels from the existing headers; cell content is never duplicated.
(() => {
  for (const table of document.querySelectorAll('.report-table--stacked')) {
    if (table.classList.contains('is-stack-ready')) continue;
    // Only direct table sections are used, avoiding accidental nested-table matches.
    if (!table.tHead || table.tHead.rows.length !== 1) continue;
    const headers = [...table.tHead.rows[0].cells];
    const rows = [...table.tBodies].flatMap(body => [...body.rows]);
    const simpleCell = cell => cell.colSpan === 1 && cell.rowSpan === 1;
    // Unsupported structures retain the original scrollable table.
    if (!headers.length || !rows.length || headers.some(cell => cell.tagName !== 'TH' || !simpleCell(cell)) ||
      (table.classList.contains('report-table--comparison') && headers.length !== 4) ||
      rows.some(row => row.cells.length !== headers.length || [...row.cells].some(cell => !simpleCell(cell)) ||
        row.cells[0].tagName !== 'TH' || [...row.cells].slice(1).some(cell => cell.tagName !== 'TD'))) continue;

    table.setAttribute('role', 'table');
    for (const group of [table.tHead, ...table.tBodies]) group.setAttribute('role', 'rowgroup');
    for (const row of table.rows) row.setAttribute('role', 'row');
    headers.forEach(header => header.setAttribute('role', 'columnheader'));
    for (const row of rows) {
      [...row.cells].forEach((cell, index) => {
        if (cell.tagName === 'TH') {
          cell.setAttribute('role', 'rowheader');
          return;
        }
        cell.setAttribute('role', 'cell');
        const label = document.createElement('span');
        label.className = 'table-cell-label';
        label.setAttribute('aria-hidden', 'true');
        label.textContent = headers[index].textContent.trim();
        const value = document.createElement('span');
        value.className = 'table-cell-value';
        value.append(...cell.childNodes);
        cell.append(label, value);
      });
    }
    table.classList.add('is-stack-ready');
  }
})();
