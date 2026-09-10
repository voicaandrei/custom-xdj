import {resolveMode} from './settings.mjs?v=2';
import {parseAnlz, PreviewCache, syntheticTracks, MAX_FILE_BYTES, validateCatalog} from './core.mjs?v=2';
const $ = q => document.querySelector(q);
const viewport = $('.viewport'), spacer = $('.spacer'), cache = new PreviewCache(256);
let tracks = syntheticTracks(), filtered = tracks, width = 80, selected = 0, ascending = true, prepared = new Map(), pending = false, painted = 0, settings = null;
function svg(preview, w, height = 25) {
  const ns='http://www.w3.org/2000/svg',s=document.createElementNS(ns,'svg');
  s.setAttribute('width',w);s.setAttribute('height',height);s.setAttribute('viewBox',`0 0 ${w} ${height}`);
  s.setAttribute('aria-label',`Waveform ${preview.mode==='rgb'?'RGB':'Blue'} for the whole track${preview.fallback?' · fallback':''}`);s.setAttribute('role','img');
  const top=$('#baseline').value==='top';
  for(const [x,c] of preview.columns.entries()) {
    for(const [value,color] of [[c.height,c.color],[c.frontHeight,c.frontColor]]) {
      const h=Math.round(value/preview.maxHeight*(height-1));if(!h||!color)continue;
      const line=document.createElementNS(ns,'path');line.setAttribute('d',`M${x+.5} ${top?0:height-1}v${top?h:-h}`);line.setAttribute('stroke',`rgb(${color.join(',')})`);s.append(line);
    }
  }
  const baseline=document.createElementNS(ns,'path');baseline.setAttribute('d',`M0 ${top?.5:height-.5}H${w}`);baseline.setAttribute('stroke','#456273');s.append(baseline);
  return s;
}
function mode() {return resolveMode($('#color-mode').value,settings).mode;}
// Preparation is explicit and separate from painting and scrolling.
function prepare() {
  prepared = new Map(tracks.map(t => [t.key, cache.prepareTrack(t, width, mode())]));
  const fallback=[...prepared.values()].filter(p=>p.fallback).length;
  $('#color-status').textContent=resolveMode($('#color-mode').value,settings).note+(fallback?` · ${fallback} tracks without RGB: Blue`:'');
}
function paint() {
  pending = false; spacer.replaceChildren();
  const start = Math.floor(viewport.scrollTop / 44), end = Math.min(filtered.length, Math.ceil((viewport.scrollTop + viewport.clientHeight) / 44));
  painted = 0;
  for(let i=start;i<end;i++) {
    const t = filtered[i], row = document.createElement('div'); row.className = `row${i===selected?' selected':''}`; row.style.top = `${i*44}px`; row.setAttribute('role','listitem');
    const title=document.createElement('span'); title.className='title'; title.textContent=t.title;
    row.append(svg(prepared.get(t.key),width),title); row.onclick=()=>{selected=i;compare();paint();}; spacer.append(row); painted++;
  }
  $('#stats').textContent=`${painted} ${painted===1?"row painted":"rows painted"} · ${cache.items.size} cache entries · ${cache.hits} hit / ${cache.misses} miss`;
}
function schedule() {if(!pending){pending=true;requestAnimationFrame(paint);}}
function compare() {
  const el=$('#comparison'); el.replaceChildren(); const t=filtered[selected]; if(!t)return;
  for(const w of [80,110,140]) {const box=document.createElement('div'), label=document.createElement('label');label.textContent=`${w} × 25 px`;box.append(label,svg(cache.prepareTrack(t,w,mode()),w));el.append(box);}
}
function filter() {
  const q=$('#search').value.toLocaleLowerCase('en'); filtered=tracks.filter(t=>t.title.toLocaleLowerCase('en').includes(q));
  filtered=[...filtered].sort((a,b)=>ascending?a.title.localeCompare(b.title):b.title.localeCompare(a.title)); selected=0;
  viewport.scrollTop=0;spacer.style.height=`${filtered.length*44}px`;$('#count').textContent=`${filtered.length} ${filtered.length===1?"TRACK":"TRACKS"}`;compare();paint();
}
function load(next, nextSettings=null) {settings=nextSettings;tracks=next;cache.clear();$('#search').value='';$('#badge').textContent=next.some(t=>t.source==='ANLZ REAL')?'REAL ANLZ DATA':'SYNTHETIC DATA';prepare();filter();}
for(const b of document.querySelectorAll('[data-width]')) b.onclick=()=>{width=Number(b.dataset.width);$('.screen').style.setProperty('--wave',`${width}px`);for(const c of document.querySelectorAll('[data-width]'))c.setAttribute('aria-pressed',String(c===b));prepare();paint();};
$('#color-mode').onchange=()=>{prepare();compare();paint();};
$('#baseline').onchange=()=>{compare();paint();};$('#toggle').onchange=()=>$('.screen').classList.toggle('off',!$('#toggle').checked);
$('#search').oninput=filter;$('#sort').onclick=()=>{ascending=!ascending;$('#sort').textContent=ascending?'Sort A–Z':'Sort Z–A';filter();};
viewport.onscroll=schedule;new ResizeObserver(schedule).observe(viewport);
viewport.onkeydown=e=>{if(!['ArrowDown','ArrowUp'].includes(e.key)||!filtered.length)return;e.preventDefault();selected=Math.max(0,Math.min(filtered.length-1,selected+(e.key==='ArrowDown'?1:-1)));if(selected*44<viewport.scrollTop)viewport.scrollTop=selected*44;else if((selected+1)*44>viewport.scrollTop+viewport.clientHeight)viewport.scrollTop=(selected+1)*44-viewport.clientHeight;compare();paint();};
$('#demo').onclick=()=>{load(syntheticTracks());$('#error').textContent='';};
$('#files').onchange=async e=>{
  const next=[],errors=[];let fallback=0;
  for(const f of e.target.files){try{if(f.size>MAX_FILE_BYTES)throw new Error('File too large');const bytes=await f.arrayBuffer(),p=parseAnlz(bytes);if(!p.heights)throw new Error('PWAV absent');const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');next.push({key:hash,title:p.path?.split('/').pop()||`${f.name} · ${++fallback}`,source:'ANLZ REAL',heights:p.heights,shades:p.shades});}catch(err){errors.push(`${f.name}: ${err.message}`);}}
  if(next.length)load(next);$('#error').textContent=errors.join('\n');e.target.value='';
};
$('#catalog').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>MAX_FILE_BYTES)throw new Error('Catalog too large');const c=validateCatalog(JSON.parse(await f.text()));load(c.tracks,c.settings);$('#error').textContent=[...(c.errors||[]),...(c.warnings||[])].map(e=>e.error).join('\n');}catch(err){$('#error').textContent=err.message;}e.target.value='';};
load(tracks);
