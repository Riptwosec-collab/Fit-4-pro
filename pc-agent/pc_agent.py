#!/usr/bin/env python3
"""PC Remote Deck Windows agent V6.

Security model:
- Whitelisted actions only; no arbitrary shell endpoint.
- Bearer token + HMAC-SHA256 + timestamp + nonce replay protection.
- Dynamic app launching is restricted to local PC-side app definitions.
- Macro steps are validated against a safe action allowlist before storage/run.
"""
import ctypes, hashlib, hmac, json, os, pathlib, socket, subprocess, sys, threading, time
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "agent_config.json"
MACRO_FILE = ROOT / "macros.json"
APPS_FILE = ROOT / "apps.json"
NONCES = {}
NONCE_LOCK = threading.Lock()
NOTIFICATIONS = []
NOTIFY_LOCK = threading.Lock()
NET_SAMPLE = {"ts": 0.0, "rx": 0, "tx": 0}

DEFAULT_CONFIG = {
    "bind": "0.0.0.0",
    "port": 8765,
    "token": "CHANGE_ME",
    "max_clock_skew_seconds": 30,
    "ping_target": "1.1.1.1",
    "notification_cpu_percent": 92,
    "notification_ram_percent": 90,
}

DEFAULT_MACROS = {
    "work": {"name": "Work Start", "steps": ["APP_VSCODE", "APP_CHROME", "DEEP_FOCUS"]},
    "game": {"name": "Game Start", "steps": ["APP_STEAM", "APP_DISCORD", "BATTLE_STATION"]},
    "meeting": {"name": "Meeting", "steps": ["MEDIA_MUTE", "SHOW_DESKTOP"]},
}

DEFAULT_APPS = {
    "chrome": {"name": "Chrome", "candidates": ["chrome.exe"]},
    "vscode": {"name": "VS Code", "candidates": ["code.cmd", "code.exe"]},
    "spotify": {"name": "Spotify", "candidates": ["Spotify.exe"]},
    "discord": {"name": "Discord", "candidates": ["Discord.exe"]},
    "steam": {"name": "Steam", "candidates": ["steam.exe"]},
    "files": {"name": "Files", "candidates": ["explorer.exe"]},
    "cmd": {"name": "Command Prompt", "candidates": ["cmd.exe"]},
}

VK = {
    "MEDIA_NEXT": 0xB0, "MEDIA_PREV": 0xB1, "MEDIA_PLAY_PAUSE": 0xB3,
    "MEDIA_MUTE": 0xAD, "VOLUME_DOWN": 0xAE, "VOLUME_UP": 0xAF,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    "TAB": 0x09, "CTRL": 0x11, "ALT": 0x12, "WIN": 0x5B,
    "C": 0x43, "V": 0x56, "D": 0x44, "L": 0x4C, "R": 0x52,
    "T": 0x54, "W": 0x57, "S": 0x53, "J": 0x4A, "F": 0x46,
    "F5": 0x74, "SHIFT": 0x10,
}
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
WM_CLOSE = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return json.loads(json.dumps(default))
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else json.loads(json.dumps(default))
    except Exception:
        return json.loads(json.dumps(default))


def save_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_config():
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(load_json(CONFIG_FILE, DEFAULT_CONFIG))
    return cfg


CFG = load_config()


def notify(kind, title, message, data=None):
    item = {"ts": int(time.time()), "kind": kind, "title": title, "message": message}
    if data is not None:
        item["data"] = data
    with NOTIFY_LOCK:
        NOTIFICATIONS.insert(0, item)
        del NOTIFICATIONS[30:]


def key(vk):
    u = ctypes.windll.user32
    u.keybd_event(vk, 0, 0, 0)
    u.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def combo(*vks):
    u = ctypes.windll.user32
    for v in vks:
        u.keybd_event(v, 0, 0, 0)
    for v in reversed(vks):
        u.keybd_event(v, 0, KEYEVENTF_KEYUP, 0)


