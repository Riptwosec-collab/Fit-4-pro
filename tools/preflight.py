#!/usr/bin/env python3
import json,pathlib,re,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[]; warnings=[]

def check(cond,msg,kind='error'):
    if not cond:
        (errors if kind=='error' else warnings).append(msg)

# Watch config
cfgp=ROOT/'watch-lite/entry/src/main/config.json'
try:
    cfg=json.loads(cfgp.read_text())
    check('liteWearable' in cfg['module']['deviceType'],'deviceType liteWearable missing')
except Exception as e:
    errors.append('config.json: '+str(e))

# HML parse
hmlp=ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.hml'
try:
    ET.fromstring(hmlp.read_text())
except Exception as e:
    errors.append('index.hml: '+str(e))

# PC-only catalog
catp=ROOT/'watch-lite/entry/src/main/js/MainAbility/common/featureCatalog.js'
cat=catp.read_text()
ids=set(re.findall(r"'([0-9]+)'\s*:\s*\{",cat))
check(len(ids)==22,'Expected 22 PC Remote Deck feature IDs, got '+str(len(ids)))
expected={'0','1','2','3','4','5','6','7','8','9','10','11','12','14','15','18','21','23','25','26','31','39'}
check(ids==expected,'PC Remote Deck feature IDs do not match expected set')

# Ensure Field Core modules are not exposed in watch UI/catalog
pc_text=(cat+'\n'+hmlp.read_text()).upper()
for forbidden in ['BIO TELEMETRY','MORNING DIAGNOSTIC','SPORTS HUD','RUN ANALYZER','AQUA RECON','TACTICAL CADDIE','BREADCRUMB','GEO ANCHOR','SOLAR SENTINEL','THERMAL LOAD','ALTITUDE SENTINEL','TRANSIT GUARDIAN','SKY SCANNER','EMERGENCY CORE','DEPTH HUD','TACTICAL NAV','SILENT NAV','ATMOSPHERIC']:
    check(forbidden not in pc_text,'Field Core module still exposed: '+forbidden)

# Placeholders
for f in [ROOT/'watch-lite/entry/src/main/js/MainAbility/common/constants.js',ROOT/'watch-lite/entry/src/main/config.json',ROOT/'android-companion/app/build.gradle',ROOT/'android-companion/app/src/main/AndroidManifest.xml']:
    t=f.read_text()
    if 'REPLACE_WITH_' in t:
        warnings.append('Identity placeholder remains in '+str(f.relative_to(ROOT)))

# SDK stub
sdk=ROOT/'watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js'
txt=sdk.read_text(errors='ignore')
if 'OFFLINE STUB' in txt:
    warnings.append('Huawei official wearengine.js has NOT been installed yet')

# PC token
agent_cfg=ROOT/'pc-agent/agent_config.json'
if not agent_cfg.exists():
    warnings.append('Run pc-agent/generate_token.py before first PC run')

print('PC REMOTE DECK FIT 4 PRO - PC ONLY PREFLIGHT')
print('Modules:',len(ids))
print('Errors:',len(errors)); [print(' ERROR:',x) for x in errors]
print('Warnings:',len(warnings)); [print(' WARN :',x) for x in warnings]
print('Result:', 'FAIL' if errors else ('READY AFTER CONFIG' if warnings else 'SOURCE READY'))
sys.exit(1 if errors else 0)
