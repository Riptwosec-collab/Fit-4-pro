package com.riptwosec.pcremotedeck;

import org.json.JSONObject;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * Watch command router with explicit lifecycle and confirmation gates.
 *
 * Lifecycle:
 * SENDING -> RUNNING -> DONE / FAILED / TIMEOUT
 *
 * The router never treats "packet sent" as command success.
 */
public final class CommandRouter {
    public interface Listener {
        void sendToWatch(JSONObject json);
        void status(String s);
        void requestWifiScan();
        void requestVoice();
        void revokePcLink();
        void confirmRiskyPcAction(String id,String action,JSONObject payload);
        void confirmRevokePcLink(String id);
    }

    private final PcBridgeClient pc;
    private final Listener listener;

    private final Set<String> risky = new HashSet<>(Arrays.asList(
        "SYSTEM_SHUTDOWN","SYSTEM_RESTART","SYSTEM_SLEEP","WINDOW_CLOSE","TRUST_ROTATE_TOKEN"
    ));

    private final Set<String> pcWhitelist = new HashSet<>(Arrays.asList(
        "PC_LOCK","GET_PC_STATUS","GET_DASHBOARD","MEDIA_PLAY_PAUSE","MEDIA_MUTE","MEDIA_NEXT","MEDIA_PREV","VOLUME_UP","VOLUME_DOWN",
        "SCREENSHOT","SHOW_DESKTOP","ALT_TAB","CTRL_C","CTRL_V","KEY_UP","KEY_DOWN","KEY_LEFT","KEY_RIGHT",
        "MOUSE_LEFT","MOUSE_RIGHT","SCROLL_UP","SCROLL_DOWN","MOUSE_MOVE",
        "APP_CHROME","APP_VSCODE","APP_SPOTIFY","APP_DISCORD","APP_STEAM","APP_FILES","APP_CMD","GET_APPS","APP_LAUNCH",
        "BATTLE_STATION","DEEP_FOCUS","GET_WINDOWS","WINDOW_FOCUS","WINDOW_MIN","WINDOW_MAX","WINDOW_CLOSE",
        "GET_AUDIO","AUDIO_SESSION_SET","GET_NETWORK","NETWORK_PING","GET_CONTEXT","CONTEXT_SLOT_1","CONTEXT_SLOT_2","CONTEXT_SLOT_3","CONTEXT_SLOT_4",
        "GET_MACROS","MACRO_SAVE","MACRO_RUN","MACRO_DELETE","GET_NOTIFICATIONS","NOTIFICATIONS_CLEAR",
        "SYSTEM_SLEEP","SYSTEM_RESTART","SYSTEM_SHUTDOWN",
        "GET_DASHBOARD_PRO","GET_TELEMETRY_HISTORY","GET_TOP_PROCESSES","GET_CONTROL_HUB","GET_EVENTS",
        "GET_PRO_SETTINGS","SET_PRO_SETTINGS","GET_PERMISSIONS","SET_PERMISSION","GET_PROFILES","PROFILE_SET",
        "MOUSE_LEFT_DOWN","MOUSE_LEFT_UP","MOUSE_DOUBLE",
        "GET_WINDOWS_PRO","GET_MONITORS","WINDOW_SNAP_LEFT","WINDOW_SNAP_RIGHT","WINDOW_MOVE_MONITOR",
        "GET_AUDIO_PRO","AUDIO_MASTER_SET","AUDIO_SESSION_PRO_SET","AUDIO_OUTPUT_LIST",
        "GET_MACROS_V2","MACRO_V2_SAVE","MACRO_V2_RUN","MACRO_V2_CANCEL","MACRO_V2_DELETE",
        "GET_APPS_PRO","APP_SMART","APP_PIN","APP_UNPIN",
        "GET_CONTEXT_PRO","CONTEXT_SET_MODE","CONTEXT_SET_MANUAL",
        "GET_NOTIFICATIONS_PRO","NOTIFICATION_ACK","NOTIFICATION_SNOOZE","NOTIFICATION_CLEAR_PRO",
        "GET_TRUST_PRO","TRUST_ROTATE_TOKEN","TRUST_SET_ROTATION"
    ));

    public CommandRouter(PcBridgeClient pc, Listener listener){
        this.pc=pc;
        this.listener=listener;
    }

