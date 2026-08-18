# PC Remote Deck V7.0 Unified Restore — HUAWEI WATCH FIT 4 Pro

V7.0 คือการรวม **แอปก่อนแยกฟังก์ชัน + ความสามารถ V6.x ปัจจุบัน** กลับมาเป็นแอปเดียว โดยไม่ใช้ ID ทับกัน

## สิ่งที่กลับมาแล้ว

หมวดเดิมก่อนแยกกลับมาครบ:

- **COMMAND** — PC Control / Media / Context / Apps / Network / Motion / Voice / Protocols
- **BIO** — Daily Hub / Bio Telemetry / Morning Diagnostic
- **SPORT** — Aqua Recon / Run Analyzer / Tactical Caddie / Sports HUD
- **FIELD** — Navigation / Wi-Fi Recon / Field Systems / Breadcrumb / Geo Anchor / Solar / Thermal / Altitude / Transit / Sky / Emergency
- **TACTICAL** — Atmospheric / Acoustic / Tactical Core / Tactical Nav / Silent Nav / Depth HUD / Tactical Light
- **SYSTEM** — Smart Room / System / Smart Wallet / Asset Radar / System Log / Light Scanner / Power Core

49 โมดูลก่อนแยกถูกคืนเป็น ID `0–48` อีกครั้ง

## ฟังก์ชันใหม่จาก V6.x ที่ยังอยู่ครบ

เพื่อไม่ชนกับ Field ID เดิม ฟังก์ชันใหม่ถูกย้ายไป ID ใหม่:

- `49` — Audio Mixer Pro
- `50` — Window Center
- `51` — Macro Deck
- `52` — Notification Bridge
- `53` — Trust Center

รวมทั้งหมด **54 Modules (0–53)**

ของ V6.x ที่เป็น upgrade ของโมดูลเดิมยังอยู่ใน ID เดิม เช่น:

- PC Monitor Pro
- Context Engine
- Air Mouse Pro
- App Launcher Pro
- Network Command
- Protocol Engine V2
- Voice Command Pro
- Wi-Fi Recon Pro

## UI

V7 คืนโครงหน้าตาแบบ pre-split:

```text
PC REMOTE DECK                         FIT 4 PRO

PHONE                                      CONNECTED
PC                                              ONLINE
BATTERY                                            84%
HR                                              -- BPM

CPU       RAM       PING       ACTIVE

[ LOCK ]                      [ MUTE ]
[ PLAY ]                      [ SHOT ]

[ COMMAND ]                   [ BIO ]
[ SPORT   ]                   [ FIELD ]
[ TACTICAL]                   [ SYSTEM ]
```

พร้อมเติมพื้นที่ของแต่ละหมวดด้วย visual ที่เกี่ยวข้อง เช่น Bio ring, Field radar, Tactical crosshair และ System battery core แต่ยังรักษาโครง Navigation เดิมไว้

Animation ยังคงเป็น lightweight และจะลดลงเมื่อใช้ ENDURANCE profile

## Watch-local capabilities ที่คืนมา

เมื่อ API/permission ของเครื่องอนุญาต:

- Heart Rate subscription
- Accelerometer
- Gyroscope
- Motion Command
- Air Mouse gyro streaming
- Compass
- Barometer
- Location
- Breadcrumb local storage
- Geo Anchor local storage
- Haptic
- Tactical red/white/SOS screen light
- Power profiles

## Phone-assisted / Provider-backed

ฟังก์ชันที่ต้องพึ่ง Android/Provider จะยังไม่สร้างข้อมูลปลอม ถ้า provider ยังไม่ต่อ ระบบจะแสดง `PROVIDER NOT CONFIGURED ON PHONE`

ตัวอย่าง:

- AI Limits
- Smart Room
- Camera Pro
- Asset Radar
- OBS
- Morning Diagnostic
- Aqua / Run / Golf / Sports data
- Silent Navigation
- Solar / Thermal / Altitude / Transit / Sky
- Emergency phone-assisted sharing

## V6.1/V6.2 ที่ไม่ถูกลบ

- QR Pairing `pcremotedeck://pair`
- LAN Auto Discovery UDP `8766`
- Credential rotation
- Companion Auto Sync
- PC Monitor telemetry
- Audio Mixer optional `pycaw`
- Window Control
- Macro Builder / safe macros
- Context Engine
- Voice TH/EN
- Wi-Fi classification + score/trend
- PC Agent HMAC/timestamp/nonce model

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

ลบ `pairing_qr.png` หลัง pairing เพราะ QR มี credential สำหรับเชื่อม PC

## ก่อน Build ลง FIT 4 Pro จริง

ยังต้องตั้งค่าของบัญชี/เครื่องคุณเอง:

1. Huawei Developer App ID
2. Android signing SHA-256 fingerprint
3. Watch Lite Wearable signing SHA-256 fingerprint
4. Official Huawei Lite Wearable `wearengine.js`

จากนั้น build/sign ผ่าน Android Studio + DevEco Studio ตาม `docs/BUILD_AND_INSTALL_TH.md`

## ตรวจ Source

รัน:

```powershell
python tools\preflight.py
```

V7 preflight จะตรวจว่า 54 modules, 6 categories, Watch permissions และ runtime หลักของทั้ง pre-split + V6.x อยู่ครบ