def mouse(flags, data=0):
    ctypes.windll.user32.mouse_event(flags, 0, 0, data, 0)


def mouse_move(dx, dy):
    u = ctypes.windll.user32
    p = wintypes.POINT()
    u.GetCursorPos(ctypes.byref(p))
    u.SetCursorPos(int(p.x + dx), int(p.y + dy))
    return {"x": int(p.x + dx), "y": int(p.y + dy)}


def run_ps(script, timeout=4):
    try:
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if p.returncode != 0:
            return None
        out = p.stdout.strip()
        return out if out else None
    except Exception:
        return None


def cpu_percent():
    out = run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    try:
        return max(0, min(100, int(float(out))))
    except Exception:
        return None


def memory_status():
    class M(ctypes.Structure):
        _fields_ = [
            ('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
            ('sullAvailExtendedVirtual', ctypes.c_ulonglong)
        ]
    m = M(); m.dwLength = ctypes.sizeof(M)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return {
        "ramPercent": int(m.dwMemoryLoad),
        "ramTotalGB": round(m.ullTotalPhys / (1024 ** 3), 1),
        "ramFreeGB": round(m.ullAvailPhys / (1024 ** 3), 1),
        "ramUsedGB": round((m.ullTotalPhys - m.ullAvailPhys) / (1024 ** 3), 1),
    }


def disk_status():
    try:
        total, used, free = __import__("shutil").disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        return {"diskPercent": int(used * 100 / total), "diskFreeGB": round(free / (1024 ** 3), 1)}
    except Exception:
        return {"diskPercent": None, "diskFreeGB": None}


def gpu_status():
    ps = "$v=(Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples | ? {$_.CookedValue -gt 0} | Measure-Object CookedValue -Sum; if($v){[math]::Round([math]::Min(100,$v.Sum),0)}"
    out = run_ps(ps, timeout=5)
    try:
        return {"gpuPercent": int(float(out)), "gpuTempC": None}
    except Exception:
        return {"gpuPercent": None, "gpuTempC": None}


def temp_status():
    ps = "$t=Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace 'root/wmi' -ErrorAction SilentlyContinue | Select -First 1 -Expand CurrentTemperature; if($t){[math]::Round(($t/10)-273.15,1)}"
    out = run_ps(ps)
    try:
        return {"cpuTempC": float(out)}
    except Exception:
        return {"cpuTempC": None}


def process_name(pid):
    try:
        k = ctypes.windll.kernel32
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return ""
        try:
            size = wintypes.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return pathlib.Path(buf.value).name
        finally:
            k.CloseHandle(h)
    except Exception:
        pass
    return ""


def active_window():
    u = ctypes.windll.user32
    hwnd = u.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "title": "", "process": ""}
    length = u.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    u.GetWindowTextW(hwnd, buf, len(buf))
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {"hwnd": int(hwnd), "title": buf.value[:120], "process": process_name(pid.value)}


def list_windows(limit=12):
    u = ctypes.windll.user32
    items = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if len(items) >= limit:
            return False
        if not u.IsWindowVisible(hwnd):
            return True
        length = u.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(min(length + 1, 512))
        u.GetWindowTextW(hwnd, buf, len(buf))
        title = buf.value.strip()
        if not title:
            return True
        pid = wintypes.DWORD(); u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        items.append({"hwnd": int(hwnd), "title": title[:100], "process": process_name(pid.value)})
        return True
    u.EnumWindows(cb, 0)
    return items


def valid_window(hwnd):
    try:
        hwnd = int(hwnd)
        return hwnd > 0 and bool(ctypes.windll.user32.IsWindow(hwnd)) and bool(ctypes.windll.user32.IsWindowVisible(hwnd))
    except Exception:
        return False


