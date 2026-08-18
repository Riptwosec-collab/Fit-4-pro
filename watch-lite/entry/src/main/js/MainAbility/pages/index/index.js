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

function nowId() {
  return String(Date.now()) + '-' + String(Math.floor(Math.random() * 10000));
}

export default {
  data: {
    view: 'home',
    category: 'CONTROL',
    showControl: false,
    showApps: false,
    showSmart: false,
    showNetwork: false,
    showSystem: false,
    motionArmed: false,
    motionCalibrating: false,
    powerProfile: 'BALANCED',
    connectionState: 'OFFLINE',
    pcState: 'UNKNOWN',
    watchBattery: 0,
    selectedId: '',
    selectedTitle: '',
    selectedSource: '',
    selectedDesc: '',
    featureState: 'READY',
    featureData: '-',
    action1Label: '', action2Label: '', action3Label: '', action4Label: '',
    action1Command: '', action2Command: '', action3Command: '', action4Command: '',
    message: 'READY'
  },

  onInit() {
    this.refreshBattery();
    this.setupWearEngine();
  },

  onDestroy() {
    this.stopMotion();
    try { p2pClient.unregisterReceiver({ onSuccess:function(){}, onFailure:function(){} }); } catch (e) {}
  },

  setupWearEngine() {
    var self = this;
    try {
      p2pClient.setPeerPkgName(PHONE_PACKAGE);
      p2pClient.setPeerFingerPrint(PHONE_FINGERPRINT);
      p2pClient.registerReceiver({
        onSuccess: function() { self.connectionState='CONNECTED'; self.message='PHONE LINK READY'; },
        onFailure: function() { self.connectionState='OFFLINE'; self.message='WEAR ENGINE OFFLINE'; },
        onReceiveMessage: function(data) { self.onPhoneMessage(data); }
      });
    } catch (e) {
      this.connectionState='OFFLINE';
      this.message='INSTALL OFFICIAL WEAR ENGINE';
    }
  },

  onPhoneMessage(data) {
    if (!data || data.isFileType) return;
    try {
      var raw = (typeof data.data !== 'undefined') ? data.data : data;
      var obj = JSON.parse(String(raw));
      if (obj.type === 'snapshot') {
        if (obj.pc && obj.pc.state) this.pcState = obj.pc.state;
        if (obj.pc && obj.pc.summary && this.selectedId === '1') this.featureData = obj.pc.summary;
        if (obj.wifi) {
          var w = obj.wifi;
          var extra = '';
          if (w.best && w.best.ssid) extra = ' | BEST ' + w.best.ssid + ' ' + String(w.best.score || 0);
          if (this.selectedId === '12' || this.selectedId === '39') this.featureData = (w.summary || 'WI-FI SYNC') + extra;
        }
        this.connectionState='CONNECTED';
        this.message='SYNC';
      } else if (obj.type === 'result') {
        this.message = obj.ok ? 'OK: ' + (obj.message || obj.action || '') : 'ERROR: ' + (obj.message || 'FAILED');
        this.featureState = obj.ok ? 'READY' : 'ERROR';
        if (typeof obj.data !== 'undefined') this.featureData = (typeof obj.data === 'object') ? JSON.stringify(obj.data) : String(obj.data);
      }
    } catch (e) {
      this.message='RX DATA';
    }
  },

  sendCommand(action, extra) {
    var self = this;
    if (!action) return;

    if (action === 'MOTION_ARM') { this.startMotion(); return; }
    if (action === 'MOTION_DISARM') { this.stopMotion(); return; }
    if (action === 'MOTION_CALIBRATE') { this.calibrateMotion(); return; }
    if (action === 'POWER_BALANCED' || action === 'POWER_ENDURANCE') { this.applyPowerProfile(action); return; }
    if (action === 'HAPTIC_TEST') { this.haptic('short'); this.message='HAPTIC OK'; return; }
    if (action === 'LOG_CLEAR') { this.featureData='EMPTY'; this.message='LOCAL LOG CLEARED'; this.haptic('short'); return; }

    var envelope = { v:1, id:nowId(), ts:Date.now(), type:'command', action:action, source:'FIT4PRO', payload:extra || {} };
    try {
      builder.setDescription(JSON.stringify(envelope));
      msg.builder = builder;
      p2pClient.send(msg, {
        onSuccess: function() { self.connectionState='CONNECTED'; self.message='SENT ' + action; },
        onFailure: function() { self.connectionState='OFFLINE'; self.message='PHONE LINK FAILED'; self.haptic('long'); },
        onSendResult: function(resultCode) { if (resultCode && resultCode.code && resultCode.code != 207) self.message='SEND CODE ' + resultCode.code; },
        onSendProgress: function() {}
      });
    } catch (e) {
      this.connectionState='OFFLINE';
      this.message='OFFLINE: ' + action;
    }
  },

  refreshBattery() {
    var self = this;
    try {
      battery.getStatus({
        success: function(d) { self.watchBattery = Math.round((d.level || 0) * 100); },
        fail: function() {}
      });
    } catch (e) {}
  },

  haptic(mode) {
    try { vibrator.vibrate({ mode:mode || 'short', success:function(){}, fail:function(){} }); } catch (e) {}
  },

  applyPowerProfile(action) {
    this.powerProfile = action === 'POWER_ENDURANCE' ? 'ENDURANCE' : 'BALANCED';
    this.featureData = this.powerProfile;
    this.message = 'POWER ' + this.powerProfile;
    if (this.powerProfile === 'ENDURANCE') this.stopMotion();
    this.haptic('short');
  },

  motionState: { baseX:0, baseY:0, baseZ:0, calCount:0, sumX:0, sumY:0, sumZ:0, lastGesture:0, lastTwist:0, twistCount:0, shakeCount:0, shakeWindow:0 },

  startMotion() {
    var self = this;
    if (this.motionArmed) return;
    this.motionArmed = true;
    this.featureState='ACTIVE';
    this.message='MOTION ARMED';
    try {
      sensor.subscribeAccelerometer({
        interval:'ui',
        success:function(r){ self.onAccel(r); },
        fail:function(d,c){ self.motionArmed=false; self.featureState='NO PERMISSION'; self.message='ACCEL ERROR ' + c; }
      });
      sensor.subscribeGyroscope({
        interval:'ui',
        success:function(r){ self.onGyro(r); },
        fail:function(d,c){ self.message='GYRO LIMITED ' + c; }
      });
    } catch (e) {
      this.motionArmed=false;
      this.featureState='UNAVAILABLE';
      this.message='MOTION API UNAVAILABLE';
    }
  },

  stopMotion() {
    try { sensor.unsubscribeAccelerometer(); } catch (e) {}
    try { sensor.unsubscribeGyroscope(); } catch (e) {}
    this.motionArmed=false;
    this.motionCalibrating=false;
    if (this.selectedId === '26') this.featureState='READY';
  },

  calibrateMotion() {
    var st=this.motionState;
    st.calCount=0; st.sumX=0; st.sumY=0; st.sumZ=0;
    this.motionCalibrating=true;
    this.message='CALIBRATE 0/20';
    if (!this.motionArmed) this.startMotion();
  },

  onAccel(r) {
    var st=this.motionState;
    var x=Number(r.x||0), y=Number(r.y||0), z=Number(r.z||0);
    if (this.motionCalibrating) {
      st.sumX+=x; st.sumY+=y; st.sumZ+=z; st.calCount++;
      this.message='CALIBRATE ' + st.calCount + '/20';
      if (st.calCount >= 20) {
        st.baseX=st.sumX/20; st.baseY=st.sumY/20; st.baseZ=st.sumZ/20;
        this.motionCalibrating=false;
        this.message='CALIBRATION GOOD';
        this.haptic('short');
      }
      return;
    }
    var now=Date.now();
    if (now-st.lastGesture < 800) return;
    var dx=x-st.baseX, dy=y-st.baseY, dz=z-st.baseZ;
    var mag=Math.sqrt(dx*dx+dy*dy+dz*dz);
    if (dx > 11 && Math.abs(dy) < 10) { this.motionGesture('FLICK RIGHT','MEDIA_NEXT',Math.min(99,Math.round(70+dx*2))); return; }
    if (dx < -11 && Math.abs(dy) < 10) { this.motionGesture('FLICK LEFT','MEDIA_PREV',Math.min(99,Math.round(70+Math.abs(dx)*2))); return; }
    if (mag > 18) {
      if (now-st.shakeWindow > 700) { st.shakeWindow=now; st.shakeCount=0; }
      st.shakeCount++;
      if (st.shakeCount >= 3) { st.shakeCount=0; this.motionGesture('SHAKE','MEDIA_MUTE',92); }
    }
  },

  onGyro(r) {
    var st=this.motionState;
    var now=Date.now();
    var z=Math.abs(Number(r.z||0));
    if (z > 3.0) {
      if (now-st.lastTwist < 700) st.twistCount++; else st.twistCount=1;
      st.lastTwist=now;
      if (st.twistCount >= 2 && now-st.lastGesture > 800) {
        st.twistCount=0;
        this.motionGesture('DOUBLE TWIST','MEDIA_PLAY_PAUSE',90);
      }
    }
  },

  motionGesture(name, cmd, confidence) {
    if (confidence < 85) return;
    this.motionState.lastGesture=Date.now();
    this.featureData=name + ' ' + confidence + '%';
    this.message='GESTURE ' + name;
    this.haptic('short');
    this.sendCommand(cmd,{gesture:name,confidence:confidence});
  },

  openFeature(id) {
    var f=getFeature(id);
    if (!f) return;
    this.selectedId=String(id);
    this.selectedTitle=f.title;
    this.selectedSource=f.source;
    this.selectedDesc=f.desc;
    this.action1Label=f.actions[0]?f.actions[0].label:''; this.action1Command=f.actions[0]?f.actions[0].command:'';
    this.action2Label=f.actions[1]?f.actions[1].label:''; this.action2Command=f.actions[1]?f.actions[1].command:'';
    this.action3Label=f.actions[2]?f.actions[2].label:''; this.action3Command=f.actions[2]?f.actions[2].command:'';
    this.action4Label=f.actions[3]?f.actions[3].label:''; this.action4Command=f.actions[3]?f.actions[3].command:'';
    this.featureState='READY';
    this.featureData='-';
    this.message='MODULE READY';
    this.view='detail';
    this.haptic('short');
  },

  setCategory(c) {
    this.category=c;
    this.view='list';
    this.showControl=c==='CONTROL';
    this.showApps=c==='APPS';
    this.showSmart=c==='SMART';
    this.showNetwork=c==='NETWORK';
    this.showSystem=c==='SYSTEM';
  },

  goHome() {
    this.view='home';
    this.showControl=false; this.showApps=false; this.showSmart=false; this.showNetwork=false; this.showSystem=false;
    this.refreshBattery();
  },
  goList() { this.setCategory(this.category); },
  catControl() { this.setCategory('CONTROL'); },
  catApps() { this.setCategory('APPS'); },
  catSmart() { this.setCategory('SMART'); },
  catNetwork() { this.setCategory('NETWORK'); },
  catSystem() { this.setCategory('SYSTEM'); },

  quickLock() { this.sendCommand('PC_LOCK'); },
  quickMute() { this.sendCommand('MEDIA_MUTE'); },
  quickPlay() { this.sendCommand('MEDIA_PLAY_PAUSE'); },
  quickShot() { this.sendCommand('SCREENSHOT'); },
  detailAction1() { this.sendCommand(this.action1Command); },
  detailAction2() { this.sendCommand(this.action2Command); },
  detailAction3() { this.sendCommand(this.action3Command); },
  detailAction4() { this.sendCommand(this.action4Command); },

  swipeEvent(e) {
    if (e.direction == 'right') {
      if (this.view == 'home') app.terminate();
      else if (this.view == 'detail') this.goList();
      else this.goHome();
    }
  },

  f0(){this.openFeature('0');}, f1(){this.openFeature('1');}, f2(){this.openFeature('2');}, f3(){this.openFeature('3');},
  f4(){this.openFeature('4');}, f5(){this.openFeature('5');}, f6(){this.openFeature('6');}, f7(){this.openFeature('7');},
  f8(){this.openFeature('8');}, f9(){this.openFeature('9');}, f10(){this.openFeature('10');}, f11(){this.openFeature('11');},
  f12(){this.openFeature('12');}, f14(){this.openFeature('14');}, f15(){this.openFeature('15');}, f18(){this.openFeature('18');},
  f21(){this.openFeature('21');}, f23(){this.openFeature('23');}, f25(){this.openFeature('25');}, f26(){this.openFeature('26');},
  f31(){this.openFeature('31');}, f39(){this.openFeature('39');}
};
