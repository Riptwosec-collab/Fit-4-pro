# Build & Install — HUAWEI WATCH FIT 4 Pro

## 1) เตรียมระบบ

ต้องมี:
- HUAWEI WATCH FIT 4 Pro ที่จับคู่กับ HUAWEI Health
- Android Phone สำหรับ Companion
- Huawei Developer account ที่เปิดใช้ Wear Engine
- DevEco Studio สำหรับ Lite Wearable project
- Android Studio + Android SDK
- Windows PC + Python 3

## 2) ตั้งค่า PC Agent

บน Windows เปิด PowerShell/CMD ใน `pc-agent/`:

```powershell
python generate_token.py
python pc_agent.py
```

`generate_token.py` จะสร้าง `agent_config.json` พร้อม token แบบสุ่ม

Default server:
- Port: `8765`
- Bind: ตาม `agent_config.json`

ถ้า Windows Firewall บล็อก ให้ Allow inbound TCP 8765 เฉพาะ Private network/LAN ที่ไว้ใจได้

> อย่า expose port 8765 ออก Internet โดยตรง

## 3) สร้าง Huawei identities

ต้องมีค่า:
- Huawei App ID ของ Android Companion
- Android SHA-256 signing fingerprint
- Lite Wearable/Watch SHA-256 signing fingerprint

จาก root project:

```bash
python tools/configure_identity.py \
  --huawei-app-id YOUR_HUAWEI_APP_ID \
  --android-fingerprint AA:BB:... \
  --watch-fingerprint 11:22:...
```

Script จะ patch:
- Android `com.huawei.hms.client.appid`
- Android `WATCH_FINGERPRINT`
- Watch `PHONE_FINGERPRINT`
- Watch `supportLists`

## 4) ใส่ Huawei Wear Engine SDK ฝั่ง Lite Wearable

ไฟล์ `watch-lite/.../wearengine/wearengine.js` ที่มากับ package นี้เป็น **offline stub** เพื่อให้โครง source เปิดอ่านได้เท่านั้น

ให้ดาวน์โหลด Wear Engine SDK for Lite Wearable จาก Huawei Developer แล้วรัน:

```bash
python tools/install_wearengine_sdk.py /path/to/wearengine.js
```

ห้ามใช้ stub สำหรับ production

## 5) Build Android Companion

เปิดโฟลเดอร์:

`android-companion/`

ด้วย Android Studio

ก่อน build:
1. Sync Gradle
2. ตรวจ Huawei Maven repository
3. ตรวจ App ID / package / fingerprint
4. Sign APK ด้วย certificate เดียวกับ fingerprint ที่ตั้งไว้
5. Install APK บน Android Phone ที่จับคู่ Watch อยู่

ใน Companion:
1. ใส่ IP ของ Windows PC
2. ใส่ token จาก `pc-agent/agent_config.json`
3. กด `SAVE PC LINK`
4. กด `AUTHORIZE WEAR ENGINE`
5. กด `FIND / REGISTER WATCH`
6. อนุญาต Wi‑Fi/Location ตาม Android version
7. ทดสอบ `SCAN WI-FI + SYNC WATCH`

## 6) Build Watch Lite Wearable

เปิด:

`watch-lite/`

ด้วย DevEco Studio

ตรวจ:
- Device Type = `liteWearable`
- Design width = `480`
- Bundle = `com.riptwosec.pcremotedeck.watch`
- `supportLists` ตรงกับ Android package + Android fingerprint
- Wear Engine SDK จริงถูกวางแทน stub
- Signing profile ตรงกับ fingerprint ที่ Android Companion ใช้เป็น `WATCH_FINGERPRINT`

จากนั้น Build HAP และติดตั้งผ่าน workflow การ Debug/Install Lite Wearable ของ Huawei

## 7) First run test

ลำดับทดสอบแนะนำ:

1. เปิด PC Agent
2. เปิด Android Companion
3. Authorize Wear Engine
4. Discover/Register Watch
5. เปิด PC Remote Deck บน Watch
6. กด `LOCK`, `PLAY`, `MUTE` เพื่อทดสอบ end-to-end
7. เปิด `WI-FI RECON` → Scan จาก Watch → ดูผลที่ Phone ส่งกลับ
8. เปิด `BIO TELEMETRY` → Start HR
9. เปิด `MOTION COMMAND` → Calibrate → Arm
10. เปิด `TACTICAL NAV` → Compass
11. เปิด `ATMOSPHERIC` → Pressure

## 8) ความหมายของสถานะ

- `WATCH` = ประมวลผลบน Watch API
- `PHONE` = ต้องใช้ Android Companion
- `PC` = ต้องใช้ PC Agent
- `CACHED` = ใช้ข้อมูลล่าสุดที่ cache
- `API GATED` = Hardware อาจมี แต่ Third-party API/permission ยังไม่พร้อม
- `UNAVAILABLE` = ไม่เปิดให้ใช้ใน build ปัจจุบัน

## 9) Troubleshooting

### PHONE LINK FAILED
- Android Companion ยังไม่ได้ Authorize Wear Engine
- Watch package/fingerprint ไม่ตรง
- Watch app ยังไม่ได้ติดตั้ง

### WI-FI PERMISSION REQUIRED
- เปิด permission ที่ Companion ขอ
- Android รุ่นใหม่อาจมีข้อกำหนด Nearby Wi‑Fi / Location ตาม API level

### SCAN LIMITED
- Android กำลัง throttle Wi‑Fi scan
- App จะใช้ recent scan results และระบุว่า CACHED

### PC command ไม่ทำงาน
- ตรวจ PC IP
- ตรวจ token
- ตรวจ Windows Firewall
- PC และ Phone ต้องเข้าถึงกันผ่าน LAN

### DEPTH / LIGHT SENSOR ไม่ทำงาน
- อย่าสรุปจาก Hardware spec อย่างเดียวว่ Third-party Lite Wearable API เปิด raw access
- หน้าดังกล่าวจะใช้ API GATED / UNAVAILABLE / Phone fallback ตาม capability
