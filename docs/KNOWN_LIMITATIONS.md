# Known Limitations

1. `wearengine.js` is a placeholder until replaced by the official Huawei Lite Wearable SDK file.
2. Huawei App ID and signing fingerprints are placeholders until configured by the developer/user.
3. Real HAP/APK binaries cannot be signed without the user's Huawei/Android signing identities.
4. Motion gesture thresholds are initial engineering values and require calibration on a physical FIT 4 Pro.
5. Wi‑Fi scanning occurs on the Android Phone; the Watch does not pretend to perform raw Wi‑Fi scans.
6. Android may throttle Wi‑Fi scans; recent results are marked CACHED/SCAN LIMITED.
7. Raw Depth/ECG/temperature access is not assumed merely because the hardware exists.
8. Weather, UV, astronomy weather conditions, transit, golf course, and advanced sports providers are stubs/providers until connected to a real data source.
9. Tactical Light is display-based light, not a hardware flashlight LED.
10. Emergency Core does not claim emergency services were contacted unless a communication provider confirms delivery.
