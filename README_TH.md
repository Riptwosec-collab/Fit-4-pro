# PC Remote Deck — HUAWEI WATCH FIT 4 Pro REAL V5

เวอร์ชันนี้แปลงจาก V4 HTML prototype ให้เป็นโครงสร้างสำหรับใช้งานกับ HUAWEI WATCH FIT 4 Pro แบบจริง โดยแยกงานตามอุปกรณ์:

- `watch-lite/` — Lite Wearable app สำหรับ Watch (480×408)
- `android-companion/` — Android Phone Companion + Huawei Wear Engine + Wi‑Fi Recon + Voice handoff
- `pc-agent/` — Windows Agent สำหรับคำสั่ง PC แบบ whitelist + authentication
- `legacy/pc_remote_deck_os_masterpiece_field_wifi_v4.html.gz` — V4 HTML เดิมแบบ gzip เก็บไว้เป็น baseline เพื่อ Zero Regression

> เป้าหมายคือ **PHONE SCANS / WATCH COMMANDS / PC EXECUTES** และไม่แสดงข้อมูล Sensor/API ที่เข้าถึงไม่ได้เป็นค่าจริง

## ฟังก์ชันหลักที่ต่อกับ FIT 4 Pro แล้วใน source

### Watch-native / local-first
- UI เป้าหมาย 480×408
- Haptic feedback
- Heart-rate subscription เมื่อ API/permission พร้อม
- Accelerometer + Gyroscope สำหรับ Motion Command
- Compass / heading
- Barometer / pressure
- Location capture / Geo Anchor เมื่อ runtime เปิด API/permission
- Tactical red/white screen light และ SOS flash safety flow
- 49 Module catalog เดิมจาก V4 ยังคงอยู่ครบ

### Phone-assisted
- Huawei Wear Engine P2P bridge
- Wi‑Fi Recon จาก Android Wi‑Fi APIs
- OPEN / SECURED / LOGIN REQUIRED / FREE VERIFIED / NO INTERNET classification
- Android network validation + captive portal state
- Android speech recognition สำหรับ Voice Command แบบ whitelist
- Provider bridge สำหรับ Weather / UV / Transit / Internet data ในอนาคต

### PC-assisted
- Lock PC
- Play/Pause / Next / Previous / Mute / Volume
- Show Desktop / Alt+Tab / Ctrl+C / Ctrl+V
- Mouse click / scroll
- Screenshot
- App Launcher บางรายการ
- Battle Station / Deep Focus protocol
- Signed command request ด้วย token + HMAC + timestamp + nonce

## สิ่งที่ยังต้องใส่ก่อน Build ลงเครื่องจริง

1. Huawei Developer App ID
2. SHA-256 fingerprint ของ Android Companion
3. SHA-256 fingerprint ของ Watch/Lite Wearable signing certificate
4. Official Huawei Wear Engine Lite Wearable `wearengine.js`
5. DevEco Studio + signing profile สำหรับ Lite Wearable
6. Android Studio/Android SDK สำหรับ build APK

ใช้ script:

```bash
python tools/configure_identity.py \
  --huawei-app-id YOUR_APP_ID \
  --android-fingerprint YOUR_ANDROID_SHA256 \
  --watch-fingerprint YOUR_WATCH_SHA256
```

จากนั้นติดตั้ง Wear Engine SDK ฝั่ง Watch:

```bash
python tools/install_wearengine_sdk.py /path/to/official/wearengine.js
```

ตรวจ preflight:

```bash
python tools/preflight.py
```

ดูขั้นตอนเต็มที่ `docs/BUILD_AND_INSTALL_TH.md`

## สำคัญ

โปรเจกต์นี้ไม่ได้สร้าง `.hap` หรือ `.apk` ที่ signed สำเร็จใน environment ปัจจุบัน เพราะไม่มี DevEco Studio, Android SDK และ signing identity ของบัญชี Huawei ของผู้ใช้ จึงส่งเป็น **source-ready project** ที่พร้อมนำไปเปิดใน IDE และใส่ identity จริงแทนการสร้าง binary ปลอม


## Legacy baseline ใน GitHub

เพื่อให้ repo เบา ไฟล์ V4 HTML baseline ถูกเก็บแบบ gzip:

```bash
gzip -dk legacy/pc_remote_deck_os_masterpiece_field_wifi_v4.html.gz
```

หลังแตกไฟล์จะได้ `legacy/pc_remote_deck_os_masterpiece_field_wifi_v4.html` ต้นฉบับ