def window_action(action, hwnd):
    if not valid_window(hwnd):
        raise ValueError("INVALID WINDOW")
    u = ctypes.windll.user32
    hwnd = int(hwnd)
    if action == "WINDOW_FOCUS":
        u.ShowWindow(hwnd, SW_RESTORE); u.SetForegroundWindow(hwnd)
    elif action == "WINDOW_MIN":
        u.ShowWindow(hwnd, SW_MINIMIZE)
    elif action == "WINDOW_MAX":
        u.ShowWindow(hwnd, SW_MAXIMIZE)
    elif action == "WINDOW_CLOSE":
        u.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    return {"hwnd": hwnd}


def find_exe(names):
    for n in names:
        try:
            out = subprocess.check_output(["where", n], text=True, stderr=subprocess.DEVNULL).splitlines()
            if out:
                return out[0]
        except Exception:
            pass
    return None


def app_definitions():
    apps = load_json(APPS_FILE, DEFAULT_APPS)
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("PROGRAMFILES", "")
    pf86 = os.environ.get("PROGRAMFILES(X86)", "")
    fallbacks = {
        "chrome": [os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"), os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe")],
        "vscode": [os.path.join(local, "Programs", "Microsoft VS Code", "Code.exe")],
        "spotify": [os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe")],
        "discord": [os.path.join(local, "Discord", "Update.exe")],
        "steam": [os.path.join(pf86, "Steam", "steam.exe")],
        "files": ["explorer.exe"],
        "cmd": [os.environ.get("COMSPEC", "cmd.exe")],
    }
    for k, defs in apps.items():
        defs.setdefault("name", k)
        defs.setdefault("candidates", [])
        defs["_fallbacks"] = fallbacks.get(k, [])
    return apps


def open_app(app_id):
    apps = app_definitions()
    d = apps.get(str(app_id).lower())
    if not d:
        return False
    candidates = []
    for n in d.get("candidates", []):
        candidates.append(find_exe([n]) or n)
    candidates += d.get("_fallbacks", [])
    for c in candidates:
        if not c:
            continue
        if c in ("explorer.exe", os.environ.get("COMSPEC", "cmd.exe")) or os.path.exists(c):
            args = [c]
            if str(app_id).lower() == "discord" and str(c).endswith("Update.exe"):
                args += ["--processStart", "Discord.exe"]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    return False


def screenshot():
    out = pathlib.Path.home() / "Pictures" / "PCRemoteDeck"
    out.mkdir(parents=True, exist_ok=True)
    f = out / (time.strftime("shot_%Y%m%d_%H%M%S") + ".png")
    ps = f"Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $i=New-Object System.Drawing.Bitmap $b.Width,$b.Height; $g=[System.Drawing.Graphics]::FromImage($i); $g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); $i.Save('{str(f).replace(chr(39), chr(39)*2)}',[System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose();$i.Dispose()"
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps], timeout=12, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    notify("info", "Screenshot", f.name, {"path": str(f)})
    return str(f)


def network_counters():
    script = "Get-NetAdapterStatistics -ErrorAction SilentlyContinue | Where-Object {$_.ReceivedBytes -ne $null} | Measure-Object ReceivedBytes,SentBytes -Sum | Select @{n='rx';e={$_.Properties[0].Sum}},@{n='tx';e={$_.Properties[1].Sum}} | ConvertTo-Json -Compress"
    raw = run_ps(script)
    try:
        j = json.loads(raw or "{}")
        return int(j.get("rx") or 0), int(j.get("tx") or 0)
    except Exception:
        return 0, 0


