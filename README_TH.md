# PC Remote Deck V6.2 — HUAWEI WATCH FIT 4 Pro

PC Remote Deck เป็น **PC-control-only** app สำหรับ FIT 4 Pro: Watch สั่งงาน → Android Companion bridge → Windows PC Agent.

## V6.2 — Masterpiece Animated HUD Upgrade

รอบ V6.2 โฟกัสที่ **ทำทุกหน้าให้เต็ม ใช้พื้นที่ 480×408 คุ้มขึ้น และเพิ่ม animation แบบ lightweight สำหรับ Lite Wearable** โดยไม่ลบฟังก์ชันเดิมและไม่เปลี่ยน security model

- Global scan beam animation
- Status-dot pulse / secure glow
- Animated segmented-style dial + sweep
- EQ bars animation
- Pulse buttons / active dock animation
- Data-flow / packet animation
- Radar sweep สำหรับ Network / Wi-Fi
- Air Mouse gyro reticle animation
- Voice pulse rings
- Notification pulse ring
- Trust / Security shield pulse
- Protocol flow animation
- Motion orbit animation
- System core / battery HUD
- Category pages ที่เคยโล่งถูกเติมด้วยข้อมูลหรือ visual ที่สัมพันธ์กับหน้าตัวเอง
- Detail pages มี visual เฉพาะโมดูล ไม่ใช้ generic empty card แบบเดิม

### หน้า Category ที่เติมใหม่

- **CONTROL** — CPU / Audio / Active App summary
- **APPS** — Active App orbit + Launcher / Stream / Camera shortcuts
- **SMART** — Context / Motion / Power summary
- **NETWORK** — latency radar + PC/Phone link quality
- **SYSTEM** — Watch battery core + Phone / PC / Power / Alerts + latest event

### Detail UI เฉพาะโมดูล

V6.2 เพิ่ม layout/visual เฉพาะสำหรับ Favorites, PC Monitor, Now Playing, AI Limits, Context Engine, Air Mouse, App Launcher, D-Pad, Smart Room, Pro Tools, System, Stream Hub, Network, Terminal Macros, Camera Pro, Asset Radar, Command Center, Protocol Engine, System Log, Motion Command, Voice Command, Wi-Fi Recon, Audio Mixer, Window Center, Macro Deck, Notification Bridge และ Trust Center

> ฟังก์ชันที่ยังไม่มี provider จริงจะยังแสดง `--` / provider state แทนการสร้างข้อมูลปลอม

## V6/V6.1 Functional Highlights

- PC Monitor Pro: CPU, GPU best-effort, RAM, Disk, Network, Top Processes, temperature when Windows exposes it
- Audio Mixer Pro: master controls + optional per-app sessions via `pycaw`
- Window Center: active/window list + focus/minimize/maximize/close
- Air Mouse Pro: gyroscope cursor streaming + sensitivity/dead-zone
- Macro Deck + Android Macro Builder: safe allowlisted multi-step macros
- Context Engine: Browser / Dev / Media / Game / Meeting / Generic profiles
- Protocol Engine V2: Battle Station / Deep Focus + safe macros
- Voice Command Pro: ไทย/อังกฤษ; Sleep/Restart/Shutdown ต้องยืนยันบนโทรศัพท์
- App Launcher Pro: fixed whitelist + PC-local `apps.json`
- Network Command: IP / Gateway / DNS / throughput / ping
- Wi-Fi Recon Pro: `OPEN != FREE VERIFIED` + RSSI trend
- Notification Bridge + Trust Center
- Companion Auto Sync: จำ PC link และ sync dashboard ทุก 12 วินาทีขณะ Companion ทำงาน
- **V6.1 Auto Find PC:** UDP LAN discovery บน port 8766 โดยไม่ส่ง token
- **V6.1 Local QR Pairing:** `pcremotedeck://pair` deep link; QR อยู่เฉพาะเครื่องและสามารถ rotate credential ได้

## Security

- ไม่มี arbitrary shell endpoint
- PC Agent รับเฉพาะ action whitelist
- Bearer token + HMAC-SHA256 + timestamp + nonce/replay protection
- Macro ทุก step ถูก validate กับ safe allowlist
- Dynamic app launcher เปิดได้เฉพาะ definition ที่อยู่ฝั่ง PC
- Risk power actions ต้องมี `confirmed=true`
- `agent_config.json`, `macros.json`, `apps.json`, `pairing_qr.png`, signing keys ถูก gitignore
- Pairing QR มี secret token: **ถือว่า QR เป็นรหัสผ่านและลบทิ้งหลัง pairing**

## Quick start on Windows

```powershell
cd pc-agent
python generate_token.py
python pair_device.py
.\start_v6.ps1
```

ถ้าต้องการ QR image และ Audio Mixer per-app:

```powershell
pip install -r requirements-optional.txt
python pair_device.py --rotate
```

`--rotate` จะสร้าง token ใหม่และทำให้ credential เดิมใช้ไม่ได้ เหมาะเมื่อต้องการ pair โทรศัพท์เครื่องใหม่หรือ revoke เครื่องเก่า.

## Pair Android Companion

1. เปิด `pairing_qr.png` บน PC
2. ใช้กล้องมือถือสแกน QR
3. เลือกเปิด **PC Remote Deck Companion**
4. Companion จะรับ host/port/token และบันทึก local link
5. ถ้าไม่ใช้ QR: กด **AUTO FIND PC ON LAN** เพื่อหา IP แล้วใส่ token เอง
6. Authorize Wear Engine → Find/Register Watch → Sync dashboard
7. ลบ `pairing_qr.png` หลัง pair

## Structure

- `watch-lite/` — Lite Wearable UI 480×408
- `android-companion/` — Huawei Wear Engine, QR/LAN pairing, auto sync, Voice, Wi-Fi, Macro Builder
- `pc-agent/` — Windows control/telemetry, discovery responder, QR pairing helper
- `tools/` — identity / SDK / preflight
- `docs/` — build/capability/regression/upgrade notes

## Provider extension points

ฟังก์ชันเดิมเหล่านี้ยังต้องต่อ provider ภายนอกก่อนจึงจะเป็น live จริง: **AI Limits, Smart Room, Camera Pro, Asset Radar, OBS scene control**. ระบบจะแจ้ง provider not configured แทนการสร้างข้อมูลปลอม.

## Before real FIT 4 Pro build

ยังต้องใส่ Huawei App ID, Android signing SHA-256, Watch signing SHA-256 และ official Lite Wearable `wearengine.js`; จากนั้น build/sign ผ่าน Android Studio + DevEco Studio ตาม `docs/BUILD_AND_INSTALL_TH.md`.