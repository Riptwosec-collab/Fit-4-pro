#!/usr/bin/env python3
"""PC Remote Deck Windows agent. Whitelisted commands only; no arbitrary shell endpoint."""
import base64, ctypes, hashlib, hmac, json, os, pathlib, secrets, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "agent_config.json"
NONCES = {}
NONCE_LOCK = threading.Lock()

DEFAULT_CONFIG = {"bind":"0.0.0.0","port":8765,"token":"CHANGE_ME","max_clock_skew_seconds":30}

def load_config():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    cfg = DEFAULT_CONFIG.copy(); cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    return cfg

CFG = load_config()

VK = {"MEDIA_NEXT":0xB0,"MEDIA_PREV":0xB1,"MEDIA_PLAY_PAUSE":0xB3,"MEDIA_MUTE":0xAD,"VOLUME_DOWN":0xAE,"VOLUME_UP":0xAF,
      "UP":0x26,"DOWN":0x28,"LEFT":0x25,"RIGHT":0x27,"TAB":0x09,"CTRL":0x11,"ALT":0x12,"WIN":0x5B,"C":0x43,"V":0x56,"D":0x44}
KEYEVENTF_KEYUP=0x0002; MOUSEEVENTF_LEFTDOWN=0x0002; MOUSEEVENTF_LEFTUP=0x0004; MOUSEEVENTF_RIGHTDOWN=0x0008; MOUSEEVENTF_RIGHTUP=0x0010; MOUSEEVENTF_WHEEL=0x0800

def key(vk):
    u=ctypes.windll.user32; u.keybd_event(vk,0,0,0); u.keybd_event(vk,0,KEYEVENTF_KEYUP,0)
def combo(*vks):
    u=ctypes.windll.user32
    for v in vks: u.keybd_event(v,0,0,0)
    for v in reversed(vks): u.keybd_event(v,0,KEYEVENTF_KEYUP,0)
def mouse(flags,data=0): ctypes.windll.user32.mouse_event(flags,0,0,data,0)

def find_exe(names):
    for n in names:
        try:
            out=subprocess.check_output(["where",n], text=True, stderr=subprocess.DEVNULL).splitlines()
            if out:return out[0]
        except Exception: pass
    return None

def open_app(app):
    local=os.environ.get("LOCALAPPDATA",""); pf=os.environ.get("PROGRAMFILES",""); pf86=os.environ.get("PROGRAMFILES(X86)","")
    candidates={
        "chrome":[find_exe(["chrome.exe","chrome"]),os.path.join(pf,"Google","Chrome","Application","chrome.exe"),os.path.join(pf86,"Google","Chrome","Application","chrome.exe")],
        "vscode":[find_exe(["code.cmd","code.exe","code"]),os.path.join(local,"Programs","Microsoft VS Code","Code.exe")],
        "spotify":[find_exe(["Spotify.exe"]),os.path.join(os.environ.get("APPDATA",""),"Spotify","Spotify.exe")],
        "discord":[os.path.join(local,"Discord","Update.exe")],
        "steam":[find_exe(["steam.exe"]),os.path.join(pf86,"Steam","steam.exe")],
        "cmd":[os.environ.get("COMSPEC","cmd.exe")],
        "files":["explorer.exe"],
    }
    for c in candidates.get(app,[]):
        if c and (os.path.exists(c) or c in ("explorer.exe",os.environ.get("COMSPEC","cmd.exe"))):
            args=[c]
            if app=="discord" and c.endswith("Update.exe"):args += ["--processStart","Discord.exe"]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return True
    return False

def screenshot():
    out=pathlib.Path.home()/"Pictures"/"PCRemoteDeck"; out.mkdir(parents=True,exist_ok=True)
    f=out/(time.strftime("shot_%Y%m%d_%H%M%S")+".png")
    ps=f'''Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $i=New-Object System.Drawing.Bitmap $b.Width,$b.Height; $g=[System.Drawing.Graphics]::FromImage($i); $g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); $i.Save('{str(f).replace("'","''")}',[System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose();$i.Dispose()'''
    subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",ps], timeout=12, check=True, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)); return str(f)

def memory_status():
    class M(ctypes.Structure): _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('sullAvailExtendedVirtual',ctypes.c_ulonglong)]
    m=M();m.dwLength=ctypes.sizeof(M);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return {"ramPercent":int(m.dwMemoryLoad),"ramTotalGB":round(m.ullTotalPhys/(1024**3),1),"ramFreeGB":round(m.ullAvailPhys/(1024**3),1)}

def status():
    d={"state":"ONLINE","host":os.environ.get("COMPUTERNAME","WINDOWS-PC"),"cpuLogical":os.cpu_count(),"time":int(time.time())}; d.update(memory_status()); return d

