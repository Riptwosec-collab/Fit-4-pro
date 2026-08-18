import app from '@system.app';
import battery from '@system.battery';
import vibrator from '@system.vibrator';
import sensor from '@system.sensor';
import { P2pClient, Message, Builder } from '../../wearengine/wearengine.js';
import { PHONE_PACKAGE, PHONE_FINGERPRINT } from '../../common/constants.js';
import { getFeature } from '../../common/featureCatalog.js';

var p2pClient = new P2pClient();
var msg = new Message();
var builder = new Builder();
function nowId(){ return String(Date.now())+'-'+String(Math.floor(Math.random()*10000)); }

export default {
  data: {
    view:'home', category:'CONTROL', showControl:false, showApps:false, showSmart:false, showNetwork:false, showSystem:false,
    connectionState:'OFFLINE', pcState:'UNKNOWN', watchBattery:0, clockText:'--:--', masterVolume:'--',
    cpu:'--', gpu:'--', ram:'--', ping:'--', activeApp:'-', contextProfile:'GENERIC', audioOutput:'DEFAULT', notificationCount:0, latestNotification:'-',
    selectedId:'', selectedTitle:'', selectedSource:'', selectedDesc:'', featureState:'READY', featureData:'-',
    action1Label:'', action2Label:'', action3Label:'', action4Label:'', action1Command:'', action2Command:'', action3Command:'', action4Command:'',
    message:'READY', motionArmed:false, motionCalibrating:false, airMouseActive:false, airMouseSensitivity:5, powerProfile:'BALANCED', currentWindowHwnd:0,
    clockTimer:null
  },

  onInit(){
    this.refreshClock();
    var self=this;
    this.clockTimer=setInterval(function(){ self.refreshClock(); },1000);
    this.refreshBattery();
    this.setupWearEngine();
  },
  onDestroy(){
    if(this.clockTimer){try{clearInterval(this.clockTimer);}catch(e){} this.clockTimer=null;}
    this.stopMotion();
    this.stopAirMouse();
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
        onSuccess:function(){ self.connectionState='CONNECTED'; self.message='PHONE LINK READY'; self.sendCommand('GET_DASHBOARD'); },
        onFailure:function(){ self.connectionState='OFFLINE'; self.message='WEAR ENGINE OFFLINE'; },
        onReceiveMessage:function(data){ self.onPhoneMessage(data); }
      });
    }catch(e){ this.connectionState='OFFLINE'; this.message='INSTALL OFFICIAL WEAR ENGINE'; }
  },

  onPhoneMessage(data){
    if(!data||data.isFileType)return;
    try{
      var raw=(typeof data.data!=='undefined')?data.data:data;
      var obj=JSON.parse(String(raw));
      if(obj.type==='snapshot'){
        if(obj.pc)this.updateDashboard(obj.pc);
        if(obj.wifi)this.updateWifi(obj.wifi);
        this.connectionState='CONNECTED'; this.message='SYNC';
        return;
      }
      if(obj.type==='result'){
        this.connectionState='CONNECTED';
        this.message=obj.ok?'OK: '+(obj.message||obj.action||''):'ERROR: '+(obj.message||'FAILED');
        this.featureState=obj.ok?'READY':'ERROR';
        var a=obj.action||''; var d=obj.data;
        if(a==='GET_DASHBOARD'||a==='GET_PC_STATUS'){ this.updateDashboard(d||{}); }
        else if(a==='GET_NETWORK'){ this.updateNetwork(d||{}); }
        else if(a==='GET_CONTEXT'){ this.updateContext(d||{}); }
        else if(a==='GET_WINDOWS'){ this.updateWindows(d||{}); }
        else if(a==='GET_AUDIO'){ this.updateAudio(d||{}); }
        else if(a==='GET_MACROS'){ this.updateMacros(d||{}); }
        else if(a==='GET_NOTIFICATIONS'){ this.updateNotifications(d||{}); }
        else if(a==='GET_APPS'){ this.updateApps(d||{}); }
        else if(typeof d!=='undefined'&&d!==null){ this.featureData=(typeof d==='object')?this.compact(d):String(d); }
      }
    }catch(e){ this.message='RX DATA'; }
  },

  compact(o){ try{return JSON.stringify(o).substring(0,150);}catch(e){return '-';} },
  updateDashboard(d){
    this.pcState=d.state||this.pcState;
    this.cpu=(typeof d.cpuPercent==='number')?d.cpuPercent+'%':'--';
    this.gpu=(typeof d.gpuPercent==='number')?d.gpuPercent+'%':'--';
    this.ram=(typeof d.ramPercent==='number')?d.ramPercent+'%':'--';
    if(d.network&&typeof d.network.pingMs==='number')this.ping=d.network.pingMs+'ms';
    this.activeApp=d.activeApp||this.activeApp;
    if(d.context){ this.contextProfile=d.context.profile||this.contextProfile; }
    if(d.audio){
      this.audioOutput=d.audio.output||this.audioOutput;
      if(typeof d.audio.master==='number')this.masterVolume=String(Math.round(d.audio.master));
    }
    this.notificationCount=Number(d.notificationCount||0);
    if(d.latestNotification)this.latestNotification=(d.latestNotification.title||'ALERT')+': '+(d.latestNotification.message||'');
    this.featureData='CPU '+this.cpu+' | GPU '+this.gpu+' | RAM '+this.ram+' | '+this.activeApp;
  },
  updateNetwork(d){ this.ping=(typeof d.pingMs==='number')?d.pingMs+'ms':'--'; this.featureData=(d.ip||'NO IP')+' | '+(d.gateway||'NO GW')+' | '+this.ping+' | ↓'+String(d.downloadMbps||0)+' ↑'+String(d.uploadMbps||0)+' Mbps'; },
  updateContext(d){ this.contextProfile=d.profile||'GENERIC'; var a=d.active||{}; this.activeApp=a.process||a.title||this.activeApp; var labels=d.actions||[]; this.featureData=this.contextProfile+' | '+this.activeApp+' | '+labels.join(' / '); },
  updateWindows(d){ var a=d.active||{}; this.currentWindowHwnd=Number(a.hwnd||0); var ws=d.windows||[]; this.featureData=(a.title||a.process||'NO ACTIVE')+' | '+ws.length+' windows'; },
  updateAudio(d){ this.audioOutput=d.output||'DEFAULT'; if(typeof d.master==='number')this.masterVolume=String(Math.round(d.master)); var sessions=d.sessions||[]; this.featureData=this.audioOutput+' | '+sessions.length+' sessions | '+(d.provider||'WINDOWS'); },
  updateMacros(d){ var m=d.macros||{}; var names=[]; for(var k in m){if(m.hasOwnProperty(k))names.push(m[k].name||k);} this.featureData=names.slice(0,5).join(' / ')||'NO MACROS'; },
  updateNotifications(d){ var items=d.items||[]; this.notificationCount=Number(d.count||items.length||0); if(items.length)this.latestNotification=(items[0].title||'ALERT')+': '+(items[0].message||''); this.featureData=this.notificationCount+' alerts | '+this.latestNotification; },
  updateApps(d){ var a=d.apps||[]; var names=[]; for(var i=0;i<a.length;i++)names.push(a[i].name||a[i].id); this.featureData=names.slice(0,7).join(' / ')||'NO APPS'; },
  updateWifi(w){ var extra=''; if(w.best&&w.best.ssid)extra=' | BEST '+w.best.ssid+' '+String(w.best.score||0); this.featureData=(w.summary||'WI-FI SYNC')+extra; },

  sendCommand(action,extra){
    if(!action)return;
    if(action==='MOTION_ARM'){this.startMotion();return;}
    if(action==='MOTION_DISARM'){this.stopMotion();return;}
    if(action==='MOTION_CALIBRATE'){this.calibrateMotion();return;}
    if(action==='AIR_MOUSE_START'){this.startAirMouse();return;}
    if(action==='AIR_MOUSE_STOP'){this.stopAirMouse();return;}
    if(action==='AIR_MOUSE_CENTER'){this.haptic('short');this.message='AIR MOUSE CENTERED';return;}
    if(action==='AIR_MOUSE_SENS_UP'){this.airMouseSensitivity++;if(this.airMouseSensitivity>9)this.airMouseSensitivity=3;this.featureData='SENS '+this.airMouseSensitivity;this.message='AIR MOUSE SENS '+this.airMouseSensitivity;return;}
    if(action==='WINDOW_FOCUS_ACTIVE'||action==='WINDOW_MIN_ACTIVE'||action==='WINDOW_CLOSE_ACTIVE'){
      if(!this.currentWindowHwnd){this.message='REFRESH WINDOWS FIRST';this.featureState='NO WINDOW';return;}
      var mapped=action==='WINDOW_FOCUS_ACTIVE'?'WINDOW_FOCUS':action==='WINDOW_MIN_ACTIVE'?'WINDOW_MIN':'WINDOW_CLOSE';
      this.sendRemote(mapped,{hwnd:this.currentWindowHwnd});return;
    }
    if(action==='MACRO_RUN_WORK'){this.sendRemote('MACRO_RUN',{id:'work'});return;}
    if(action==='MACRO_RUN_GAME'){this.sendRemote('MACRO_RUN',{id:'game'});return;}
    if(action==='MACRO_RUN_MEETING'){this.sendRemote('MACRO_RUN',{id:'meeting'});return;}
    if(action==='HAPTIC_TEST'){this.haptic('short');this.message='HAPTIC OK';return;}
    if(action==='POWER_BALANCED'||action==='POWER_ENDURANCE'){this.powerProfile=action.replace('POWER_','');this.featureData=this.powerProfile;this.message='POWER '+this.powerProfile;if(this.powerProfile==='ENDURANCE'){this.stopMotion();this.stopAirMouse();}return;}
    if(action==='LOG_CLEAR'){this.message='LOG CLEARED';this.featureData='-';return;}
    this.sendRemote(action,extra||{});
  },

  sendRemote(action,payload){
    var self=this;
    var envelope={v:1,id:nowId(),ts:Date.now(),type:'command',action:action,source:'FIT4PRO',payload:payload||{}};
    try{
      builder.setDescription(JSON.stringify(envelope)); msg.builder=builder;
      p2pClient.send(msg,{
        onSuccess:function(){self.connectionState='CONNECTED';self.message='SENT '+action;},
        onFailure:function(){self.connectionState='OFFLINE';self.message='PHONE LINK FAILED';self.haptic('long');},
        onSendResult:function(resultCode){if(resultCode&&resultCode.code&&resultCode.code!=207)self.message='SEND CODE '+resultCode.code;},
        onSendProgress:function(){}
      });
    }catch(e){this.connectionState='OFFLINE';this.message='OFFLINE: '+action;}
  },

  refreshBattery(){var self=this;try{battery.getStatus({success:function(d){self.watchBattery=Math.round((d.level||0)*100);},fail:function(){}});}catch(e){}},
  haptic(mode){try{vibrator.vibrate({mode:mode||'short',success:function(){},fail:function(){}});}catch(e){}},

  motionState:{baseX:0,baseY:0,baseZ:0,calCount:0,sumX:0,sumY:0,sumZ:0,lastGesture:0,lastTwist:0,twistCount:0,shakeCount:0,shakeWindow:0},
  startMotion(){var self=this;if(this.motionArmed)return;this.stopAirMouse();this.motionArmed=true;this.featureState='ACTIVE';this.message='MOTION ARMED';try{sensor.subscribeAccelerometer({interval:'ui',success:function(r){self.onAccel(r);},fail:function(d,c){self.motionArmed=false;self.featureState='NO PERMISSION';self.message='ACCEL ERROR '+c;}});sensor.subscribeGyroscope({interval:'ui',success:function(r){self.onGyro(r);},fail:function(d,c){self.message='GYRO LIMITED '+c;}});}catch(e){this.motionArmed=false;this.featureState='UNAVAILABLE';this.message='MOTION API UNAVAILABLE';}},
  stopMotion(){try{sensor.unsubscribeAccelerometer();}catch(e){}try{if(!this.airMouseActive)sensor.unsubscribeGyroscope();}catch(e){}this.motionArmed=false;this.motionCalibrating=false;if(this.selectedId==='26')this.featureState='READY';},
  calibrateMotion(){var st=this.motionState;st.calCount=0;st.sumX=0;st.sumY=0;st.sumZ=0;this.motionCalibrating=true;this.message='CALIBRATE 0/20';if(!this.motionArmed)this.startMotion();},
  onAccel(r){var st=this.motionState;var x=Number(r.x||0),y=Number(r.y||0),z=Number(r.z||0);if(this.motionCalibrating){st.sumX+=x;st.sumY+=y;st.sumZ+=z;st.calCount++;this.message='CALIBRATE '+st.calCount+'/20';if(st.calCount>=20){st.baseX=st.sumX/20;st.baseY=st.sumY/20;st.baseZ=st.sumZ/20;this.motionCalibrating=false;this.message='CALIBRATION GOOD';this.haptic('short');}return;}var now=Date.now();if(now-st.lastGesture<800)return;var dx=x-st.baseX,dy=y-st.baseY,dz=z-st.baseZ;var mag=Math.sqrt(dx*dx+dy*dy+dz*dz);if(dx>11&&Math.abs(dy)<10){this.motionGesture('FLICK RIGHT','MEDIA_NEXT',Math.min(99,Math.round(70+dx*2)));return;}if(dx<-11&&Math.abs(dy)<10){this.motionGesture('FLICK LEFT','MEDIA_PREV',Math.min(99,Math.round(70+Math.abs(dx)*2)));return;}if(mag>18){if(now-st.shakeWindow>700){st.shakeWindow=now;st.shakeCount=0;}st.shakeCount++;if(st.shakeCount>=3){st.shakeCount=0;this.motionGesture('SHAKE','MEDIA_MUTE',92);}}},
  onGyro(r){if(this.airMouseActive){this.onAirMouseGyro(r);return;}var st=this.motionState;var now=Date.now();var z=Math.abs(Number(r.z||0));if(z>3.0){if(now-st.lastTwist<700)st.twistCount++;else st.twistCount=1;st.lastTwist=now;if(st.twistCount>=2&&now-st.lastGesture>800){st.twistCount=0;this.motionGesture('DOUBLE TWIST','MEDIA_PLAY_PAUSE',90);}}},
  motionGesture(name,cmd,confidence){if(confidence<85)return;this.motionState.lastGesture=Date.now();this.featureData=name+' '+confidence+'%';this.message='GESTURE '+name;this.haptic('short');this.sendRemote(cmd,{gesture:name,confidence:confidence});},

  airMouseLast:0,
  startAirMouse(){var self=this;if(this.airMouseActive)return;this.stopMotion();this.airMouseActive=true;this.featureState='ACTIVE';this.featureData='SENS '+this.airMouseSensitivity;this.message='AIR MOUSE ACTIVE';try{sensor.subscribeGyroscope({interval:'ui',success:function(r){self.onAirMouseGyro(r);},fail:function(d,c){self.airMouseActive=false;self.featureState='NO PERMISSION';self.message='GYRO ERROR '+c;}});this.haptic('short');}catch(e){this.airMouseActive=false;this.featureState='UNAVAILABLE';this.message='GYRO API UNAVAILABLE';}},
  stopAirMouse(){if(!this.airMouseActive)return;try{sensor.unsubscribeGyroscope();}catch(e){}this.airMouseActive=false;if(this.selectedId==='5')this.featureState='READY';this.message='AIR MOUSE STOPPED';},
  onAirMouseGyro(r){var now=Date.now();if(now-this.airMouseLast<120)return;this.airMouseLast=now;var x=Number(r.y||0),y=Number(r.x||0);var dead=0.18;if(Math.abs(x)<dead)x=0;if(Math.abs(y)<dead)y=0;if(x===0&&y===0)return;var s=this.airMouseSensitivity;var dx=Math.round(x*s*2.2),dy=Math.round(y*s*2.2);if(dx>35)dx=35;if(dx<-35)dx=-35;if(dy>35)dy=35;if(dy<-35)dy=-35;this.sendRemote('MOUSE_MOVE',{dx:dx,dy:dy});},

  openFeature(id){var f=getFeature(id);if(!f)return;this.selectedId=String(id);this.selectedTitle=f.title;this.selectedSource=f.source;this.selectedDesc=f.desc;this.action1Label=f.actions[0]?f.actions[0].label:'';this.action1Command=f.actions[0]?f.actions[0].command:'';this.action2Label=f.actions[1]?f.actions[1].label:'';this.action2Command=f.actions[1]?f.actions[1].command:'';this.action3Label=f.actions[2]?f.actions[2].label:'';this.action3Command=f.actions[2]?f.actions[2].command:'';this.action4Label=f.actions[3]?f.actions[3].label:'';this.action4Command=f.actions[3]?f.actions[3].command:'';this.featureState='READY';this.featureData='-';this.message='MODULE READY';this.view='detail';this.haptic('short');},
  setCategory(c){this.category=c;this.view='list';this.showControl=c==='CONTROL';this.showApps=c==='APPS';this.showSmart=c==='SMART';this.showNetwork=c==='NETWORK';this.showSystem=c==='SYSTEM';},
  goHome(){this.view='home';this.showControl=false;this.showApps=false;this.showSmart=false;this.showNetwork=false;this.showSystem=false;this.refreshBattery();this.sendRemote('GET_DASHBOARD',{});},
  goList(){this.setCategory(this.category);},catControl(){this.setCategory('CONTROL');},catApps(){this.setCategory('APPS');},catSmart(){this.setCategory('SMART');},catNetwork(){this.setCategory('NETWORK');},catSystem(){this.setCategory('SYSTEM');},
  quickLock(){this.sendCommand('PC_LOCK');},quickMute(){this.sendCommand('MEDIA_MUTE');},quickPlay(){this.sendCommand('MEDIA_PLAY_PAUSE');},quickSync(){this.sendCommand('GET_DASHBOARD');},
  detailAction1(){this.sendCommand(this.action1Command);},detailAction2(){this.sendCommand(this.action2Command);},detailAction3(){this.sendCommand(this.action3Command);},detailAction4(){this.sendCommand(this.action4Command);},
  swipeEvent(e){if(e.direction=='right'){if(this.view=='home')app.terminate();else if(this.view=='detail')this.goList();else this.goHome();}},

  f0(){this.openFeature('0');},f1(){this.openFeature('1');},f2(){this.openFeature('2');},f3(){this.openFeature('3');},f4(){this.openFeature('4');},f5(){this.openFeature('5');},f6(){this.openFeature('6');},f7(){this.openFeature('7');},f8(){this.openFeature('8');},f9(){this.openFeature('9');},f10(){this.openFeature('10');},f11(){this.openFeature('11');},f12(){this.openFeature('12');},f14(){this.openFeature('14');},f15(){this.openFeature('15');},f18(){this.openFeature('18');},f21(){this.openFeature('21');},f23(){this.openFeature('23');},f25(){this.openFeature('25');},f26(){this.openFeature('26');},f31(){this.openFeature('31');},f39(){this.openFeature('39');},f40(){this.openFeature('40');},f41(){this.openFeature('41');},f42(){this.openFeature('42');},f43(){this.openFeature('43');},f44(){this.openFeature('44');}
};
