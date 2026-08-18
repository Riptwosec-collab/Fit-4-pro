#!/usr/bin/env python3
"""Shared V8 Pro support primitives for PC Remote Deck."""
from __future__ import annotations
import collections,ctypes,json,os,pathlib,secrets,subprocess,threading,time,urllib.parse,webbrowser
from ctypes import wintypes
ROOT=pathlib.Path(__file__).resolve().parent
PRO_SETTINGS_FILE=ROOT/"pro_settings.json";MACRO_V2_FILE=ROOT/"macros_v2.json";TRUST_FILE=ROOT/"trust_state.json"
DEFAULT_PRO_SETTINGS={"telemetry_interval_seconds":5,"history_seconds":300,"context_mode":"AUTO","context_locked":False,"manual_context":"DESKTOP","profile":"WORK","motion_confidence_threshold":85,"notification_min_priority":"WARNING","token_rotation_days":30,"alert_thresholds":{"cpuPercent":{"threshold":90,"duration":15},"gpuPercent":{"threshold":95,"duration":15},"ramPercent":{"threshold":90,"duration":15},"cpuTempC":{"threshold":85,"duration":15},"gpuTempC":{"threshold":85,"duration":15}},"permissions":{"SYSTEM_MONITOR":True,"INPUT_CONTROL":True,"WINDOW_CONTROL":True,"AUDIO":True,"APP_LAUNCH":True,"NOTIFICATION":True,"MACRO":True,"TRUST":True},"pinned_apps":["chrome","vscode","discord","spotify","steam","files","cmd"],"favorite_audio_apps":["spotify","chrome","discord"]}
DEFAULT_MACROS_V2={"work":{"name":"Work Mode","folder":"Profiles","icon":"briefcase","accent":"cyan","favorite":True,"pinned":True,"steps":[{"type":"APP","id":"vscode"},{"type":"DELAY","ms":500},{"type":"APP","id":"chrome"},{"type":"PC_COMMAND","action":"DEEP_FOCUS"}]},"game":{"name":"Game Mode","folder":"Profiles","icon":"gamepad","accent":"cyan","favorite":True,"pinned":True,"steps":[{"type":"APP","id":"steam"},{"type":"APP","id":"discord"},{"type":"PC_COMMAND","action":"BATTLE_STATION"}]},"meeting":{"name":"Meeting Mode","folder":"Profiles","icon":"microphone","accent":"cyan","favorite":True,"pinned":True,"steps":[{"type":"PC_COMMAND","action":"MEDIA_MUTE"},{"type":"PC_COMMAND","action":"SHOW_DESKTOP"}]}}
PROFILE_DEFAULTS={"WORK":{"context":"DESKTOP","notification":"WARNING"},"CODING":{"context":"CODING","notification":"WARNING"},"MEETING":{"context":"MEETING","notification":"WARNING"},"MEDIA":{"context":"MEDIA","notification":"CRITICAL"},"GAME":{"context":"GAME","notification":"CRITICAL"},"PRESENTATION":{"context":"PRESENTATION","notification":"WARNING"},"CUSTOM":{"context":"DESKTOP","notification":"WARNING"}}
PRIORITY_ORDER={"INFO":1,"WARNING":2,"CRITICAL":3}
NEW_ACTIONS={"GET_DASHBOARD_PRO","GET_TELEMETRY_HISTORY","GET_TOP_PROCESSES","GET_CONTROL_HUB","GET_EVENTS","GET_PRO_SETTINGS","SET_PRO_SETTINGS","GET_PERMISSIONS","SET_PERMISSION","GET_PROFILES","PROFILE_SET","MOUSE_LEFT_DOWN","MOUSE_LEFT_UP","MOUSE_DOUBLE","GET_WINDOWS_PRO","GET_MONITORS","WINDOW_SNAP_LEFT","WINDOW_SNAP_RIGHT","WINDOW_MOVE_MONITOR","GET_AUDIO_PRO","AUDIO_MASTER_SET","AUDIO_SESSION_PRO_SET","AUDIO_OUTPUT_LIST","GET_MACROS_V2","MACRO_V2_SAVE","MACRO_V2_RUN","MACRO_V2_CANCEL","MACRO_V2_DELETE","GET_APPS_PRO","APP_SMART","APP_PIN","APP_UNPIN","GET_CONTEXT_PRO","CONTEXT_SET_MODE","CONTEXT_SET_MANUAL","GET_NOTIFICATIONS_PRO","NOTIFICATION_ACK","NOTIFICATION_SNOOZE","NOTIFICATION_CLEAR_PRO","GET_TRUST_PRO","TRUST_ROTATE_TOKEN","TRUST_SET_ROTATION"}
PERMISSION_BY_ACTION={"GET_DASHBOARD":"SYSTEM_MONITOR","GET_DASHBOARD_PRO":"SYSTEM_MONITOR","GET_PC_STATUS":"SYSTEM_MONITOR","GET_TELEMETRY_HISTORY":"SYSTEM_MONITOR","GET_TOP_PROCESSES":"SYSTEM_MONITOR","GET_CONTROL_HUB":"SYSTEM_MONITOR","MOUSE_MOVE":"INPUT_CONTROL","MOUSE_LEFT":"INPUT_CONTROL","MOUSE_RIGHT":"INPUT_CONTROL","MOUSE_LEFT_DOWN":"INPUT_CONTROL","MOUSE_LEFT_UP":"INPUT_CONTROL","MOUSE_DOUBLE":"INPUT_CONTROL","SCROLL_UP":"INPUT_CONTROL","SCROLL_DOWN":"INPUT_CONTROL","GET_WINDOWS":"WINDOW_CONTROL","GET_WINDOWS_PRO":"WINDOW_CONTROL","GET_MONITORS":"WINDOW_CONTROL","WINDOW_FOCUS":"WINDOW_CONTROL","WINDOW_MIN":"WINDOW_CONTROL","WINDOW_MAX":"WINDOW_CONTROL","WINDOW_CLOSE":"WINDOW_CONTROL","WINDOW_SNAP_LEFT":"WINDOW_CONTROL","WINDOW_SNAP_RIGHT":"WINDOW_CONTROL","WINDOW_MOVE_MONITOR":"WINDOW_CONTROL","GET_AUDIO":"AUDIO","GET_AUDIO_PRO":"AUDIO","AUDIO_SESSION_SET":"AUDIO","AUDIO_SESSION_PRO_SET":"AUDIO","AUDIO_MASTER_SET":"AUDIO","AUDIO_OUTPUT_LIST":"AUDIO","GET_APPS":"APP_LAUNCH","GET_APPS_PRO":"APP_LAUNCH","APP_LAUNCH":"APP_LAUNCH","APP_SMART":"APP_LAUNCH","APP_PIN":"APP_LAUNCH","APP_UNPIN":"APP_LAUNCH","GET_MACROS":"MACRO","GET_MACROS_V2":"MACRO","MACRO_SAVE":"MACRO","MACRO_RUN":"MACRO","MACRO_DELETE":"MACRO","MACRO_V2_SAVE":"MACRO","MACRO_V2_RUN":"MACRO","MACRO_V2_CANCEL":"MACRO","MACRO_V2_DELETE":"MACRO","GET_NOTIFICATIONS":"NOTIFICATION","GET_NOTIFICATIONS_PRO":"NOTIFICATION","NOTIFICATION_ACK":"NOTIFICATION","NOTIFICATION_SNOOZE":"NOTIFICATION","NOTIFICATION_CLEAR_PRO":"NOTIFICATION","GET_TRUST_PRO":"TRUST","TRUST_ROTATE_TOKEN":"TRUST","TRUST_SET_ROTATION":"TRUST"}
RISKY_ACTIONS={"SYSTEM_SHUTDOWN","SYSTEM_RESTART","SYSTEM_SLEEP","WINDOW_CLOSE","TRUST_ROTATE_TOKEN"}
SAFE_PC_COMMAND_STEPS={"MEDIA_PLAY_PAUSE","MEDIA_MUTE","MEDIA_NEXT","MEDIA_PREV","VOLUME_UP","VOLUME_DOWN","SCREENSHOT","SHOW_DESKTOP","ALT_TAB","CTRL_C","CTRL_V","APP_CHROME","APP_VSCODE","APP_SPOTIFY","APP_DISCORD","APP_STEAM","APP_FILES","BATTLE_STATION","DEEP_FOCUS"}
ALLOWED_MACRO_TYPES={"KEY","HOTKEY","TEXT","APP","URL","DELAY","WINDOW","AUDIO","MEDIA","CONDITION","PC_COMMAND"}
def _clone(o):return json.loads(json.dumps(o))
def load_json(path,default):
    if not path.exists():return _clone(default)
    try:
        v=json.loads(path.read_text(encoding="utf-8"));return v if isinstance(v,type(default)) else _clone(default)
    except Exception:return _clone(default)
