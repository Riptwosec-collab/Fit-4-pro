import app from '@system.app';
import battery from '@system.battery';
import vibrator from '@system.vibrator';
import geolocation from '@system.geolocation';
import sensor from '@system.sensor';
import storage from '@system.storage';
import { P2pClient, Message, Builder } from '../../wearengine/wearengine.js';
import { PHONE_PACKAGE, PHONE_FINGERPRINT } from '../../common/constants.js';
import { getFeature } from '../../common/featureCatalog.js';

var p2pClient = new P2pClient();
var msg = new Message();
var builder = new Builder();
function nowId(){ return String(Date.now())+'-'+String(Math.floor(Math.random()*10000)); }

export default {
  data:{
    view:'home', category:'COMMAND',
    showCommand:false, showBio:false, showSport:false, showField:false, showTactical:false, showSystem:false,
    connectionState:'OFFLINE', pcState:'UNKNOWN', watchBattery:0, clockText:'--:--', masterVolume:'--',
    cpu:'--', gpu:'--', ram:'--', ping:'--', activeApp:'-', contextProfile:'GENERIC', audioOutput:'DEFAULT', notificationCount:0, latestNotification:'-',
    heartRate:'--', hrSubscribed:false, motionArmed:false, motionCalibrating:false, airMouseActive:false, airMouseSensitivity:5,
    compassActive:false, barometerActive:false, breadcrumbActive:false, breadcrumbPoints:0, powerProfile:'BALANCED', sosConfirmUntil:0, currentWindowHwnd:0,
    selectedId:'', selectedTitle:'', selectedSource:'', selectedDesc:'', featureState:'READY', featureData:'-',
    action1Label:'', action2Label:'', action3Label:'', action4Label:'', action1Command:'', action2Command:'', action3Command:'', action4Command:'',
    visualMain:'READY', visualSub:'MODULE', message:'READY', clockTimer:null
  },

  onInit(){
    this.refreshClock();
    var self=this;
    this.clockTimer=setInterval(function(){self.refreshClock();},1000);
    this.refreshBattery();
    this.setupWearEngine();
  },

  onDestroy(){
    if(this.clockTimer){try{clearInterval(this.clockTimer);}catch(e){} this.clockTimer=null;}
    this.stopHeartRate();this.stopMotion();this.stopAirMouse();this.stopCompass();this.stopBarometer();this.stopBreadcrumb();this.stopLight();
    try{p2pClient.unregisterReceiver({onSuccess:function(){},onFailure:function(){}});}catch(e){}
  },

  two(n){ return n<10?'0'+String(n):String(n); },
  refreshClock(){ var d=new Date(); this.clockText=this.two(d.getHours())+':'+this.two(d.getMinutes()); },

  setupWearEngine(){
    var self=this;
    try{
      p2pClient.setPeerPkgName(PHONE_PACKAGE);
      p2pClient.setPeerFingerPrint(PHONE_FINGERPRINT);
      p2pClient.registerReceiver({
        onSuccess:function(){self.connectionState='CONNECTED';self.message='PHONE LINK READY';self.sendRemote('GET_DASHBOARD',{});},
        onFailure:function(){self.connectionState='OFFLINE';self.message='WEAR ENGINE OFFLINE';},
        onReceiveMessage:function(data){self.onPhoneMessage(data);}
      });
    }catch(e){this.connectionState='OFFLINE';this.message='INSTALL OFFICIAL WEAR ENGINE';}
  },

  onPhoneMessage(data){
    if(!data||data.isFileType)return;
    try{
      var raw=(typeof data.data!=='undefined')?data.data:data;
      var obj=JSON.parse(String(raw));
      if(obj.type==='snapshot'){
        if(obj.pc)this.updateDashboard(obj.pc);
        if(obj.wifi)this.updateWifi(obj.wifi);
        this.connectionState='CONNECTED';this.message='SYNC';return;
      }
      if(obj.type==='result'){
        this.connectionState='CONNECTED';
        this.message=obj.ok?'OK: '+(obj.message||obj.action||''):'ERROR: '+(obj.message||'FAILED');
        this.featureState=obj.ok?'READY':'ERROR';
        var a=obj.action||'',d=obj.data;
        if(a==='GET_DASHBOARD'||a==='GET_PC_STATUS')this.updateDashboard(d||{});
        else if(a==='GET_NETWORK'||a==='PHONE_NETWORK_STATUS'||a==='NETWORK_PING')this.updateNetwork(d||{});
        else if(a==='GET_CONTEXT')this.updateContext(d||{});
        else if(a==='GET_WINDOWS')this.updateWindows(d||{});
        else if(a==='GET_AUDIO')this.updateAudio(d||{});
        else if(a==='GET_MACROS')this.updateMacros(d||{});
        else if(a==='GET_NOTIFICATIONS')this.updateNotifications(d||{});
        else if(a==='GET_APPS')this.updateApps(d||{});
        else if(typeof d!=='undefined'&&d!==null)this.featureData=(typeof d==='object')?this.compact(d):String(d);
      }
    }catch(e){this.message='RX DATA';}
  },

  compact(o){try{return JSON.stringify(o).substring(0,150);}catch(e){return '-';}},
  updateDashboard(d){
    this.pcState=d.state||this.pcState;
    this.cpu=(typeof d.cpuPercent==='number')?d.cpuPercent+'%':'--';
    this.gpu=(typeof d.gpuPercent==='number')?d.gpuPercent+'%':'--';
    this.ram=(typeof d.ramPercent==='number')?d.ramPercent+'%':'--';
    if(d.network&&typeof d.network.pingMs==='number')this.ping=d.network.pingMs+'ms';
    this.activeApp=d.activeApp||this.activeApp;
    if(d.context)this.contextProfile=d.context.profile||this.contextProfile;
    if(d.audio){this.audioOutput=d.audio.output||this.audioOutput;if(typeof d.audio.master==='number')this.masterVolume=String(Math.round(d.audio.master));}
    this.notificationCount=Number(d.notificationCount||0);
    if(d.latestNotification)this.latestNotification=(d.latestNotification.title||'ALERT')+': '+(d.latestNotification.message||'');
    if(this.selectedId==='1')this.featureData='CPU '+this.cpu+' | GPU '+this.gpu+' | RAM '+this.ram+' | '+this.activeApp;
  },
  updateNetwork(d){this.ping=(typeof d.pingMs==='number')?d.pingMs+'ms':'--';this.featureData=(d.ip||'NO IP')+' | '+(d.gateway||'NO GW')+' | '+this.ping+' | ↓'+String(d.downloadMbps||0)+' ↑'+String(d.uploadMbps||0)+' Mbps';},
  updateContext(d){this.contextProfile=d.profile||'GENERIC';var a=d.active||{};this.activeApp=a.process||a.title||this.activeApp;var labels=d.actions||[];this.featureData=this.contextProfile+' | '+this.activeApp+' | '+labels.join(' / ');},
  updateWindows(d){var a=d.active||{};this.currentWindowHwnd=Number(a.hwnd||0);var ws=d.windows||[];this.featureData=(a.title||a.process||'NO ACTIVE')+' | '+ws.length+' windows';},
  updateAudio(d){this.audioOutput=d.output||'DEFAULT';if(typeof d.master==='number')this.masterVolume=String(Math.round(d.master));var sessions=d.sessions||[];this.featureData=this.audioOutput+' | '+sessions.length+' sessions | '+(d.provider||'WINDOWS');},
  updateMacros(d){var m=d.macros||{},names=[];for(var k in m){if(m.hasOwnProperty(k))names.push(m[k].name||k);}this.featureData=names.slice(0,5).join(' / ')||'NO MACROS';},
  updateNotifications(d){var items=d.items||[];this.notificationCount=Number(d.count||items.length||0);if(items.length)this.latestNotification=(items[0].title||'ALERT')+': '+(items[0].message||'');this.featureData=this.notificationCount+' alerts | '+this.latestNotification;},
  updateApps(d){var a=d.apps||[],names=[];for(var i=0;i<a.length;i++)names.push(a[i].name||a[i].id);this.featureData=names.slice(0,7).join(' / ')||'NO APPS';},
  updateWifi(w){var extra='';if(w.best&&w.best.ssid)extra=' | BEST '+w.best.ssid+' '+String(w.best.score||0);this.featureData=(w.summary||'WI-FI SYNC')+extra;},

  sendCommand(action,extra){
    if(!action)return;
    if(action==='BIO_START'){this.startHeartRate();return;}if(action==='BIO_STOP'){this.stopHeartRate();return;}
    if(action==='MOTION_ARM'){this.startMotion();return;}if(action==='MOTION_DISARM'){this.stopMotion();return;}if(action==='MOTION_CALIBRATE'){this.calibrateMotion();return;}
    if(action==='AIR_MOUSE_START'){this.startAirMouse();return;}if(action==='AIR_MOUSE_STOP'){this.stopAirMouse();return;}
    if(action==='AIR_MOUSE_CENTER'){this.haptic('short');this.message='AIR MOUSE CENTERED';return;}
    if(action==='AIR_MOUSE_SENS_UP'){this.airMouseSensitivity++;if(this.airMouseSensitivity>9)this.airMouseSensitivity=3;this.featureData='SENS '+this.airMouseSensitivity;this.message='AIR MOUSE SENS '+this.airMouseSensitivity;return;}
    if(action==='COMPASS_START'){this.startCompass();return;}if(action==='COMPASS_STOP'){this.stopCompass();return;}
    if(action==='BAROMETER_START'){this.startBarometer();return;}if(action==='BAROMETER_STOP'){this.stopBarometer();return;}
    if(action==='TACTICAL_LIGHT_RED'){this.startLight('red');return;}if(action==='TACTICAL_LIGHT_WHITE'){this.startLight('white');return;}if(action==='TACTICAL_LIGHT_SOS'){this.confirmSosLight();return;}
    if(action==='FIELD_LOCATION'||action==='GEO_SAVE_TEMP'||action==='BREADCRUMB_MARK'){this.captureLocation(action);return;}
    if(action==='BREADCRUMB_START'){this.startBreadcrumb();return;}if(action==='BREADCRUMB_STOP'){this.stopBreadcrumb();return;}if(action==='BREADCRUMB_RETURN'){this.returnBreadcrumb();return;}
    if(action==='GEO_LAST'||action==='GEO_RETURN'){this.showLastAnchor(action==='GEO_RETURN');return;}
    if(action==='POWER_PERFORMANCE'||action==='POWER_BALANCED'||action==='POWER_ENDURANCE'||action==='POWER_GRID'){this.applyPowerProfile(action);return;}
    if(action==='WINDOW_FOCUS_ACTIVE'||action==='WINDOW_MIN_ACTIVE'||action==='WINDOW_CLOSE_ACTIVE'){
      if(!this.currentWindowHwnd){this.message='REFRESH WINDOWS FIRST';this.featureState='NO WINDOW';return;}
      var mapped=action==='WINDOW_FOCUS_ACTIVE'?'WINDOW_FOCUS':action==='WINDOW_MIN_ACTIVE'?'WINDOW_MIN':'WINDOW_CLOSE';this.sendRemote(mapped,{hwnd:this.currentWindowHwnd});return;
    }
    if(action==='MACRO_RUN_WORK'){this.sendRemote('MACRO_RUN',{id:'work'});return;}if(action==='MACRO_RUN_GAME'){this.sendRemote('MACRO_RUN',{id:'game'});return;}if(action==='MACRO_RUN_MEETING'){this.sendRemote('MACRO_RUN',{id:'meeting'});return;}
    if(action==='HAPTIC_TEST'||action==='COGNITIVE_RESET'){this.haptic('short');this.message=action;return;}
    if(action==='LOG_CLEAR'){this.message='LOG CLEARED';this.featureData='-';return;}
    this.sendRemote(action,extra||{});
  },

  sendRemote(action,payload){
    var self=this;var envelope={v:1,id:nowId(),ts:Date.now(),type:'command',action:action,source:'FIT4PRO',payload:payload||{}};
    try{builder.setDescription(JSON.stringify(envelope));msg.builder=builder;p2pClient.send(msg,{onSuccess:function(){self.connectionState='CONNECTED';self.message='SENT '+action;},onFailure:function(){self.connectionState='OFFLINE';self.message='PHONE LINK FAILED';self.haptic('long');},onSendResult:function(resultCode){if(resultCode&&resultCode.code&&resultCode.code!=207)self.message='SEND CODE '+resultCode.code;},onSendProgress:function(){}});}catch(e){this.connectionState='OFFLINE';this.message='OFFLINE: '+action;}
  },

  refreshBattery(){var self=this;try{battery.getStatus({success:function(d){self.watchBattery=Math.round((d.level||0)*100);},fail:function(){}});}catch(e){}},
  haptic(mode){try{vibrator.vibrate({mode:mode||'short',success:function(){},fail:function(){}});}catch(e){}},

  startHeartRate(){var self=this;if(this.hrSubscribed)return;try{sensor.subscribeHeartRate({success:function(ret){self.heartRate=ret.heartRate||ret.rate||ret.value||'--';self.featureData=self.heartRate+' BPM';},fail:function(){self.featureState='NO PERMISSION';}});this.hrSubscribed=true;this.featureState='ACTIVE';this.message='HEART RATE ACTIVE';}catch(e){this.featureState='UNAVAILABLE';this.message='HEART RATE API UNAVAILABLE';}},
  stopHeartRate(){if(!this.hrSubscribed)return;try{sensor.unsubscribeHeartRate();}catch(e){}this.hrSubscribed=false;if(this.selectedId==='22')this.featureState='READY';},

  captureLocation(reason){var self=this;this.featureState='INITIALIZING';try{geolocation.getLocation({success:function(d){var display=String(d.latitude).substring(0,9)+', '+String(d.longitude).substring(0,9);self.featureData=display;self.featureState='READY';self.haptic('short');if(reason==='GEO_SAVE_TEMP'||reason==='BREADCRUMB_MARK'){var anchorObj={lat:Number(d.latitude),lon:Number(d.longitude),accuracy:d.accuracy||null,ts:Date.now()};storage.set({key:'last_anchor',value:JSON.stringify(anchorObj),success:function(){},fail:function(){}});}self.sendRemote('WATCH_LOCATION_RESULT',{reason:reason,latitude:d.latitude,longitude:d.longitude,accuracy:d.accuracy||null});},fail:function(data,code){self.featureState='NO LOCATION';self.message='LOCATION ERROR '+code;self.haptic('long');}});}catch(e){this.featureState='UNAVAILABLE';this.message='LOCATION API UNAVAILABLE';}},

  breadcrumbTimer:null,breadcrumbRoute:[],
  getLocationOnce(cb){try{geolocation.getLocation({success:function(d){cb(null,{lat:Number(d.latitude),lon:Number(d.longitude),accuracy:d.accuracy||null,ts:Date.now()});},fail:function(data,code){cb('LOCATION '+code,null);}});}catch(e){cb('LOCATION API',null);}},
  distanceM(a,b){var R=6371000,p1=a.lat*Math.PI/180,p2=b.lat*Math.PI/180,dp=(b.lat-a.lat)*Math.PI/180,dl=(b.lon-a.lon)*Math.PI/180;var x=Math.sin(dp/2)*Math.sin(dp/2)+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)*Math.sin(dl/2);return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));},
  bearingDeg(a,b){var p1=a.lat*Math.PI/180,p2=b.lat*Math.PI/180,dl=(b.lon-a.lon)*Math.PI/180,y=Math.sin(dl)*Math.cos(p2),x=Math.cos(p1)*Math.sin(p2)-Math.sin(p1)*Math.cos(p2)*Math.cos(dl);return (Math.atan2(y,x)*180/Math.PI+360)%360;},
  headingName(d){var a=['N','NE','E','SE','S','SW','W','NW'];return a[Math.round(((d%360)+360)%360/45)%8];},
  startBreadcrumb(){var self=this;if(this.breadcrumbActive)return;this.breadcrumbActive=true;this.breadcrumbRoute=[];this.breadcrumbPoints=0;this.featureState='ACTIVE';this.message='BREADCRUMB START';var sample=function(){self.getLocationOnce(function(err,p){if(err||!p){self.message='BREADCRUMB NO GPS';return;}var route=self.breadcrumbRoute,last=route.length?route[route.length-1]:null;if(!last||self.distanceM(last,p)>=50){route.push(p);if(route.length>100)route.shift();self.breadcrumbPoints=route.length;self.featureData=route.length+' POINTS';storage.set({key:'breadcrumb_route',value:JSON.stringify(route),success:function(){},fail:function(){}});}});};sample();this.breadcrumbTimer=setInterval(sample,this.powerProfile==='ENDURANCE'||this.powerProfile==='GRID'?60000:30000);this.haptic('short');},
  stopBreadcrumb(){if(this.breadcrumbTimer){clearInterval(this.breadcrumbTimer);this.breadcrumbTimer=null;}if(!this.breadcrumbActive)return;this.breadcrumbActive=false;this.featureState='READY';this.message='BREADCRUMB SAVED '+this.breadcrumbPoints;this.haptic('short');},
  returnBreadcrumb(){var self=this;storage.get({key:'breadcrumb_route',success:function(v){try{var route=JSON.parse(v||'[]');if(!route.length){self.featureState='NO DATA';self.message='NO BREADCRUMB';return;}var base=route[0];self.getLocationOnce(function(err,cur){if(err||!cur){self.featureState='NO LOCATION';self.message='RETURN NEEDS GPS';return;}var dist=Math.round(self.distanceM(cur,base)),bearing=Math.round(self.bearingDeg(cur,base));self.featureData=dist+' M | '+bearing+'° '+self.headingName(bearing);self.featureState='RETURN';self.message='RETURN TO BASE';self.haptic('long');});}catch(e){self.featureState='ERROR';self.message='ROUTE DATA ERROR';}},fail:function(){self.featureState='NO DATA';self.message='NO BREADCRUMB';}});},
  showLastAnchor(returnMode){var self=this;storage.get({key:'last_anchor',success:function(v){try{var a=JSON.parse(v||'{}');if(typeof a.lat==='undefined'){self.featureState='NO DATA';self.message='NO ANCHOR';return;}if(!returnMode){self.featureData=String(a.lat).substring(0,9)+', '+String(a.lon).substring(0,9);self.message='LAST ANCHOR';return;}self.getLocationOnce(function(err,cur){if(err||!cur){self.featureState='NO LOCATION';self.message='ANCHOR RETURN NEEDS GPS';return;}var dist=Math.round(self.distanceM(cur,a)),b=Math.round(self.bearingDeg(cur,a));self.featureData=dist+' M | '+b+'° '+self.headingName(b);self.featureState='RETURN';self.message='RETURN TO ANCHOR';});}catch(e){self.featureState='ERROR';self.message='ANCHOR DATA ERROR';}},fail:function(){self.featureState='NO DATA';self.message='NO ANCHOR';}});},

  applyPowerProfile(action){var p=action.replace('POWER_','');this.powerProfile=p;this.featureData=p;this.message='POWER '+p;if(p==='ENDURANCE'||p==='GRID'){this.stopMotion();this.stopAirMouse();this.stopBarometer();if(p==='GRID')this.stopCompass();}this.haptic('short');},

  motionState:{baseX:0,baseY:0,baseZ:0,calCount:0,sumX:0,sumY:0,sumZ:0,lastGesture:0,lastTwist:0,twistCount:0,shakeCount:0,shakeWindow:0},
  startMotion(){var self=this;if(this.motionArmed)return;this.stopAirMouse();this.motionArmed=true;this.featureState='ACTIVE';this.message='MOTION ARMED';try{sensor.subscribeAccelerometer({interval:'ui',success:function(r){self.onAccel(r);},fail:function(d,c){self.motionArmed=false;self.featureState='NO PERMISSION';self.message='ACCEL ERROR '+c;}});sensor.subscribeGyroscope({interval:'ui',success:function(r){self.onGyro(r);},fail:function(d,c){self.message='GYRO LIMITED '+c;}});}catch(e){this.motionArmed=false;this.featureState='UNAVAILABLE';this.message='MOTION API UNAVAILABLE';}},
  stopMotion(){try{sensor.unsubscribeAccelerometer();}catch(e){}try{if(!this.airMouseActive)sensor.unsubscribeGyroscope();}catch(e){}this.motionArmed=false;this.motionCalibrating=false;if(this.selectedId==='26')this.featureState='READY';},
  calibrateMotion(){var st=this.motionState;st.calCount=0;st.sumX=0;st.sumY=0;st.sumZ=0;this.motionCalibrating=true;this.message='CALIBRATE 0/20';if(!this.motionArmed)this.startMotion();},
  onAccel(r){var st=this.motionState,x=Number(r.x||0),y=Number(r.y||0),z=Number(r.z||0);if(this.motionCalibrating){st.sumX+=x;st.sumY+=y;st.sumZ+=z;st.calCount++;this.message='CALIBRATE '+st.calCount+'/20';if(st.calCount>=20){st.baseX=st.sumX/20;st.baseY=st.sumY/20;st.baseZ=st.sumZ/20;this.motionCalibrating=false;this.message='CALIBRATION GOOD';this.haptic('short');}return;}var now=Date.now();if(now-st.lastGesture<800)return;var dx=x-st.baseX,dy=y-st.baseY,dz=z-st.baseZ,mag=Math.sqrt(dx*dx+dy*dy+dz*dz);if(dx>11&&Math.abs(dy)<10){this.motionGesture('FLICK RIGHT','MEDIA_NEXT',Math.min(99,Math.round(70+dx*2)));return;}if(dx<-11&&Math.abs(dy)<10){this.motionGesture('FLICK LEFT','MEDIA_PREV',Math.min(99,Math.round(70+Math.abs(dx)*2)));return;}if(mag>18){if(now-st.shakeWindow>700){st.shakeWindow=now;st.shakeCount=0;}st.shakeCount++;if(st.shakeCount>=3){st.shakeCount=0;this.motionGesture('SHAKE','MEDIA_MUTE',92);}}},
  onGyro(r){if(this.airMouseActive){this.onAirMouseGyro(r);return;}var st=this.motionState,now=Date.now(),z=Math.abs(Number(r.z||0));if(z>3.0){if(now-st.lastTwist<700)st.twistCount++;else st.twistCount=1;st.lastTwist=now;if(st.twistCount>=2&&now-st.lastGesture>800){st.twistCount=0;this.motionGesture('DOUBLE TWIST','MEDIA_PLAY_PAUSE',90);}}},
  motionGesture(name,cmd,confidence){if(confidence<85)return;this.motionState.lastGesture=Date.now();this.featureData=name+' '+confidence+'%';this.message='GESTURE '+name;this.haptic('short');this.sendRemote(cmd,{gesture:name,confidence:confidence});},

  airMouseLast:0,
  startAirMouse(){var self=this;if(this.airMouseActive)return;this.stopMotion();this.airMouseActive=true;this.featureState='ACTIVE';this.featureData='SENS '+this.airMouseSensitivity;this.message='AIR MOUSE ACTIVE';try{sensor.subscribeGyroscope({interval:'ui',success:function(r){self.onAirMouseGyro(r);},fail:function(d,c){self.airMouseActive=false;self.featureState='NO PERMISSION';self.message='GYRO ERROR '+c;}});this.haptic('short');}catch(e){this.airMouseActive=false;this.featureState='UNAVAILABLE';this.message='GYRO API UNAVAILABLE';}},
  stopAirMouse(){if(!this.airMouseActive)return;try{sensor.unsubscribeGyroscope();}catch(e){}this.airMouseActive=false;if(this.selectedId==='5')this.featureState='READY';this.message='AIR MOUSE STOPPED';},
  onAirMouseGyro(r){var now=Date.now();if(now-this.airMouseLast<120)return;this.airMouseLast=now;var x=Number(r.y||0),y=Number(r.x||0),dead=0.18;if(Math.abs(x)<dead)x=0;if(Math.abs(y)<dead)y=0;if(x===0&&y===0)return;var s=this.airMouseSensitivity,dx=Math.round(x*s*2.2),dy=Math.round(y*s*2.2);if(dx>35)dx=35;if(dx<-35)dx=-35;if(dy>35)dy=35;if(dy<-35)dy=-35;this.sendRemote('MOUSE_MOVE',{dx:dx,dy:dy});},

  startCompass(){var self=this;if(this.compassActive)return;try{sensor.subscribeCompass({success:function(r){var d=Math.round(Number(r.direction||0));self.featureData=d+' deg '+self.headingName(d);self.featureState='ACTIVE';},fail:function(d,c){self.featureState='UNAVAILABLE';self.message='COMPASS ERROR '+c;}});this.compassActive=true;this.message='COMPASS ACTIVE';}catch(e){this.featureState='UNAVAILABLE';this.message='COMPASS API UNAVAILABLE';}},
  stopCompass(){try{sensor.unsubscribeCompass();}catch(e){}this.compassActive=false;if(this.selectedId==='27')this.featureState='READY';this.message='COMPASS STOPPED';},
  startBarometer(){var self=this;if(this.barometerActive)return;try{sensor.subscribeBarometer({success:function(r){var pa=Number(r.pressure||0);self.featureData=(pa/100).toFixed(1)+' hPa';self.featureState='ACTIVE';},fail:function(d,c){self.featureState='UNAVAILABLE';self.message='BAROMETER ERROR '+c;}});this.barometerActive=true;this.message='PRESSURE ACTIVE';}catch(e){this.featureState='UNAVAILABLE';this.message='BAROMETER API UNAVAILABLE';}},
  stopBarometer(){try{sensor.unsubscribeBarometer();}catch(e){}this.barometerActive=false;if(this.selectedId==='19')this.featureState='READY';this.message='PRESSURE STOPPED';},

  lightTimer:null,
  startLight(mode){this.sosConfirmUntil=0;if(this.lightTimer){clearInterval(this.lightTimer);this.lightTimer=null;}this.view=mode==='white'?'lightWhite':'lightRed';this.message='TACTICAL LIGHT '+mode.toUpperCase();},
  confirmSosLight(){var now=Date.now();if(now>this.sosConfirmUntil){this.sosConfirmUntil=now+5000;this.message='SOS SAFETY: TAP SOS AGAIN';this.haptic('long');return;}this.sosConfirmUntil=0;this.startSosLight();},
  startSosLight(){var self=this,on=true;this.view='lightRed';this.message='SOS FLASH ACTIVE';this.haptic('long');this.lightTimer=setInterval(function(){on=!on;self.view=on?'lightRed':'lightBlack';},450);},
  stopLight(){if(this.lightTimer){clearInterval(this.lightTimer);this.lightTimer=null;}if(this.view==='lightRed'||this.view==='lightWhite'||this.view==='lightBlack')this.view='detail';this.sosConfirmUntil=0;},

  visualFor(id){var n=String(id);if(n==='1')return ['CPU '+this.cpu,'PC MONITOR'];if(n==='5')return ['GYRO','AIR MOUSE'];if(n==='12')return [this.ping,'NETWORK'];if(n==='22')return [this.heartRate+'','BPM'];if(n==='27')return ['NAV','COMPASS'];if(n==='30')return ['LIGHT','TACTICAL'];if(n==='37')return [this.powerProfile,'POWER'];if(n==='39')return ['WI-FI','RECON'];if(n==='41')return [String(this.breadcrumbPoints),'POINTS'];if(n==='42')return ['ANCHOR','LOCAL'];if(n==='43')return ['UV','PROVIDER'];if(n==='44')return ['HEAT','ESTIMATE'];if(n==='45')return ['ALT','WELLNESS'];if(n==='46')return ['TRANSIT','GEOFENCE'];if(n==='47')return ['SKY','WINDOW'];if(n==='48')return ['SOS','LOCAL CORE'];if(n==='49')return [this.masterVolume+'%','AUDIO'];if(n==='50')return ['WINDOW','CONTROL'];if(n==='51')return ['MACRO','SAFE'];if(n==='52')return [String(this.notificationCount),'ALERTS'];if(n==='53')return ['TRUST','SECURE'];return ['READY','MODULE'];},

  openFeature(id){var f=getFeature(id);if(!f)return;this.selectedId=String(id);this.selectedTitle=f.title;this.selectedSource=f.source;this.selectedDesc=f.desc;this.action1Label=f.actions[0]?f.actions[0].label:'';this.action1Command=f.actions[0]?f.actions[0].command:'';this.action2Label=f.actions[1]?f.actions[1].label:'';this.action2Command=f.actions[1]?f.actions[1].command:'';this.action3Label=f.actions[2]?f.actions[2].label:'';this.action3Command=f.actions[2]?f.actions[2].command:'';this.action4Label=f.actions[3]?f.actions[3].label:'';this.action4Command=f.actions[3]?f.actions[3].command:'';this.featureState=f.source==='UNAVAILABLE'?'API GATED':'READY';this.featureData='-';this.message='MODULE READY';var v=this.visualFor(id);this.visualMain=v[0];this.visualSub=v[1];this.view='detail';this.haptic('short');if(String(id)==='1')this.sendRemote('GET_DASHBOARD',{});else if(String(id)==='4')this.sendRemote('GET_CONTEXT',{});else if(String(id)==='6')this.sendRemote('GET_APPS',{});else if(String(id)==='12')this.sendRemote('GET_NETWORK',{});else if(String(id)==='49')this.sendRemote('GET_AUDIO',{});else if(String(id)==='50')this.sendRemote('GET_WINDOWS',{});else if(String(id)==='51')this.sendRemote('GET_MACROS',{});else if(String(id)==='52')this.sendRemote('GET_NOTIFICATIONS',{});},
  setCategory(c){this.category=c;this.view='list';this.showCommand=c==='COMMAND';this.showBio=c==='BIO';this.showSport=c==='SPORT';this.showField=c==='FIELD';this.showTactical=c==='TACTICAL';this.showSystem=c==='SYSTEM';},
  goHome(){this.view='home';this.showCommand=false;this.showBio=false;this.showSport=false;this.showField=false;this.showTactical=false;this.showSystem=false;this.refreshBattery();this.sendRemote('GET_DASHBOARD',{});},
  goList(){this.setCategory(this.category);},catCommand(){this.setCategory('COMMAND');},catBio(){this.setCategory('BIO');},catSport(){this.setCategory('SPORT');},catField(){this.setCategory('FIELD');},catTactical(){this.setCategory('TACTICAL');},catSystem(){this.setCategory('SYSTEM');},
  quickLock(){this.sendCommand('PC_LOCK');},quickMute(){this.sendCommand('MEDIA_MUTE');},quickPlay(){this.sendCommand('MEDIA_PLAY_PAUSE');},quickShot(){this.sendCommand('SCREENSHOT');},detailAction1(){this.sendCommand(this.action1Command);},detailAction2(){this.sendCommand(this.action2Command);},detailAction3(){this.sendCommand(this.action3Command);},detailAction4(){this.sendCommand(this.action4Command);},
  swipeEvent(e){if(e.direction=='right'){if(this.view==='lightRed'||this.view==='lightWhite'||this.view==='lightBlack'){this.stopLight();return;}if(this.view==='home')app.terminate();else if(this.view==='detail')this.goList();else this.goHome();}},

  f0(){this.openFeature('0');},f1(){this.openFeature('1');},f2(){this.openFeature('2');},f3(){this.openFeature('3');},f4(){this.openFeature('4');},f5(){this.openFeature('5');},f6(){this.openFeature('6');},f7(){this.openFeature('7');},f8(){this.openFeature('8');},f9(){this.openFeature('9');},f10(){this.openFeature('10');},f11(){this.openFeature('11');},f12(){this.openFeature('12');},f13(){this.openFeature('13');},f14(){this.openFeature('14');},f15(){this.openFeature('15');},f16(){this.openFeature('16');},f17(){this.openFeature('17');},f18(){this.openFeature('18');},f19(){this.openFeature('19');},f20(){this.openFeature('20');},f21(){this.openFeature('21');},f22(){this.openFeature('22');},f23(){this.openFeature('23');},f24(){this.openFeature('24');},f25(){this.openFeature('25');},f26(){this.openFeature('26');},f27(){this.openFeature('27');},f28(){this.openFeature('28');},f29(){this.openFeature('29');},f30(){this.openFeature('30');},f31(){this.openFeature('31');},f32(){this.openFeature('32');},f33(){this.openFeature('33');},f34(){this.openFeature('34');},f35(){this.openFeature('35');},f36(){this.openFeature('36');},f37(){this.openFeature('37');},f38(){this.openFeature('38');},f39(){this.openFeature('39');},f40(){this.openFeature('40');},f41(){this.openFeature('41');},f42(){this.openFeature('42');},f43(){this.openFeature('43');},f44(){this.openFeature('44');},f45(){this.openFeature('45');},f46(){this.openFeature('46');},f47(){this.openFeature('47');},f48(){this.openFeature('48');},f49(){this.openFeature('49');},f50(){this.openFeature('50');},f51(){this.openFeature('51');},f52(){this.openFeature('52');},f53(){this.openFeature('53');}
};
