# Build & Install — PC Remote Deck / HUAWEI WATCH FIT 4 Pro

โปรเจกต์นี้เหลือเฉพาะ **PC Remote Deck** แล้ว ไม่รวม Field Core / Bio / Sport / Outdoor modules

## 1) เตรียมระบบ

ต้องมี:
- HUAWEI WATCH FIT 4 Pro ที่จับคู่กับ HUAWEI Health
- Android Phone สำหรับ Companion
- Huawei Developer account ที่เปิดใช้ Wear Engine
- DevEco Studio
- Android Studio + Android SDK
- Windows PC + Python 3

## 2) ตั้งค่า PC Agent

เปิด PowerShell/CMD ใน `pc-agent/`:

```powershell
python generate_token.py
python pc_agent.py
```

Default port: `8765`

ถ้า Windows Firewall บล็อก ให้ Allow inbound TCP 8765 เฉพาะ Private LAN ที่ไว้ใจได้

> ห้าม expose port 8765 ออก Internet โดยตรง

## 3) ตั้ง Huawei identities

ต้องมี:
- Huawei App ID ของ Android Companion
- Android SHA-256 signing fingerprint
- Lite Wearable SHA-256 signing fingerprint

จาก root project:

```powershell
python tools/configure_identity.py `
  --huawei-app-id YOUR_HUAWEI_APP_ID `
  --android-fingerprint AA:BB:... `
  --watch-fingerprint 11:22:...
```

## 4) ใส่ Wear Engine SDK ฝั่ง Watch

`watch-lite/.../wearengine/wearengine.js` ใน repo เป็น offline stub เท่านั้น

ดาวน์โหลด official Wear Engine SDK for Lite Wearable แล้วรัน:

```powershell
python tools/install_wearengine_sdk.py C:\path\to\wearengine.js
```

## 5) Build Android Companion

เปิด `android-companion/` ด้วย Android Studio

ตรวจ:
1. Gradle sync สำเร็จ
2. Huawei Maven repository พร้อม
3. App ID / package / fingerprint ถูกต้อง
4. Sign APK ด้วย certificate ที่ลงทะเบียน
5. Install APK บน Android Phone ที่จับคู่กับ Watch

ใน Companion:
1. ใส่ IP ของ Windows PC
2. ใส่ token จาก `pc-agent/agent_config.json`
3. `SAVE PC LINK`
4. `AUTHORIZE WEAR ENGINE`
5. `FIND / REGISTER WATCH`
6. อนุญาต Wi-Fi/Location permissions ที่ Android ต้องใช้สำหรับ Wi-Fi Recon

## 6) Build Watch Lite Wearable

เปิด `watch-lite/` ด้วย DevEco Studio

ตรวจ:
- Device type = `liteWearable`
- Design width = `480`
- Bundle = `com.riptwosec.pcremotedeck.watch`
- `supportLists` ตรงกับ Android package + fingerprint
- Official `wearengine.js` ถูกติดตั้งแล้ว
- Signing profile ตรงกับ `WATCH_FINGERPRINT`

จากนั้น Build/Run ผ่าน workflow Lite Wearable ของ DevEco Studio

## 7) First Run Test

ทดสอบตามลำดับ:

1. เปิด PC Agent
2. เปิด Android Companion
3. Authorize Wear Engine
4. Discover/Register Watch
5. เปิด PC Remote Deck บน Watch
6. ทดสอบ `LOCK`
7. ทดสอบ `PLAY / MUTE / NEXT / PREV`
8. ทดสอบ `SCREENSHOT`
9. ทดสอบ `ALT+TAB / WIN+D`
10. เปิด `APP LAUNCHER`
11. เปิด `MOTION COMMAND` → Calibrate → Arm
12. เปิด `WI-FI RECON` → Scan → ตรวจข้อมูลจาก Phone
13. เปิด `VOICE COMMAND`
14. ทดสอบ `BATTLE STATION / DEEP FOCUS`

## 8) Motion Command

```text
FLICK RIGHT  → NEXT TRACK
FLICK LEFT   → PREVIOUS TRACK
DOUBLE TWIST → PLAY / PAUSE
SHAKE        → MUTE
```

มี confidence threshold + cooldown ลด false positive

## 9) Troubleshooting

### PHONE LINK FAILED
- Wear Engine ยังไม่ได้ authorize
- package/fingerprint ไม่ตรง
- Watch app ยังไม่ได้ติดตั้ง

### WI-FI PERMISSION REQUIRED
- เปิด Nearby Wi-Fi / Location permission ตาม Android version

### SCAN LIMITED
- Android throttle Wi-Fi scan
- ระบบจะใช้ recent result และไม่อ้างว่าเป็น scan ใหม่

### PC command ไม่ทำงาน
- ตรวจ PC IP
- ตรวจ token
- ตรวจ Windows Firewall
- PC และ Phone ต้องเชื่อมถึงกันผ่าน LAN

## 10) สิ่งที่ไม่มีใน Repo นี้แล้ว

- Bio / Sleep
- Sports / Running / Aqua / Golf
- Navigation / Breadcrumb / Geo Anchor
- Atmospheric / Solar / Heat / Altitude / Sky
- Tactical / Depth / Emergency / Grid-Down

ทั้งหมดถูกแยกไปโปรเจกต์ **Field Core** แล้ว
