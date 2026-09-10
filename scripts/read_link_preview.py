#!/usr/bin/env python3
"""Bounded stock preview read, PLAYER 4 only; no playback/firmware commands.
Original implementation based on Deep Symmetry protocol documentation.
Temporary client 1: requires absence during discovery; stops on collision.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import socket
import subprocess
import re
import threading
import time
from pathlib import Path
from probe_link_db import announcement, PORT_QUERY, GREETING, receive_exact

ROOT = Path(__file__).resolve().parents[1]


def message(tx, kind, args=()):
    if kind not in (0, 0x100, 0x2004, 0x2c04) or len(args) > 12:
        raise ValueError('Request not allowed')
    n = lambda v: b'\x11' + v.to_bytes(4, 'big')
    return (n(0x872349ae) + n(tx) + b'\x10' + kind.to_bytes(2, 'big') +
            b'\x0f' + bytes([len(args)]) + b'\x14\0\0\0\x0c' +
            bytes([6] * len(args) + [0] * (12-len(args))) + b''.join(n(v) for v in args))


def read_message(sock):
    deadline = time.monotonic()+5
    def read(n):
        result=bytearray()
        while len(result)<n:
            left=deadline-time.monotonic()
            if left<=0: raise TimeoutError('Message deadline exceeded')
            sock.settimeout(left)
            part=sock.recv(n-len(result))
            if not part: raise EOFError('Incomplete dbserver message')
            result.extend(part)
        return bytes(result)
    def field():
        kind=read(1)[0]
        if kind in (15,16,17): return kind,int.from_bytes(read({15:1,16:2,17:4}[kind]),'big')
        if kind != 20: raise ValueError('Unexpected field type')
        size=int.from_bytes(read(4),'big')
        if size>65536: raise ValueError('Response exceeds preview limit')
        return kind,read(size)
    if field()!=(17,0x872349ae): raise ValueError('Bad message magic')
    tx=field();kind=field();count=field();tags=field()
    if tx[0]!=17 or kind[0]!=16 or count[0]!=15 or count[1]>12 or tags[0]!=20 or len(tags[1])!=12:
        raise ValueError('Invalid header')
    args=[]
    for i in range(count[1]):
        tag=tags[1][i]
        # Stock server omits the blob entirely when preceding payload length is zero.
        if tag==3 and i==3 and args[2]==0:
            args.append(b'');continue
        f,v=field()
        if (tag,f) not in ((6,17),(3,20)): raise ValueError('Argument type mismatch')
        args.append(v)
    return tx[1],kind[1],args


def keepalive(ip, mac):
    d=bytearray(54);d[:11]=b'Qspt1WmJOL\x06'
    d[12:32]=b'xdj-preview-read'.ljust(20,b'\0')
    d[32:38]=bytes.fromhex('010200360101')
    d[38:44]=bytes.fromhex(mac.replace(':',''));d[44:48]=socket.inet_aton(ip)
    d[48:54]=bytes.fromhex('020000000164')
    return bytes(d)


def status(data):
    if len(data)<0x30 or data[:11]!=b'Qspt1WmJOL\x0a' or data[0x21]!=4 or data[0x24]!=4:
        return None
    return {'source_player':data[0x28], 'source_slot':data[0x29], 'track_type':data[0x2a],
            'track_id':int.from_bytes(data[0x2c:0x30],'big')}


def run():
    report={'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'target_player':4,'temporary_client':1,'stages':[],'announcements_sent':0}
    stop=threading.Event();collision=threading.Event();worker=None
    try:
        interface=subprocess.check_output(['ifconfig','en10'],text=True)
        ip=re.search(r'\binet (\S+)',interface).group(1)
        mac=re.search(r'\bether (\S+)',interface).group(1)
        broadcast=re.search(r'\bbroadcast (\S+)',interface).group(1)
        if 'status: active' not in interface: raise ValueError('en10 not active')
        with contextlib.ExitStack() as stack:
            ann=stack.enter_context(socket.socket(socket.AF_INET,socket.SOCK_DGRAM))
            ann.bind(('',50000));ann.settimeout(.2)
            devices={};deadline=time.monotonic()+6
            while time.monotonic()<deadline:
                try:d,peer=ann.recvfrom(2048)
                except socket.timeout:continue
                info=announcement(d)
                if info:devices[peer[0]]=info
            if any(v['player_number']==1 for v in devices.values()): raise ValueError('Client number 1 occupied')
            targets=[a for a,v in devices.items() if v['player_number']==4]
            if len(targets)!=1 or devices[targets[0]]['model']!='XDJ-1000MK2': raise ValueError('Target absent or ambiguous')
            address=targets[0];report['target_ip']=address
            udp=stack.enter_context(socket.socket(socket.AF_INET,socket.SOCK_DGRAM))
            udp.bind((ip,50002));udp.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1);udp.settimeout(.2)
            packet=keepalive(ip,mac)
            def announce():
                next_send=0;end=time.monotonic()+25
                while not stop.is_set() and time.monotonic()<end:
                    try:
                        if time.monotonic()>=next_send:
                            udp.sendto(packet,(broadcast,50000));report['announcements_sent']+=1;next_send=time.monotonic()+1.5
                        try:d,peer=ann.recvfrom(2048)
                        except socket.timeout:continue
                        info=announcement(d)
                        if info and info['player_number']==1 and peer[0]!=ip:
                            collision.set();stop.set()
                    except OSError:
                        stop.set()
            worker=threading.Thread(target=announce,daemon=True);worker.start()
            try:
                loaded=None;deadline=time.monotonic()+8
                while time.monotonic()<deadline and not stop.is_set():
                    try:d,peer=udp.recvfrom(2048)
                    except socket.timeout:continue
                    if peer[0]==address:
                        loaded=status(d)
                        if loaded: break
                if not loaded: raise ValueError('No valid PLAYER 4 status received')
                report['loaded_track']=loaded;report['stages'].append('status_received')
                if loaded['source_player']!=4 or loaded['source_slot']!=3 or loaded['track_type']!=1 or not loaded['track_id']:
                    raise ValueError('Loaded track is not a rekordbox track from PLAYER 4 USB; no query sent')
                with socket.create_connection((address,12523),timeout=3) as tcp:
                    tcp.sendall(PORT_QUERY);port=int.from_bytes(receive_exact(tcp,2),'big')
                if port in (0,65535):raise ValueError('Database not available')
                with socket.create_connection((address,port),timeout=3) as tcp:
                    def send(tx,kind,args=()):
                        if stop.is_set() or collision.is_set():raise ValueError('Client stopped or number collision')
                        tcp.sendall(message(tx,kind,args))
                    tcp.sendall(GREETING)
                    if receive_exact(tcp,5)!=GREETING:raise ValueError('Bad greeting')
                    send(0xfffffffe,0,[1]);tx,kind,args=read_message(tcp)
                    if (tx,kind,args)!=(0xfffffffe,0x4000,[0,4]):raise ValueError('Setup identity mismatch')
                    report['stages'].append('database_context_verified')
                    try:
                        for tx,req,expected,params,name in [
                            (1,0x2004,0x4402,[0x01080301,1,loaded['track_id'],0],'blue'),
                            (2,0x2c04,0x4f02,[0x01010301,loaded['track_id'],0x34565750,0x00545845],'rgb')]:
                            send(tx,req,params);rt,kind,args=read_message(tcp)
                            if rt!=tx or kind!=expected or len(args)<4 or args[0]!=req or not isinstance(args[3],bytes) or args[2]!=len(args[3]):
                                raise ValueError('Unexpected preview response')
                            payload=args[3]
                            output=ROOT / ('private/owner/link-preview-'+name+'.bin');output.write_bytes(payload)
                            report[name]={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
                    finally:
                        if not collision.is_set():tcp.sendall(message(0xfffffffe,0x100))
                report['result']='preview_responses_received'
            finally:
                stop.set();worker.join(timeout=1)
    except (OSError,ValueError,EOFError,AttributeError) as exc:
        report['result']='not_verified';report['error']=str(exc)
    report['collision_detected']=collision.is_set()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-player-4',action='store_true',required=True);p.parse_args()
    report=run();out=ROOT/'private/owner/player4-preview-read.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='target_ip'},indent=2))