    public void route(JSONObject envelope){
        final String id=envelope.optString("id","watch-"+System.currentTimeMillis());
        final String action=envelope.optString("action","");
        JSONObject payload=envelope.optJSONObject("payload");
        if(payload==null)payload=new JSONObject();

        lifecycle(id,action,"SENDING","WATCH COMMAND RECEIVED");

        if(action.length()==0){
            complete(id,action,false,"MISSING ACTION",null,"FAILED");
            return;
        }
        if(action.startsWith("WIFI_")){
            lifecycle(id,action,"RUNNING","PHONE WI-FI PROVIDER");
            listener.requestWifiScan();
            complete(id,action,true,"WI-FI SCAN REQUESTED",null,"DONE");
            return;
        }
        if("VOICE_PTT".equals(action)){
            lifecycle(id,action,"RUNNING","VOICE RECOGNITION");
            listener.requestVoice();
            return;
        }
        if("PAIR_STATUS".equals(action)){
            lifecycle(id,action,"RUNNING","PAIR STATUS");
            try{
                JSONObject d=new JSONObject();
                d.put("phone","READY");
                d.put("pc",pc.isConfigured()?"CONFIGURED":"NOT CONFIGURED");
                complete(id,action,true,"TRUST STATUS",d,"DONE");
            }catch(Exception e){
                complete(id,action,false,e.getMessage(),null,"FAILED");
            }
            return;
        }
        if("REVOKE_PC_LINK".equals(action)){
            lifecycle(id,action,"RUNNING","REVOKE CONFIRMATION REQUIRED");
            listener.confirmRevokePcLink(id);
            return;
        }
        if("TRUST_ROTATE_TOKEN_REQUEST".equals(action)){
            lifecycle(id,"TRUST_ROTATE_TOKEN","RUNNING","TOKEN ROTATION CONFIRMATION REQUIRED");
            listener.confirmRiskyPcAction(id,"TRUST_ROTATE_TOKEN",payload);
            return;
        }
        if(action.startsWith("PHONE_") || action.startsWith("IOT_") || action.startsWith("OBS_")){
            complete(id,action,false,"PROVIDER NOT CONFIGURED ON PHONE",null,"FAILED");
            return;
        }
        if(pcWhitelist.contains(action)){
            if(risky.contains(action) && payload.optBoolean("confirmed",false)!=true){
                lifecycle(id,action,"RUNNING","CONFIRMATION REQUIRED");
                listener.confirmRiskyPcAction(id,action,payload);
                return;
            }
            executePc(id,action,payload);
            return;
        }
        complete(id,action,false,"COMMAND NOT WHITELISTED",null,"FAILED");
    }

    public void executeConfirmed(String id,String action,JSONObject payload){
        try{
            JSONObject p=payload==null?new JSONObject():new JSONObject(payload.toString());
            p.put("confirmed",true);
            executePc(id,action,p);
        }catch(Exception e){
            complete(id,action,false,e.getMessage(),null,"FAILED");
        }
    }

    public void completeRevoke(String id,boolean confirmed){
        if(!confirmed){
            complete(id,"REVOKE_PC_LINK",false,"REVOKE CANCELLED",null,"FAILED");
            return;
        }
        listener.revokePcLink();
        complete(id,"REVOKE_PC_LINK",true,"PC LINK REVOKED",null,"DONE");
    }

    private void executePc(final String id,final String action,final JSONObject payload){
        if(!pc.isConfigured()){
            complete(id,action,false,"PC LINK NOT CONFIGURED",null,"FAILED");
            return;
        }
        lifecycle(id,action,"RUNNING","PC EXECUTING");
        pc.command(id,action,payload,new PcBridgeClient.Callback(){
            @Override public void onResult(boolean ok,String msg,JSONObject body){
                JSONObject data=body.optJSONObject("data");
                String state=ok?"DONE":"FAILED";
                if(!ok && msg!=null && msg.toLowerCase().contains("timed out"))state="TIMEOUT";
                complete(id,action,ok,msg,data!=null?data:body.optJSONObject("payload"),state);
            }
        });
    }

    private void lifecycle(String id,String action,String state,String message){
        try{
            JSONObject r=new JSONObject();
            r.put("v",2);
            r.put("type","lifecycle");
            r.put("id",id);
            r.put("action",action);
            r.put("state",state);
            r.put("message",message);
            listener.sendToWatch(r);
        }catch(Exception ignored){}
    }

    public void complete(String id,String action,boolean ok,String message,JSONObject data,String commandState){
        try{
            JSONObject r=new JSONObject();
            r.put("v",2);
            r.put("type","result");
            r.put("id",id);
            r.put("action",action);
            r.put("ok",ok);
            r.put("commandState",commandState);
            r.put("message",message==null?(ok?"DONE":"FAILED"):message);
            if(data!=null)r.put("data",data);
            listener.sendToWatch(r);
        }catch(Exception ignored){}
    }
}
