package com.riptwosec.pcremotedeck;

import org.json.JSONObject;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public final class CommandRouter {
    public interface Listener { void sendToWatch(JSONObject json); void status(String s); void requestWifiScan(); void requestVoice(); }
    private final PcBridgeClient pc;
    private final Listener listener;
    private final Set<String> pcWhitelist = new HashSet<>(Arrays.asList(
        "PC_LOCK","GET_PC_STATUS","MEDIA_PLAY_PAUSE","MEDIA_MUTE","MEDIA_NEXT","MEDIA_PREV","VOLUME_UP","VOLUME_DOWN",
        "SCREENSHOT","SHOW_DESKTOP","ALT_TAB","CTRL_C","CTRL_V","KEY_UP","KEY_DOWN","KEY_LEFT","KEY_RIGHT",
        "MOUSE_LEFT","MOUSE_RIGHT","SCROLL_UP","SCROLL_DOWN","APP_CHROME","APP_VSCODE","APP_SPOTIFY","APP_DISCORD","APP_STEAM","APP_FILES","APP_CMD",
        "BATTLE_STATION","DEEP_FOCUS"
    ));
    public CommandRouter(PcBridgeClient pc, Listener listener){this.pc=pc;this.listener=listener;}

    public void route(JSONObject envelope){
        final String id=envelope.optString("id",""); final String action=envelope.optString("action",""); JSONObject payload=envelope.optJSONObject("payload"); if(payload==null)payload=new JSONObject();
        if(action.length()==0){result(id,action,false,"MISSING ACTION",null);return;}
        if("WIFI_SCAN".equals(action)||"WIFI_BEST".equals(action)||"WIFI_FREE".equals(action)||"WIFI_STATUS".equals(action)){listener.requestWifiScan();return;}
        if("VOICE_PTT".equals(action)){listener.requestVoice();return;}
        if("WATCH_LOCATION_RESULT".equals(action)){result(id,action,true,"PHONE RECEIVED WATCH LOCATION",payload);return;}
        if(pcWhitelist.contains(action)){
            final JSONObject fp=payload;
            pc.command(action,fp,new PcBridgeClient.Callback(){@Override public void onResult(boolean ok,String msg,JSONObject body){result(id,action,ok,msg,body);}});return;
        }
        // Provider-backed features remain explicit instead of fabricating data.
        result(id,action,false,"PROVIDER NOT CONFIGURED ON PHONE",null);
    }

    private void result(String id,String action,boolean ok,String message,JSONObject data){
        try{JSONObject r=new JSONObject();r.put("v",1);r.put("type","result");r.put("id",id);r.put("action",action);r.put("ok",ok);r.put("message",message);if(data!=null)r.put("data",data);listener.sendToWatch(r);}catch(Exception ignored){}
    }
}
