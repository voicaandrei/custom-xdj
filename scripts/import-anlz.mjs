import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {parseAnlz, MAX_FILE_BYTES} from '../web/core.mjs';
import {parseDevSetting} from '../web/settings.mjs';
const root = process.argv[2];
if (!root) { console.error('Usage: npm run import -- /Volumes/USB/PIONEER/USBANLZ [output/catalog.json]'); process.exit(2); }
const dest = path.resolve(process.argv[3] || 'output/catalog.json');
const project = path.resolve(import.meta.dirname, '..');
if (!['output', 'private'].some(p => dest.startsWith(path.join(project, p) + path.sep))) throw new Error('Private catalogs must be saved in output/ or private/');
async function* walk(dir) {
  for (const e of await fs.readdir(dir, {withFileTypes: true})) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (e.isFile() && /\.dat$/i.test(e.name)) yield p;
  }
}
const tracks = [], errors = [], warnings = [];
let settings=null;
const settingPath=process.argv[4] || path.resolve(root,'../DEVSETTING.DAT');
try {settings=parseDevSetting(await fs.readFile(settingPath));}catch(e){warnings.push({type:'settings',error:e.code==='ENOENT'?'DEVSETTING absent':e.message});}
for await (const file of walk(root)) {
  try {
    if ((await fs.stat(file)).size > MAX_FILE_BYTES) throw new Error('File too large');
    const bytes = await fs.readFile(file), data = parseAnlz(bytes);
    if (!data.heights) throw new Error('PWAV absent');
    let colorPreview=null,extBytes=Buffer.alloc(0);
    try {
      const ext=file.replace(/\.dat$/i,'.EXT');
      if((await fs.stat(ext)).size>MAX_FILE_BYTES)throw new Error('EXT prea mare');
      extBytes=await fs.readFile(ext);const color=parseAnlz(extBytes);
      if(color.path&&data.path&&color.path!==data.path)throw new Error('EXT belongs to a different track');
      colorPreview=color.colorPreview;
      if(!colorPreview)throw new Error('PWV4 absent');
    } catch(e) {warnings.push({file:path.relative(root,file),type:'rgb',error:e.code==='ENOENT'?'EXT absent':e.message});}
    tracks.push({key: createHash('sha256').update(bytes).update(extBytes).digest('hex'), shades:Array.from(data.shades),colorPreview, title: data.path?.split('/').pop() || path.relative(root, file), source: 'ANLZ REAL', heights: Array.from(data.heights)});
  } catch (e) { errors.push({file: path.relative(root, file), error: e.message}); }
}
await fs.mkdir(path.dirname(dest), {recursive: true});
await fs.writeFile(dest, JSON.stringify({schema: 2, settings, tracks, errors, warnings}, null, 2));
console.log(`${tracks.length} tracks, ${errors.length} errors, ${warnings.length} warnings. Catalog: ${dest}`);
if (errors.length) process.exitCode = 1;