def ping_ms(target):
    try:
        p = subprocess.run(["ping", "-n", "1", "-w", "900", target], capture_output=True, text=True, timeout=2, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        import re
        m = re.search(r"time[=<](\d+)ms", p.stdout, re.I)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def network_status():
    global NET_SAMPLE
    now = time.time(); rx, tx = network_counters()
    down = up = 0.0
    if NET_SAMPLE["ts"] and now > NET_SAMPLE["ts"] and rx >= NET_SAMPLE["rx"] and tx >= NET_SAMPLE["tx"]:
        dt = now - NET_SAMPLE["ts"]
        down = round((rx - NET_SAMPLE["rx"]) * 8 / dt / 1_000_000, 1)
        up = round((tx - NET_SAMPLE["tx"]) * 8 / dt / 1_000_000, 1)
    NET_SAMPLE = {"ts": now, "rx": rx, "tx": tx}
    ps = "Get-NetIPConfiguration | ? {$_.IPv4DefaultGateway -ne $null} | Select -First 1 @{n='ip';e={$_.IPv4Address.IPAddress}},@{n='gateway';e={$_.IPv4DefaultGateway.NextHop}},@{n='dns';e={($_.DNSServer.ServerAddresses -join ',')}} | ConvertTo-Json -Compress"
    raw = run_ps(ps)
    try:
        info = json.loads(raw or "{}")
    except Exception:
        info = {}
    target = str(CFG.get("ping_target") or info.get("gateway") or "1.1.1.1")
    latency = ping_ms(target)
    return {
        "ip": info.get("ip"), "gateway": info.get("gateway"), "dns": info.get("dns"),
        "downloadMbps": down, "uploadMbps": up, "pingMs": latency,
        "internet": latency is not None, "target": target,
    }


def top_processes(limit=5):
    script = f"Get-Process | Sort-Object CPU -Descending | Select -First {int(limit)} Name,Id,CPU,WorkingSet | ConvertTo-Json -Compress"
    raw = run_ps(script, timeout=5)
    try:
        arr = json.loads(raw or "[]")
        if isinstance(arr, dict): arr = [arr]
        out = []
        for p in arr:
            out.append({"name": p.get("Name", ""), "pid": p.get("Id"), "cpuTime": round(float(p.get("CPU") or 0), 1), "ramMB": round(float(p.get("WorkingSet") or 0) / 1048576, 1)})
        return out
    except Exception:
        return []


def audio_sessions():
    result = {"master": None, "sessions": [], "provider": "WINDOWS"}
    try:
        from pycaw.pycaw import AudioUtilities
        sessions = AudioUtilities.GetAllSessions()
        out = []
        for s in sessions:
            if not s.Process:
                continue
            v = s.SimpleAudioVolume
            out.append({"id": str(s.ProcessId), "name": s.Process.name(), "volume": int(round(v.GetMasterVolume() * 100)), "muted": bool(v.GetMute())})
        result["sessions"] = out[:12]
        result["provider"] = "PYCAW"
    except Exception:
        result["provider"] = "OPTIONAL_PYCAW_MISSING"
    sound = run_ps("Get-CimInstance Win32_SoundDevice -ErrorAction SilentlyContinue | Where-Object {$_.Status -eq 'OK'} | Select -First 1 -Expand Name")
    result["output"] = sound or "DEFAULT"
    return result


def set_audio_session(pid, volume=None, mute=None):
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            if s.Process and str(s.ProcessId) == str(pid):
                v = s.SimpleAudioVolume
                if volume is not None:
                    v.SetMasterVolume(max(0.0, min(1.0, float(volume) / 100.0)), None)
                if mute is not None:
                    v.SetMute(1 if bool(mute) else 0, None)
                return True
    except Exception:
        pass
    return False


def context_status():
    a = active_window(); exe = (a.get("process") or "").lower(); title = (a.get("title") or "").lower()
    profile = "GENERIC"
    if "chrome" in exe or "msedge" in exe:
        profile = "BROWSER"
    elif "code" in exe:
        profile = "DEV"
    elif "spotify" in exe:
        profile = "MEDIA"
    elif "steam" in exe or "game" in title:
        profile = "GAME"
    elif "discord" in exe or "teams" in exe or "zoom" in exe:
        profile = "MEETING"
    labels = {
        "BROWSER": ["ADDRESS", "REFRESH", "NEW TAB", "CLOSE TAB"],
        "DEV": ["SAVE", "TERMINAL", "RUN", "SEARCH"],
        "MEDIA": ["PREV", "PLAY", "NEXT", "MUTE"],
        "GAME": ["ALT+TAB", "MUTE", "SHOT", "DESKTOP"],
        "MEETING": ["MUTE", "ALT+TAB", "SHOT", "DESKTOP"],
        "GENERIC": ["ALT+TAB", "DESKTOP", "SHOT", "LOCK"],
    }
    return {"profile": profile, "active": a, "actions": labels[profile]}


def context_action(slot):
    profile = context_status()["profile"]
    slot = max(1, min(4, int(slot)))
    table = {
        "BROWSER": [(VK["CTRL"], VK["L"]), (VK["CTRL"], VK["R"]), (VK["CTRL"], VK["T"]), (VK["CTRL"], VK["W"])],
        "DEV": [(VK["CTRL"], VK["S"]), (VK["CTRL"], VK["J"]), (VK["F5"],), (VK["CTRL"], VK["SHIFT"], VK["F"])],
        "MEDIA": [(VK["MEDIA_PREV"],), (VK["MEDIA_PLAY_PAUSE"],), (VK["MEDIA_NEXT"],), (VK["MEDIA_MUTE"],)],
        "GAME": [(VK["ALT"], VK["TAB"]), (VK["MEDIA_MUTE"],), None, (VK["WIN"], VK["D"])],
        "MEETING": [(VK["MEDIA_MUTE"],), (VK["ALT"], VK["TAB"]), None, (VK["WIN"], VK["D"])],
        "GENERIC": [(VK["ALT"], VK["TAB"]), (VK["WIN"], VK["D"]), None, (VK["WIN"], VK["L"])],
    }
    action = table[profile][slot - 1]
    if action is None:
        screenshot(); return {"profile": profile, "slot": slot, "action": "SCREENSHOT"}
    combo(*action)
    return {"profile": profile, "slot": slot}


def dashboard():
    mem = memory_status(); cpu = cpu_percent(); net = network_status(); gpu = gpu_status(); temp = temp_status(); ctx = context_status(); disk = disk_status()
    d = {
        "state": "ONLINE", "host": os.environ.get("COMPUTERNAME", "WINDOWS-PC"),
        "cpuLogical": os.cpu_count(), "cpuPercent": cpu, "time": int(time.time()),
        "activeApp": ctx["active"].get("process") or ctx["active"].get("title") or "Desktop",
        "context": ctx, "network": net, "audio": audio_sessions(), "topProcesses": top_processes(4),
    }
    d.update(mem); d.update(gpu); d.update(temp); d.update(disk)
    if cpu is not None and cpu >= int(CFG.get("notification_cpu_percent", 92)):
        notify("warning", "CPU High", f"CPU {cpu}%")
    if mem["ramPercent"] >= int(CFG.get("notification_ram_percent", 90)):
        notify("warning", "RAM High", f"RAM {mem['ramPercent']}%")
    with NOTIFY_LOCK:
        d["notificationCount"] = len(NOTIFICATIONS)
        d["latestNotification"] = NOTIFICATIONS[0] if NOTIFICATIONS else None
    return d


SAFE_MACRO_ACTIONS = {
    "MEDIA_PLAY_PAUSE", "MEDIA_MUTE", "MEDIA_NEXT", "MEDIA_PREV", "VOLUME_UP", "VOLUME_DOWN",
    "SCREENSHOT", "SHOW_DESKTOP", "ALT_TAB", "CTRL_C", "CTRL_V",
    "APP_CHROME", "APP_VSCODE", "APP_SPOTIFY", "APP_DISCORD", "APP_STEAM", "APP_FILES",
    "BATTLE_STATION", "DEEP_FOCUS",
}


def macro_list():
    return load_json(MACRO_FILE, DEFAULT_MACROS)


def macro_save(payload):
    macro_id = str(payload.get("id") or "").strip().lower()
    name = str(payload.get("name") or macro_id).strip()[:40]
    steps = payload.get("steps") or []
    if not macro_id or not macro_id.replace("_", "").replace("-", "").isalnum():
        raise ValueError("BAD MACRO ID")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
        raise ValueError("MACRO STEPS 1-12")
    clean = []
    for s in steps:
        a = str(s).strip().upper()
        if a not in SAFE_MACRO_ACTIONS:
            raise ValueError("UNSAFE MACRO STEP: " + a)
        clean.append(a)
    m = macro_list(); m[macro_id] = {"name": name, "steps": clean}; save_json(MACRO_FILE, m)
    notify("info", "Macro Saved", name)
    return m[macro_id]


def macro_run(macro_id):
    m = macro_list(); item = m.get(str(macro_id).lower())
    if not item:
        raise ValueError("MACRO NOT FOUND")
    results = []
    for step in item.get("steps", []):
        if step not in SAFE_MACRO_ACTIONS:
            raise ValueError("MACRO STEP BLOCKED")
        msg, _ = execute(step, {})
        results.append(msg)
        time.sleep(0.18)
    notify("info", "Macro Complete", item.get("name", macro_id))
    return {"name": item.get("name", macro_id), "steps": results}


def execute(action, payload):
    u = ctypes.windll.user32
    if action == "PC_LOCK": u.LockWorkStation(); return "PC LOCKED", None
    if action in ("SYSTEM_SLEEP", "SYSTEM_RESTART", "SYSTEM_SHUTDOWN"):
        if payload.get("confirmed") is not True: raise ValueError("CONFIRMATION REQUIRED")
        if action == "SYSTEM_SLEEP":
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]); return "SLEEP REQUESTED", None
        if action == "SYSTEM_RESTART":
            subprocess.Popen(["shutdown.exe", "/r", "/t", "0"]); return "RESTART REQUESTED", None
        subprocess.Popen(["shutdown.exe", "/s", "/t", "0"]); return "SHUTDOWN REQUESTED", None
    if action in ("MEDIA_NEXT", "MEDIA_PREV", "MEDIA_PLAY_PAUSE", "MEDIA_MUTE", "VOLUME_UP", "VOLUME_DOWN"):
        key(VK[action]); return action, None
    if action == "SHOW_DESKTOP": combo(VK["WIN"], VK["D"]); return "SHOW DESKTOP", None
    if action == "ALT_TAB": combo(VK["ALT"], VK["TAB"]); return "ALT TAB", None
    if action == "CTRL_C": combo(VK["CTRL"], VK["C"]); return "CTRL+C", None
    if action == "CTRL_V": combo(VK["CTRL"], VK["V"]); return "CTRL+V", None
    if action.startswith("KEY_") and action[4:] in VK: key(VK[action[4:]]); return action, None
    if action == "MOUSE_LEFT": mouse(MOUSEEVENTF_LEFTDOWN); mouse(MOUSEEVENTF_LEFTUP); return action, None
    if action == "MOUSE_RIGHT": mouse(MOUSEEVENTF_RIGHTDOWN); mouse(MOUSEEVENTF_RIGHTUP); return action, None
    if action == "SCROLL_UP": mouse(MOUSEEVENTF_WHEEL, 120); return action, None
    if action == "SCROLL_DOWN": mouse(MOUSEEVENTF_WHEEL, -120); return action, None
    if action == "MOUSE_MOVE": return "MOUSE MOVE", mouse_move(int(payload.get("dx", 0)), int(payload.get("dy", 0)))
    if action == "SCREENSHOT": return "SCREENSHOT SAVED", {"path": screenshot()}
    if action in ("GET_PC_STATUS", "GET_DASHBOARD"): return "PC DASHBOARD", dashboard()
    if action == "GET_WINDOWS": return "WINDOWS", {"active": active_window(), "windows": list_windows()}
    if action in ("WINDOW_FOCUS", "WINDOW_MIN", "WINDOW_MAX", "WINDOW_CLOSE"):
        return action, window_action(action, payload.get("hwnd"))
    if action == "GET_AUDIO": return "AUDIO", audio_sessions()
    if action == "AUDIO_SESSION_SET":
        ok = set_audio_session(payload.get("pid"), payload.get("volume"), payload.get("mute"))
        if not ok: raise RuntimeError("AUDIO SESSION UNAVAILABLE")
        return "AUDIO SESSION UPDATED", audio_sessions()
    if action == "GET_NETWORK": return "NETWORK", network_status()
    if action == "NETWORK_PING":
        target = str(payload.get("target") or CFG.get("ping_target") or "1.1.1.1")[:120]
        return "PING", {"target": target, "pingMs": ping_ms(target)}
    if action == "GET_CONTEXT": return "CONTEXT", context_status()
    if action.startswith("CONTEXT_SLOT_"):
        return action, context_action(int(action.rsplit("_", 1)[-1]))
    if action == "GET_NOTIFICATIONS":
        with NOTIFY_LOCK: return "NOTIFICATIONS", {"items": list(NOTIFICATIONS), "count": len(NOTIFICATIONS)}
    if action == "NOTIFICATIONS_CLEAR":
        with NOTIFY_LOCK: NOTIFICATIONS.clear()
        return "NOTIFICATIONS CLEARED", None
    if action == "GET_MACROS": return "MACROS", {"macros": macro_list()}
    if action == "MACRO_SAVE": return "MACRO SAVED", macro_save(payload)
    if action == "MACRO_RUN": return "MACRO COMPLETE", macro_run(payload.get("id"))
    if action == "MACRO_DELETE":
        macro_id = str(payload.get("id") or "").lower(); m = macro_list()
        if macro_id in m: m.pop(macro_id); save_json(MACRO_FILE, m)
        return "MACRO DELETED", {"id": macro_id}
    if action == "GET_APPS":
        apps = app_definitions(); return "APPS", {"apps": [{"id": k, "name": v.get("name", k)} for k, v in apps.items()]}
    if action == "APP_LAUNCH":
        app_id = str(payload.get("id") or "").lower()
        if not open_app(app_id): raise RuntimeError("APP NOT FOUND")
        return "APP LAUNCHED", {"id": app_id}
    if action.startswith("APP_"):
        app_id = action[4:].lower()
        if not open_app(app_id): raise RuntimeError("APP NOT FOUND")
        return action, None
    if action == "BATTLE_STATION":
        open_app("steam"); open_app("discord"); key(VK["VOLUME_UP"])
        notify("info", "Protocol", "Battle Station active")
        return "BATTLE STATION", {"steam": "requested", "discord": "requested"}
    if action == "DEEP_FOCUS":
        open_app("vscode"); open_app("chrome")
        notify("info", "Protocol", "Deep Focus active")
        return "DEEP FOCUS", {"vscode": "requested", "chrome": "requested"}
    raise ValueError("COMMAND NOT WHITELISTED")


