// DEVSETTING layout: rekordcrate setting.rs; header/CRC: pyrekordbox docs.
export function crc16(bytes) {
  let crc=0;
  for(const byte of bytes) {crc^=byte<<8;for(let i=0;i<8;i++)crc=((crc<<1)^((crc&0x8000)?0x1021:0))&0xffff;}
  return crc;
}
export function parseDevSetting(input) {
  const b=input instanceof Uint8Array?input:new Uint8Array(input);
  if(b.length!==140)throw new Error('Unsupported DEVSETTING size');
  const v=new DataView(b.buffer,b.byteOffset,b.byteLength);
  const str=p=>new TextDecoder('ascii').decode(b.subarray(p,p+32)).replace(/\0+$/,'');
  if(v.getUint32(0,true)!==96||v.getUint32(100,true)!==32||str(4)!=='PIONEER DJ'||str(36)!=='rekordbox')throw new Error('Antet DEVSETTING nesuportat');
  if(v.getUint16(136,true)!==crc16(b.subarray(104,136))||v.getUint16(138,true)!==0)throw new Error('Checksum DEVSETTING invalid');
  const signature=[0x78,0x56,0x34,0x12,1,0,0,0,1];
  if(signature.some((n,i)=>b[104+i]!==n)||b[115]!==1||b.subarray(118,136).some(n=>n!==0))throw new Error('Unknown DEVSETTING variant');
  const waveformColor=({1:'blue',3:'rgb',4:'three-band'})[b[114]];
  if(!waveformColor)throw new Error('Unknown USB color');
  return {waveformColor,rawColor:b[114],rekordboxVersion:str(68),checksumValid:true};
}
export function resolveMode(requested,settings) {
  if(requested==='blue'||requested==='rgb')return {mode:requested,note:`${requested==='rgb'?'RGB':'Blue'} · local selection`};
  if(settings?.waveformColor==='rgb'||settings?.waveformColor==='blue')return {mode:settings.waveformColor,note:`Din USB · ${settings.waveformColor==='rgb'?'RGB':'Blue'}`};
  return {mode:'blue',note:settings?.waveformColor==='three-band'?'USB: unsupported 3-band · fallback Blue':'USB setting unavailable · fallback Blue'};
}