def save_json(path,value):
    t=path.with_suffix(path.suffix+".tmp");t.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8");t.replace(path)
class EventBus:
    def __init__(self,limit=300):self._items=collections.deque(maxlen=limit);self._lock=threading.Lock();self._seq=0
    def emit(self,event,data=None,priority="INFO"):
        with self._lock:self._seq+=1;item={"id":self._seq,"ts":int(time.time()),"event":str(event),"priority":priority if priority in PRIORITY_ORDER else "INFO","data":data or {}};self._items.appendleft(item);return dict(item)
    def list(self,limit=80,event=None):
        limit=max(1,min(200,int(limit or 80)))
        with self._lock:v=list(self._items)
        if event:v=[x for x in v if x.get("event")==event]
        return v[:limit]
class TelemetryHistory:
    def __init__(self,max_seconds=300,min_interval=2):self._lock=threading.Lock();self._points=collections.deque(maxlen=max(90,int(max_seconds/max(1,min_interval))+20));self._last=0.;self._min_interval=min_interval
    def record(self,d):
        now=time.time()
        with self._lock:
            if now-self._last<self._min_interval:return
            self._last=now;n=d.get("network") or {};self._points.append({"ts":int(now),"cpu":d.get("cpuPercent"),"gpu":d.get("gpuPercent"),"ram":d.get("ramPercent"),"down":n.get("downloadMbps"),"up":n.get("uploadMbps")})
    def query(self,seconds=300):
        seconds=max(60,min(300,int(seconds or 300)));cut=int(time.time())-seconds
        with self._lock:p=[x for x in self._points if x["ts"]>=cut]
        return {"seconds":seconds,"points":p}
