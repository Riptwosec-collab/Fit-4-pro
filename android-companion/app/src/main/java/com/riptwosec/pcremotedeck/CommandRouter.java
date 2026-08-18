package com.riptwosec.pcremotedeck;

import org.json.JSONObject;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public final class CommandRouter {
    public interface Listener {
        void sendToWatch(JSONObject json);
        void status(String s);
        void requestWifiScan();
        void requestVoice();
        void revokePcLink();
    }
    private final PcBridgeClient pc;
    private final Listener listener;
    private final Set<String> pcWhitelist = new HashSet<>(Arrays.asList(
        "PC_LOCK","GET_PC_STATUS","GET_DASHBOARD","MEDIA_PLAY_PAUSE","MEDIA_MUTE","MEDIA_NEXT","MEDIA_PREV","VOLUME_UP","VOLUME_DOWN",
        "SCREENSHOT","SHOW_DESKTOP","ALT_TAB","CTRL_C","CTRL_V","KEY_UP","KEY_DOWN","KEY_LEFT","KEY_RIGHT",
        "MOUSE_LEFT","MOUSE_RIGHT","SCROLL_UP","SCROLL_DOWN","MOUSE_MOVE",
        "APP_CHROME","APP_VSCODE","APP_SPOTIFY","APP_DISCORD","APP_STEAM","APP_FILES","APP_CMD","GET_APPS","APP_LAUNCH",
        "BATTLE_STATION","DEEP_FOCUS","GET_WINDOWS","WINDOW_FOCUS","WINDOW_MIN","WINDOW_MAX","WINDOW_CLOSE",
        "GET_AUDIO","AUDIO_SESSION_SET","GET_NETWORK","NETWORK_PING","GET_CONTEXT","CONTEXT_SLOT_1","CONTEXT_SLOT_2","CONTEXT_SLOT_3","CONTEXT_SLOT_4",
        "GET_MACROS","MACRO_SAVE","MACRO_RUN","MACRO_DELETE","GET_NOTIFICATIONS","NOTIFICATIONS_CLEAR",
        "SYSTEM_SLEEP","SYSTEM_RESTART","SYSTEM_SHUTDOWN"
    ));
    public CommandRouter(PcBridgeClient pc, Listener listener){this.pc=pc;this.listener=listener;}

    public void route(JSONObject envelope){
        final String id=envelope.optString("id","");final String action=envelope.optString("action","");JSONObject payload=envelope.optJSONObject("payload");if(payload==null)payload=new JSONObject();
        if(action.length()==0){result(id,action,false,"MISSING ACTION",null);return;}
        if("WIFI_SCAN".equals(action)||"WIFI_BEST".equals(action)||"WIFI_FREE".equals(action)||"WIFI_STATUS".equals(action)){listener.requestWifiScan();return;}
        if("VOICE_PTT".equals(action)){listener.requestVoice();return;}
        if("PAIR_STATUS".equals(action)){try{JSONObject d=new JSONObject();d.put("phone","READY");d.put("pc",pc.isConfigured()?"CONFIGURED":"NOT CONFIGURED");result(id,action,true,"TRUST STATUS",d);}catch(Exception ignored){}return;}
        if("REVOKE_PC_LINK".equals(action)){listener.revokePcLink();result(id,action,true,"PC LINK REVOKED",null);return;}
        if(pcWhitelist.contains(action)){
            final JSONObject fp=payload;
            pc.command(action,fp,new PcBridgeClient.Callback(){@Override public void onResult(boolean ok,String msg,JSONObject body){JSONObject data=body.optJSONObject("data");result(id,action,ok,msg,data!=null?data:body.optJSONObject("payload"));}});return;
        }
        result(id,action,false,"PROVIDER NOT CONFIGURED ON PHONE",null);
    }

    private void result(String id,String action,boolean ok,String message,JSONObject data){
        try{JSONObject r=new JSONObject();r.put("v",1);r.put("type","result");r.put("id",id);r.put("action",action);r.put("ok",ok);r.put("message",message);if(data!=null)r.put("data",data);listener.sendToWatch(r);}catch(Exception ignored){}
    }
}