ALLOWED = {
    "PC_LOCK", "GET_PC_STATUS", "GET_DASHBOARD", "MEDIA_PLAY_PAUSE", "MEDIA_MUTE", "MEDIA_NEXT", "MEDIA_PREV", "VOLUME_UP", "VOLUME_DOWN",
    "SCREENSHOT", "SHOW_DESKTOP", "ALT_TAB", "CTRL_C", "CTRL_V", "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT",
    "MOUSE_LEFT", "MOUSE_RIGHT", "SCROLL_UP", "SCROLL_DOWN", "MOUSE_MOVE",
    "APP_CHROME", "APP_VSCODE", "APP_SPOTIFY", "APP_DISCORD", "APP_STEAM", "APP_FILES", "APP_CMD", "GET_APPS", "APP_LAUNCH",
    "BATTLE_STATION", "DEEP_FOCUS", "GET_WINDOWS", "WINDOW_FOCUS", "WINDOW_MIN", "WINDOW_MAX", "WINDOW_CLOSE",
    "GET_AUDIO", "AUDIO_SESSION_SET", "GET_NETWORK", "NETWORK_PING", "GET_CONTEXT", "CONTEXT_SLOT_1", "CONTEXT_SLOT_2", "CONTEXT_SLOT_3", "CONTEXT_SLOT_4",
    "GET_MACROS", "MACRO_SAVE", "MACRO_RUN", "MACRO_DELETE", "GET_NOTIFICATIONS", "NOTIFICATIONS_CLEAR",
    "SYSTEM_SLEEP", "SYSTEM_RESTART", "SYSTEM_SHUTDOWN",
}


