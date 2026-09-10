// Private-fixture oracle for C parity. Never writes to the export or device.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {parseAnlz, buildPreview} from '../web/core.mjs';

const base = new URL('../private/owner/andrei-sample/', import.meta.url);
const manifest = JSON.parse(fs.readFileSync(new URL('manifest.json', base)));
const color = JSON.parse(fs.readFileSync(new URL('color-manifest.json', base)));
const result = [];
for (const entry of manifest.files) {
  for (const mode of ['blue', 'rgb']) {
    const relative = `anlz/${entry.relative.replace(/\.DAT$/, mode === 'rgb' ? '.EXT' : '.DAT')}`;
    const expectedHash = mode === 'blue' ? entry.sha256 : color.records.find(r => r.relative === relative)?.sha256;
    const bytes = fs.readFileSync(new URL(relative, base));
    if (crypto.createHash('sha256').update(bytes).digest('hex') !== expectedHash) throw Error('Fixture hash mismatch');
    const parsed = parseAnlz(bytes);
    const tag = parsed.tags.find(t => t.name === (mode === 'blue' ? 'PWAV' : 'PWV4'));
    const preview = buildPreview(parsed, 80, mode);
    result.push({mode, payload: bytes.subarray(tag.offset + tag.headerBytes, tag.offset + tag.bytes).toString('base64'),
      columns: preview.columns.map(c => ({back: Math.round(c.height * 27 / preview.maxHeight),
        front: Math.round(c.frontHeight * 27 / preview.maxHeight),
        color: c.color, frontColor: c.frontColor}))});
  }
}
process.stdout.write(JSON.stringify(result));
