package com.riptwosec.pcremotedeck;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognizerIntent;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends Activity implements WearBridge.Listener, WifiReconManager.Listener, CommandRouter.Listener {
    private static final int REQ_WIFI=4401, REQ_VOICE=4402;
    private static final int DISCOVERY_PORT=8766;
    private static final String DISCOVERY_MESSAGE="PC_REMOTE_DECK_DISCOVER_V6";
    private static final String PREFS="prd_v6";
    private final Handler handler=new Handler(Looper.getMainLooper());
    private TextView log, syncState;
    private EditText host, token, macroName, macroSteps;
    private WearBridge wear;
    private WifiReconManager wifi;
    private PcBridgeClient pc;
    private CommandRouter router;
    private JSONObject lastWifi,lastDashboard;
    private boolean autoSync=true;
    private SharedPreferences prefs;
    private int pcPort=8765;

    private final Runnable syncLoop=new Runnable(){@Override public void run(){if(autoSync)refreshDashboard(false);handler.postDelayed(this,12000);}};

    @Override protected void onCreate(Bundle b){
        super.onCreate(b);
        prefs=getSharedPreferences(PREFS,MODE_PRIVATE);
        buildUi();
        pc=new PcBridgeClient();wear=new WearBridge(this,this);wifi=new WifiReconManager(this,this);router=new CommandRouter(pc,this);
        restorePcLink();
        handlePairIntent(getIntent());
        handler.postDelayed(syncLoop,2500);
    }
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);handlePairIntent(intent);}
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);if(wear!=null)wear.unregister();if(wifi!=null)wifi.stop();super.onDestroy();}

    private void buildUi(){
        ScrollView sc=new ScrollView(this);LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(28,28,28,28);root.setBackgroundColor(Color.rgb(2,7,13));sc.addView(root);
        TextView title=txt("PC REMOTE DECK V6.1\nFIT 4 PRO COMPANION",22,Color.CYAN);root.addView(title);
        syncState=txt("AUTO SYNC: ON",12,Color.GREEN);root.addView(syncState);
        host=input("PC IP (example 192.168.1.10)");root.addView(host);
        token=input("PC Agent token / scan pairing QR");root.addView(token);
        root.addView(btn("SAVE PC LINK",v->savePcLink()));
        root.addView(btn("AUTO FIND PC ON LAN",v->discoverPcLan()));
        root.addView(btn("1. AUTHORIZE WEAR ENGINE",v->wear.requestAuthorization()));
        root.addView(btn("2. FIND / REGISTER WATCH",v->wear.discoverConnectedWatch()));
        root.addView(btn("3. GRANT WI-FI / LOCATION",v->requestWifiPermissions()));
        root.addView(btn("4. SCAN WI-FI + SYNC WATCH",v->requestWifiScan()));
        root.addView(btn("5. REFRESH PC DASHBOARD",v->refreshDashboard(true)));
        root.addView(btn("AUTO SYNC ON/OFF",v->{autoSync=!autoSync;syncState.setText("AUTO SYNC: "+(autoSync?"ON":"OFF"));status("AUTO SYNC "+(autoSync?"ON":"OFF"));}));

        TextView macroTitle=txt("MACRO BUILDER",16,Color.CYAN);macroTitle.setPadding(0,24,0,4);root.addView(macroTitle);
        macroName=input("Macro name (example: Work Start)");root.addView(macroName);
        macroSteps=input("Steps: APP_VSCODE,APP_CHROME,DEEP_FOCUS");root.addView(macroSteps);
        root.addView(btn("SAVE SAFE MACRO TO PC",v->saveMacro()));
        root.addView(btn("REFRESH MACROS TO WATCH",v->forwardPcResult("GET_MACROS",new JSONObject())));
        root.addView(btn("REVOKE PC LINK",v->revokePcLink()));
        log=txt("READY",13,Color.LTGRAY);log.setPadding(0,24,0,80);root.addView(log);setContentView(sc);
    }

    private EditText input(String hint){EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.GRAY);e.setTextColor(Color.WHITE);e.setSingleLine(true);return e;}
    private Button btn(String t,View.OnClickListener l){Button b=new Button(this);b.setText(t);b.setOnClickListener(l);return b;}
    private TextView txt(String s,int sp,int c){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setTextColor(c);return t;}

    private void restorePcLink(){
        String h=prefs.getString("host","192.168.1.10"),t=prefs.getString("token","CHANGE_ME");pcPort=prefs.getInt("port",8765);
        host.setText(h);token.setText(t);pc.configure(h,pcPort,t);if(pc.isConfigured())status("PC LINK RESTORED");
    }
    private void savePcLink(){
        String h=host.getText().toString().trim(),t=token.getText().toString().trim();pc.configure(h,pcPort,t);prefs.edit().putString("host",h).putString("token",t).putInt("port",pcPort).apply();status("PC LINK SAVED "+h+":"+pcPort);refreshDashboard(true);
    }
    @Override public void revokePcLink(){
        prefs.edit().remove("host").remove("token").remove("port").apply();host.setText("192.168.1.10");token.setText("CHANGE_ME");pcPort=8765;pc.configure("192.168.1.10",pcPort,"CHANGE_ME");lastDashboard=null;status("PC LINK REVOKED LOCALLY");
    }

    private void handlePairIntent(Intent intent){
        if(intent==null)return;Uri u=intent.getData();if(u==null||!"pcremotedeck".equalsIgnoreCase(u.getScheme())||!"pair".equalsIgnoreCase(u.getHost()))return;
        String h=u.getQueryParameter("host"),t=u.getQueryParameter("token"),p=u.getQueryParameter("port");
        if(h==null||t==null||h.trim().length()==0||t.length()<16){status("INVALID PAIRING QR");return;}
        int port=8765;try{port=Integer.parseInt(p);}catch(Exception ignored){}if(port<1||port>65535)port=8765;
        pcPort=port;host.setText(h.trim());token.setText(t);pc.configure(h.trim(),pcPort,t);prefs.edit().putString("host",h.trim()).putString("token",t).putInt("port",pcPort).apply();status("QR PAIRING SAVED • "+h+":"+pcPort);refreshDashboard(true);
    }

    private void discoverPcLan(){
        status("SEARCHING LAN...");
        new Thread(()->{
            DatagramSocket s=null;
            try{
                s=new DatagramSocket();s.setBroadcast(true);s.setSoTimeout(2200);
                byte[] q=DISCOVERY_MESSAGE.getBytes(StandardCharsets.UTF_8);DatagramPacket out=new DatagramPacket(q,q.length,InetAddress.getByName("255.255.255.255"),DISCOVERY_PORT);s.send(out);
                byte[] buf=new byte[2048];DatagramPacket in=new DatagramPacket(buf,buf.length);s.receive(in);
                String raw=new String(in.getData(),0,in.getLength(),StandardCharsets.UTF_8);JSONObject j=new JSONObject(raw);if(!"PC_REMOTE_DECK_V6".equals(j.optString("service")))throw new Exception("UNKNOWN SERVICE");
                final String found=in.getAddress().getHostAddress();final int port=j.optInt("port",8765);runOnUiThread(()->{host.setText(found);pcPort=port;status("PC FOUND "+found+":"+port+" • PAIR TOKEN/QR STILL REQUIRED");});
            }catch(Exception e){runOnUiThread(()->status("AUTO FIND: NO PC RESPONSE"));}finally{if(s!=null)s.close();}
        }).start();
    }

    private void requestWifiPermissions(){ArrayList<String> p=new ArrayList<>();if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED)p.add(Manifest.permission.ACCESS_FINE_LOCATION);if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.NEARBY_WIFI_DEVICES)!=PackageManager.PERMISSION_GRANTED)p.add(Manifest.permission.NEARBY_WIFI_DEVICES);if(p.isEmpty())status("WI-FI PERMISSIONS READY");else requestPermissions(p.toArray(new String[0]),REQ_WIFI);}
    @Override public void onRequestPermissionsResult(int req,String[] ps,int[] gs){super.onRequestPermissionsResult(req,ps,gs);if(req==REQ_WIFI)status(wifi.hasScanPermission()?"WI-FI PERMISSIONS READY":"WI-FI PERMISSION DENIED");}

    @Override public void onStatus(final String s){runOnUiThread(()->status(s));}
    @Override public void onMessage(String json){try{router.route(new JSONObject(json));}catch(Exception e){status("WATCH JSON ERROR: "+e.getMessage());}}
    @Override public void onRecon(JSONObject snapshot){lastWifi=snapshot;sendSnapshot();status(snapshot.optString("summary","WI-FI READY"));}
    @Override public void sendToWatch(JSONObject json){wear.sendJson(json.toString());}
    @Override public void status(String s){if(log!=null)log.setText(s+"\n\n"+log.getText());}
    @Override public void requestWifiScan(){runOnUiThread(()->{if(!wifi.hasScanPermission()){requestWifiPermissions();status("GRANT PERMISSION THEN SCAN AGAIN");}else wifi.start();});}
    @Override public void requestVoice(){runOnUiThread(()->{try{Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,Locale.getDefault());i.putExtra(RecognizerIntent.EXTRA_PROMPT,"PC Remote Deck command / คำสั่ง PC");startActivityForResult(i,REQ_VOICE);}catch(Exception e){status("VOICE RECOGNITION UNAVAILABLE");}});}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==REQ_VOICE&&result==RESULT_OK&&data!=null){ArrayList<String> r=data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);String speech=r!=null&&!r.isEmpty()?r.get(0):"";handleVoice(speech);}}

    private void handleVoice(String speech){
        String s=speech.toLowerCase(Locale.ROOT);String action=null;
        if(has(s,"battle","เกม","gaming"))action="BATTLE_STATION";else if(has(s,"focus","โฟกัส","ทำงาน"))action="DEEP_FOCUS";else if(has(s,"lock","ล็อก"))action="PC_LOCK";else if(has(s,"mute","ปิดเสียง"))action="MEDIA_MUTE";else if(has(s,"volume up","เพิ่มเสียง"))action="VOLUME_UP";else if(has(s,"volume down","ลดเสียง"))action="VOLUME_DOWN";else if(has(s,"chrome","โครม"))action="APP_CHROME";else if(has(s,"vs code","visual studio code","วีเอสโค้ด"))action="APP_VSCODE";else if(has(s,"steam","สตีม"))action="APP_STEAM";else if(has(s,"discord","ดิสคอร์ด"))action="APP_DISCORD";else if(has(s,"screenshot","แคปหน้าจอ","จับภาพ"))action="SCREENSHOT";else if(has(s,"desktop","เดสก์ท็อป"))action="SHOW_DESKTOP";else if(has(s,"next","เพลงต่อไป"))action="MEDIA_NEXT";else if(has(s,"previous","เพลงก่อน"))action="MEDIA_PREV";else if(has(s,"play","pause","เล่นเพลง","หยุดเพลง"))action="MEDIA_PLAY_PAUSE";else if(has(s,"network","เน็ตเวิร์ก","เครือข่าย"))action="GET_NETWORK";else if(has(s,"monitor","cpu","สถานะคอม"))action="GET_DASHBOARD";else if(has(s,"window","หน้าต่าง"))action="GET_WINDOWS";else if(has(s,"audio","มิกเซอร์"))action="GET_AUDIO";else if(has(s,"macro work","มาโครทำงาน")){runMacroVoice("work",speech);return;}else if(has(s,"macro game","มาโครเกม")){runMacroVoice("game",speech);return;}else if(has(s,"shutdown","ปิดคอม")){confirmRisk("SYSTEM_SHUTDOWN","Shutdown PC?",speech);return;}else if(has(s,"restart","รีสตาร์ต")){confirmRisk("SYSTEM_RESTART","Restart PC?",speech);return;}else if(has(s,"sleep","สลีป")){confirmRisk("SYSTEM_SLEEP","Sleep PC?",speech);return;}
        sendVoiceResult(action,speech,new JSONObject());
    }
    private boolean has(String s,String...terms){for(String t:terms)if(s.contains(t))return true;return false;}
    private void runMacroVoice(String id,String speech){try{JSONObject p=new JSONObject();p.put("id",id);sendVoiceResult("MACRO_RUN",speech,p);}catch(Exception ignored){}}
    private void confirmRisk(final String action,String title,String speech){new AlertDialog.Builder(this).setTitle(title).setMessage("Voice command: "+speech).setNegativeButton("Cancel",null).setPositiveButton("Confirm",(d,w)->{try{JSONObject p=new JSONObject();p.put("confirmed",true);sendVoiceResult(action,speech,p);}catch(Exception ignored){}}).show();}
    private void sendVoiceResult(String action,String speech,JSONObject payload){try{JSONObject r=new JSONObject();r.put("type","result");r.put("ok",action!=null);r.put("action","VOICE_PTT");r.put("message",action==null?"VOICE INTENT UNKNOWN":"VOICE: "+action);r.put("data",speech);wear.sendJson(r.toString());if(action!=null){JSONObject e=new JSONObject();e.put("id","voice-"+System.currentTimeMillis());e.put("action",action);e.put("payload",payload==null?new JSONObject():payload);router.route(e);}}catch(Exception ignored){}}

    private void refreshDashboard(boolean verbose){if(!pc.isConfigured()){if(verbose)status("PC LINK NOT CONFIGURED");return;}pc.command("GET_DASHBOARD",new JSONObject(),(ok,msg,body)->{if(ok){JSONObject d=body.optJSONObject("data");if(d!=null)lastDashboard=d;sendSnapshot();if(verbose)runOnUiThread(()->status("DASHBOARD SYNC OK"));}else if(verbose)runOnUiThread(()->status("PC DASHBOARD: "+msg));});}
    private void forwardPcResult(String action,JSONObject payload){if(!pc.isConfigured()){status("PC LINK NOT CONFIGURED");return;}pc.command(action,payload,(ok,msg,body)->{try{JSONObject r=new JSONObject();r.put("v",1);r.put("type","result");r.put("action",action);r.put("ok",ok);r.put("message",msg);JSONObject d=body.optJSONObject("data");if(d!=null)r.put("data",d);sendToWatch(r);runOnUiThread(()->status(msg));}catch(Exception ignored){}});}
    private void saveMacro(){String name=macroName.getText().toString().trim();String raw=macroSteps.getText().toString().trim();if(name.length()==0||raw.length()==0){status("MACRO NAME/STEPS REQUIRED");return;}String id=name.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_-]+","_");JSONArray steps=new JSONArray();for(String part:raw.split(",")){String a=part.trim().toUpperCase(Locale.ROOT);if(a.length()>0)steps.put(a);}try{JSONObject p=new JSONObject();p.put("id",id);p.put("name",name);p.put("steps",steps);forwardPcResult("MACRO_SAVE",p);}catch(Exception e){status("MACRO ERROR");}}

    private void sendSnapshot(){
        try{JSONObject snap=new JSONObject();snap.put("type","snapshot");snap.put("ts",System.currentTimeMillis());snap.put("pc",lastDashboard!=null?lastDashboard:new JSONObject().put("state",pc.isConfigured()?"CONFIGURED":"NOT CONFIGURED"));JSONObject compact=new JSONObject();if(lastWifi!=null){compact.put("summary",lastWifi.optString("summary","WI-FI READY"));compact.put("scanState",lastWifi.optString("scanState","UNKNOWN"));compact.put("timestamp",lastWifi.optLong("timestamp",System.currentTimeMillis()));compact.put("nearby",lastWifi.optInt("nearby",0));compact.put("freeVerified",lastWifi.optInt("freeVerified",0));compact.put("open",lastWifi.optInt("open",0));compact.put("secured",lastWifi.optInt("secured",0));compact.put("loginRequired",lastWifi.optInt("loginRequired",0));JSONObject best=lastWifi.optJSONObject("best");if(best!=null){JSONObject bb=new JSONObject();bb.put("ssid",best.optString("ssid","UNKNOWN"));bb.put("status",best.optString("status","UNKNOWN"));bb.put("signalDbm",best.optInt("signalDbm",-127));bb.put("band",best.optString("band",""));bb.put("security",best.optString("security","UNKNOWN"));bb.put("score",best.optInt("score",0));bb.put("trend",best.optString("trend","STABLE"));compact.put("best",bb);}}else{compact.put("summary","NO SCAN");compact.put("scanState","UNKNOWN");}snap.put("wifi",compact);wear.sendJson(snap.toString());}catch(Exception e){status("SNAPSHOT ERROR: "+e.getMessage());}
    }
}