def auth_ok(headers, body):
    token = str(CFG.get("token", ""))
    if not token or token == "CHANGE_ME": return False, "CHANGE TOKEN FIRST"
    if headers.get("Authorization", "") != "Bearer " + token: return False, "BAD TOKEN"
    ts = headers.get("X-PRD-Timestamp", ""); nonce = headers.get("X-PRD-Nonce", ""); sig = headers.get("X-PRD-Signature", "")
    try: t = int(ts)
    except Exception: return False, "BAD TIMESTAMP"
    if abs(int(time.time()) - t) > int(CFG.get("max_clock_skew_seconds", 30)): return False, "STALE REQUEST"
    if not nonce or len(nonce) > 100: return False, "BAD NONCE"
    now = time.time()
    with NONCE_LOCK:
        for k, v in list(NONCES.items()):
            if now - v > 120: NONCES.pop(k, None)
        if nonce in NONCES: return False, "REPLAY"
        expected = hmac.new(token.encode(), (ts + "\n" + nonce + "\n").encode() + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig): return False, "BAD SIGNATURE"
        NONCES[nonce] = now
    return True, "OK"


class Handler(BaseHTTPRequestHandler):
    server_version = "PCRemoteDeck/6"
    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/health": self._json(200, {"ok": True, "agent": "PC Remote Deck V6", "state": "ONLINE"})
        else: self._json(404, {"ok": False, "message": "NOT FOUND"})
    def do_POST(self):
        if urlparse(self.path).path != "/command": self._json(404, {"ok": False, "message": "NOT FOUND"}); return
        try:
            length = int(self.headers.get("Content-Length", "0")); body = self.rfile.read(min(length, 65536)); ok, why = auth_ok(self.headers, body)
        except Exception:
            self._json(400, {"ok": False, "message": "BAD REQUEST"}); return
        if not ok:
            self._json(401, {"ok": False, "message": why}); return
        try:
            req = json.loads(body.decode()); action = req.get("action", ""); payload = req.get("payload") or {}
            if action not in ALLOWED: raise ValueError("COMMAND NOT WHITELISTED")
            message, data = execute(action, payload)
            self._json(200, {"ok": True, "action": action, "message": message, "data": data})
        except ValueError as e: self._json(403, {"ok": False, "message": str(e)})
        except Exception as e: self._json(500, {"ok": False, "message": str(e)})
    def log_message(self, fmt, *args): print("[%s] %s" % (self.address_string(), fmt % args))


def main():
    if os.name != "nt": print("This agent is intended for Windows.", file=sys.stderr); return 2
    if CFG.get("token") == "CHANGE_ME": print("SECURITY STOP: run generate_token.py first."); return 3
    notify("info", "Agent", "PC Remote Deck V6 started")
    srv = ThreadingHTTPServer((CFG.get("bind", "0.0.0.0"), int(CFG.get("port", 8765))), Handler)
    print(f"PC Remote Deck V6 agent listening on {CFG.get('bind')}:{CFG.get('port')}")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