class NotificationCenter:
    def __init__(self,event_bus,limit=120):self.event_bus=event_bus;self.limit=limit;self._lock=threading.Lock();self._items=[];self._next_id=1
    def add(self,priority,title,message,data=None,dedupe_key=None):
        priority=priority.upper() if str(priority).upper() in PRIORITY_ORDER else "INFO";now=int(time.time());key=dedupe_key or (priority+"|"+title+"|"+message)
        with self._lock:
            for item in self._items:
                if item.get("dedupeKey")==key and now-int(item.get("lastTs",0))<=300:item["count"]=int(item.get("count",1))+1;item["lastTs"]=now;item["message"]=message;item["priority"]=max([item.get("priority","INFO"),priority],key=lambda x:PRIORITY_ORDER.get(x,1));self.event_bus.emit("NOTIFICATION_RECEIVED",{"id":item["id"],"count":item["count"]},item["priority"]);return dict(item)
            item={"id":self._next_id,"ts":now,"lastTs":now,"priority":priority,"title":title[:80],"message":message[:200],"data":data or {},"count":1,"acknowledged":False,"snoozeUntil":0,"dedupeKey":key};self._next_id+=1;self._items.insert(0,item);del self._items[self.limit:]
        self.event_bus.emit("NOTIFICATION_RECEIVED",{"id":item["id"],"title":title},priority);return dict(item)
    def list(self,priority=None,include_snoozed=False,limit=60):
        now=int(time.time());limit=max(1,min(120,int(limit or 60)))
        with self._lock:items=[dict(x) for x in self._items]
        if priority and priority.upper() in PRIORITY_ORDER:items=[x for x in items if x.get("priority")==priority.upper()]
        if not include_snoozed:items=[x for x in items if int(x.get("snoozeUntil",0))<=now]
        return items[:limit]
    def ack(self,i):
        with self._lock:
            for x in self._items:
                if str(x.get("id"))==str(i):x["acknowledged"]=True;self.event_bus.emit("NOTIFICATION_ACKNOWLEDGED",{"id":x["id"]});return dict(x)
        raise ValueError("NOTIFICATION NOT FOUND")
    def snooze(self,i,minutes):
        minutes=max(1,min(1440,int(minutes or 5)));until=int(time.time())+minutes*60
        with self._lock:
            for x in self._items:
                if str(x.get("id"))==str(i):x["snoozeUntil"]=until;self.event_bus.emit("NOTIFICATION_SNOOZED",{"id":x["id"],"minutes":minutes});return dict(x)
        raise ValueError("NOTIFICATION NOT FOUND")
    def clear(self):
        with self._lock:self._items.clear()
        self.event_bus.emit("NOTIFICATIONS_CLEARED")
class AlertDurationTracker:
    def __init__(self):self._since={};self._last_emit={}
    def check(self,settings,dashboard,center):
        thresholds=settings.get("alert_thresholds") or {};now=time.time()
        for metric,cfg in thresholds.items():
            val=dashboard.get(metric);threshold=cfg.get("threshold");duration=int(cfg.get("duration",15))
            if not isinstance(val,(int,float)) or not isinstance(threshold,(int,float)):self._since.pop(metric,None);continue
            if val>threshold:
                self._since.setdefault(metric,now);elapsed=int(now-self._since[metric])
                if elapsed<duration:continue
                priority="CRITICAL" if elapsed>=max(duration*8,120) else "WARNING" if elapsed>=max(duration*2,30) else "INFO";last=self._last_emit.get(metric,0)
                if now-last>=30:self._last_emit[metric]=now;title=metric.replace("Percent","").replace("TempC"," Temp").upper()+" HIGH";center.add(priority,title,f"{metric} {val} above {threshold} for {elapsed}s",{"metric":metric,"value":val,"threshold":threshold,"duration":elapsed},dedupe_key="THRESHOLD:"+metric)
            else:self._since.pop(metric,None)
