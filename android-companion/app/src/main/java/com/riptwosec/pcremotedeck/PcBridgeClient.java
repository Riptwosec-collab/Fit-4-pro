package com.riptwosec.pcremotedeck;

import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.util.UUID;

public final class PcBridgeClient {
    public interface Callback { void onResult(boolean ok, String message, JSONObject body); }
    private String baseUrl="http://192.168.1.10:8765";
    private String token="CHANGE_ME";
    public void configure(String host,int port,String token){this.baseUrl="http://"+host+":"+port;this.token=token;}
    public void command(final String action, final JSONObject payload, final Callback cb){
        new Thread(new Runnable(){@Override public void run(){
            HttpURLConnection c=null;
            try{
                URL u=new URL(baseUrl+"/command");c=(HttpURLConnection)u.openConnection();c.setConnectTimeout(2500);c.setReadTimeout(4000);c.setRequestMethod("POST");c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");c.setRequestProperty("Authorization","Bearer "+token);
                JSONObject req=new JSONObject();req.put("action",action);req.put("payload",payload==null?new JSONObject():payload);byte[] b=req.toString().getBytes(StandardCharsets.UTF_8);String ts=String.valueOf(System.currentTimeMillis()/1000L);String nonce=UUID.randomUUID().toString();String sig=hmacHex(token,ts+"\n"+nonce+"\n"+new String(b,StandardCharsets.UTF_8));c.setRequestProperty("X-PRD-Timestamp",ts);c.setRequestProperty("X-PRD-Nonce",nonce);c.setRequestProperty("X-PRD-Signature",sig);c.setFixedLengthStreamingMode(b.length);try(OutputStream o=c.getOutputStream()){o.write(b);}int code=c.getResponseCode();BufferedReader r=new BufferedReader(new InputStreamReader(code>=200&&code<300?c.getInputStream():c.getErrorStream(),StandardCharsets.UTF_8));StringBuilder s=new StringBuilder();String line;while((line=r.readLine())!=null)s.append(line);JSONObject body=s.length()>0?new JSONObject(s.toString()):new JSONObject();if(cb!=null)cb.onResult(code>=200&&code<300,body.optString("message","HTTP "+code),body);
            }catch(Exception e){if(cb!=null)cb.onResult(false,e.getMessage(),new JSONObject());}finally{if(c!=null)c.disconnect();}
        }}).start();
    }
    private static String hmacHex(String secret,String data) throws Exception {Mac m=Mac.getInstance("HmacSHA256");m.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8),"HmacSHA256"));byte[] out=m.doFinal(data.getBytes(StandardCharsets.UTF_8));StringBuilder s=new StringBuilder();for(byte x:out)s.append(String.format("%02x",x));return s.toString();}
}
