#!/usr/bin/env python3
import json,pathlib,re,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[];warnings=[]
def check(cond,msg):
    if not cond: errors.append(msg)
try:
    cfg=json.loads((ROOT/'watch-lite/entry/src/main/config.json').read_text())
    check('liteWearable' in cfg['module']['deviceType'],'deviceType liteWearable missing')
    check(cfg['app']['version']['name'].startswith('7.0'),'Watch version is not V7.0')
    perms={x.get('name') for x in cfg['module'].get('reqPermissions',[])}
    for p in ['ohos.permission.VIBRATE','ohos.permission.LOCATION','ohos.permission.READ_HEALTH_DATA','ohos.permission.ACTIVITY_MOTION','ohos.permission.ACCELEROMETER','ohos.permission.GYROSCOPE']:
        check(p in perms,'permission missing: '+p)
except Exception as e: errors.append('config.json: '+str(e))
try:
    hml=(ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.hml').read_text()
    ET.fromstring(hml)
    for token in ['COMMAND','BIO','SPORT','FIELD','TACTICAL','SYSTEM','AUDIO MIXER PRO','WINDOW CENTER','MACRO DECK','NOTIFICATION BRIDGE','TRUST CENTER']:
        check(token in hml,'navigation/module missing: '+token)
except Exception as e: errors.append('index.hml: '+str(e))
cat=(ROOT/'watch-lite/entry/src/main/js/MainAbility/common/featureCatalog.js').read_text()
ids=set(re.findall(r"'([0-9]+)'\s*:\s*\{",cat))
check(len(ids)==54,'Expected 54 unified feature IDs, got '+str(len(ids)))
check(ids==set(str(i) for i in range(54)),'Feature IDs must be contiguous 0-53')
for required in ['BIO TELEMETRY','AQUA RECON','TACTICAL NAV','BREADCRUMB','GEO ANCHOR','SOLAR SENTINEL','EMERGENCY CORE','AUDIO MIXER PRO','WINDOW CENTER','MACRO DECK','NOTIFICATION BRIDGE','TRUST CENTER']:
    check(required in cat,'module missing: '+required)
watch=(ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.js').read_text()
for required in ['subscribeHeartRate','getLocation','subscribeCompass','subscribeBarometer','startBreadcrumb','startAirMouse','GET_AUDIO','GET_WINDOWS','GET_MACROS','GET_NOTIFICATIONS']:
    check(required in watch,'Watch runtime missing: '+required)
router=(ROOT/'android-companion/app/src/main/java/com/riptwosec/pcremotedeck/CommandRouter.java').read_text()
check('WATCH_LOCATION_RESULT' in router,'Watch location handoff missing')
for rel in ['pc-agent/discovery_service.py','pc-agent/pair_device.py','pc-agent/start_v6.ps1']:
    check((ROOT/rel).exists(),'helper missing: '+rel)
for f in [ROOT/'watch-lite/entry/src/main/js/MainAbility/common/constants.js',ROOT/'watch-lite/entry/src/main/config.json',ROOT/'android-companion/app/build.gradle',ROOT/'android-companion/app/src/main/AndroidManifest.xml']:
    if 'REPLACE_WITH_' in f.read_text(): warnings.append('Identity placeholder remains in '+str(f.relative_to(ROOT)))
sdk=ROOT/'watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js'
if 'OFFLINE STUB' in sdk.read_text(errors='ignore'): warnings.append('Huawei official wearengine.js has NOT been installed yet')
print('PC REMOTE DECK FIT 4 PRO V7.0 UNIFIED PREFLIGHT')
print('Errors:',len(errors));[print(' ERROR:',x) for x in errors]
print('Warnings:',len(warnings));[print(' WARN :',x) for x in warnings]
print('Result:','FAIL' if errors else ('READY AFTER CONFIG' if warnings else 'SOURCE READY'))
sys.exit(1 if errors else 0)
