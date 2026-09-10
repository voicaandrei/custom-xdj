// Read only the EXT companions of the already accepted private DAT sample.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root = path.resolve(import.meta.dirname, '../private/owner/andrei-sample');
const manifest = JSON.parse(await fs.readFile(path.join(root, 'manifest.json')));
const sha = b => createHash('sha256').update(b).digest('hex');
const records = [];
async function copyVerified(source, target) {
  const before = await fs.stat(source);
  if (!before.isFile() || before.size > 32 * 1024 * 1024) throw new Error('Invalid input size');
  const bytes = await fs.readFile(source);
  await fs.mkdir(path.dirname(target), {recursive:true});
  try { const existing = await fs.readFile(target); if (!existing.equals(bytes)) throw new Error('Different snapshot exists'); }
  catch(e) { if(e.code !== 'ENOENT') throw e; await fs.writeFile(target, bytes); }
  const after = await fs.stat(source), second = await fs.readFile(source);
  if (!bytes.equals(second) || before.size !== after.size || before.mtimeMs !== after.mtimeMs) throw new Error('Source changed');
  records.push({relative:path.relative(root,target),bytes:bytes.length,sha256:sha(bytes),sourceUnchanged:true});
}
for (const f of manifest.files) {
  const rel = f.relative.replace(/\.DAT$/i,'.EXT');
  await copyVerified(path.join(manifest.source,rel),path.join(root,'anlz',rel));
}
await copyVerified(path.resolve(manifest.source,'../DEVSETTING.DAT'),path.join(root,'DEVSETTING.DAT'));
await fs.writeFile(path.join(root,'color-manifest.json'),JSON.stringify({records},null,2));
console.log(`${records.length} files copied and verified; sampled USB files unchanged.`);
