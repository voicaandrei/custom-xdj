import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {parseAnlz,bucketMax} from '../web/core.mjs';
const location=new URL('../evidence/reference-fixtures.json',import.meta.url);
const manifest=fs.existsSync(location)?JSON.parse(fs.readFileSync(location)):{files:[]};
if(!manifest.files.length) test('optional reference fixtures',{skip:'Private fixture manifest not supplied'},()=>{});
for(const f of manifest.files) {
  test(`public fixture ${f.file}`,{skip:!fs.existsSync(f.file)},()=>{
    const data=fs.readFileSync(f.file);assert.equal(createHash('sha256').update(data).digest('hex'),f.sha256);
    const parsed=parseAnlz(data);assert.equal(parsed.heights.length,400);assert.ok(parsed.path);assert.ok(parsed.tags.some(t=>t.name==='PQTZ'));
    for(const w of [80,110,140]){const out=bucketMax(parsed.heights,w);assert.equal(out.length,w);assert.equal(Math.max(...out),Math.max(...parsed.heights));}
  });
}
