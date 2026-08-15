#!/usr/bin/env python3
import argparse,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Configure Huawei app identities/fingerprints without editing multiple files')
p.add_argument('--huawei-app-id',required=True)
p.add_argument('--android-fingerprint',required=True,help='Phone app fingerprint used by Lite Wearable Wear Engine')
p.add_argument('--watch-fingerprint',required=True,help='Lite Wearable fingerprint used by Android Wear Engine')
a=p.parse_args()
# Watch constant
c=ROOT/'watch-lite/entry/src/main/js/MainAbility/common/constants.js'
s=c.read_text();s=s.replace('REPLACE_WITH_ANDROID_SHA256_FINGERPRINT',a.android_fingerprint);c.write_text(s)
# Watch metadata support list
cfgp=ROOT/'watch-lite/entry/src/main/config.json';cfg=json.loads(cfgp.read_text());cfg['module']['metaData']['customizeData'][0]['value']='com.riptwosec.pcremotedeck:'+a.android_fingerprint;cfgp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
# Android watch fingerprint
b=ROOT/'android-companion/app/build.gradle';s=b.read_text();s=s.replace('REPLACE_WITH_WATCH_SHA256_FINGERPRINT',a.watch_fingerprint);b.write_text(s)
# Android app id
m=ROOT/'android-companion/app/src/main/AndroidManifest.xml';s=m.read_text();s=s.replace('REPLACE_WITH_HUAWEI_APP_ID',a.huawei_app_id);m.write_text(s)
print('Identity configuration updated.')
