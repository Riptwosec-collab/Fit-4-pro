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

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Wi-Fi Recon Pro 2.0.
 *
 * PHONE SCANS — WATCH COMMANDS.
 * Adds 5-minute signal history, channel congestion, band counts, heuristic
 * security grade and same-SSID AP comparison. OPEN != FREE VERIFIED.
 * No cracking, deauth, packet capture or forced roaming.
 */
public final class WifiReconManager {
    public interface Listener { void onRecon(JSONObject snapshot); void onStatus(String status); }
    private static final long HISTORY_MS=5*60*1000L;
    private static final int HISTORY_LIMIT=80;
    private static final class Sample { long ts; int rssi; Sample(long ts,int rssi){this.ts=ts;this.rssi=rssi;} }
    private final Context context;
    private final WifiManager wifi;
    private final ConnectivityManager connectivity;
    private final Listener listener;
    private final Map<String,Integer> previousRssi=new HashMap<>();
    private final Map<String,Deque<Sample>> history=new HashMap<>();
    private boolean registered;

    public WifiReconManager(Context c, Listener listener) {
        context=c.getApplicationContext();
        wifi=(WifiManager)context.getSystemService(Context.WIFI_SERVICE);
        connectivity=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
        this.listener=listener;
    }
    public boolean hasScanPermission(){
        boolean loc=context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED;
        boolean nearby=Build.VERSION.SDK_INT<33 || context.checkSelfPermission(Manifest.permission.NEARBY_WIFI_DEVICES)==PackageManager.PERMISSION_GRANTED;
        return loc && nearby;
    }
    public void start(){
        if(!hasScanPermission()){status("WI-FI PERMISSION REQUIRED");return;}
        if(wifi==null || !wifi.isWifiEnabled()){status("WI-FI DISABLED");return;}
        if(!registered){IntentFilter f=new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION);if(Build.VERSION.SDK_INT>=33)context.registerReceiver(receiver,f,Context.RECEIVER_NOT_EXPORTED);else context.registerReceiver(receiver,f);registered=true;}
        boolean ok=wifi.startScan();if(!ok){status("SCAN LIMITED — USING RECENT RESULTS");publish(false);}else status("SCANNING");
    }
    public void stop(){if(registered){try{context.unregisterReceiver(receiver);}catch(Exception ignored){}registered=false;}}
    private final BroadcastReceiver receiver=new BroadcastReceiver(){@Override public void onReceive(Context c,Intent i){publish(i.getBooleanExtra(WifiManager.EXTRA_RESULTS_UPDATED,false));}};

    private void publish(boolean fresh){
        try{
            List<ScanResult> raw=wifi.getScanResults();long now=System.currentTimeMillis();
            List<ScanResult> all=new ArrayList<>(raw);Collections.sort(all,new Comparator<ScanResult>(){@Override public int compare(ScanResult a,ScanResult b){return Integer.compare(b.level,a.level);}});
            Map<String,ScanResult> strongest=new LinkedHashMap<>();
            for(ScanResult r:all){String ssid=ssidOf(r);if(ssid.length()==0)ssid="<hidden>";ScanResult old=strongest.get(ssid);if(old==null||r.level>old.level)strongest.put(ssid,r);recordHistory(historyKey(r),r.level,now);}
            List<ScanResult> list=new ArrayList<>(strongest.values());Collections.sort(list,new Comparator<ScanResult>(){@Override public int compare(ScanResult a,ScanResult b){return Integer.compare(b.level,a.level);}});
            String connectedSsid=currentSsid(),connectedBssid=currentBssid();CurrentValidation cv=currentValidation();JSONArray networks=new JSONArray();
            int open=0,secured=0,login=0,verified=0,count24=0,count5=0,count6=0;Map<Integer,Integer> channelCounts=new HashMap<>();
            for(ScanResult r:all){String band=bandOf(r.frequency);if("2.4 GHz".equals(band))count24++;else if("5 GHz".equals(band))count5++;else if("6 GHz".equals(band))count6++;int ch=channelOf(r.frequency);if(ch>0)channelCounts.put(ch,(channelCounts.containsKey(ch)?channelCounts.get(ch):0)+1);}
            int limit=Math.min(16,list.size());
            for(int n=0;n<limit;n++){
                ScanResult r=list.get(n);String ssid=ssidOf(r);if(ssid.length()==0)ssid="<hidden>";String security=securityOf(r);boolean isOpen="OPEN".equals(security);if(isOpen)open++;else secured++;
                String state=isOpen?"OPEN":"SECURED",internet="NOT TESTED";
                if(sameSsid(ssid,connectedSsid)){if(cv.captive){state="LOGIN REQUIRED";internet="CAPTIVE PORTAL";login++;}else if(cv.validated){state="FREE VERIFIED";internet="AVAILABLE";verified++;}else{state="NO INTERNET";internet="NOT VALIDATED";}}
                Integer prev=previousRssi.get(ssid);String trend=prev==null?"NEW":r.level>=prev+4?"RISING":r.level<=prev-4?"FALLING":"STABLE";previousRssi.put(ssid,r.level);
                JSONObject j=new JSONObject();j.put("ssid",ssid);j.put("bssid",safeBssid(r.BSSID));j.put("signalDbm",r.level);j.put("signalLevel",signalLabel(r.level));j.put("trend",trend);j.put("band",bandOf(r.frequency));j.put("frequency",r.frequency);j.put("channel",channelOf(r.frequency));j.put("security",security);j.put("securityGrade",securityGrade(security));j.put("status",state);j.put("internet",internet);j.put("score",score(r.level,security,state));j.put("live",fresh);j.put("history",historyStats(historyKey(r),now));networks.put(j);
            }
            JSONObject out=new JSONObject();out.put("timestamp",now);out.put("scanState",fresh?"READY":"CACHED");out.put("summary",list.size()+" SSIDs • "+all.size()+" APs • "+verified+" verified • "+open+" open • "+secured+" secured");out.put("nearby",list.size());out.put("apCount",all.size());out.put("freeVerified",verified);out.put("open",open);out.put("secured",secured);out.put("loginRequired",login);out.put("networks",networks);
            JSONObject bands=new JSONObject();bands.put("2.4GHz",count24);bands.put("5GHz",count5);bands.put("6GHz",count6);bands.put("6GHzAvailable",count6>0);out.put("bandAnalysis",bands);
            out.put("channelAnalysis",channelAnalysis(channelCounts));out.put("roaming",roamingComparison(all,connectedSsid,connectedBssid,now));
            JSONObject best=null;for(int i=0;i<networks.length();i++){JSONObject candidate=networks.optJSONObject(i);if(candidate!=null&&(best==null||candidate.optInt("score",0)>best.optInt("score",0)))best=candidate;}
            if(best!=null){out.put("best",best);out.put("signalHistory",best.optJSONObject("history"));}
            if(listener!=null)listener.onRecon(out);
        }catch(Exception e){status("WI-FI ERROR: "+e.getMessage());}
    }

    private String historyKey(ScanResult r){String b=safeBssid(r.BSSID);return b.length()>0?b:ssidOf(r)+"|"+r.frequency;}
    private void recordHistory(String key,int rssi,long now){Deque<Sample> q=history.get(key);if(q==null){q=new ArrayDeque<>();history.put(key,q);}q.addLast(new Sample(now,rssi));while(!q.isEmpty()&&(now-q.peekFirst().ts>HISTORY_MS||q.size()>HISTORY_LIMIT))q.removeFirst();}
    private JSONObject historyStats(String key,long now){JSONObject j=new JSONObject();try{Deque<Sample> q=history.get(key);if(q==null||q.isEmpty()){j.put("current",JSONObject.NULL);j.put("avg",JSONObject.NULL);j.put("best",JSONObject.NULL);j.put("points",new JSONArray());return j;}int sum=0,best=-127,current=-127;JSONArray pts=new JSONArray();for(Sample s:q){sum+=s.rssi;if(s.rssi>best)best=s.rssi;current=s.rssi;JSONObject p=new JSONObject();p.put("ts",s.ts);p.put("rssi",s.rssi);pts.put(p);}j.put("windowMinutes",5);j.put("current",current);j.put("avg",Math.round((float)sum/q.size()));j.put("best",best);j.put("points",pts);}catch(Exception ignored){}return j;}
    private JSONObject channelAnalysis(Map<Integer,Integer> counts){JSONObject out=new JSONObject();try{JSONArray items=new JSONArray();List<Integer> keys=new ArrayList<>(counts.keySet());Collections.sort(keys);for(Integer ch:keys){int count=counts.get(ch);JSONObject x=new JSONObject();x.put("channel",ch);x.put("networks",count);x.put("state",count<=1?"CLEAR":count<=3?"MEDIUM":"BUSY");items.put(x);}out.put("items",items);int[] common24={1,6,11};int recommended=1,bestCount=Integer.MAX_VALUE;for(int ch:common24){int c=counts.containsKey(ch)?counts.get(ch):0;if(c<bestCount){bestCount=c;recommended=ch;}}out.put("recommended",recommended);out.put("recommendationScope","2.4 GHz HEURISTIC");}catch(Exception ignored){}return out;}
    private JSONObject roamingComparison(List<ScanResult> all,String connectedSsid,String connectedBssid,long now){JSONObject out=new JSONObject();try{out.put("ssid",connectedSsid.length()==0?JSONObject.NULL:connectedSsid);out.put("currentBssid",connectedBssid.length()==0?JSONObject.NULL:connectedBssid);JSONArray aps=new JSONArray();ScanResult best=null,current=null;if(connectedSsid.length()>0){for(ScanResult r:all){String ssid=ssidOf(r);if(!sameSsid(ssid,connectedSsid))continue;if(best==null||r.level>best.level)best=r;if(connectedBssid.length()>0&&connectedBssid.equalsIgnoreCase(safeBssid(r.BSSID)))current=r;JSONObject x=new JSONObject();x.put("bssid",safeBssid(r.BSSID));x.put("signalDbm",r.level);x.put("band",bandOf(r.frequency));x.put("channel",channelOf(r.frequency));x.put("current",connectedBssid.length()>0&&connectedBssid.equalsIgnoreCase(safeBssid(r.BSSID)));aps.put(x);}}out.put("aps",aps);if(best!=null){out.put("bestBssid",safeBssid(best.BSSID));out.put("bestSignalDbm",best.level);}if(current!=null){out.put("currentSignalDbm",current.level);if(best!=null)out.put("signalDifferenceDb",best.level-current.level);}out.put("forceRoamingAvailable",false);out.put("note","Comparison only; OS roaming is not forced.");}catch(Exception ignored){}return out;}
    private int score(int rssi,String security,String state){int signal=rssi>=-50?95:rssi>=-60?82:rssi>=-70?68:rssi>=-80?48:25;int sec="WPA3".equals(security)?95:"WPA2/WPA3".equals(security)?90:"WPA2".equals(security)?82:"ENTERPRISE".equals(security)?88:"OWE".equals(security)?75:"WEP".equals(security)?12:28;int net="FREE VERIFIED".equals(state)?100:"LOGIN REQUIRED".equals(state)?55:"NO INTERNET".equals(state)?0:50;return Math.max(0,Math.min(100,(signal*45+sec*30+net*25)/100));}
    private String securityGrade(String security){if("WPA3".equals(security)||"ENTERPRISE".equals(security))return "A";if("WPA2/WPA3".equals(security)||"WPA2".equals(security)||"OWE".equals(security))return "B";if("OPEN".equals(security))return "C";return "D";}
    private String ssidOf(ScanResult r){if(Build.VERSION.SDK_INT>=33&&r.getWifiSsid()!=null)return r.getWifiSsid().toString().replace("\"","");return r.SSID==null?"":r.SSID;}
    private String safeBssid(String b){return b==null?"":b;}
    private String securityOf(ScanResult r){String c=r.capabilities==null?"":r.capabilities.toUpperCase();if(c.contains("WPA3")||c.contains("SAE")){if(c.contains("WPA2")||c.contains("PSK"))return "WPA2/WPA3";return "WPA3";}if(c.contains("EAP"))return "ENTERPRISE";if(c.contains("OWE"))return "OWE";if(c.contains("WPA2")||c.contains("RSN")||c.contains("PSK"))return "WPA2";if(c.contains("WEP"))return "WEP";return "OPEN";}
    private String bandOf(int f){if(f>=5925)return "6 GHz";if(f>=4900)return "5 GHz";return "2.4 GHz";}
    private int channelOf(int f){if(f>=2412&&f<=2472)return (f-2407)/5;if(f==2484)return 14;if(f>=5000&&f<5925)return (f-5000)/5;if(f>=5955&&f<=7115)return (f-5950)/5;return 0;}
    private String signalLabel(int r){return r>=-50?"EXCELLENT":r>=-60?"GOOD":r>=-70?"FAIR":"WEAK";}
    private String currentSsid(){try{WifiInfo info=wifi.getConnectionInfo();if(info==null)return "";String s=info.getSSID();return s==null?"":s.replace("\"","");}catch(Exception e){return "";}}
    private String currentBssid(){try{WifiInfo info=wifi.getConnectionInfo();if(info==null)return "";String s=info.getBSSID();return s==null?"":s;}catch(Exception e){return "";}}
    private boolean sameSsid(String a,String b){return a!=null&&b!=null&&a.equals(b)&&a.length()>0;}
    private CurrentValidation currentValidation(){CurrentValidation v=new CurrentValidation();try{Network n=connectivity.getActiveNetwork();NetworkCapabilities c=connectivity.getNetworkCapabilities(n);if(c!=null){v.validated=c.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);v.captive=c.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL);}}catch(Exception ignored){}return v;}
    private static final class CurrentValidation{boolean validated;boolean captive;}
    private void status(String s){if(listener!=null)listener.onStatus(s);}
}
