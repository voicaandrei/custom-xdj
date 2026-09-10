import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {parseAnlz,buildPreview,PreviewCache,validateCatalog} from '../web/core.mjs';
import {crc16,parseDevSetting,resolveMode} from '../web/settings.mjs';
function ext() {
 const b=Buffer.alloc(28+24+7200);b.write('PMAI');b.writeUInt32BE(28,4);b.writeUInt32BE(b.length,8);
 b.write('PWV4',28);b.writeUInt32BE(24,32);b.writeUInt32BE(7224,36);b.writeUInt32BE(6,40);b.writeUInt32BE(1200,44);return b;
}
const track=()=>({key:'test',title:'Test',source:'ANLZ REAL',heights:Array(400).fill(0),shades:Array(400).fill(0),colorPreview:Array.from({length:1200},()=>[0,0,0])});
function setting(value=3){const b=Buffer.alloc(140);b.writeUInt32LE(96);b.write('PIONEER DJ',4);b.write('rekordbox',36);b.write('6.6.1',68);b.writeUInt32LE(32,100);b.set([120,86,52,18,1,0,0,0,1,1,value,1,1,1],104);b.writeUInt16LE(crc16(b.subarray(104,136)),136);return b;}
test('PWV4 reads last three bytes, ignores first three, bounds and duplicates rejected',()=>{
 const b=ext();b.set([255,254,253,12,24,48],52);assert.deepEqual(parseAnlz(b).colorPreview[0],[12,24,48]);
 for(const [offset,value] of [[32,20],[40,5],[44,1199],[36,7223]]){const c=Buffer.from(b);c.writeUInt32BE(value,offset);assert.throws(()=>parseAnlz(c));}
 const duplicate=Buffer.concat([b,b.subarray(28)]);duplicate.writeUInt32BE(duplicate.length,8);assert.throws(()=>parseAnlz(duplicate));assert.throws(()=>parseAnlz(b.subarray(0,-1)));
});
test('RGB bucket maxima retain back and front transients with their own colors',()=>{
 const t=track();t.colorPreview[0]=[100,0,0];t.colorPreview[1]=[0,0,80];t.colorPreview[1199]=[0,200,0];
 const p=buildPreview(t,80,'rgb');assert.equal(p.maxHeight,200);assert.equal(p.columns[0].height,100);assert.equal(p.columns[0].frontHeight,80);assert.deepEqual(p.columns[0].color,[191,0,0]);assert.deepEqual(p.columns[0].frontColor,[0,0,255]);assert.equal(p.columns[79].height,200);
 assert.ok(buildPreview(track(),80,'rgb').columns.every(c=>c.height===0));
});
test('Blue retains shade, absent RGB falls back, mode changes cannot reuse stale colors',()=>{
 const t=track();delete t.colorPreview;t.heights[399]=31;t.shades[399]=7;
 const p=buildPreview(t,80,'rgb');assert.equal(p.mode,'blue');assert.equal(p.fallback,true);assert.deepEqual(p.columns[79].color,[116,246,244]);
 const cache=new PreviewCache(2);cache.prepareTrack(t,80,'blue');cache.prepareTrack(t,80,'rgb');cache.prepareTrack(t,80,'rgb');assert.equal(cache.misses,2);assert.equal(cache.hits,1);cache.prepareTrack(t,110,'blue');assert.equal(cache.items.size,2);
});
test('DEVSETTING validates CRC, shape, endian and explicit unknown/3-band handling',()=>{
 assert.equal(crc16(Buffer.from('123456789')),0x31c3);
 assert.equal(parseDevSetting(setting(1)).waveformColor,'blue');assert.equal(parseDevSetting(setting()).waveformColor,'rgb');
 const b=setting();b[114]=1;assert.throws(()=>parseDevSetting(b));assert.throws(()=>parseDevSetting(setting(9)));assert.throws(()=>parseDevSetting(setting().subarray(0,-1)));
 assert.equal(resolveMode('usb',parseDevSetting(setting(4))).mode,'blue');assert.match(resolveMode('usb',null).note,/unavailable/);assert.equal(resolveMode('usb',parseDevSetting(setting())).mode,'rgb');
});
test('catalog rejects malformed color data, duplicate keys, and unknown settings',()=>{
 const c={schema:2,tracks:[track()],settings:{waveformColor:'rgb'}};assert.equal(validateCatalog(c),c);
 for(const change of [c=>c.tracks[0].colorPreview[0][0]=256,c=>c.tracks[0].shades[0]=8,c=>c.tracks.push(c.tracks[0]),c=>c.settings.waveformColor='rgba']){const d=structuredClone(c);change(d);assert.throws(()=>validateCatalog(d));}
});
const root=new URL('../private/owner/andrei-sample/',import.meta.url);let manifest;
try{manifest=JSON.parse(await fs.readFile(new URL('color-manifest.json',root)));}catch(e){if(e.code!=='ENOENT')throw e;}
test('owner: 50 paired EXT previews and RGB USB setting match frozen hashes', {skip:!manifest&&'Private color sample absent'},async()=>{
 assert.equal(manifest.records.length,51);
 for(const record of manifest.records){const b=await fs.readFile(new URL(record.relative,root));assert.equal(createHash('sha256').update(b).digest('hex'),record.sha256);assert.equal(record.sourceUnchanged,true);
  if(record.relative.endsWith('.EXT')){const e=parseAnlz(b),d=parseAnlz(await fs.readFile(new URL(record.relative.replace(/\.EXT$/,'.DAT'),root)));assert.equal(e.path,d.path);assert.equal(e.colorPreview.length,1200);assert.ok(e.colorPreview.some(v=>Math.max(...v)>0));}
  else assert.equal(parseDevSetting(b).waveformColor,'rgb');
 }
});
