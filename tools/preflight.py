#!/usr/bin/env python3
import json,pathlib,re,sys,xml.etree.ElementTree as ET,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[]; warnings=[]
def check(cond,msg,kind='error'):
    if not cond:(errors if kind=='error' else warnings).append(msg)
# Watch config
cfgp=ROOT/'watch-lite/entry/src/main/config.json'
try: cfg=json.loads(cfgp.read_text());check('liteWearable' in cfg['module']['deviceType'],'deviceType liteWearable missing')
except Exception as e: errors.append('config.json: '+str(e))
# HML parse
try: ET.fromstring((ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.hml').read_text())
except Exception as e: errors.append('index.hml: '+str(e))
cat=(ROOT/'watch-lite/entry/src/main/js/MainAbility/common/featureCatalog.js').read_text()
ids=set(re.findall(r"'([0-9]+)'\s*:\s*\{",cat));check(len(ids)==49,'Expected 49 feature IDs, got '+str(len(ids)))
# placeholders
for f in [ROOT/'watch-lite/entry/src/main/js/MainAbility/common/constants.js',ROOT/'watch-lite/entry/src/main/config.json',ROOT/'android-companion/app/build.gradle',ROOT/'android-companion/app/src/main/AndroidManifest.xml']:
    t=f.read_text();
    if 'REPLACE_WITH_' in t:warnings.append('Identity placeholder remains in '+str(f.relative_to(ROOT)))
# SDK stub
sdk=ROOT/'watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js';txt=sdk.read_text(errors='ignore')
if 'OFFLINE STUB' in txt:warnings.append('Huawei official wearengine.js has NOT been installed yet')
# PC token
cfg=ROOT/'pc-agent/agent_config.json'
if not cfg.exists(): warnings.append('Run pc-agent/generate_token.py before first PC run')
print('PC REMOTE DECK FIT 4 PRO PREFLIGHT')
print('Errors:',len(errors));[print(' ERROR:',x) for x in errors]
print('Warnings:',len(warnings));[print(' WARN :',x) for x in warnings]
print('Result:', 'FAIL' if errors else ('READY AFTER CONFIG' if warnings else 'SOURCE READY'))
sys.exit(1 if errors else 0)
