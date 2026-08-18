# PC Remote Deck — HUAWEI WATCH FIT 4 Pro

Repository นี้เหลือเฉพาะ **PC Remote Deck** สำหรับ HUAWEI WATCH FIT 4 Pro แล้ว

Field Core / Bio / Sport / Outdoor / Tactical Navigation ถูกแยกออกไปเป็นอีกโปรเจกต์และไม่อยู่ในแอปนี้

## Architecture

```text
HUAWEI WATCH FIT 4 PRO
        │
        │ Huawei Wear Engine
        ▼
ANDROID PHONE COMPANION
        │
        │ Authenticated LAN channel
        ▼
WINDOWS PC AGENT
```

เป้าหมายหลัก:

**WATCH COMMANDS → PHONE BRIDGE → PC EXECUTES**

## Watch App — 22 Modules

### CONTROL
- Favorites
- PC Monitor
- Now Playing
- Air Mouse
- D-Pad
- Pro Tools
- Terminal
- Command System

### APPS
- App Launcher
- Stream Hub
- Camera Pro

### SMART
- AI Limits
- Context Aware
- Smart Room
- Asset Radar
- Protocols
- Motion Command
- Voice Command

### NETWORK
- Network Status
- Wi-Fi Recon

### SYSTEM
- System
- System Log

## Removed from this app

สิ่งต่อไปนี้ไม่อยู่ใน PC Remote Deck แล้ว:

- Bio Telemetry / Daily Hub / Sleep
- Sports HUD / Running / Aqua / Golf
- Navigation / Silent Nav / Tactical Nav
- Atmospheric / Acoustic
- Depth HUD / Tactical Light / Grid-Down
- Field Systems
- Breadcrumb / Geo Anchor
- Solar / Thermal / Altitude / Transit / Sky
- Emergency Core
- Light Guardian

ระบบเหล่านี้เป็นหน้าที่ของโปรเจกต์ **Field Core** แยกต่างหาก

## Watch-native

- UI 480×408
- Haptic feedback
- Battery status
- Accelerometer + Gyroscope สำหรับ Motion Command
- Motion calibration / confidence / cooldown
- Local power profile สำหรับ PC Remote Deck
- Local System Log state

Motion mapping:

```text
FLICK RIGHT  → NEXT TRACK
FLICK LEFT   → PREVIOUS TRACK
DOUBLE TWIST → PLAY / PAUSE
SHAKE        → MUTE
```

## Phone-assisted

- Huawei Wear Engine P2P bridge
- Wi-Fi Recon ผ่าน Android Wi-Fi APIs
- Network validation / captive portal classification
- Android Speech Recognition สำหรับ Voice Command
- Phone providers สำหรับ AI Limits / Asset Radar / Camera / Smart Room ตามการเชื่อมต่อที่ตั้งค่า

Wi-Fi Recon ยึดหลัก:

**OPEN ≠ FREE**

และไม่รวมเครื่องมือโจมตีเครือข่าย

## PC-assisted

- Lock PC
- Play/Pause / Next / Previous / Mute / Volume
- Show Desktop / Alt+Tab
- Ctrl+C / Ctrl+V
- Arrow/D-Pad
- Mouse click / scroll
- Screenshot
- Whitelisted App Launcher
- Battle Station
- Deep Focus
- PC status

PC Agent ใช้ token + HMAC + timestamp + nonce และไม่มี arbitrary shell endpoint

## Project Structure

```text
Fit-4-pro/
├── watch-lite/
├── android-companion/
├── pc-agent/
├── docs/
├── tools/
├── REAL_DEVICE_INSTALL.ps1
└── README_TH.md
```

## ก่อน Build ลงเครื่องจริง

ต้องมี:

1. Huawei Developer App ID
2. Android signing SHA-256 fingerprint
3. Lite Wearable signing SHA-256 fingerprint
4. Official Huawei Wear Engine `wearengine.js`
5. DevEco Studio
6. Android Studio / Android SDK

ตั้ง identity:

```powershell
python tools/configure_identity.py `
  --huawei-app-id YOUR_APP_ID `
  --android-fingerprint YOUR_ANDROID_SHA256 `
  --watch-fingerprint YOUR_WATCH_SHA256
```

ติดตั้ง Wear Engine SDK ฝั่ง Watch:

```powershell
python tools/install_wearengine_sdk.py C:\path\to\wearengine.js
```

ตรวจ source:

```powershell
python tools/preflight.py
```

หรือใช้:

```powershell
.\REAL_DEVICE_INSTALL.ps1
```

ดูขั้นตอนเต็มใน `docs/BUILD_AND_INSTALL_TH.md` และ `docs/REAL_DEVICE_INSTALL_TH.md`
