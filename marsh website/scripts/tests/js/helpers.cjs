// Load production assets relative to this file, independently of the caller's cwd.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function runAsset(name, globals) {
  const filename = path.resolve(__dirname, '../../../src/assets', name);
  return vm.runInNewContext(fs.readFileSync(filename, 'utf8'), globals, { filename });
}

module.exports = { runAsset };
