// Owner data stays private; this integration test is explicitly skipped elsewhere.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {parseAnlz, bucketMax} from '../web/core.mjs';
const root = new URL('../private/owner/andrei-sample/', import.meta.url);
let manifest;
try { manifest = JSON.parse(await fs.readFile(new URL('manifest.json', root))); }
catch (e) { if (e.code !== 'ENOENT') throw e; }
test('owner export: frozen DAT hashes, valid PWAV and full-track resampling', {skip: !manifest && 'Private owner sample not available'}, async () => {
  assert.equal(manifest.files.length, 50);
  assert.equal(manifest.errors.length, 0);
  assert.equal(manifest.sampleUnchanged, true);
  for (const [index, entry] of manifest.files.entries()) {
    const data = await fs.readFile(new URL('anlz/' + entry.relative, root));
    assert.equal(createHash('sha256').update(data).digest('hex'), entry.sha256, `sample ${index + 1}`);
    const {heights, path} = parseAnlz(data);
    assert.equal(heights.length, 400);
    assert.ok(path);
    for (const width of [80, 110, 140]) {
      const result = bucketMax(heights, width);
      assert.equal(result.length, width);
      assert.equal(Math.max(...result), Math.max(...heights));
    }
  }
});
