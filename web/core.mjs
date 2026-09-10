// Original implementation from documented ANLZ structures; see docs/sources.md.
export const MAX_FILE_BYTES = 32 * 1024 * 1024;
export function parseAnlz(input) {
  const bytes = input instanceof Uint8Array ? input : new Uint8Array(input);
  if (bytes.length < 12 || bytes.length > MAX_FILE_BYTES) throw new Error('Invalid ANLZ size');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const u32 = p => view.getUint32(p, false);
  const tag = p => String.fromCharCode(...bytes.subarray(p, p + 4));
  if (tag(0) !== 'PMAI') throw new Error('Missing PMAI header');
  const header = u32(4), total = u32(8);
  if (header < 12 || header > total || total !== bytes.length) throw new Error('Inconsistent PMAI length');
  let heights = null, shades = null, colorPreview = null, path = null;
  const tags = [];
  for (let p = header; p < total;) {
    if (total - p < 12) throw new Error('Truncated section header');
    const name = tag(p), h = u32(p + 4), size = u32(p + 8);
    if (h < 12 || size < h || size > total - p) throw new Error(`Invalid length: ${name}`);
    tags.push({name, offset: p, headerBytes: h, bytes: size});
    if (name === 'PWAV') {
      if (heights !== null) throw new Error('Duplicate PWAV section');
      if (h < 20) throw new Error('Antet PWAV prea scurt');
      const n = u32(p + 12);
      if (n !== 400 || size - h !== n) throw new Error('PWAV must contain 400 columns');
      heights = Uint8Array.from(bytes.subarray(p + h, p + size), v => v & 0x1f);
      shades = Uint8Array.from(bytes.subarray(p + h, p + size), v => v >>> 5);
    }
    if (name === 'PWV4') {
      if (colorPreview !== null) throw new Error('Duplicate PWV4 section');
      if (h !== 24 || u32(p + 12) !== 6 || u32(p + 16) !== 1200 || size - h !== 7200) throw new Error('Invalid PWV4: expected 1200 columns of 6 bytes');
      colorPreview = Array.from({length:1200}, (_,i) => Array.from(bytes.subarray(p+h+i*6+3,p+h+i*6+6)));
    }
    if (name === 'PPTH') {
      if (h < 16) throw new Error('Antet PPTH prea scurt');
      const n = u32(p + 12);
      if (n % 2 || n > size - h) throw new Error('Invalid PPTH length');
      if (n) path = new TextDecoder('utf-16be', {fatal: true}).decode(bytes.subarray(p + h, p + h + n)).replace(/\0+$/, '');
    }
    p += size;
  }
  return {heights, shades, colorPreview, path, tags};
}

// Disjoint half-open buckets cover every source column exactly once.
export function bucketMax(values, width) {
  if (!Number.isInteger(width) || width < 1 || width > values.length) throw new Error('Invalid downsampling width');
  const result = new Uint8Array(width);
  for (let x = 0; x < width; x++) {
    let max = 0;
    for (let i = Math.floor(x * values.length / width); i < Math.floor((x + 1) * values.length / width); i++) {
      const v = values[i];
      if (!Number.isInteger(v) || v < 0 || v > 31) throw new Error('Invalid PWAV amplitude');
      if (v > max) max = v;
    }
    result[x] = max;
  }
  return result;
}

export class PreviewCache {
  constructor(capacity = 256) {
    if (!Number.isInteger(capacity) || capacity < 1) throw new Error('Invalid capacity');
    this.capacity = capacity; this.items = new Map(); this.hits = 0; this.misses = 0;
  }
  prepare(contentKey, heights, width) {
    const key = `${contentKey}:${width}`;
    if (this.items.has(key)) {
      const v = this.items.get(key); this.items.delete(key); this.items.set(key, v); this.hits++; return v;
    }
    const value = bucketMax(heights, width); this.misses++;
    this.items.set(key, value);
    if (this.items.size > this.capacity) this.items.delete(this.items.keys().next().value);
    return value;
  }
  prepareTrack(track, width, mode) {
    const key = JSON.stringify([track.key, width, mode, 'color-v1']);
    if (this.items.has(key)) {
      const value = this.items.get(key); this.items.delete(key); this.items.set(key,value); this.hits++; return value;
    }
    const value = buildPreview(track, width, mode);
    this.items.set(key,value); this.misses++;
    if (this.items.size > this.capacity) this.items.delete(this.items.keys().next().value);
    return value;
  }
  clear() { this.items.clear(); }
}

