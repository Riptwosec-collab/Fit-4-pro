from pro_support import *
from pro_macro import MacroRunner

class ProEngine:
    def __init__(self,base):
        self.base=base;self.original_execute=base.execute;self.original_dashboard=base.dashboard;self.original_notify=base.notify
        self.settings=DEFAULT_PRO_SETTINGS.copy();self.settings.update(load_json(PRO_SETTINGS_FILE,DEFAULT_PRO_SETTINGS))
        self.event_bus=EventBus();self.history=TelemetryHistory(self.settings.get("history_seconds",300));self.notifications=NotificationCenter(self.event_bus);self.alerts=AlertDurationTracker();self.macros=MacroRunner(self)
        self.session_start=int(time.time());self.recent_apps=collections.deque(maxlen=12);self._dashboard_lock=threading.Lock();self._last_dashboard=None
        trust=load_json(TRUST_FILE,{});trust.setdefault("pairedTs",int(time.time()));trust.setdefault("lastAccessTs",int(time.time()));trust.setdefault("tokenRotatedTs",int(time.time()));save_json(TRUST_FILE,trust)

    def ensure_permission(self,action):
        perm=PERMISSION_BY_ACTION.get(action)
        if perm and not bool((self.settings.get("permissions") or {}).get(perm,False)):raise PermissionError(perm+" PERMISSION REQUIRED")
    def settings_view(self):return _clone(self.settings)
    def update_settings(self,payload):
        allowed={"telemetry_interval_seconds","context_mode","context_locked","manual_context","profile","motion_confidence_threshold","notification_min_priority","token_rotation_days","alert_thresholds","pinned_apps","favorite_audio_apps"}
        for k in allowed:
            if k in payload:self.settings[k]=payload[k]
        self.settings["telemetry_interval_seconds"]=max(2,min(60,int(self.settings.get("telemetry_interval_seconds",5))))
        self.settings["motion_confidence_threshold"]=max(60,min(99,int(self.settings.get("motion_confidence_threshold",85))))
        self.settings["token_rotation_days"]=max(0,min(365,int(self.settings.get("token_rotation_days",30))))
        save_json(PRO_SETTINGS_FILE,self.settings);self.event_bus.emit("SETTINGS_CHANGED",{"keys":list(payload.keys())});return self.settings_view()

    def dashboard_pro(self):
        with self._dashboard_lock:
            d=self.original_dashboard();d["uptimeSeconds"]=int(time.monotonic());d["battery"]=self.windows_battery();d["contextPro"]=self.context_status_pro();d["connectionQuality"]=self.connection_quality((d.get("network") or {}).get("pingMs"));d["permissions"]=_clone(self.settings.get("permissions") or {});d["agentVersion"]="8.0-pro"
            self.history.record(d);d["history"]=self.history.query(300);self.alerts.check(self.settings,d,self.notifications)
            visible=self.notifications.list(limit=60);minimum=str(self.settings.get("notification_min_priority","WARNING")).upper();rank=PRIORITY_ORDER.get(minimum,PRIORITY_ORDER["WARNING"]);visible=[x for x in visible if PRIORITY_ORDER.get(x.get("priority","INFO"),1)>=rank][:20]
            d["notificationCountPro"]=len(visible);d["latestNotificationPro"]=visible[0] if visible else None;self._last_dashboard=d;return d
    def dashboard_wrapper(self):return self.dashboard_pro()
    def windows_battery(self):
        raw=self.base.run_ps("$b=Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select -First 1 EstimatedChargeRemaining,BatteryStatus; if($b){$b|ConvertTo-Json -Compress}",timeout=3)
        try:
            o=json.loads(raw or "{}")
            if o:return {"percent":o.get("EstimatedChargeRemaining"),"status":o.get("BatteryStatus"),"available":True}
        except Exception:pass
        return {"percent":None,"status":None,"available":False}
    @staticmethod
    def connection_quality(ping):
        if ping is None:return "OFFLINE"
        if ping<=30:return "EXCELLENT"
        if ping<=80:return "GOOD"
        if ping<=150:return "FAIR"
        return "POOR"
    def control_hub(self):
        d=self.dashboard_pro();ctx=d.get("contextPro") or {};return {"state":d.get("state"),"host":d.get("host"),"cpu":d.get("cpuPercent"),"ram":d.get("ramPercent"),"gpu":d.get("gpuPercent"),"pingMs":(d.get("network") or {}).get("pingMs"),"quality":d.get("connectionQuality"),"context":ctx.get("profile"),"activeApp":(ctx.get("active") or {}).get("process") or d.get("activeApp"),"quickActions":ctx.get("actions",[])[:6],"profile":self.settings.get("profile","WORK")}

    def running_processes(self):
        raw=self.base.run_ps("Get-Process | Select Name,Id,CPU,WorkingSet,StartTime -ErrorAction SilentlyContinue | ConvertTo-Json -Compress",timeout=6)
        try:
            arr=json.loads(raw or "[]");arr=[arr] if isinstance(arr,dict) else arr;return [{"name":str(p.get("Name") or ""),"pid":p.get("Id"),"cpuTime":round(float(p.get("CPU") or 0),1),"ramMB":round(float(p.get("WorkingSet") or 0)/1048576,1)} for p in arr]
        except Exception:return []
    def top_processes_pro(self,metric="CPU",limit=8):
        metric=str(metric or "CPU").upper();limit=max(1,min(15,int(limit or 8)));items=self.running_processes()
        if metric=="RAM":items.sort(key=lambda x:x.get("ramMB") or 0,reverse=True)
        elif metric=="GPU":return {"metric":"GPU","items":[],"available":False,"reason":"PER-PROCESS GPU UNAVAILABLE"}
        else:items.sort(key=lambda x:x.get("cpuTime") or 0,reverse=True)
        return {"metric":metric,"items":items[:limit],"available":True}
    def mark_recent_app(self,app_id):
        app_id=str(app_id or "").lower()
        try:self.recent_apps.remove(app_id)
        except ValueError:pass
        if app_id:self.recent_apps.appendleft(app_id)
        self.event_bus.emit("APP_LAUNCHED",{"id":app_id})
    def apps_pro(self):
        defs=self.base.app_definitions();names=[x.get("name","").lower() for x in self.running_processes()];pins=list(self.settings.get("pinned_apps") or [])[:8];items=[]
        for app_id,spec in defs.items():
            cands=[str(x).lower().replace(".exe","").replace(".cmd","") for x in spec.get("candidates",[])];running=any(any(c and c in n for c in cands) for n in names);items.append({"id":app_id,"name":spec.get("name",app_id),"running":running,"pinned":app_id in pins,"recent":app_id in self.recent_apps})
        items.sort(key=lambda x:(not x["pinned"],not x["running"],not x["recent"],x["name"].lower()));return {"apps":items,"pinned":pins,"recent":list(self.recent_apps)}
    def app_smart(self,app_id):
        app_id=str(app_id or "").lower();apps={x["id"]:x for x in self.apps_pro()["apps"]};item=apps.get(app_id)
        if not item:raise ValueError("APP NOT FOUND")
        if item.get("running"):
            for w in self.base.list_windows(30):
                proc=(w.get("process") or "").lower()
                if app_id in proc or item["name"].lower() in proc:self.base.window_action("WINDOW_FOCUS",w["hwnd"]);self.event_bus.emit("APP_FOCUSED",{"id":app_id});return {"id":app_id,"action":"FOCUS"}
        if not self.base.open_app(app_id):raise RuntimeError("APP NOT FOUND")
        self.mark_recent_app(app_id);return {"id":app_id,"action":"LAUNCH"}

    def context_status_pro(self):
        mode=str(self.settings.get("context_mode","AUTO")).upper();locked=bool(self.settings.get("context_locked",False));active=self.base.active_window()
        if mode=="MANUAL" or locked:profile=str(self.settings.get("manual_context") or "DESKTOP").upper()
        else:
            exe=(active.get("process") or "").lower();title=(active.get("title") or "").lower();profile="DESKTOP"
            if any(x in exe for x in ("chrome","msedge","firefox","opera","brave")):profile="BROWSER"
            elif any(x in exe for x in ("code","devenv","pycharm","idea","webstorm")):profile="CODING"
            elif any(x in exe for x in ("teams","zoom","webex","skype")) or "meeting" in title:profile="MEETING"
            elif any(x in exe for x in ("spotify","vlc","music","netflix")) or "youtube" in title:profile="MEDIA"
            elif any(x in exe for x in ("steam","epicgameslauncher")) or "game" in title:profile="GAME"
            elif any(x in title for x in ("powerpoint slide show","presentation")):profile="PRESENTATION"
        amap={"BROWSER":["BACK","FORWARD","NEW TAB","CLOSE TAB","REFRESH","COPY URL"],"CODING":["SAVE","TERMINAL","RUN","SEARCH","GIT","MUTE"],"GAME":["GAME MACROS","AUDIO","PERFORMANCE","SCREENSHOT","MUTE","ALT+TAB"],"MEETING":["MUTE","CAMERA","SHARE","CHAT","LEAVE","VOLUME"],"MEDIA":["PLAY","NEXT","PREVIOUS","VOL+","VOL-","FULLSCREEN"],"PRESENTATION":["PREV SLIDE","NEXT SLIDE","BLACK SCREEN","TIMER","MUTE","END"],"DESKTOP":["ALT+TAB","DESKTOP","SHOT","LOCK","APPS","WINDOWS"],"IDLE":["WAKE","APPS","MONITOR","LOCK","TRUST","SETTINGS"],"CUSTOM":["ACTION 1","ACTION 2","ACTION 3","ACTION 4"]}
        return {"profile":profile,"mode":mode,"locked":locked,"active":active,"actions":amap.get(profile,amap["DESKTOP"])}
    def context_action_pro(self,slot):
        ctx=self.context_status_pro();profile=ctx.get("profile","DESKTOP");slot=max(1,min(4,int(slot)));b=self.base
        def combo(*names):b.combo(*[b.VK[n] for n in names])
        if profile=="BROWSER":actions=[("BACK",lambda:combo("ALT","LEFT")),("FORWARD",lambda:combo("ALT","RIGHT")),("NEW TAB",lambda:combo("CTRL","T")),("CLOSE TAB",lambda:combo("CTRL","W"))]
        elif profile=="CODING":actions=[("SAVE",lambda:combo("CTRL","S")),("TERMINAL",lambda:combo("CTRL","J")),("RUN",lambda:b.key(b.VK["F5"])),("SEARCH",lambda:combo("CTRL","SHIFT","F"))]
        elif profile=="MEDIA":actions=[("PLAY",lambda:b.key(b.VK["MEDIA_PLAY_PAUSE"])),("NEXT",lambda:b.key(b.VK["MEDIA_NEXT"])),("PREVIOUS",lambda:b.key(b.VK["MEDIA_PREV"])),("MUTE",lambda:b.key(b.VK["MEDIA_MUTE"]))]
        elif profile=="PRESENTATION":actions=[("PREV SLIDE",lambda:b.key(b.VK["LEFT"])),("NEXT SLIDE",lambda:b.key(b.VK["RIGHT"])),("BLACK SCREEN",lambda:b.key(ord("B"))),("MUTE",lambda:b.key(b.VK["MEDIA_MUTE"]))]
        elif profile in ("MEETING","GAME"):actions=[("MUTE",lambda:b.key(b.VK["MEDIA_MUTE"])),("ALT+TAB",lambda:combo("ALT","TAB")),("SHOT",lambda:b.screenshot()),("DESKTOP",lambda:combo("WIN","D"))]
        else:actions=[("ALT+TAB",lambda:combo("ALT","TAB")),("DESKTOP",lambda:combo("WIN","D")),("SHOT",lambda:b.screenshot()),("LOCK",lambda:ctypes.windll.user32.LockWorkStation())]
        label,fn=actions[slot-1];fn();self.event_bus.emit("CONTEXT_ACTION",{"profile":profile,"slot":slot,"label":label});return {"profile":profile,"slot":slot,"action":label}

    def monitors(self):
        raw=self.base.run_ps("Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { [pscustomobject]@{device=$_.DeviceName;primary=$_.Primary;x=$_.WorkingArea.X;y=$_.WorkingArea.Y;width=$_.WorkingArea.Width;height=$_.WorkingArea.Height} } | ConvertTo-Json -Compress",timeout=4)
        try:arr=json.loads(raw or "[]");return [arr] if isinstance(arr,dict) else arr
        except Exception:return []
    def windows_pro(self):return {"active":self.base.active_window(),"windows":self.base.list_windows(20),"monitors":self.monitors(),"thumbnailCapability":False,"thumbnailReason":"THUMBNAIL TRANSPORT NOT ENABLED"}
    def window_snap(self,hwnd,side):
        if not self.base.valid_window(hwnd):raise ValueError("INVALID WINDOW")
        u=ctypes.windll.user32;MONITOR_DEFAULTTONEAREST=2;hmon=u.MonitorFromWindow(int(hwnd),MONITOR_DEFAULTTONEAREST)
        class MONITORINFO(ctypes.Structure):_fields_=[("cbSize",wintypes.DWORD),("rcMonitor",wintypes.RECT),("rcWork",wintypes.RECT),("dwFlags",wintypes.DWORD)]
        mi=MONITORINFO();mi.cbSize=ctypes.sizeof(MONITORINFO)
        if not u.GetMonitorInfoW(hmon,ctypes.byref(mi)):raise RuntimeError("MONITOR INFO UNAVAILABLE")
        work=mi.rcWork;width=int((work.right-work.left)/2);x=work.left if side=="left" else work.left+width;u.ShowWindow(int(hwnd),self.base.SW_RESTORE);u.MoveWindow(int(hwnd),x,work.top,width,work.bottom-work.top,True);self.event_bus.emit("WINDOW_CHANGED",{"hwnd":int(hwnd),"snap":side});return {"hwnd":int(hwnd),"snap":side}
    def window_move_monitor(self,hwnd,monitor_index):
        if not self.base.valid_window(hwnd):raise ValueError("INVALID WINDOW")
        mons=self.monitors();idx=int(monitor_index)
        if idx<0 or idx>=len(mons):raise ValueError("MONITOR NOT FOUND")
        t=mons[idx];u=ctypes.windll.user32;r=wintypes.RECT();u.GetWindowRect(int(hwnd),ctypes.byref(r));w=min(r.right-r.left,int(t["width"]));h=min(r.bottom-r.top,int(t["height"]));u.ShowWindow(int(hwnd),self.base.SW_RESTORE);u.MoveWindow(int(hwnd),int(t["x"]),int(t["y"]),int(w),int(h),True);self.event_bus.emit("WINDOW_CHANGED",{"hwnd":int(hwnd),"monitor":idx});return {"hwnd":int(hwnd),"monitor":idx,"device":t.get("device")}

    def get_master_volume(self):
        try:
            from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            device=AudioUtilities.GetSpeakers();interface=device.Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None);endpoint=ctypes.cast(interface,ctypes.POINTER(IAudioEndpointVolume));return int(round(endpoint.GetMasterVolumeLevelScalar()*100))
        except Exception:return None
    def set_master_volume(self,volume):
        volume=max(0,min(100,int(volume)))
        try:
            from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            device=AudioUtilities.GetSpeakers();interface=device.Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None);endpoint=ctypes.cast(interface,ctypes.POINTER(IAudioEndpointVolume));endpoint.SetMasterVolumeLevelScalar(volume/100.,None);self.event_bus.emit("AUDIO_CHANGED",{"master":volume});return True
        except Exception:return False
    def audio_pro(self):
        d=self.base.audio_sessions();d["master"]=self.get_master_volume();d["favoriteApps"]=list(self.settings.get("favorite_audio_apps") or []);d["outputSwitchAvailable"]=False;d["outputSwitchReason"]="NO SAFE BUILT-IN OUTPUT SWITCH PROVIDER";return d
    def notify_proxy(self,kind,title,message,data=None):
        self.original_notify(kind,title,message,data);p=str(kind or "info").upper();p=p if p in PRIORITY_ORDER else "INFO";self.notifications.add(p,title,message,data)
    def trust_status(self):
        trust=load_json(TRUST_FILE,{});now=int(time.time());rot=int(trust.get("tokenRotatedTs") or now);days=int(self.settings.get("token_rotation_days",30));due=days>0 and now-rot>=days*86400
        return {"device":os.environ.get("COMPUTERNAME","WINDOWS-PC"),"status":"TRUSTED","pairedTs":int(trust.get("pairedTs") or now),"lastAccessTs":now,"sessionStartTs":self.session_start,"sessionAgeSeconds":now-self.session_start,"auth":"HMAC-SHA256","replayProtection":"NONCE","token":{"status":"ROTATION DUE" if due else "HEALTHY","rotatedTs":rot,"rotationDays":days,"rotationDue":due},"secretExposed":False}
    def rotate_token(self,payload):
        if payload.get("confirmed") is not True:raise ValueError("CONFIRMATION REQUIRED")
        cfg=self.base.load_config();cfg["token"]=secrets.token_urlsafe(32);save_json(self.base.CONFIG_FILE,cfg);self.base.CFG["token"]=cfg["token"];trust=load_json(TRUST_FILE,{});trust["tokenRotatedTs"]=int(time.time());save_json(TRUST_FILE,trust);self.event_bus.emit("TRUST_CHANGED",{"event":"TOKEN_ROTATED"},"WARNING");return {"status":"ROTATED","requiresRepair":True,"message":"TOKEN ROTATED. RE-PAIR PHONE USING QR."}

    def execute(self,action,payload):
        self.ensure_permission(action);cid=str(payload.get("_commandId") or ("pc-"+str(int(time.time()*1000))));self.event_bus.emit("COMMAND_RUNNING",{"commandId":cid,"action":action})
        if action=="GET_DASHBOARD_PRO":return "PC DASHBOARD PRO",self.dashboard_pro()
        if action=="GET_TELEMETRY_HISTORY":return "TELEMETRY HISTORY",self.history.query(payload.get("seconds",300))
        if action=="GET_TOP_PROCESSES":return "TOP PROCESSES",self.top_processes_pro(payload.get("metric","CPU"),payload.get("limit",8))
        if action=="GET_CONTROL_HUB":return "PC CONTROL HUB",self.control_hub()
        if action=="GET_EVENTS":return "EVENTS",{"items":self.event_bus.list(payload.get("limit",80),payload.get("event"))}
        if action=="GET_PRO_SETTINGS":return "PRO SETTINGS",self.settings_view()
        if action=="SET_PRO_SETTINGS":return "PRO SETTINGS UPDATED",self.update_settings(payload)
        if action=="GET_PERMISSIONS":return "PERMISSIONS",_clone(self.settings.get("permissions") or {})
        if action=="SET_PERMISSION":
            name=str(payload.get("name") or "").upper()
            if name not in (self.settings.get("permissions") or {}):raise ValueError("UNKNOWN PERMISSION")
            if payload.get("confirmed") is not True:raise ValueError("CONFIRMATION REQUIRED")
            self.settings["permissions"][name]=bool(payload.get("enabled"));save_json(PRO_SETTINGS_FILE,self.settings);self.event_bus.emit("PERMISSION_CHANGED",{"name":name,"enabled":self.settings["permissions"][name]},"WARNING");return "PERMISSION UPDATED",{"name":name,"enabled":self.settings["permissions"][name]}
        if action=="GET_PROFILES":return "PROFILES",{"active":self.settings.get("profile"),"profiles":PROFILE_DEFAULTS}
        if action=="PROFILE_SET":
            profile=str(payload.get("profile") or "").upper()
            if profile not in PROFILE_DEFAULTS:raise ValueError("UNKNOWN PROFILE")
            self.settings["profile"]=profile;save_json(PRO_SETTINGS_FILE,self.settings);self.event_bus.emit("PROFILE_CHANGED",{"profile":profile});return "PROFILE SET",{"profile":profile}
        if action=="MOUSE_LEFT_DOWN":self.base.mouse(self.base.MOUSEEVENTF_LEFTDOWN);return "MOUSE LEFT DOWN",None
        if action=="MOUSE_LEFT_UP":self.base.mouse(self.base.MOUSEEVENTF_LEFTUP);return "MOUSE LEFT UP",None
        if action=="MOUSE_DOUBLE":self.base.mouse(self.base.MOUSEEVENTF_LEFTDOWN);self.base.mouse(self.base.MOUSEEVENTF_LEFTUP);time.sleep(.06);self.base.mouse(self.base.MOUSEEVENTF_LEFTDOWN);self.base.mouse(self.base.MOUSEEVENTF_LEFTUP);return "MOUSE DOUBLE CLICK",None
        if action=="GET_WINDOWS_PRO":return "WINDOWS PRO",self.windows_pro()
        if action=="GET_MONITORS":return "MONITORS",{"monitors":self.monitors()}
        if action in ("WINDOW_SNAP_LEFT","WINDOW_SNAP_RIGHT"):hwnd=payload.get("hwnd") or self.base.active_window().get("hwnd");return action,self.window_snap(hwnd,"left" if action.endswith("LEFT") else "right")
        if action=="WINDOW_MOVE_MONITOR":hwnd=payload.get("hwnd") or self.base.active_window().get("hwnd");return action,self.window_move_monitor(hwnd,payload.get("monitor",0))
        if action=="GET_AUDIO_PRO":return "AUDIO PRO",self.audio_pro()
        if action=="AUDIO_MASTER_SET":
            if not self.set_master_volume(payload.get("volume",50)):raise RuntimeError("MASTER VOLUME PROVIDER UNAVAILABLE")
            return "MASTER VOLUME UPDATED",self.audio_pro()
        if action=="AUDIO_SESSION_PRO_SET":
            if not self.base.set_audio_session(payload.get("pid"),payload.get("volume"),payload.get("mute")):raise RuntimeError("AUDIO SESSION UNAVAILABLE")
            return "AUDIO SESSION UPDATED",self.audio_pro()
        if action=="AUDIO_OUTPUT_LIST":a=self.audio_pro();return "AUDIO OUTPUTS",{"active":a.get("output"),"switchAvailable":a.get("outputSwitchAvailable"),"items":[a.get("output")] if a.get("output") else []}
        if action=="GET_MACROS_V2":return "MACROS V2",{"macros":self.macros.list()}
        if action=="MACRO_V2_SAVE":return "MACRO V2 SAVED",self.macros.save(payload)
        if action=="MACRO_V2_RUN":return "MACRO V2 COMPLETE",self.macros.run(payload.get("id"))
        if action=="MACRO_V2_CANCEL":return "MACRO V2 CANCEL",self.macros.cancel(str(payload.get("runId") or ""))
        if action=="MACRO_V2_DELETE":return "MACRO V2 DELETED",self.macros.delete(payload.get("id"))
        if action=="GET_APPS_PRO":return "APPS PRO",self.apps_pro()
        if action=="APP_SMART":return "APP SMART",self.app_smart(payload.get("id"))
        if action in ("APP_PIN","APP_UNPIN"):
            app_id=str(payload.get("id") or "").lower();pins=list(self.settings.get("pinned_apps") or [])
            if action=="APP_PIN" and app_id and app_id not in pins:pins.append(app_id)
            if action=="APP_UNPIN" and app_id in pins:pins.remove(app_id)
            self.settings["pinned_apps"]=pins[:8];save_json(PRO_SETTINGS_FILE,self.settings);return "APP PINS UPDATED",{"pinned":self.settings["pinned_apps"]}
        if action.startswith("CONTEXT_SLOT_"):return action,self.context_action_pro(int(action.rsplit("_",1)[-1]))
        if action=="GET_CONTEXT_PRO":return "CONTEXT PRO",self.context_status_pro()
        if action=="CONTEXT_SET_MODE":
            mode=str(payload.get("mode") or "AUTO").upper()
            if mode not in ("AUTO","MANUAL"):raise ValueError("MODE AUTO/MANUAL ONLY")
            self.settings["context_mode"]=mode;self.settings["context_locked"]=bool(payload.get("locked",False));save_json(PRO_SETTINGS_FILE,self.settings);self.event_bus.emit("CONTEXT_CHANGED",self.context_status_pro());return "CONTEXT MODE UPDATED",self.context_status_pro()
        if action=="CONTEXT_SET_MANUAL":
            profile=str(payload.get("profile") or "DESKTOP").upper()
            if profile not in PROFILE_DEFAULTS and profile not in ("BROWSER","CODING","GAME","MEETING","MEDIA","DESKTOP","IDLE","CUSTOM","PRESENTATION"):raise ValueError("UNKNOWN CONTEXT")
            self.settings["manual_context"]=profile;self.settings["context_mode"]="MANUAL";save_json(PRO_SETTINGS_FILE,self.settings);self.event_bus.emit("CONTEXT_CHANGED",self.context_status_pro());return "CONTEXT MANUAL",self.context_status_pro()
        if action=="GET_NOTIFICATIONS_PRO":return "NOTIFICATIONS PRO",{"items":self.notifications.list(payload.get("priority"),payload.get("includeSnoozed",False),payload.get("limit",60))}
        if action=="NOTIFICATION_ACK":return "NOTIFICATION ACKNOWLEDGED",self.notifications.ack(payload.get("id"))
        if action=="NOTIFICATION_SNOOZE":return "NOTIFICATION SNOOZED",self.notifications.snooze(payload.get("id"),payload.get("minutes",5))
        if action=="NOTIFICATION_CLEAR_PRO":self.notifications.clear();return "NOTIFICATIONS CLEARED",None
        if action=="GET_TRUST_PRO":return "TRUST PRO",self.trust_status()
        if action=="TRUST_ROTATE_TOKEN":return "TOKEN ROTATED",self.rotate_token(payload)
        if action=="TRUST_SET_ROTATION":
            days=int(payload.get("days",30))
            if days not in (0,30,60,90):raise ValueError("ROTATION DAYS MUST BE 0/30/60/90")
            self.settings["token_rotation_days"]=days;save_json(PRO_SETTINGS_FILE,self.settings);return "TOKEN ROTATION UPDATED",self.trust_status()
        return self.original_execute(action,payload)
    def finish_command(self,action,ok,data=None):self.event_bus.emit("COMMAND_DONE" if ok else "COMMAND_FAILED",{"action":action,"data":data or {}},"INFO" if ok else "WARNING")
