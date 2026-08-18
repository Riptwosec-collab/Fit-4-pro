# PC Remote Deck V8.0 Pro Control Platform — HUAWEI WATCH FIT 4 Pro

PC Remote Deck V8 เป็นแอป **PC Remote / PC Control เท่านั้น**

> FIELD CORE, BIO, SPORT, FIELD, TACTICAL และ OUTDOOR ถูกแยกเป็นอีกแอป และไม่อยู่ใน Feature Catalog / Navigation / Watch permissions ของ PC Remote Deck อีกต่อไป

## Architecture

```text
HUAWEI WATCH FIT 4 PRO
        │ Huawei Wear Engine
        ▼
ANDROID COMPANION
        │ Bearer + HMAC + Timestamp + Nonce
        ▼
WINDOWS PC AGENT V8 PRO
        ├── System Monitor / History / Alerts
        ├── Air Mouse / Input
        ├── Window / Monitor Manager
        ├── Audio Controller
        ├── App Manager
        ├── Macro Engine
        ├── Context Detector
        ├── Notification Center
        ├── Trust Manager
        └── Unified Event Bus
```

## V8 Pro modules

### CONTROL
- Favorites / Dynamic Home
- PC Monitor Pro 2.0
- Now Playing
- Air Mouse Pro 3.0
- D-Pad
- Pro Tools
- Terminal Macros
- Command Center Pro
- Audio Mixer Pro 2.0
- Window Center 2.0
- PC Control Hub

### APPS
- App Launcher Pro 2.0
- Stream Hub
- Camera Pro provider extension

### SMART
- AI Limits provider extension
- Context Engine 2.0
- Smart Room provider extension
- Asset Radar provider extension
- Protocol Engine V2
- Motion Command 2.0
- Voice Command Pro 2.0
- Macro Deck 2.0

### NETWORK
- Network Command
- Wi-Fi Recon Pro 2.0

### SYSTEM
- System
- System Log / Event History
- Notification Bridge 2.0
- Trust Center 2.0
- PC Remote Settings

## 12 Pro upgrades

1. **PC Monitor Pro 2.0** — live telemetry, short ring-buffer history, top processes, duration-based thresholds, temperature only when a real provider exists.
2. **Air Mouse Pro 3.0** — auto calibration, precision ×0.25, acceleration curve, drag/drop and double click.
3. **Window Center 2.0** — window list, focus/min/max legacy support, snap left/right and move monitor.
4. **Audio Mixer Pro 2.0** — master/per-app audio through optional `pycaw`; output switching reports unavailable when no safe provider exists.
5. **Macro Deck 2.0** — safe structured workflows: APP / DELAY / URL / TEXT / KEY / HOTKEY / WINDOW / AUDIO / MEDIA / CONDITION / PC_COMMAND. No arbitrary shell step.
6. **App Launcher Pro 2.0** — pinned, recent, running indicator and smart focus-or-launch.
7. **Context Engine 2.0** — BROWSER / CODING / GAME / MEETING / MEDIA / PRESENTATION / DESKTOP / IDLE / CUSTOM, AUTO/MANUAL/LOCK.
8. **Voice Command Pro 2.0** — TH/EN aliases, context-aware commands and risky-command confirmation.
9. **Motion Command 2.0** — baseline training, sensitivity, confidence threshold and test mode.
10. **Wi-Fi Recon Pro 2.0** — 5-min signal history, channel/band analysis, heuristic security grade and same-SSID AP comparison; no forced roaming.
11. **Notification Bridge 2.0** — INFO/WARNING/CRITICAL, dedupe, ACK, snooze, history and threshold escalation.
12. **Trust Center 2.0** — session/trust metadata, revoke and token-rotation health; full secret is never displayed on Watch.

## Command lifecycle

ทุกคำสั่ง V8 มี Command ID และ lifecycle:

```text
SENDING → RUNNING → DONE
                  ├→ FAILED
                  └→ TIMEOUT
```

Watch จะไม่ขึ้น `DONE` เพียงเพราะส่ง packet สำเร็จ และคำสั่งเสี่ยงจะไม่ Auto Retry

## Security

ยังคงระบบเดิม:
- Bearer token
- HMAC-SHA256
- Timestamp validation
- Nonce / replay protection
- Safe command allowlist
- QR Pairing `pcremotedeck://pair`
- LAN Discovery UDP 8766

Token rotation จะสร้าง credential ใหม่ฝั่ง PC และบังคับ re-pair โดยไม่ส่ง token เต็มกลับไปแสดงบน Watch

## Real Data Rule

Production ห้ามใช้ Fake CPU / GPU / RAM / Temperature / Process / Window / AP / Session

ถ้าอ่านไม่ได้ให้แสดง `UNAVAILABLE` หรือ capability flag เช่น:
- Per-process GPU ranking — unavailable ใน safe implementation ปัจจุบัน
- GPU temperature — unavailable ถ้าไม่มี real provider
- Window thumbnail transport — ยังไม่ enabled
- Audio output switch — unavailable ถ้าไม่มี safe provider
- Wi-Fi forced roaming — false; วิเคราะห์/เปรียบเทียบเท่านั้น

## Original Masterpiece Watch UI

Watch ใช้ Masterpiece visual language แบบ lightweight สำหรับ Lite Wearable:
- Black / Deep Navy + Neon Cyan
- HUD grid / scan beam
- status pulse
- segmented/dashed volume dial
- animated EQ / radar / flow
- Dynamic Home ตาม PC Context
- Floating cyber dock
- specialized visuals สำหรับ Monitor / Air Mouse / Context / Wi-Fi / Audio / Windows / Macro / Notification / Trust

## Windows quick start

```powershell
cd pc-agent
python generate_token.py
python pair_device.py
.\start_v6.ps1
```

`start_v6.ps1` และ `run_agent.bat` จะเริ่ม `pc_agent_pro.py` ซึ่ง wrap `pc_agent.py` เดิมเพื่อรักษา legacy commands

Optional per-app audio / QR image:

```powershell
pip install -r requirements-optional.txt
python pair_device.py --rotate
```

ลบ `pairing_qr.png` หลัง Pairing เพราะ QR มี credential

## ก่อน Build ลง FIT 4 Pro จริง

ยังต้องมี:
1. Huawei Developer App ID
2. Android signing SHA-256
3. Watch Lite Wearable signing SHA-256
4. Official Huawei Lite Wearable `wearengine.js`
5. Android Studio / SDK
6. DevEco Studio + signing profile
7. Physical device authorization/testing

## ตรวจ Source

```powershell
python tools\preflight.py
```

และ repository มี GitHub Actions `V8 Static Check` สำหรับ Python syntax, Watch JavaScript, HML/JSON และ PC-only scope guard

รายละเอียดเพิ่มเติม: `docs/PC_REMOTE_DECK_V8_PRO.md`
