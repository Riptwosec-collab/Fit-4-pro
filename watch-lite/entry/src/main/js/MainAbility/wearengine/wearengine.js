// OFFLINE STUB. Replace with Huawei official Lite Wearable wearengine.js.
export class Builder{constructor(){this.description='';this.payload=null;}setDescription(v){this.description=v;}setPayload(v){this.payload=v;}}
export class Message{constructor(){this.builder=null;}getData(){return this.builder?this.builder.description:'';}}
export class P2pClient{setPeerPkgName(v){this.pkg=v;}setPeerFingerPrint(v){this.fp=v;}registerReceiver(cb){this.cb=cb;if(cb&&cb.onFailure)cb.onFailure();}unregisterReceiver(cb){if(cb&&cb.onSuccess)cb.onSuccess();}send(m,cb){if(cb&&cb.onFailure)cb.onFailure();}}
