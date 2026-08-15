package com.riptwosec.pcremotedeck;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends Activity implements WearBridge.Listener, WifiReconManager.Listener, CommandRouter.Listener {
    private static final int REQ_WIFI=4401, REQ_VOICE=4402;
    private TextView log;
    private EditText host, token;
    private WearBridge wear;
    private WifiReconManager wifi;
    private PcBridgeClient pc;
    private CommandRouter router;
    private JSONObject lastWifi;

    @Override protected void onCreate(Bundle b){super.onCreate(b);buildUi();pc=new PcBridgeClient();wear=new WearBridge(this,this);wifi=new WifiReconManager(this,this);router=new CommandRouter(pc,this);}
    @Override protected void onDestroy(){if(wear!=null)wear.unregister();if(wifi!=null)wifi.stop();super.onDestroy();}

    private void buildUi(){
        ScrollView sc=new ScrollView(this);LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(28,28,28,28);root.setBackgroundColor(Color.rgb(2,7,13));sc.addView(root);
        TextView title=txt("PC REMOTE DECK\nFIT 4 PRO COMPANION",22,Color.CYAN);root.addView(title);
        host=input("PC IP (example 192.168.1.10)");host.setText("192.168.1.10");root.addView(host);
        token=input("PC Agent token");token.setText("CHANGE_ME");root.addView(token);
        root.addView(btn("SAVE PC LINK",v->{pc.configure(host.getText().toString().trim(),8765,token.getText().toString());status("PC LINK SAVED");}));
        root.addView(btn("1. AUTHORIZE WEAR ENGINE",v->wear.requestAuthorization()));
        root.addView(btn("2. FIND / REGISTER WATCH",v->wear.discoverConnectedWatch()));
        root.addView(btn("3. GRANT WI-FI / LOCATION",v->requestWifiPermissions()));
        root.addView(btn("4. SCAN WI-FI + SYNC WATCH",v->requestWifiScan()));
        root.addView(btn("5. SEND STATUS SNAPSHOT",v->sendSnapshot()));
        log=txt("READY",13,Color.LTGRAY);log.setPadding(0,24,0,80);root.addView(log);setContentView(sc);
    }
    private EditText input(String hint){EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.GRAY);e.setTextColor(Color.WHITE);e.setSingleLine(true);return e;}
    private Button btn(String t,View.OnClickListener l){Button b=new Button(this);b.setText(t);b.setOnClickListener(l);return b;}
    private TextView txt(String s,int sp,int c){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setTextColor(c);return t;}

    private void requestWifiPermissions(){ArrayList<String> p=new ArrayList<>();if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED)p.add(Manifest.permission.ACCESS_FINE_LOCATION);if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.NEARBY_WIFI_DEVICES)!=PackageManager.PERMISSION_GRANTED)p.add(Manifest.permission.NEARBY_WIFI_DEVICES);if(p.isEmpty())status("WI-FI PERMISSIONS READY");else requestPermissions(p.toArray(new String[0]),REQ_WIFI);}
    @Override public void onRequestPermissionsResult(int req,String[] ps,int[] gs){super.onRequestPermissionsResult(req,ps,gs);if(req==REQ_WIFI)status(wifi.hasScanPermission()?"WI-FI PERMISSIONS READY":"WI-FI PERMISSION DENIED");}

    @Override public void onStatus(final String s){runOnUiThread(()->status(s));}
    @Override public void onMessage(String json){try{router.route(new JSONObject(json));}catch(Exception e){status("WATCH JSON ERROR: "+e.getMessage());}}
    @Override public void onRecon(JSONObject snapshot){lastWifi=snapshot;sendSnapshot();status(snapshot.optString("summary","WI-FI READY"));}
    @Override public void sendToWatch(JSONObject json){wear.sendJson(json.toString());}
    @Override public void status(String s){if(log!=null)log.setText(s+"\n\n"+log.getText());}
    @Override public void requestWifiScan(){runOnUiThread(()->{if(!wifi.hasScanPermission()){requestWifiPermissions();status("GRANT PERMISSION THEN SCAN AGAIN");}else wifi.start();});}
    @Override public void requestVoice(){runOnUiThread(()->{try{Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,Locale.getDefault());i.putExtra(RecognizerIntent.EXTRA_PROMPT,"PC Remote Deck command");startActivityForResult(i,REQ_VOICE);}catch(Exception e){status("VOICE RECOGNITION UNAVAILABLE");}});}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==REQ_VOICE&&result==RESULT_OK&&data!=null){ArrayList<String> r=data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);String speech=r!=null&&!r.isEmpty()?r.get(0):"";handleVoice(speech);}}

    private void handleVoice(String speech){String s=speech.toLowerCase(Locale.ROOT);String action=null;if(s.contains("battle"))action="BATTLE_STATION";else if(s.contains("focus"))action="DEEP_FOCUS";else if(s.contains("lock"))action="PC_LOCK";else if(s.contains("mute"))action="MEDIA_MUTE";else if(s.contains("chrome"))action="APP_CHROME";else if(s.contains("play")||s.contains("pause"))action="MEDIA_PLAY_PAUSE";try{JSONObject r=new JSONObject();r.put("type","result");r.put("ok",action!=null);r.put("action","VOICE_PTT");r.put("message",action==null?"VOICE INTENT UNKNOWN":"VOICE: "+action);r.put("data",speech);wear.sendJson(r.toString());if(action!=null){JSONObject e=new JSONObject();e.put("id","voice-"+System.currentTimeMillis());e.put("action",action);e.put("payload",new JSONObject());router.route(e);}}catch(Exception ignored){}}

    private void sendSnapshot(){
        try{
            JSONObject snap=new JSONObject();
            snap.put("type","snapshot");
            snap.put("ts",System.currentTimeMillis());
            JSONObject pcj=new JSONObject();
            pcj.put("state","CONFIGURED");
            snap.put("pc",pcj);

            JSONObject compact=new JSONObject();
            if(lastWifi!=null){
                compact.put("summary",lastWifi.optString("summary","WI-FI READY"));
                compact.put("scanState",lastWifi.optString("scanState","UNKNOWN"));
                compact.put("timestamp",lastWifi.optLong("timestamp",System.currentTimeMillis()));
                compact.put("nearby",lastWifi.optInt("nearby",0));
                compact.put("freeVerified",lastWifi.optInt("freeVerified",0));
                compact.put("open",lastWifi.optInt("open",0));
                compact.put("secured",lastWifi.optInt("secured",0));
                compact.put("loginRequired",lastWifi.optInt("loginRequired",0));
                JSONObject best=lastWifi.optJSONObject("best");
                if(best!=null){
                    JSONObject b=new JSONObject();
                    b.put("ssid",best.optString("ssid","UNKNOWN"));
                    b.put("status",best.optString("status","UNKNOWN"));
                    b.put("signalDbm",best.optInt("signalDbm",-127));
                    b.put("band",best.optString("band",""));
                    b.put("security",best.optString("security","UNKNOWN"));
                    b.put("score",best.optInt("score",0));
                    compact.put("best",b);
                }
            }else{
                compact.put("summary","NO SCAN");
                compact.put("scanState","UNKNOWN");
            }
            snap.put("wifi",compact);
            wear.sendJson(snap.toString());
        }catch(Exception e){status("SNAPSHOT ERROR: "+e.getMessage());}
    }
}
