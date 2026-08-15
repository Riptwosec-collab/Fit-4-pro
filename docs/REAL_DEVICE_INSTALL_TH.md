# ลง PC Remote Deck บน HUAWEI WATCH FIT 4 Pro จริง

เอกสารนี้ใช้กับ source ใน repo นี้โดยตรง ไม่ใช่ HTML prototype

## สิ่งที่ต้องมีบนเครื่อง Windows

- HUAWEI WATCH FIT 4 Pro จับคู่กับโทรศัพท์ผ่าน HUAWEI Health
- Huawei Developer account ที่เปิดใช้ Wear Engine
- DevEco Studio + Lite Wearable/HarmonyOS SDK ที่ Huawei ระบุสำหรับการพัฒนา wearable
- Android Studio + Android SDK
- JDK (`java` และ `keytool`)
- Python 3
- Android Phone Companion ที่จะติดตั้ง APK

## ขั้นที่ 1 — Clone repo

```powershell
git clone https://github.com/Riptwosec-collab/Fit-4-pro.git
cd Fit-4-pro
```

## ขั้นที่ 2 — เตรียม Huawei App ID และ signing

Huawei Wear Engine ตรวจ package name, App ID และ signing certificate fingerprint ให้ตรงกับข้อมูลที่ลงทะเบียนไว้

ค่าที่ต้องได้:

1. Huawei App ID
2. SHA-256 ของ Android Companion signing certificate
3. SHA-256 ของ Watch/Lite Wearable signing certificate

หา fingerprint จาก keystore ด้วย:

```powershell
.\tools\get_signing_fingerprint.ps1 -Keystore "C:\path\your-release.jks" -Alias "yourAlias"
```

สำหรับ Watch ให้ใช้ certificate/profile ที่ DevEco Studio ใช้ sign watch app แล้วนำ fingerprint ที่ถูกต้องมาใช้กับ Wear Engine peer configuration

## ขั้นที่ 3 — ใส่ Official Wear Engine Lite Wearable SDK

ไฟล์ `watch-lite/entry/src/main/js/MainAbility/wearengine/wearengine.js` ใน repo เป็น offline stub เท่านั้น

ดาวน์โหลด `wearengine.js` อย่างเป็นทางการจาก Huawei Wear Engine SDK แล้วรัน:

```powershell
python tools/install_wearengine_sdk.py "C:\path\wearengine.js"
```

## ขั้นที่ 4 — รัน Real Device Installer

ตัวอย่าง:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\REAL_DEVICE_INSTALL.ps1 `
  -HuaweiAppId "YOUR_APP_ID" `
  -AndroidFingerprint "AA:BB:CC:..." `
  -WatchFingerprint "11:22:33:..." `
  -StartPcAgent `
  -BuildAndroid `
  -InstallAndroid `
  -OpenWatchProject
```

สคริปต์จะ:

- ตรวจ Python/JDK/keytool/ADB/IDE
- สร้าง PC Agent token แบบ local
- patch Huawei App ID + fingerprints
- รัน preflight
- เปิด/Build Android Companion
- ติดตั้ง APK ผ่าน ADB เมื่อ APK และ ADB พร้อม
- เปิด `watch-lite/` ใน DevEco Studio

## ขั้นที่ 5 — ติดตั้ง Android Companion บนโทรศัพท์

ใน Android Studio:

1. Open `android-companion/`
2. Sync Gradle
3. ตรวจ signing config ให้ใช้ certificate ที่ลงทะเบียนกับ Huawei
4. Build/Run ลง Android phone จริง
5. เปิด app และอนุญาต Wear Engine / Wi-Fi permissions ที่จำเป็น

หลังเปิด app:

1. ใส่ IP ของ Windows PC
2. ใส่ token จาก `pc-agent/agent_config.json`
3. SAVE PC LINK
4. AUTHORIZE WEAR ENGINE
5. FIND / REGISTER WATCH

## ขั้นที่ 6 — ติดตั้ง Watch app บน FIT 4 Pro

ใน DevEco Studio:

1. Open `watch-lite/`
2. ตรวจ `liteWearable` target และ design width 480
3. ตรวจ Official `wearengine.js` ถูกแทน stub แล้ว
4. ตั้ง signing profile ของ Watch
5. ตรวจ Watch package/fingerprint ตรงกับ Android Companion
6. เชื่อมโทรศัพท์ที่ login Huawei Health และจับคู่ FIT 4 Pro
7. เลือก real wearable/debug target ตาม workflow ของ DevEco Studio
8. กด Run/Install

การกด Run/Install ขั้นนี้ต้องทำบนเครื่องที่มีบัญชี Huawei, signing profile และอุปกรณ์จริง จึงไม่สามารถ bypass ด้วย GitHub หรือ remote build ได้

## ขั้นที่ 7 — Test end-to-end

เปิดตามลำดับ:

1. `python pc-agent/pc_agent.py`
2. Android Companion
3. PC Remote Deck บน Watch

ทดสอบ:

- LOCK PC
- PLAY/PAUSE
- MUTE
- ALT+TAB
- Screenshot
- WI-FI RECON (Phone scans, Watch displays)
- Heart Rate
- Motion Command
- Compass
- Barometer
- Geo Anchor/Breadcrumb เมื่อ Location API พร้อม

## ถ้า Wear Engine เชื่อมไม่ได้

ตรวจ 4 ค่าเป็นอันดับแรก:

- Android package = `com.riptwosec.pcremotedeck`
- Watch package = `com.riptwosec.pcremotedeck.watch`
- Huawei App ID ถูกต้อง
- peer signing fingerprints ตรงกับ certificate ที่ใช้ sign binary จริง

## Security

- ห้าม commit `agent_config.json`
- ห้าม commit `.jks`, `.keystore`, `.p12`, private key หรือ token
- Repo มี `.gitignore` ป้องกันไฟล์เหล่านี้แล้ว
- PC Agent port 8765 ใช้เฉพาะ LAN/Private network และไม่ควร expose ออก Internet
