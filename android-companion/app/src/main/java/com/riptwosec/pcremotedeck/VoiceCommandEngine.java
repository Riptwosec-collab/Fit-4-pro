package com.riptwosec.pcremotedeck;

import android.content.SharedPreferences;
import org.json.JSONObject;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/** Context-aware whitelist-only voice intent resolver. */
public final class VoiceCommandEngine {
    public static final class Result {
        public final String action; public final JSONObject payload; public final boolean risky; public final String normalized;
        Result(String action,JSONObject payload,boolean risky,String normalized){this.action=action;this.payload=payload;this.risky=risky;this.normalized=normalized;}
    }
    private static final String PREF_KEY="voice_aliases_json";
    private final SharedPreferences prefs;
    private final LinkedHashMap<String,String> aliases=new LinkedHashMap<>();
    public VoiceCommandEngine(SharedPreferences prefs){this.prefs=prefs;load();}
    private void load(){
        aliases.clear();
        addBuiltIn("open visual studio code","APP_VSCODE");addBuiltIn("visual studio code","APP_VSCODE");addBuiltIn("open vs code","APP_VSCODE");addBuiltIn("vs code","APP_VSCODE");addBuiltIn("วีเอสโค้ด","APP_VSCODE");
        addBuiltIn("open browser","APP_CHROME");addBuiltIn("open chrome","APP_CHROME");addBuiltIn("start chrome","APP_CHROME");addBuiltIn("browser","APP_CHROME");addBuiltIn("chrome","APP_CHROME");addBuiltIn("โครม","APP_CHROME");
        addBuiltIn("battle station","BATTLE_STATION");addBuiltIn("battle","BATTLE_STATION");addBuiltIn("gaming","BATTLE_STATION");addBuiltIn("เกม","BATTLE_STATION");
        addBuiltIn("deep focus","DEEP_FOCUS");addBuiltIn("focus","DEEP_FOCUS");addBuiltIn("โฟกัส","DEEP_FOCUS");addBuiltIn("ทำงาน","DEEP_FOCUS");
        addBuiltIn("lock pc","PC_LOCK");addBuiltIn("lock","PC_LOCK");addBuiltIn("ล็อก","PC_LOCK");
        addBuiltIn("volume up","VOLUME_UP");addBuiltIn("เพิ่มเสียง","VOLUME_UP");addBuiltIn("volume down","VOLUME_DOWN");addBuiltIn("ลดเสียง","VOLUME_DOWN");addBuiltIn("mute","MEDIA_MUTE");addBuiltIn("ปิดเสียง","MEDIA_MUTE");
        addBuiltIn("open steam","APP_STEAM");addBuiltIn("steam","APP_STEAM");addBuiltIn("สตีม","APP_STEAM");addBuiltIn("open discord","APP_DISCORD");addBuiltIn("discord","APP_DISCORD");addBuiltIn("ดิสคอร์ด","APP_DISCORD");
        addBuiltIn("screenshot","SCREENSHOT");addBuiltIn("แคปหน้าจอ","SCREENSHOT");addBuiltIn("จับภาพ","SCREENSHOT");addBuiltIn("show desktop","SHOW_DESKTOP");addBuiltIn("desktop","SHOW_DESKTOP");addBuiltIn("เดสก์ท็อป","SHOW_DESKTOP");
        addBuiltIn("previous track","MEDIA_PREV");addBuiltIn("เพลงก่อน","MEDIA_PREV");addBuiltIn("next track","MEDIA_NEXT");addBuiltIn("เพลงต่อไป","MEDIA_NEXT");addBuiltIn("play pause","MEDIA_PLAY_PAUSE");addBuiltIn("เล่นเพลง","MEDIA_PLAY_PAUSE");addBuiltIn("หยุดเพลง","MEDIA_PLAY_PAUSE");
        addBuiltIn("network status","GET_NETWORK");addBuiltIn("network","GET_NETWORK");addBuiltIn("เน็ตเวิร์ก","GET_NETWORK");addBuiltIn("เครือข่าย","GET_NETWORK");
        addBuiltIn("pc monitor","GET_DASHBOARD_PRO");addBuiltIn("monitor","GET_DASHBOARD_PRO");addBuiltIn("cpu","GET_DASHBOARD_PRO");addBuiltIn("สถานะคอม","GET_DASHBOARD_PRO");
        addBuiltIn("window center","GET_WINDOWS_PRO");addBuiltIn("windows","GET_WINDOWS_PRO");addBuiltIn("หน้าต่าง","GET_WINDOWS_PRO");addBuiltIn("audio mixer","GET_AUDIO_PRO");addBuiltIn("audio","GET_AUDIO_PRO");addBuiltIn("มิกเซอร์","GET_AUDIO_PRO");
        addBuiltIn("macro work","MACRO_V2_RUN:work");addBuiltIn("มาโครทำงาน","MACRO_V2_RUN:work");addBuiltIn("macro game","MACRO_V2_RUN:game");addBuiltIn("มาโครเกม","MACRO_V2_RUN:game");addBuiltIn("macro meeting","MACRO_V2_RUN:meeting");
        addBuiltIn("shutdown pc","SYSTEM_SHUTDOWN");addBuiltIn("shutdown","SYSTEM_SHUTDOWN");addBuiltIn("ปิดคอม","SYSTEM_SHUTDOWN");addBuiltIn("restart pc","SYSTEM_RESTART");addBuiltIn("restart","SYSTEM_RESTART");addBuiltIn("รีสตาร์ต","SYSTEM_RESTART");addBuiltIn("sleep pc","SYSTEM_SLEEP");addBuiltIn("sleep","SYSTEM_SLEEP");addBuiltIn("สลีป","SYSTEM_SLEEP");
        try{JSONObject saved=new JSONObject(prefs.getString(PREF_KEY,"{}"));java.util.Iterator<String> keys=saved.keys();while(keys.hasNext()){String k=keys.next();String v=saved.optString(k,"");if(k.trim().length()>0&&v.trim().length()>0)aliases.put(k.toLowerCase(Locale.ROOT),v.toUpperCase(Locale.ROOT));}}catch(Exception ignored){}
    }
    private void addBuiltIn(String phrase,String action){aliases.put(phrase.toLowerCase(Locale.ROOT),action);}
    public synchronized void saveAlias(String phrase,String action) throws Exception {
        String p=phrase==null?"":phrase.trim().toLowerCase(Locale.ROOT),a=action==null?"":action.trim().toUpperCase(Locale.ROOT);
        if(p.length()<2)throw new IllegalArgumentException("ALIAS TOO SHORT");if(!isAliasTargetAllowed(a))throw new IllegalArgumentException("ALIAS ACTION NOT ALLOWED");
        JSONObject saved;try{saved=new JSONObject(prefs.getString(PREF_KEY,"{}"));}catch(Exception e){saved=new JSONObject();}saved.put(p,a);prefs.edit().putString(PREF_KEY,saved.toString()).apply();load();
    }
    private boolean isAliasTargetAllowed(String action){
        if(action.startsWith("MACRO_V2_RUN:"))return true;
        switch(action){case "APP_CHROME":case "APP_VSCODE":case "APP_STEAM":case "APP_DISCORD":case "BATTLE_STATION":case "DEEP_FOCUS":case "PC_LOCK":case "MEDIA_MUTE":case "MEDIA_NEXT":case "MEDIA_PREV":case "MEDIA_PLAY_PAUSE":case "VOLUME_UP":case "VOLUME_DOWN":case "SCREENSHOT":case "SHOW_DESKTOP":case "GET_NETWORK":case "GET_DASHBOARD_PRO":case "GET_WINDOWS_PRO":case "GET_AUDIO_PRO":case "SYSTEM_SHUTDOWN":case "SYSTEM_RESTART":case "SYSTEM_SLEEP":return true;default:return false;}
    }
    public synchronized Result resolve(String speech,String context){
        String s=(speech==null?"":speech).trim().toLowerCase(Locale.ROOT),ctx=(context==null?"DESKTOP":context).trim().toUpperCase(Locale.ROOT);if(s.length()==0)return new Result(null,new JSONObject(),false,s);
        if("next".equals(s)||"ถัดไป".equals(s)){if("MEDIA".equals(ctx))return plain("MEDIA_NEXT",s);if("BROWSER".equals(ctx))return plain("CONTEXT_SLOT_2",s);if("PRESENTATION".equals(ctx))return plain("KEY_RIGHT",s);}
        if("previous".equals(s)||"ก่อนหน้า".equals(s)){if("MEDIA".equals(ctx))return plain("MEDIA_PREV",s);if("BROWSER".equals(ctx))return plain("CONTEXT_SLOT_1",s);if("PRESENTATION".equals(ctx))return plain("KEY_LEFT",s);}
        if("run".equals(s)&&"CODING".equals(ctx))return plain("CONTEXT_SLOT_3",s);if("save".equals(s)&&"CODING".equals(ctx))return plain("CONTEXT_SLOT_1",s);if("mute".equals(s)&&"MEETING".equals(ctx))return plain("MEDIA_MUTE",s);
        for(Map.Entry<String,String> e:aliases.entrySet()){if(s.contains(e.getKey())){String spec=e.getValue();if(spec.startsWith("MACRO_V2_RUN:")){JSONObject p=new JSONObject();try{p.put("id",spec.substring("MACRO_V2_RUN:".length()).toLowerCase(Locale.ROOT));}catch(Exception ignored){}return new Result("MACRO_V2_RUN",p,false,s);}return new Result(spec,new JSONObject(),isRisky(spec),s);}}
        return new Result(null,new JSONObject(),false,s);
    }
    private Result plain(String action,String normalized){return new Result(action,new JSONObject(),isRisky(action),normalized);}
    public static boolean isRisky(String action){return "SYSTEM_SHUTDOWN".equals(action)||"SYSTEM_RESTART".equals(action)||"SYSTEM_SLEEP".equals(action)||"WINDOW_CLOSE".equals(action)||"TRUST_ROTATE_TOKEN".equals(action);}
}
