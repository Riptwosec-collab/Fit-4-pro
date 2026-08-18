#!/usr/bin/env python3
import json,pathlib,re,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[];warnings=[]
def check(cond,msg):
    if not cond: errors.append(msg)

try:
    cfg=json.loads((ROOT/'watch-lite/entry/src/main/config.json').read_text(encoding='utf-8'))
    check('liteWearable' in cfg['module']['deviceType'],'deviceType liteWearable missing')
    check(cfg['app']['version']['name'].startswith('8.0'),'Watch version is not V8.0')
    perms={x.get('name') for x in cfg['module'].get('reqPermissions',[])}
    for p in ['ohos.permission.VIBRATE','ohos.permission.ACTIVITY_MOTION','ohos.permission.ACCELEROMETER','ohos.permission.GYROSCOPE']:
        check(p in perms,'permission missing: '+p)
    for p in ['ohos.permission.LOCATION','ohos.permission.READ_HEALTH_DATA']:
        check(p not in perms,'FIELD CORE permission leaked into PC Remote Deck: '+p)
except Exception as e: errors.append('config.json: '+str(e))

try:
    hml=(ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.hml').read_text(encoding='utf-8')
    ET.fromstring(hml)
    for token in ['PC REMOTE DECK','REMOTE DECK MODULES','commandState','retryAllowed']:
        check(token in hml,'V8 watch UI token missing: '+token)
except Exception as e: errors.append('index.hml: '+str(e))

cat=(ROOT/'watch-lite/entry/src/main/js/MainAbility/common/featureCatalog.js').read_text(encoding='utf-8')
ids=set(re.findall(r"'([0-9]+)'\s*:\s*\{",cat))
expected={'0','1','2','3','4','5','6','7','8','9','10','11','12','14','15','18','21','23','25','26','31','39','49','50','51','52','53','54','55'}
check(ids==expected,'PC Remote V8 feature IDs mismatch: '+str(sorted(ids,key=int)))
for banned in ["category:'BIO'","category:'SPORT'","category:'FIELD'","category:'TACTICAL'","category:'OUTDOOR'"]:
    check(banned not in cat,'FIELD CORE category leaked into PC Remote Deck: '+banned)
for required in ['PC MONITOR PRO 2.0','AIR MOUSE PRO 3.0','WINDOW CENTER 2.0','AUDIO MIXER PRO 2.0','MACRO DECK 2.0','APP LAUNCHER PRO 2.0','CONTEXT ENGINE 2.0','VOICE COMMAND PRO 2.0','MOTION COMMAND 2.0','WI-FI RECON PRO 2.0','NOTIFICATION BRIDGE 2.0','TRUST CENTER 2.0','PC CONTROL HUB','PC REMOTE SETTINGS']:
    check(required in cat,'module missing: '+required)

watch=(ROOT/'watch-lite/entry/src/main/js/MainAbility/pages/index/index.js').read_text(encoding='utf-8')
for required in ['startAirMouse','airMousePrecision','MOUSE_LEFT_DOWN','MOUSE_DOUBLE','trainMotion','motionConfidence','GET_CONTROL_HUB','GET_DASHBOARD_PRO','GET_CONTEXT_PRO','GET_AUDIO_PRO','GET_WINDOWS_PRO','GET_MACROS_V2','GET_NOTIFICATIONS_PRO','GET_TRUST_PRO','retryLast']:
    check(required in watch,'Watch runtime missing: '+required)
for banned in ['@system.geolocation','subscribeHeartRate','subscribeCompass','subscribeBarometer','startBreadcrumb']:
    check(banned not in watch,'FIELD CORE runtime leaked into PC Remote Deck: '+banned)

for rel in ['pc-agent/pc_agent_pro.py','pc-agent/pro_engine.py','pc-agent/pro_support.py','pc-agent/pro_macro.py','pc-agent/discovery_service.py','pc-agent/pair_device.py','pc-agent/start_v6.ps1','android-companion/app/src/main/java/com/riptwosec/pcremotedeck/VoiceCommandEngine.java','android-companion/app/src/main/java/com/riptwosec/pcremotedeck/WifiReconManager.java']:
    check((ROOT/rel).exists(),'V8 file missing: '+rel)

try:
    pro=(ROOT/'pc-agent/pro_engine.py').read_text(encoding='utf-8')
    for token in ['EventBus','GET_DASHBOARD_PRO','GET_TELEMETRY_HISTORY','GET_TOP_PROCESSES','WINDOW_SNAP_LEFT','WINDOW_MOVE_MONITOR','GET_AUDIO_PRO','GET_MACROS_V2','GET_APPS_PRO','GET_CONTEXT_PRO','GET_NOTIFICATIONS_PRO','GET_TRUST_PRO','TRUST_ROTATE_TOKEN']:
        check(token in pro,'PC Pro engine missing: '+token)
    check('arbitrary raw shell' not in pro.lower(),'unexpected raw-shell wording in Pro engine')
except Exception as e: errors.append('pro_engine.py: '+str(e))

try:
    manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    check(manifest.get('pcRemoteOnly') is True,'SOURCE_MANIFEST pcRemoteOnly must be true')
    check(manifest.get('fieldCoreSeparateApplication') is True,'SOURCE_MANIFEST must keep FIELD CORE separate')
except Exception as e: errors.append('SOURCE_MANIFEST.json: '+str(e))

for f in [ROOT/'watch-lite/entry/src/main/js/MainAbility/common/constants.js',ROOT/'watch-lite/entry/src/main/config.json',ROOT/'android-companion/app/build.gradle',ROOT/'android-companion/app/src/main/AndroidManifest.xml']:
    if f.exists() and 'REPLACE_WITH_' in f.read_text(encoding='utf-8',errors='ignore'): warnings.append('Identity placeholder remains in '+str(f.relative_to(ROOT)))
sdk=ROOT/'watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js'
if sdk.exists() and 'OFFLINE STUB' in sdk.read_text(errors='ignore'): warnings.append('Huawei official wearengine.js has NOT been installed yet')

print('PC REMOTE DECK FIT 4 PRO V8.0 PRO CONTROL PREFLIGHT')
print('Errors:',len(errors));[print(' ERROR:',x) for x in errors]
print('Warnings:',len(warnings));[print(' WARN :',x) for x in warnings]
print('Result:','FAIL' if errors else ('READY AFTER CONFIG' if warnings else 'SOURCE READY'))
sys.exit(1 if errors else 0)
