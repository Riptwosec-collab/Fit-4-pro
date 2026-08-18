# PC Remote Deck V6 — HUAWEI WATCH FIT 4 Pro

V6 ยังคงเป็น **PC Remote Deck only** และยกระดับจาก remote button deck เป็น wrist PC control system แบบมี live state.

## V6 Highlights

- Watch Home V2: CPU / GPU / RAM / Ping / Active App / Context / Alerts
- PC Monitor Pro: CPU, GPU usage (best-effort Windows counter), RAM, Disk, Network, Top Processes, temperature when Windows exposes it
- Audio Mixer Pro: master media controls และ optional per-app sessions ผ่าน `pycaw`
- Window Center: active window / window list / focus / minimize / maximize / close
- Air Mouse Pro: gyroscope cursor streaming พร้อม sensitivity/dead-zone
- Macro Deck: safe macro storage/run; Macro Builder อยู่ใน Android Companion
- Context Engine: Browser / Dev / Media / Game / Meeting / Generic profiles และ contextual action slots
- Protocol Engine V2: Battle Station / Deep Focus + safe multi-step macros
- Voice Command Pro: ไทย/อังกฤษ; Sleep/Restart/Shutdown ต้องยืนยันบนโทรศัพท์
- App Launcher Pro: whitelist เดิม + PC-local `apps.json`
- Network Command Center: IP / Gateway / DNS / throughput / ping
- Wi-Fi Recon Pro: OPEN != FREE VERIFIED + RSSI trend
- Companion Auto Sync: จำ PC IP/token ในเครื่องและ sync dashboard ทุก 12 วินาทีขณะ Companion ทำงาน
- Notification Bridge: agent alerts เช่น CPU/RAM สูง, macro complete, screenshot
- Trust Center: peer status + local PC link revoke

## Security

- ไม่มี arbitrary shell endpoint
- PC Agent รับเฉพาะ action whitelist
- Bearer token + HMAC-SHA256 + timestamp + nonce/replay protection
- Macro step ทุกตัวถูกตรวจ safe allowlist ก่อน save/run
- Dynamic app launcher เปิดได้เฉพาะ app definition ที่อยู่บน PC เอง
- Power actions ต้องมี `confirmed=true`; Voice flow แสดง confirmation dialog บนมือถือก่อนส่ง
- runtime secrets/config (`agent_config.json`, `macros.json`, `apps.json`) ถูก gitignore

## Structure

- `watch-lite/` — Lite Wearable UI 480×408
- `android-companion/` — Wear Engine bridge, auto sync, Voice, Wi-Fi Recon, Macro Builder
- `pc-agent/` — Windows agent V6
- `tools/` — identity / SDK / preflight
- `docs/` — build, capability, regression, V6 upgrade notes

## Optional Audio Mixer dependency

บน Windows:

```powershell
pip install -r pc-agent\requirements-optional.txt
```

ถ้าไม่ติดตั้ง `pycaw` แอปยังทำงานได้ แต่ per-app Audio Mixer จะแสดง `OPTIONAL_PYCAW_MISSING` และ master media controls ยังใช้ได้.

## First run

```powershell
python pc-agent\generate_token.py
python pc-agent\pc_agent.py
```

นำ token ไปใส่ Android Companion จากนั้น Authorize Wear Engine → Find/Register Watch → Sync dashboard.

ก่อน build เครื่องจริงยังต้องใส่ Huawei App ID, Android signing fingerprint, Watch signing fingerprint และ official Lite Wearable `wearengine.js` ตาม `docs/BUILD_AND_INSTALL_TH.md`.
