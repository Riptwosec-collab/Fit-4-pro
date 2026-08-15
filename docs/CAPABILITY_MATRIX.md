# Capability Matrix — REAL V5

| Module / Capability | Source in V5 | Status |
|---|---|---|
| Watch UI 480×408 | Lite Wearable | SOURCE READY |
| Haptic | Watch API | IMPLEMENTED |
| Heart Rate | Watch sensor API | IMPLEMENTED / PERMISSION GATED |
| Accelerometer | Watch sensor API | IMPLEMENTED |
| Gyroscope | Watch sensor API | IMPLEMENTED |
| Motion gestures | Watch local engine | EXPERIMENTAL / CALIBRATION REQUIRED |
| Compass | Watch sensor API | IMPLEMENTED |
| Barometer | Watch sensor API | IMPLEMENTED |
| Location / anchor | Watch location API when available | IMPLEMENTED / CAPABILITY GATED |
| Wi‑Fi Recon | Android Phone | IMPLEMENTED |
| Wi‑Fi Captive Portal / Validation | Android Phone | IMPLEMENTED |
| Voice recognition | Android Phone | IMPLEMENTED |
| PC Lock / Media / Windows controls | Windows PC Agent | IMPLEMENTED |
| PC App Launcher | Windows PC Agent | IMPLEMENTED (whitelist) |
| Protocols Battle / Focus | Phone → PC | IMPLEMENTED (basic) |
| Tactical screen light | Watch display | IMPLEMENTED |
| Depth raw data | Third-party Watch API | UNAVAILABLE / API GATED |
| Ambient light raw data | Lite Wearable | UNAVAILABLE IN CURRENT IMPLEMENTATION |
| ECG raw data | Third-party Watch API | NOT ASSUMED AVAILABLE |
| Temperature raw data | Third-party Watch API | NOT ASSUMED AVAILABLE |
| Weather / UV / Sky cloud data | Phone/provider | PROVIDER NOT CONFIGURED |
| Transit geofence | Phone/provider | PROVIDER NOT CONFIGURED |
| Sleep readiness advanced metrics | Health/provider | PROVIDER NOT CONFIGURED |
| Running advanced metrics | Health/provider | PROVIDER NOT CONFIGURED |
| Golf course data | Phone/provider | PROVIDER NOT CONFIGURED |
| Emergency share acknowledgement | Phone communication provider | PROVIDER NOT CONFIGURED |

## Rule

Hardware presence does not automatically mean a third-party Lite Wearable application receives raw sensor access. V5 therefore distinguishes `WATCH`, `PHONE`, `PC`, `CACHED`, `API GATED`, and `UNAVAILABLE` instead of presenting demo values as live measurements.
