// Read a bounded sample from an owner-selected export; write only under private/.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {parseAnlz, MAX_FILE_BYTES} from '../web/core.mjs';
const source = process.argv[2];
const destination = path.resolve(process.argv[3] || 'private/owner/andrei-sample');
const limit = Number(process.argv[4] || 50);
const project = path.resolve(import.meta.dirname, '..');
if (!source || !Number.isInteger(limit) || limit < 1 || limit > 200) throw new Error('Utilizare: node scripts/snapshot-anlz.mjs SOURCE private/DEST [1..200]');
if (!destination.startsWith(path.join(project, 'private') + path.sep)) throw new Error('Snapshots must remain in private/');
await fs.mkdir(destination, {recursive: true});
const sha = b => createHash('sha256').update(b).digest('hex');
async function* walk(dir) {
  const entries = await fs.readdir(dir, {withFileTypes: true});
  entries.sort((a,b) => a.name.localeCompare(b.name, 'en'));
  for (const e of entries) {
    if (e.name.startsWith('._')) continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(full);
    else if (e.isFile() && /\.dat$/i.test(e.name)) yield full;
  }
}
const manifest = {created: new Date().toISOString(), source, selection: 'first valid DAT paths in deterministic directory order; not a random sample or playlist', requested: limit, files: [], errors: []};
for await (const file of walk(source)) {
  const relative = path.relative(source, file);
  try {
    const before = await fs.stat(file);
    if (before.size > MAX_FILE_BYTES) throw new Error('DAT prea mare');
    const data = await fs.readFile(file), parsed = parseAnlz(data);
    if (!parsed.heights) throw new Error('PWAV absent');
    const after = await fs.stat(file);
    if (before.size !== after.size || before.mtimeMs !== after.mtimeMs) throw new Error('Source changed while reading');
    const output = path.join(destination, 'anlz', relative);
    await fs.mkdir(path.dirname(output), {recursive: true});
    let existing;
    try { existing = await fs.readFile(output); } catch(e) { if(e.code !== 'ENOENT') throw e; }
    if (existing && sha(existing) !== sha(data)) throw new Error('Snapshot existent diferit; alege alt director');
    if (!existing) await fs.writeFile(output, data);
    let ext = null;
    try { const info = await fs.stat(file.replace(/\.dat$/i, '.EXT')); ext = {present: info.isFile(), bytes: info.size}; } catch(e) { if(e.code !== 'ENOENT') throw e; }
    manifest.files.push({relative, bytes: data.length, sha256: sha(data), columns: parsed.heights.length, sourceMtimeMs: before.mtimeMs, tags: parsed.tags, ext});
    if (manifest.files.length % 10 === 0) console.log(`${manifest.files.length} DAT files copied and validated`);
    if (manifest.files.length >= limit) break;
  } catch(e) { manifest.errors.push({relative, error: e.message}); }
}
for (const f of manifest.files) {
  const reread = await fs.readFile(path.join(source, f.relative));
  const stat = await fs.stat(path.join(source, f.relative));
  f.sourceUnchangedOnRecheck = sha(reread) === f.sha256 && stat.size === f.bytes && stat.mtimeMs === f.sourceMtimeMs;
}
manifest.sampleUnchanged = manifest.files.every(f => f.sourceUnchangedOnRecheck);
await fs.writeFile(path.join(destination, 'manifest.json'), JSON.stringify(manifest, null, 2));
console.log(JSON.stringify({files: manifest.files.length, errors: manifest.errors.length, sampleUnchanged: manifest.sampleUnchanged, manifest: path.join(destination, 'manifest.json')}));
if (!manifest.files.length || !manifest.sampleUnchanged) process.exitCode = 1;
