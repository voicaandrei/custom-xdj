import fs from 'node:fs/promises';
import {parseAnlz,bucketMax,MAX_FILE_BYTES} from '../web/core.mjs';
const file=process.argv[2];
if(!file){console.error('Utilizare: node scripts/sparkline.mjs /cale/ANLZ0000.DAT [coloane 1..400]');process.exit(2);}
if((await fs.stat(file)).size>MAX_FILE_BYTES)throw new Error('File too large');
const p=parseAnlz(await fs.readFile(file));if(!p.heights)throw new Error('PWAV absent');
const values=bucketMax(p.heights,Number(process.argv[3]||24));
for(const [name,alphabet] of [['Unicode',' ▁▂▃▄▅▆▇█'],['ASCII',' .:-=+*#@']])console.log(`${name}: ${Array.from(values,v=>alphabet[Math.round(v/31*(alphabet.length-1))]).join('')}`);
console.log('Local text only. MK2 font and column support are unverified. Metadata was not modified.');
