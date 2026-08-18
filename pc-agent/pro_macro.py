from pro_support import *

class MacroRunner:
    def __init__(self,engine):self.engine=engine;self._lock=threading.Lock();self._cancel={};self._runs={}
    def list(self):return load_json(MACRO_V2_FILE,DEFAULT_MACROS_V2)
    def _validate_step(self,step):
        if not isinstance(step,dict):raise ValueError("MACRO STEP MUST BE OBJECT")
        typ=str(step.get("type") or "").upper()
        if typ not in ALLOWED_MACRO_TYPES:raise ValueError("UNSUPPORTED MACRO TYPE: "+typ)
        clean={"type":typ}
        if typ=="DELAY":clean["ms"]=max(0,min(5000,int(step.get("ms",500))))
        elif typ=="APP":
            clean["id"]=str(step.get("id") or "")[:40].lower()
            if not clean["id"]:raise ValueError("APP ID REQUIRED")
        elif typ=="URL":
            url=str(step.get("url") or "")[:500];parsed=urllib.parse.urlparse(url)
            if parsed.scheme not in ("http","https"):raise ValueError("URL MUST BE HTTP/HTTPS")
            clean["url"]=url
        elif typ=="TEXT":clean["text"]=str(step.get("text") or "")[:500]
        elif typ in ("KEY","HOTKEY"):
            keys=step.get("keys") or [];keys=[keys] if isinstance(keys,str) else keys;clean["keys"]=[str(x).upper()[:20] for x in keys][:4]
            if not clean["keys"]:raise ValueError("KEYS REQUIRED")
        elif typ=="WINDOW":
            a=str(step.get("action") or "").upper()
            if a not in {"FOCUS","MIN","MAX","SNAP_LEFT","SNAP_RIGHT"}:raise ValueError("WINDOW ACTION BLOCKED")
            clean["action"]=a
        elif typ=="AUDIO":
            a=str(step.get("action") or "").upper()
            if a not in {"MUTE","VOL_UP","VOL_DOWN","MASTER_SET"}:raise ValueError("AUDIO ACTION BLOCKED")
            clean["action"]=a
            if a=="MASTER_SET":clean["volume"]=max(0,min(100,int(step.get("volume",50))))
        elif typ=="MEDIA":
            a=str(step.get("action") or "").upper()
            if a not in {"PLAY_PAUSE","NEXT","PREV","MUTE"}:raise ValueError("MEDIA ACTION BLOCKED")
            clean["action"]=a
        elif typ=="CONDITION":
            c=str(step.get("condition") or "").upper()
            if c not in {"APP_RUNNING","WINDOW_EXISTS","CONTEXT_EQUALS","AUDIO_PLAYING"}:raise ValueError("CONDITION BLOCKED")
            clean["condition"]=c;clean["value"]=str(step.get("value") or "")[:120];clean["then"]=[self._validate_step(s) for s in (step.get("then") or [])[:8]];clean["else"]=[self._validate_step(s) for s in (step.get("else") or [])[:8]]
        elif typ=="PC_COMMAND":
            a=str(step.get("action") or "").upper()
            if a not in SAFE_PC_COMMAND_STEPS:raise ValueError("UNSAFE PC COMMAND STEP")
            clean["action"]=a
        return clean
    def save(self,payload):
        mid=str(payload.get("id") or "").strip().lower()
        if not mid or not mid.replace("_","").replace("-","").isalnum():raise ValueError("BAD MACRO ID")
        steps=payload.get("steps") or []
        if not isinstance(steps,list) or not 1<=len(steps)<=32:raise ValueError("MACRO STEPS 1-32")
        clean={"name":str(payload.get("name") or mid)[:50],"folder":str(payload.get("folder") or "General")[:30],"icon":str(payload.get("icon") or "bolt")[:30],"accent":str(payload.get("accent") or "cyan")[:20],"favorite":bool(payload.get("favorite",False)),"pinned":bool(payload.get("pinned",False)),"steps":[self._validate_step(s) for s in steps],"updatedTs":int(time.time())}
        items=self.list();items[mid]=clean;save_json(MACRO_V2_FILE,items);self.engine.event_bus.emit("MACRO_SAVED",{"id":mid,"name":clean["name"]});return clean
    def delete(self,mid):
        items=self.list();mid=str(mid or "").lower();items.pop(mid,None);save_json(MACRO_V2_FILE,items);self.engine.event_bus.emit("MACRO_DELETED",{"id":mid});return {"id":mid}
    def cancel(self,run_id):
        with self._lock:
            if run_id in self._cancel:self._cancel[run_id].set();return {"runId":run_id,"state":"CANCEL_REQUESTED"}
        raise ValueError("MACRO RUN NOT FOUND")
    def run(self,mid):
        items=self.list();item=items.get(str(mid or "").lower())
        if not item:raise ValueError("MACRO NOT FOUND")
        rid="macro-"+str(int(time.time()*1000));cancel=threading.Event()
        with self._lock:self._cancel[rid]=cancel;self._runs[rid]={"state":"RUNNING","step":0,"total":len(item["steps"]),"name":item["name"]}
        self.engine.event_bus.emit("MACRO_STARTED",{"id":mid,"runId":rid,"name":item["name"]});results=[];state="RUNNING"
        try:
            for index,step in enumerate(item["steps"],1):
                if cancel.is_set():raise RuntimeError("MACRO CANCELLED")
                with self._lock:self._runs[rid]["step"]=index;self._runs[rid]["current"]=step.get("type")
                results.append(self._execute_step(step))
            state="DONE";self.engine.event_bus.emit("MACRO_FINISHED",{"id":mid,"runId":rid,"name":item["name"]})
        except Exception as exc:
            state="CANCELLED" if "CANCELLED" in str(exc) else "FAILED";self.engine.event_bus.emit("MACRO_FAILED",{"id":mid,"runId":rid,"error":str(exc)},"WARNING");raise
        finally:
            with self._lock:
                if rid in self._runs:self._runs[rid]["state"]=state
                self._cancel.pop(rid,None)
        return {"runId":rid,"state":state,"name":item["name"],"steps":results}
    def _execute_step(self,step):
        typ=step["type"];b=self.engine.base
        if typ=="DELAY":time.sleep(step["ms"]/1000.);return {"type":typ,"ms":step["ms"]}
        if typ=="APP":
            if not b.open_app(step["id"]):raise RuntimeError("APP NOT FOUND: "+step["id"])
            self.engine.mark_recent_app(step["id"]);return {"type":typ,"id":step["id"]}
        if typ=="URL":webbrowser.open(step["url"],new=2);return {"type":typ,"url":step["url"]}
        if typ=="TEXT":
            escaped=step["text"].replace("'","''");b.run_ps(f"Set-Clipboard -Value '{escaped}'",timeout=3);b.combo(b.VK["CTRL"],b.VK["V"]);return {"type":typ,"chars":len(step["text"])}
        if typ in ("KEY","HOTKEY"):
            v=[]
            for k in step["keys"]:
                if k not in b.VK:raise RuntimeError("KEY NOT ALLOWED: "+k)
                v.append(b.VK[k])
            b.key(v[0]) if len(v)==1 else b.combo(*v);return {"type":typ,"keys":step["keys"]}
        if typ=="WINDOW":
            h=b.active_window().get("hwnd");a=step["action"]
            if a in ("FOCUS","MIN","MAX"):b.window_action({"FOCUS":"WINDOW_FOCUS","MIN":"WINDOW_MIN","MAX":"WINDOW_MAX"}[a],h)
            else:self.engine.window_snap(h,"left" if a=="SNAP_LEFT" else "right")
            return {"type":typ,"action":a}
        if typ=="AUDIO":
            a=step["action"]
            if a=="MUTE":b.key(b.VK["MEDIA_MUTE"])
            elif a=="VOL_UP":b.key(b.VK["VOLUME_UP"])
            elif a=="VOL_DOWN":b.key(b.VK["VOLUME_DOWN"])
            else:self.engine.set_master_volume(step["volume"])
            return {"type":typ,"action":a}
        if typ=="MEDIA":
            amap={"PLAY_PAUSE":"MEDIA_PLAY_PAUSE","NEXT":"MEDIA_NEXT","PREV":"MEDIA_PREV","MUTE":"MEDIA_MUTE"};b.key(b.VK[amap[step["action"]]]);return {"type":typ,"action":step["action"]}
        if typ=="CONDITION":
            branch=step["then"] if self._condition(step["condition"],step["value"]) else step["else"];return {"type":typ,"condition":step["condition"],"results":[self._execute_step(x) for x in branch]}
        if typ=="PC_COMMAND":
            msg,data=self.engine.original_execute(step["action"],{});return {"type":typ,"action":step["action"],"message":msg,"data":data}
        raise RuntimeError("MACRO STEP UNSUPPORTED")
    def _condition(self,cond,value):
        v=(value or "").lower()
        if cond=="CONTEXT_EQUALS":return self.engine.context_status_pro().get("profile","").upper()==value.upper()
        if cond=="APP_RUNNING":return any(v in x.get("name","").lower() for x in self.engine.running_processes())
        if cond=="WINDOW_EXISTS":return any(v in x.get("title","").lower() for x in self.engine.base.list_windows(20))
        if cond=="AUDIO_PLAYING":return any(not x.get("muted") and int(x.get("volume") or 0)>0 for x in self.engine.base.audio_sessions().get("sessions",[]))
        return False
