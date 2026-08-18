# PC Remote Deck V8 — Pro Control Platform

PC Remote Deck is now scoped to **PC remote/control only**. FIELD CORE, BIO, SPORT, FIELD, TACTICAL and OUTDOOR modules are separate and are not part of this repository runtime/navigation.

## V8 Pro upgrades

- PC Monitor Pro 2.0 — live telemetry, short ring-buffer history, top processes, duration thresholds, real-data-only temperatures.
- Air Mouse Pro 3.0 — auto calibration, precision mode, acceleration curves, drag/drop, double click.
- Window Center 2.0 — window management, maximize/restore legacy support, snap left/right, monitor move. Thumbnail transport is explicitly not enabled.
- Audio Mixer Pro 2.0 — master/per-app state through optional pycaw. Output switching is reported unavailable unless a safe provider is added.
- Macro Deck 2.0 — structured safe workflows with APP/DELAY/URL/TEXT/KEY/HOTKEY/WINDOW/AUDIO/MEDIA/CONDITION/PC_COMMAND steps; no arbitrary shell step.
- App Launcher Pro 2.0 — pinned/recent/running and smart focus-or-launch.
- Context Engine 2.0 — BROWSER, CODING, GAME, MEETING, MEDIA, PRESENTATION, DESKTOP, IDLE, CUSTOM; AUTO/MANUAL/LOCK.
- Voice Command Pro 2.0 — Thai/English aliases, context-aware short commands and confirmation for risky commands.
- Motion Command 2.0 — training baseline, sensitivity, confidence threshold, test mode.
- Wi-Fi Recon Pro 2.0 — phone-side scan history, band/channel analysis, heuristic security grade and roaming comparison. OPEN is never labeled FREE unless the active network is validated; no forced roaming.
- Notification Bridge 2.0 — INFO/WARNING/CRITICAL, dedupe, ACK, snooze, history and threshold escalation.
- Trust Center 2.0 — session metadata, last access, token-rotation health and explicit revoke/rotation. Full secrets are never returned to the Watch.

## Core V8 architecture

```text
HUAWEI WATCH FIT 4 PRO
        │ Wear Engine
        ▼
ANDROID COMPANION
        │ Bearer + HMAC + timestamp + nonce
        ▼
WINDOWS PC AGENT V8 PRO
        ├─ monitor/history/alerts
        ├─ input + air mouse
        ├─ windows/monitors
        ├─ audio
        ├─ apps
        ├─ macro engine
        ├─ context detector
        ├─ notification center
        ├─ trust manager
        └─ unified event bus
```

Command lifecycle is correlated by ID:

`SENDING → RUNNING → DONE | FAILED | TIMEOUT`

The Watch does not show DONE merely because a packet was sent. Risky commands are not automatically retried.

## Runtime files

The legacy `pc-agent/pc_agent.py` remains the compatibility implementation. V8 runs through:

- `pc-agent/pc_agent_pro.py`
- `pc-agent/pro_engine.py`
- `pc-agent/pro_support.py`
- `pc-agent/pro_macro.py`

`run_agent.bat` and `start_v6.ps1` now start `pc_agent_pro.py`.

Runtime settings/macros/trust files are gitignored. Examples are committed as `pro_settings.example.json` and `macros_v2.example.json`.

## Real-data rule

Production UI must use actual provider data. If Windows/driver/SDK does not expose a metric, V8 returns `UNAVAILABLE` or a capability flag instead of inventing values.

Known intentional capability flags:

- Per-process GPU ranking: unavailable in the current safe implementation.
- GPU temperature: only available if a real provider is added; no fabricated value.
- Window thumbnails: `thumbnailCapability=false` until a thumbnail transport is implemented.
- Audio output switching: `outputSwitchAvailable=false` unless a safe output-device provider is added.
- Wi-Fi forced roaming: false; the phone only compares APs.

## Build/device status

Source changes can be statically checked, but a real signed Watch/Android package still requires Huawei Developer App ID, signing fingerprints, official Lite Wearable Wear Engine integration, DevEco/Android build environment and physical-device testing.
