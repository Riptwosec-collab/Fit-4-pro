#!/usr/bin/env python3
import argparse, pathlib, shutil, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
DEST=ROOT/'watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js'
p=argparse.ArgumentParser(description='Install Huawei official Lite Wearable wearengine.js into PC Remote Deck')
p.add_argument('wearengine_js',help='Path to wearengine.js downloaded from Huawei Developer')
a=p.parse_args(); src=pathlib.Path(a.wearengine_js).expanduser().resolve()
if not src.is_file(): raise SystemExit('File not found: '+str(src))
data=src.read_bytes()
if b'P2pClient' not in data or b'Message' not in data: raise SystemExit('This file does not look like Huawei Lite Wearable wearengine.js')
shutil.copy2(src,DEST)
print('Installed:',DEST)
print('SHA256:',hashlib.sha256(data).hexdigest())
