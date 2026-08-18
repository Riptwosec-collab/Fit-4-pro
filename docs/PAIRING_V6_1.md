# V6.1 Pairing & Auto Discovery

## Recommended: local QR pairing

บน Windows:

```powershell
cd pc-agent
pip install -r requirements-optional.txt
python pair_device.py --rotate
.\start_v6.ps1
```

`pair_device.py --rotate` จะสร้าง token ใหม่ใน `agent_config.json` และสร้าง `pairing_qr.png` ถ้ามี `qrcode` package. Credential เก่าจะใช้งานไม่ได้หลัง rotate.

สแกน QR ด้วยกล้อง Android แล้วเปิด URI `pcremotedeck://pair` ด้วย PC Remote Deck Companion. Companion จะบันทึก host/port/token ใน private SharedPreferences แล้วเริ่ม dashboard sync ได้.

**QR มี secret token — ห้ามส่งให้ผู้อื่น และลบ `pairing_qr.png` หลัง pair.** ไฟล์นี้ถูก `.gitignore` ไว้แล้ว.

## Auto Find PC on LAN

`start_v6.ps1` เปิด `discovery_service.py` พร้อม PC Agent. Companion กด **AUTO FIND PC ON LAN** แล้ว broadcast ข้อความ discovery ไป UDP 8766.

Responder ส่งกลับเฉพาะ service name / PC identity / command port. **ไม่มี token, HMAC key หรือ credential ถูกส่งผ่าน discovery broadcast.** หลังพบ PC แล้วผู้ใช้ยังต้องมี token หรือ QR pairing จึงสั่งงานได้.

## Threat model

- LAN discovery = service discovery only, not authentication.
- Authentication = secret token + HMAC-SHA256 + timestamp + nonce.
- QR pairing = local transfer of the secret; treat it like a password.
- `--rotate` = single-active-phone credential rotation model. หากต้องการ multi-device trust store แบบหลายกุญแจพร้อมกันให้ทำเป็นรุ่นถัดไป; V6.1 ไม่อ้างว่ารองรับ multi-device keys.