export function syntheticTracks(count = 40) {
  const forms = ['Long intro', 'Central breakdown', 'Two builds', 'Steady energy', 'Gradual ending'];
  return Array.from({length: count}, (_, i) => {
    let seed = i + 71;
    const heights = Uint8Array.from({length: 400}, (_, x) => {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      const t = x / 399;
      const envelope = [Math.min(1, t * 4), (t > .42 && t < .59) ? .18 : .9, .35 + .6 * Math.abs(Math.sin(t * Math.PI * 2)), .85, 1 - t * .85][i % 5];
      return Math.min(31, Math.round(envelope * (12 + seed % 20)));
    });
    return {key: `synthetic-v1-${i}`, title: `Studiu ${String(i + 1).padStart(2, '0')} · ${forms[i % 5]}`, source: 'SYNTHETIC', heights};
  });
}

// Rendering approximation from documented PWV4 components. No device palette is assumed.
export function buildPreview(track, width, mode) {
  const rgb = mode === 'rgb' && track.colorPreview;
  const n = rgb ? 1200 : 400;
  if (!Number.isInteger(width) || width < 1 || width > n) throw new Error('Invalid width');
  const rows = rgb ? track.colorPreview.map(([r,g,b]) => {
    const height = Math.max(r,g,b);
    const color = level => [r,g,b].map(v=>height ? Math.floor(v*level/height) : 0);
    return {height, frontHeight:b, color:color(191), frontColor:color(255)};
  }) : Array.from(track.heights,(height,i)=>({height,frontHeight:0,color:(track.shades?.[i]??0)>=5?[116,246,244]:[43,89,255]}));
  const columns = Array.from({length:width},(_,x)=>{
    const start=Math.floor(x*n/width),end=Math.floor((x+1)*n/width);
    let back=rows[start],front=rows[start];
    for(let i=start+1;i<end;i++) {if(rows[i].height>back.height)back=rows[i];if(rows[i].frontHeight>front.frontHeight)front=rows[i];}
    return {...back,frontHeight:front.frontHeight,frontColor:front.frontColor};
  });
  return {columns,maxHeight:rgb?Math.max(1,...rows.map(r=>r.height)):31,mode:rgb?'rgb':'blue',fallback:mode==='rgb'&&!rgb};
}

export function validateCatalog(c) {
  if (![1,2].includes(c.schema) || !Array.isArray(c.tracks) || !c.tracks.length) throw new Error('Invalid catalog');
  const validArray=(a,n,max)=>Array.isArray(a)&&a.length===n&&a.every(v=>Number.isInteger(v)&&v>=0&&v<=max);
  const keys=new Set();
  for(const t of c.tracks) {
    if(typeof t.key!=='string'||keys.has(t.key)||typeof t.title!=='string'||t.source!=='ANLZ REAL'||!validArray(t.heights,400,31))throw new Error('Invalid or duplicate track');
    keys.add(t.key);
    if(t.shades!=null&&!validArray(t.shades,400,7))throw new Error('Invalid Blue shades');
    if(t.colorPreview!=null&&(!Array.isArray(t.colorPreview)||t.colorPreview.length!==1200||!t.colorPreview.every(v=>validArray(v,3,255))))throw new Error('Invalid RGB data');
  }
  if(c.settings?.waveformColor!=null&&!['blue','rgb','three-band'].includes(c.settings.waveformColor))throw new Error('Invalid color setting');
  return c;
}