def execute(action,payload):
    u=ctypes.windll.user32
    if action=="PC_LOCK": u.LockWorkStation(); return "PC LOCKED",None
    if action in ("MEDIA_NEXT","MEDIA_PREV","MEDIA_PLAY_PAUSE","MEDIA_MUTE","VOLUME_UP","VOLUME_DOWN"): key(VK[action]); return action,None
    if action=="SHOW_DESKTOP": combo(VK["WIN"],VK["D"]); return "SHOW DESKTOP",None
    if action=="ALT_TAB": combo(VK["ALT"],VK["TAB"]); return "ALT TAB",None
    if action=="CTRL_C": combo(VK["CTRL"],VK["C"]); return "CTRL+C",None
    if action=="CTRL_V": combo(VK["CTRL"],VK["V"]); return "CTRL+V",None
    if action.startswith("KEY_") and action[4:] in VK: key(VK[action[4:]]); return action,None
    if action=="MOUSE_LEFT": mouse(MOUSEEVENTF_LEFTDOWN);mouse(MOUSEEVENTF_LEFTUP);return action,None
    if action=="MOUSE_RIGHT": mouse(MOUSEEVENTF_RIGHTDOWN);mouse(MOUSEEVENTF_RIGHTUP);return action,None
    if action=="SCROLL_UP": mouse(MOUSEEVENTF_WHEEL,120);return action,None
    if action=="SCROLL_DOWN": mouse(MOUSEEVENTF_WHEEL,-120);return action,None
    if action=="SCREENSHOT": return "SCREENSHOT SAVED",{"path":screenshot()}
    if action=="GET_PC_STATUS": return "PC STATUS",status()
    if action.startswith("APP_"):
        ok=open_app(action[4:].lower());
        if not ok: raise RuntimeError("APP NOT FOUND")
        return action,None
    if action=="BATTLE_STATION":
        open_app("steam"); key(VK["VOLUME_UP"]); return "BATTLE STATION",{"steam":"requested"}
    if action=="DEEP_FOCUS":
        open_app("vscode"); return "DEEP FOCUS",{"vscode":"requested"}
    raise ValueError("COMMAND NOT WHITELISTED")

ALLOWED={"PC_LOCK","GET_PC_STATUS","MEDIA_PLAY_PAUSE","MEDIA_MUTE","MEDIA_NEXT","MEDIA_PREV","VOLUME_UP","VOLUME_DOWN","SCREENSHOT","SHOW_DESKTOP","ALT_TAB","CTRL_C","CTRL_V","KEY_UP","KEY_DOWN","KEY_LEFT","KEY_RIGHT","MOUSE_LEFT","MOUSE_RIGHT","SCROLL_UP","SCROLL_DOWN","APP_CHROME","APP_VSCODE","APP_SPOTIFY","APP_DISCORD","APP_STEAM","APP_FILES","APP_CMD","BATTLE_STATION","DEEP_FOCUS"}

def auth_ok(headers,body):
    token=str(CFG.get("token",""))
    if not token or token=="CHANGE_ME": return False,"CHANGE TOKEN FIRST"
    if headers.get("Authorization","") != "Bearer "+token: return False,"BAD TOKEN"
    ts=headers.get("X-PRD-Timestamp",""); nonce=headers.get("X-PRD-Nonce",""); sig=headers.get("X-PRD-Signature","")
    try: t=int(ts)
    except: return False,"BAD TIMESTAMP"
    if abs(int(time.time())-t)>int(CFG.get("max_clock_skew_seconds",30)):return False,"STALE REQUEST"
    if not nonce or len(nonce)>100:return False,"BAD NONCE"
    now=time.time()
    with NONCE_LOCK:
        for k,v in list(NONCES.items()):
            if now-v>120:NONCES.pop(k,None)
        if nonce in NONCES:return False,"REPLAY"
        expected=hmac.new(token.encode(),(ts+"\n"+nonce+"\n").encode()+body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,sig):return False,"BAD SIGNATURE"
        NONCES[nonce]=now
    return True,"OK"

class Handler(BaseHTTPRequestHandler):
    server_version="PCRemoteDeck/5"
    def _json(self,code,obj):
        b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=="/health":self._json(200,{"ok":True,"agent":"PC Remote Deck V5","state":"ONLINE"})
        else:self._json(404,{"ok":False,"message":"NOT FOUND"})
    def do_POST(self):
        if urlparse(self.path).path!="/command":self._json(404,{"ok":False,"message":"NOT FOUND"});return
        try:length=int(self.headers.get("Content-Length","0"));body=self.rfile.read(min(length,65536));ok,why=auth_ok(self.headers,body)
        except Exception as e:self._json(400,{"ok":False,"message":"BAD REQUEST"});return
        if not ok:self._json(401,{"ok":False,"message":why});return
        try:
            req=json.loads(body.decode());action=req.get("action","");payload=req.get("payload") or {}
            if action not in ALLOWED:raise ValueError("COMMAND NOT WHITELISTED")
            message,data=execute(action,payload);self._json(200,{"ok":True,"action":action,"message":message,"data":data})
        except ValueError as e:self._json(403,{"ok":False,"message":str(e)})
        except Exception as e:self._json(500,{"ok":False,"message":str(e)})
    def log_message(self,fmt,*args):print("[%s] %s"%(self.address_string(),fmt%args))

def main():
    if os.name!="nt": print("This agent is intended for Windows.",file=sys.stderr);return 2
    if CFG.get("token")=="CHANGE_ME": print("SECURITY STOP: edit agent_config.json or run generate_token.py first.");return 3
    srv=ThreadingHTTPServer((CFG.get("bind","0.0.0.0"),int(CFG.get("port",8765))),Handler)
    print(f"PC Remote Deck agent listening on {CFG.get('bind')}:{CFG.get('port')}")
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
    return 0
if __name__=="__main__":raise SystemExit(main())
