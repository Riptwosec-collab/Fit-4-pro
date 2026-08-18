package com.riptwosec.pcremotedeck;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class WifiReconManager {
    public interface Listener { void onRecon(JSONObject snapshot); void onStatus(String status); }
    private final Context context;
    private final WifiManager wifi;
    private final ConnectivityManager connectivity;
    private final Listener listener;
    private final Map<String,Integer> previousRssi=new HashMap<>();
    private boolean registered;

    public WifiReconManager(Context c, Listener listener) {
        context=c.getApplicationContext();wifi=(WifiManager)context.getSystemService(Context.WIFI_SERVICE);connectivity=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);this.listener=listener;
    }

    public boolean hasScanPermission(){boolean loc=context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED;boolean nearby=Build.VERSION.SDK_INT<33||context.checkSelfPermission(Manifest.permission.NEARBY_WIFI_DEVICES)==PackageManager.PERMISSION_GRANTED;return loc&&nearby;}
    public void start(){if(!hasScanPermission()){status("WI-FI PERMISSION REQUIRED");return;}if(wifi==null||!wifi.isWifiEnabled()){status("WI-FI DISABLED");return;}if(!registered){IntentFilter f=new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION);if(Build.VERSION.SDK_INT>=33)context.registerReceiver(receiver,f,Context.RECEIVER_NOT_EXPORTED);else context.registerReceiver(receiver,f);registered=true;}boolean ok=wifi.startScan();if(!ok){status("SCAN LIMITED — USING RECENT RESULTS");publish(false);}else status("SCANNING");}
    public void stop(){if(registered){try{context.unregisterReceiver(receiver);}catch(Exception ignored){}registered=false;}}

    private final BroadcastReceiver receiver=new BroadcastReceiver(){@Override public void onReceive(Context c,Intent i){publish(i.getBooleanExtra(WifiManager.EXTRA_RESULTS_UPDATED,false));}};

    private void publish(boolean fresh){
        try{
            List<ScanResult> raw=wifi.getScanResults();Map<String,ScanResult> strongest=new HashMap<>();
            for(ScanResult r:raw){String ssid=ssidOf(r);if(ssid.length()==0)ssid="<hidden>";ScanResult old=strongest.get(ssid);if(old==null||r.level>old.level)strongest.put(ssid,r);}
            List<ScanResult> list=new ArrayList<>(strongest.values());Collections.sort(list,new Comparator<ScanResult>(){@Override public int compare(ScanResult a,ScanResult b){return Integer.compare(b.level,a.level);}});
            String connectedSsid=currentSsid();CurrentValidation cv=currentValidation();JSONArray networks=new JSONArray();int open=0,secured=0,login=0,verified=0;int limit=Math.min(12,list.size());
            for(int n=0;n<limit;n++){
                ScanResult r=list.get(n);String ssid=ssidOf(r);if(ssid.length()==0)ssid="<hidden>";String security=securityOf(r);boolean isOpen="OPEN".equals(security);if(isOpen)open++;else secured++;
                String state=isOpen?"OPEN":"SECURED";String internet="NOT TESTED";
                if(sameSsid(ssid,connectedSsid)){if(cv.captive){state="LOGIN REQUIRED";internet="CAPTIVE PORTAL";login++;}else if(cv.validated){state="FREE VERIFIED";internet="AVAILABLE";verified++;}else{state="NO INTERNET";internet="NOT VALIDATED";}}
                Integer prev=previousRssi.get(ssid);String trend=prev==null?"NEW":r.level>=prev+4?"RISING":r.level<=prev-4?"FALLING":"STABLE";previousRssi.put(ssid,r.level);
                JSONObject j=new JSONObject();j.put("ssid",ssid);j.put("signalDbm",r.level);j.put("signalLevel",signalLabel(r.level));j.put("trend",trend);j.put("band",bandOf(r.frequency));j.put("frequency",r.frequency);j.put("security",security);j.put("status",state);j.put("internet",internet);j.put("score",score(r.level,security,state));j.put("live",fresh);networks.put(j);
            }
            JSONObject out=new JSONObject();out.put("timestamp",System.currentTimeMillis());out.put("scanState",fresh?"READY":"CACHED");out.put("summary",list.size()+" nearby • "+verified+" verified • "+open+" open • "+secured+" secured");out.put("nearby",list.size());out.put("freeVerified",verified);out.put("open",open);out.put("secured",secured);out.put("loginRequired",login);out.put("networks",networks);
            JSONObject best=null;for(int i=0;i<networks.length();i++){JSONObject candidate=networks.optJSONObject(i);if(candidate!=null&&(best==null||candidate.optInt("score",0)>best.optInt("score",0)))best=candidate;}if(best!=null)out.put("best",best);if(listener!=null)listener.onRecon(out);
        }catch(Exception e){status("WI-FI ERROR: "+e.getMessage());}
    }

    private int score(int rssi,String security,String state){int signal=rssi>=-50?95:rssi>=-60?82:rssi>=-70?68:rssi>=-80?48:25;int sec="WPA3".equals(security)?95:"WPA2/WPA3".equals(security)?90:"WPA2".equals(security)?82:"ENTERPRISE".equals(security)?88:"OWE".equals(security)?75:28;int net="FREE VERIFIED".equals(state)?100:"LOGIN REQUIRED".equals(state)?55:"NO INTERNET".equals(state)?0:50;return Math.max(0,Math.min(100,(signal*45+sec*30+net*25)/100));}
    private String ssidOf(ScanResult r){if(Build.VERSION.SDK_INT>=33&&r.getWifiSsid()!=null)return r.getWifiSsid().toString().replace("\"","");return r.SSID==null?"":r.SSID;}
    private String securityOf(ScanResult r){String c=r.capabilities==null?"":r.capabilities.toUpperCase();if(c.contains("WPA3")||c.contains("SAE")){if(c.contains("WPA2")||c.contains("PSK"))return "WPA2/WPA3";return "WPA3";}if(c.contains("EAP"))return "ENTERPRISE";if(c.contains("OWE"))return "OWE";if(c.contains("WPA2")||c.contains("RSN")||c.contains("PSK"))return "WPA2";if(c.contains("WEP"))return "WEP";return "OPEN";}
    private String bandOf(int f){if(f>=5925)return "6 GHz";if(f>=4900)return "5 GHz";return "2.4 GHz";}
    private String signalLabel(int r){return r>=-50?"EXCELLENT":r>=-60?"GOOD":r>=-70?"FAIR":"WEAK";}
    private String currentSsid(){try{WifiInfo info=wifi.getConnectionInfo();if(info==null)return "";String s=info.getSSID();return s==null?"":s.replace("\"","");}catch(Exception e){return "";}}
    private boolean sameSsid(String a,String b){return a!=null&&b!=null&&a.equals(b)&&a.length()>0;}
    private CurrentValidation currentValidation(){CurrentValidation v=new CurrentValidation();try{Network n=connectivity.getActiveNetwork();NetworkCapabilities c=connectivity.getNetworkCapabilities(n);if(c!=null){v.validated=c.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);v.captive=c.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL);}}catch(Exception ignored){}return v;}
    private static final class CurrentValidation{boolean validated;boolean captive;}
    private void status(String s){if(listener!=null)listener.onStatus(s);}
}
