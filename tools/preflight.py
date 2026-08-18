#!/usr/bin/env python3
import json,pathlib,re,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[];warnings=[]
def check(cond,msg,kind='error'):
    if not cond:(errors if kind=='error' else warnings).append(msg)
try:
    cfg=json.loads((ROOT/'watch-lite/entry/src/main/config.json').read_text())
    check('liteWearable' in cfg['module']['deviceType'],'deviceType liteWearable missing')
    check(cfg['app']['version']['name'].startswith('6.'),'Watch version is not V6')
except Exception as e: errors.append('config.json: '+str(e))
try: ET.fromstring((ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.hml').read_text())
except Exception as e: errors.append('index.hml: '+str(e))
cat=(ROOT/'watch-lite/entry/src/main/js/MainAbility/common/featureCatalog.js').read_text()
ids=set(re.findall(r"'([0-9]+)'\s*:\s*\{",cat));check(len(ids)==27,'Expected 27 PC Remote Deck feature IDs, got '+str(len(ids)))
for banned in ['BREADCRUMB','GEO ANCHOR','SOLAR SENTINEL','AQUA RECON','BIO TELEMETRY','TACTICAL NAV']:
    check(banned not in cat,'Field Core module leaked into PC Remote Deck: '+banned)
agent=(ROOT/'pc-agent/pc_agent.py').read_text()
for required in ['GET_DASHBOARD','GET_WINDOWS','GET_AUDIO','GET_NETWORK','GET_CONTEXT','GET_MACROS','GET_NOTIFICATIONS','MOUSE_MOVE']:
    check(required in agent,'V6 agent command missing: '+required)
check('COMMAND NOT WHITELISTED' in agent,'Whitelist guard missing')
for f in [ROOT/'watch-lite/entry/src/main/js/MainAbility/common/constants.js',ROOT/'watch-lite/entry/src/main/config.json',ROOT/'android-companion/app/build.gradle',ROOT/'android-companion/app/src/main/AndroidManifest.xml']:
    if 'REPLACE_WITH_' in f.read_text():warnings.append('Identity placeholder remains in '+str(f.relative_to(ROOT)))
sdk=ROOT/'watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js'
if 'OFFLINE STUB' in sdk.read_text(errors='ignore'):warnings.append('Huawei official wearengine.js has NOT been installed yet')
if not (ROOT/'pc-agent/agent_config.json').exists():warnings.append('Run pc-agent/generate_token.py before first PC run')
print('PC REMOTE DECK FIT 4 PRO V6 PREFLIGHT')
print('Errors:',len(errors));[print(' ERROR:',x) for x in errors]
print('Warnings:',len(warnings));[print(' WARN :',x) for x in warnings]
print('Result:', 'FAIL' if errors else ('READY AFTER CONFIG' if warnings else 'SOURCE READY'))
sys.exit(1 if errors else 0)
