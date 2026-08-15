# Watch ↔ Phone ↔ PC Protocol

## Watch → Phone command

```json
{
  "v": 1,
  "id": "timestamp-random",
  "ts": 1760000000000,
  "type": "command",
  "action": "PC_LOCK",
  "source": "FIT4PRO",
  "payload": {}
}
```

Phone `CommandRouter` accepts only known/whitelisted actions.

## Phone → Watch result

```json
{
  "type": "result",
  "ok": true,
  "action": "PC_LOCK",
  "message": "LOCK SENT",
  "data": {}
}
```

## Phone → Watch snapshot

Wi‑Fi raw scans are processed on Android first. The Watch receives a compact snapshot only:

```json
{
  "type": "snapshot",
  "ts": 1760000000000,
  "pc": { "state": "CONFIGURED" },
  "wifi": {
    "summary": "14 nearby • 1 verified • 3 open • 11 secured",
    "scanState": "READY",
    "nearby": 14,
    "freeVerified": 1,
    "open": 3,
    "secured": 11,
    "loginRequired": 1,
    "best": {
      "ssid": "Cafe_Free",
      "status": "FREE VERIFIED",
      "signalDbm": -47,
      "band": "5 GHz",
      "security": "OPEN",
      "score": 81
    }
  }
}
```

`OPEN` is not treated as `FREE VERIFIED`. Verification is only assigned to the currently connected network when Android reports validated Internet without a captive portal.

## Phone → PC

HTTP POST `/command`

Headers:
- `Authorization: Bearer <token>`
- `X-PRD-Timestamp`
- `X-PRD-Nonce`
- `X-PRD-Signature` = HMAC-SHA256 over request data

PC Agent rejects:
- unknown actions
- expired timestamp
- replayed nonce
- invalid token/signature

There is no arbitrary shell execution endpoint.
