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
import java.util.Iterator;
import java.util.Locale;

/** PC Remote Deck V8 Pro companion. PC-control scope only. */
public class MainActivity extends Activity implements WearBridge.Listener, WifiReconManager.Listener, CommandRouter.Listener {
    private static final int REQ_WIFI=4401,REQ_VOICE=4402;
    private static final int DISCOVERY_PORT=8766;
    private static final String DISCOVERY_MESSAGE="PC_REMOTE_DECK_DISCOVER_V6";
    private static final String PREFS="prd_v6"; // migration-safe existing key
    private final Handler handler=new Handler(Looper.getMainLooper());
    private TextView log,syncState;
    private EditText host,token,macroName,macroSteps,aliasPhrase,aliasAction;
    private WearBridge wear; private WifiReconManager wifi; private PcBridgeClient pc; private CommandRouter router; private VoiceCommandEngine voice;
    private SharedPreferences prefs; private int pcPort=8765; private boolean autoSync=true;
    private JSONObject lastWifi,lastDashboard,lastSentPc; private String lastSentWifiSignature=""; private String lastContext="DESKTOP";
    private final Runnable syncLoop=new Runnable(){@Override public void run(){if(autoSync)refreshDashboard(false);handler.postDelayed(this,5000);}};

    @Override protected void onCreate(Bundle b){super.onCreate(b);prefs=getSharedPreferences(PREFS,MODE_PRIVATE);buildUi();pc=new PcBridgeClient();wear=new WearBridge(this,this);wifi=new WifiReconManager(this,this);router=new CommandRouter(pc,this);voice=new VoiceCommandEngine(prefs);restorePcLink();handlePairIntent(getIntent());handler.postDelayed(syncLoop,2200);}
    @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);handlePairIntent(i);}
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);if(wear!=null)wear.unregister();if(wifi!=null)wifi.stop();super.onDestroy();}

    private void buildUi(){
        ScrollView sc=new ScrollView(this);LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(28,28,28,28);root.setBackgroundColor(Color.rgb(2,7,13));sc.addView(root);
        root.addView(txt("PC REMOTE DECK V8 PRO\nFIT 4 PRO COMPANION",22,Color.CYAN));root.addView(txt("PC CONTROL • CONTEXT • AUTOMATION • NETWORK • SECURITY",11,Color.LTGRAY));
        syncState=txt("AUTO SYNC: ON • 5 SEC",12,Color.GREEN);root.addView(syncState);
        host=input("PC IP (example 192.168.1.10)");token=input("PC Agent token / scan pairing QR");root.addView(host);root.addView(token);
        root.addView(btn("SAVE PC LINK",v->savePcLink()));root.addView(btn("AUTO FIND PC ON LAN",v->discoverPcLan()));
        root.addView(btn("1. AUTHORIZE WEAR ENGINE",v->wear.requestAuthorization()));root.addView(btn("2. FIND / REGISTER WATCH",v->wear.discoverConnectedWatch()));
        root.addView(btn("3. GRANT WI-FI / LOCATION",v->requestWifiPermissions()));root.addView(btn("4. WI-FI RECON PRO 2.0 SCAN",v->requestWifiScan()));root.addView(btn("5. REFRESH PC CONTROL HUB",v->refreshDashboard(true)));
        root.addView(btn("TRUST CENTER 2.0",v->forwardPcResult("GET_TRUST_PRO",new JSONObject())));root.addView(btn("PC REMOTE SETTINGS",v->forwardPcResult("GET_PRO_SETTINGS",new JSONObject())));
        root.addView(btn("AUTO SYNC ON/OFF",v->{autoSync=!autoSync;syncState.setText("AUTO SYNC: "+(autoSync?"ON":"OFF")+" • 5 SEC");status("AUTO SYNC "+(autoSync?"ON":"OFF"));}));
        TextView mt=txt("MACRO DECK 2.0",16,Color.CYAN);mt.setPadding(0,24,0,4);root.addView(mt);macroName=input("Macro name");macroSteps=input("JSON steps OR legacy comma actions");root.addView(macroName);root.addView(macroSteps);root.addView(btn("SAVE LEGACY SAFE MACRO",v->saveLegacyMacro()));root.addView(btn("SAVE PRO MACRO V2",v->saveMacroV2()));root.addView(btn("REFRESH MACROS V2",v->forwardPcResult("GET_MACROS_V2",new JSONObject())));
        TextView vt=txt("VOICE COMMAND PRO 2.0",16,Color.CYAN);vt.setPadding(0,24,0,4);root.addView(vt);aliasPhrase=input("Alias phrase");aliasAction=input("Whitelisted action, e.g. APP_VSCODE");root.addView(aliasPhrase);root.addView(aliasAction);root.addView(btn("SAVE VOICE ALIAS",v->saveVoiceAlias()));root.addView(btn("TEST PUSH TO TALK",v->requestVoice()));
        root.addView(btn("REVOKE PC LINK",v->confirmRevokePcLink("phone-ui-"+System.currentTimeMillis())));log=txt("READY",13,Color.LTGRAY);log.setPadding(0,24,0,80);root.addView(log);setContentView(sc);
    }
    private EditText input(String h){EditText e=new EditText(this);e.setHint(h);e.setHintTextColor(Color.GRAY);e.setTextColor(Color.WHITE);e.setSingleLine(true);return e;}
    private Button btn(String t,View.OnClickListener l){Button b=new Button(this);b.setText(t);b.setOnClickListener(l);return b;}
    private TextView txt(String s,int sp,int c){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setTextColor(c);return t;}

    private void restorePcLink(){String h=prefs.getString("host","192.168.1.10"),t=prefs.getString("token","CHANGE_ME");pcPort=prefs.getInt("port",8765);host.setText(h);token.setText(t);pc.configure(h,pcPort,t);if(pc.isConfigured())status("PC LINK RESTORED");}
    private void savePcLink(){String h=host.getText().toString().trim(),t=token.getText().toString().trim();pc.configure(h,pcPort,t);prefs.edit().putString("host",h).putString("token",t).putInt("port",pcPort).apply();status("PC LINK SAVED "+h+":"+pcPort);refreshDashboard(true);}
    @Override public void revokePcLink(){prefs.edit().remove("host").remove("token").remove("port").apply();host.setText("192.168.1.10");token.setText("CHANGE_ME");pcPort=8765;pc.configure("192.168.1.10",pcPort,"CHANGE_ME");lastDashboard=null;lastSentPc=null;status("PC LINK REVOKED LOCALLY");}

    private void handlePairIntent(Intent i){if(i==null)return;Uri u=i.getData();if(u==null||!"pcremotedeck".equalsIgnoreCase(u.getScheme())||!"pair".equalsIgnoreCase(u.getHost()))return;String h=u.getQueryParameter("host"),t=u.getQueryParameter("token"),p=u.getQueryParameter("port");if(h==null||t==null||h.trim().isEmpty()||t.length()<16){status("INVALID PAIRING QR");return;}int port=8765;try{port=Integer.parseInt(p);}catch(Exception ignored){}if(port<1||port>65535)port=8765;pcPort=port;host.setText(h.trim());token.setText(t);pc.configure(h.trim(),pcPort,t);prefs.edit().putString("host",h.trim()).putString("token",t).putInt("port",pcPort).apply();status("QR PAIRING SAVED • "+h+":"+pcPort);refreshDashboard(true);}
    private void discoverPcLan(){status("SEARCHING LAN...");new Thread(()->{DatagramSocket s=null;try{s=new DatagramSocket();s.setBroadcast(true);s.setSoTimeout(2200);byte[] q=DISCOVERY_MESSAGE.getBytes(StandardCharsets.UTF_8);s.send(new DatagramPacket(q,q.length,InetAddress.getByName("255.255.255.255"),DISCOVERY_PORT));byte[] buf=new byte[2048];DatagramPacket in=new DatagramPacket(buf,buf.length);s.receive(in);JSONObject j=new JSONObject(new String(in.getData(),0,in.getLength(),StandardCharsets.UTF_8));if(!"PC_REMOTE_DECK_V6".equals(j.optString("service")))throw new Exception("UNKNOWN SERVICE");final String found=in.getAddress().getHostAddress();final int port=j.optInt("port",8765);runOnUiThread(()->{host.setText(found);pcPort=port;status("PC FOUND "+found+":"+port+" • TOKEN/QR REQUIRED");});}catch(Exception e){runOnUiThread(()->status("AUTO FIND: NO PC RESPONSE"));}finally{if(s!=null)s.close();}}).start();}

    private void requestWifiPermissions(){ArrayList<String> p=new ArrayList<>();if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED)p.add(Manifest.permission.ACCESS_FINE_LOCATION);if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.NEARBY_WIFI_DEVICES)!=PackageManager.PERMISSION_GRANTED)p.add(Manifest.permission.NEARBY_WIFI_DEVICES);if(p.isEmpty())status("WI-FI PERMISSIONS READY");else requestPermissions(p.toArray(new String[0]),REQ_WIFI);}
    @Override public void onRequestPermissionsResult(int req,String[] ps,int[] gs){super.onRequestPermissionsResult(req,ps,gs);if(req==REQ_WIFI)status(wifi.hasScanPermission()?"WI-FI PERMISSIONS READY":"WI-FI PERMISSION DENIED");}
    @Override public void onStatus(String s){runOnUiThread(()->status(s));}
    @Override public void status(String s){runOnUiThread(()->{if(log!=null)log.setText(s+"\n\n"+log.getText());});}
    @Override public void onMessage(String json){try{router.route(new JSONObject(json));}catch(Exception e){status("WATCH JSON ERROR: "+e.getMessage());}}
    @Override public void sendToWatch(JSONObject j){wear.sendJson(j.toString());}
    @Override public void requestWifiScan(){runOnUiThread(()->{if(!wifi.hasScanPermission()){requestWifiPermissions();status("GRANT PERMISSION THEN SCAN AGAIN");}else wifi.start();});}
    @Override public void onRecon(JSONObject snapshot){lastWifi=snapshot;sendSnapshot();status(snapshot.optString("summary","WI-FI READY"));}

    @Override public void requestVoice(){runOnUiThread(()->{try{Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,Locale.getDefault());i.putExtra(RecognizerIntent.EXTRA_PROMPT,"PC Remote Deck command / คำสั่ง PC");startActivityForResult(i,REQ_VOICE);}catch(Exception e){status("VOICE RECOGNITION UNAVAILABLE");}});}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==REQ_VOICE&&result==RESULT_OK&&data!=null){ArrayList<String> r=data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);handleVoice(r!=null&&!r.isEmpty()?r.get(0):"");}}
    private void handleVoice(String speech){VoiceCommandEngine.Result r=voice.resolve(speech,lastContext);if(r.action==null){sendVoiceFeedback(false,"VOICE INTENT UNKNOWN",speech);return;}sendVoiceFeedback(true,"UNDERSTOOD: "+r.action,speech);String id="voice-"+System.currentTimeMillis();if(r.risky)confirmRiskyPcAction(id,r.action,r.payload);else router.executeConfirmed(id,r.action,r.payload);}
    private void sendVoiceFeedback(boolean ok,String msg,String speech){try{JSONObject r=new JSONObject();r.put("v",2);r.put("type","result");r.put("action","VOICE_PTT");r.put("ok",ok);r.put("commandState",ok?"RUNNING":"FAILED");r.put("message",msg);r.put("data",speech);sendToWatch(r);}catch(Exception ignored){}}
    private void saveVoiceAlias(){try{voice.saveAlias(aliasPhrase.getText().toString(),aliasAction.getText().toString());status("VOICE ALIAS SAVED");}catch(Exception e){status("VOICE ALIAS: "+e.getMessage());}}

    @Override public void confirmRiskyPcAction(String id,String action,JSONObject payload){runOnUiThread(()->new AlertDialog.Builder(this).setTitle("Confirm "+action+"?").setMessage("This command changes PC/security state and requires confirmation.").setNegativeButton("Cancel",(d,w)->router.complete(id,action,false,"CANCELLED",null,"FAILED")).setPositiveButton("Confirm",(d,w)->{if("TRUST_ROTATE_TOKEN".equals(action))rotatePcTokenConfirmed(id);else router.executeConfirmed(id,action,payload);}).show());}
    @Override public void confirmRevokePcLink(String id){runOnUiThread(()->new AlertDialog.Builder(this).setTitle("REVOKE PC LINK?").setMessage("This phone will forget the current PC pairing.").setNegativeButton("Cancel",(d,w)->router.completeRevoke(id,false)).setPositiveButton("Revoke",(d,w)->router.completeRevoke(id,true)).show());}
    private void rotatePcTokenConfirmed(String id){try{JSONObject p=new JSONObject();p.put("confirmed",true);pc.command(id,"TRUST_ROTATE_TOKEN",p,(ok,msg,body)->{router.complete(id,"TRUST_ROTATE_TOKEN",ok,msg,body.optJSONObject("data"),ok?"DONE":"FAILED");runOnUiThread(()->{status(ok?"TOKEN ROTATED • RE-PAIR REQUIRED":"TOKEN ROTATION FAILED: "+msg);if(ok)revokePcLink();});});}catch(Exception e){router.complete(id,"TRUST_ROTATE_TOKEN",false,e.getMessage(),null,"FAILED");}}

    private void refreshDashboard(boolean verbose){if(!pc.isConfigured()){if(verbose)status("PC LINK NOT CONFIGURED");return;}pc.command("GET_DASHBOARD_PRO",new JSONObject(),(ok,msg,body)->{if(ok){JSONObject d=body.optJSONObject("data");if(d!=null){lastDashboard=d;JSONObject c=d.optJSONObject("contextPro");if(c!=null)lastContext=c.optString("profile",lastContext);}sendSnapshot();if(verbose)status("V8 DASHBOARD SYNC OK");}else pc.command("GET_DASHBOARD",new JSONObject(),(ok2,msg2,b2)->{if(ok2){JSONObject d=b2.optJSONObject("data");if(d!=null)lastDashboard=d;sendSnapshot();if(verbose)status("LEGACY DASHBOARD SYNC OK");}else if(verbose)status("PC DASHBOARD: "+msg2);});});}
    private void forwardPcResult(String action,JSONObject payload){if(!pc.isConfigured()){status("PC LINK NOT CONFIGURED");return;}String id="phone-ui-"+System.currentTimeMillis();pc.command(id,action,payload,(ok,msg,body)->{try{JSONObject r=new JSONObject();r.put("v",2);r.put("type","result");r.put("id",id);r.put("action",action);r.put("ok",ok);r.put("commandState",ok?"DONE":"FAILED");r.put("message",msg);JSONObject d=body.optJSONObject("data");if(d!=null)r.put("data",d);sendToWatch(r);status(msg);}catch(Exception ignored){}});}

    private void saveLegacyMacro(){String name=macroName.getText().toString().trim(),raw=macroSteps.getText().toString().trim();if(name.isEmpty()||raw.isEmpty()){status("MACRO NAME/STEPS REQUIRED");return;}String id=name.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_-]+","_");JSONArray steps=new JSONArray();for(String part:raw.split(",")){String a=part.trim().toUpperCase(Locale.ROOT);if(!a.isEmpty())steps.put(a);}try{JSONObject p=new JSONObject();p.put("id",id);p.put("name",name);p.put("steps",steps);forwardPcResult("MACRO_SAVE",p);}catch(Exception e){status("MACRO ERROR");}}
    private void saveMacroV2(){String name=macroName.getText().toString().trim(),raw=macroSteps.getText().toString().trim();if(name.isEmpty()||raw.isEmpty()){status("MACRO NAME/STEPS REQUIRED");return;}try{String id=name.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_-]+","_");JSONArray steps;if(raw.startsWith("["))steps=new JSONArray(raw);else{steps=new JSONArray();for(String part:raw.split(",")){String a=part.trim().toUpperCase(Locale.ROOT);if(!a.isEmpty()){JSONObject s=new JSONObject();s.put("type","PC_COMMAND");s.put("action",a);steps.put(s);}}}JSONObject p=new JSONObject();p.put("id",id);p.put("name",name);p.put("folder","General");p.put("icon","bolt");p.put("accent","cyan");p.put("steps",steps);forwardPcResult("MACRO_V2_SAVE",p);}catch(Exception e){status("MACRO V2 ERROR: "+e.getMessage());}}

    private JSONObject compactWifi(JSONObject src){JSONObject c=new JSONObject();try{if(src==null){c.put("summary","NO SCAN");c.put("scanState","UNKNOWN");return c;}String[] ks={"summary","scanState","timestamp","nearby","apCount","freeVerified","open","secured","loginRequired"};for(String k:ks)if(src.has(k))c.put(k,src.opt(k));for(String k:new String[]{"best","bandAnalysis","channelAnalysis","roaming","signalHistory"})if(src.has(k))c.put(k,src.optJSONObject(k));}catch(Exception ignored){}return c;}
    private JSONObject diffObject(JSONObject cur,JSONObject prev){if(prev==null)return cur;JSONObject out=new JSONObject();try{Iterator<String> it=cur.keys();while(it.hasNext()){String k=it.next();Object a=cur.opt(k),b=prev.opt(k);if(!String.valueOf(a).equals(String.valueOf(b)))out.put(k,a);}}catch(Exception ignored){}return out;}
    private void sendSnapshot(){try{JSONObject snap=new JSONObject();snap.put("type","snapshot");snap.put("ts",System.currentTimeMillis());if(lastDashboard!=null){JSONObject d=diffObject(lastDashboard,lastSentPc);if(lastSentPc==null||d.length()>0){snap.put("pc",lastSentPc==null?lastDashboard:d);lastSentPc=new JSONObject(lastDashboard.toString());}}else snap.put("pc",new JSONObject().put("state",pc.isConfigured()?"CONFIGURED":"NOT CONFIGURED"));JSONObject w=compactWifi(lastWifi);String sig=w.toString();if(!sig.equals(lastSentWifiSignature)){snap.put("wifi",w);lastSentWifiSignature=sig;}if(snap.has("pc")||snap.has("wifi"))wear.sendJson(snap.toString());}catch(Exception e){status("SNAPSHOT ERROR: "+e.getMessage());}}
}
