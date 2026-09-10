#!/usr/bin/env python3
"""Read cached macOS IORegistry properties. Never opens USB/HID endpoints."""
import argparse,datetime,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP_SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
def analyze(text,image=None):
    def number(name):
        m=re.search(r'"'+name+r'" = (\d+)',text)
        return int(m[1]) if m else None
    if number('idVendor')!=0x2b73 or number('idProduct')!=0x11:raise ValueError('Expected XDJ-1000MK2 USB identity absent')
    descriptor=re.search(r'"ReportDescriptor" = <([0-9a-f]+)>',text)
    if not descriptor:raise ValueError('Cached HID descriptor unavailable')
    raw=bytes.fromhex(descriptor[1])
    interfaces=[]
    for block in re.split(r'\+-o ',text):
        if '<class IOUSBHostInterface,' not in block:continue
        props={}
        for key in ['bInterfaceNumber','bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol','bNumEndpoints']:
            m=re.search(r'"'+key+r'" = (\d+)',block)
            if m:props[key]=int(m[1])
        interfaces.append(props)
    r={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'cached IORegistry properties only; no endpoint open, claim, USB control/HID output or network request','vid':number('idVendor'),'pid':number('idProduct'),'bcdDevice':number('bcdDevice'),'interfaces':interfaces,'hid':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'max_input_report':number('MaxInputReportSize'),'max_output_report':number('MaxOutputReportSize'),'max_feature_report':number('MaxFeatureReportSize')},'serial_interface_in_observed_configuration':any(i.get('bInterfaceClass') in (2,10) for i in interfaces),'device_code_execution':False}
    if image is not None:
        digest=hashlib.sha256(image).hexdigest()
        if digest!=APP_SHA:raise ValueError('Unexpected firmware application hash')
        r['firmware_match']={'sha256':digest,'address_space':'file offsets in unpacked main-040000 v1.44','descriptor_offsets':[m.start() for m in re.finditer(re.escape(raw),image)],'scope':'descriptor match only, not a full installed firmware dump'}
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path);a=p.parse_args()
    if a.snapshot:raw=a.snapshot.read_text()
    else:
        raw=subprocess.run(['ioreg','-p','IOService','-r','-n','XDJ-1000MK2','-l','-w','0'],capture_output=True,text=True,check=True).stdout
        dest=ROOT/'private/owner/usb-xdj-services.txt';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(raw)
    image=ROOT/'private/extracted/v144/main-040000-unpacked.bin'
    r=analyze(raw,image.read_bytes() if image.exists() else None)
    (ROOT/'evidence/usb-player.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
