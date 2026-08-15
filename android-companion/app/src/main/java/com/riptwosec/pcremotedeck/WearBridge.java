package com.riptwosec.pcremotedeck;

import android.content.Context;
import java.nio.charset.StandardCharsets;
import java.util.List;
import com.huawei.hmf.tasks.OnFailureListener;
import com.huawei.hmf.tasks.OnSuccessListener;
import com.huawei.wearengine.HiWear;
import com.huawei.wearengine.auth.AuthCallback;
import com.huawei.wearengine.auth.Permission;
import com.huawei.wearengine.device.Device;
import com.huawei.wearengine.device.DeviceClient;
import com.huawei.wearengine.p2p.Message;
import com.huawei.wearengine.p2p.P2pClient;
import com.huawei.wearengine.p2p.Receiver;
import com.huawei.wearengine.p2p.SendCallback;

public final class WearBridge {
    public interface Listener { void onStatus(String status); void onMessage(String json); }
    private final Context context;
    private final Listener listener;
    private final P2pClient p2pClient;
    private final DeviceClient deviceClient;
    private Device connectedDevice;
    private boolean receiverRegistered;

    public WearBridge(Context context, Listener listener) {
        this.context = context;
        this.listener = listener;
        this.p2pClient = HiWear.getP2pClient(context);
        this.deviceClient = HiWear.getDeviceClient(context);
        p2pClient.setPeerPkgName(BuildConfig.WATCH_PACKAGE);
        p2pClient.setPeerFingerPrint(BuildConfig.WATCH_FINGERPRINT);
    }

    public void requestAuthorization() {
        HiWear.getAuthClient(context).requestPermission(new AuthCallback() {
            @Override public void onOk(Permission[] permissions) {
                status("WEAR ENGINE AUTHORIZED");
                discoverConnectedWatch();
            }
            @Override public void onCancel() { status("WEAR ENGINE AUTH CANCELED"); }
        }, Permission.DEVICE_MANAGER);
    }

    public void discoverConnectedWatch() {
        deviceClient.getBondedDevices()
            .addOnSuccessListener(new OnSuccessListener<List<Device>>() {
                @Override public void onSuccess(List<Device> devices) {
                    connectedDevice = null;
                    if (devices != null) {
                        for (Device d : devices) if (d != null && d.isConnected()) { connectedDevice = d; break; }
                    }
                    if (connectedDevice != null) {
                        status("WATCH CONNECTED");
                        registerReceiver();
                    } else status("NO CONNECTED HUAWEI WATCH");
                }
            })
            .addOnFailureListener(new OnFailureListener() {
                @Override public void onFailure(Exception e) { status("WATCH DISCOVERY ERROR: " + e.getMessage()); }
            });
    }

    private final Receiver receiver = new Receiver() {
        @Override public void onReceiveMessage(Message message) {
            if (message == null || message.getData() == null) return;
            String json = new String(message.getData(), StandardCharsets.UTF_8);
            if (listener != null) listener.onMessage(json);
        }
    };

    public void registerReceiver() {
        if (receiverRegistered) return;
        if (connectedDevice == null) { status("WATCH OFFLINE"); return; }
        try {
            p2pClient.registerReceiver(connectedDevice, receiver)
                .addOnSuccessListener(new OnSuccessListener<Void>() { @Override public void onSuccess(Void v) { receiverRegistered = true; status("WATCH RECEIVER READY"); } })
                .addOnFailureListener(new OnFailureListener() { @Override public void onFailure(Exception e) { status("RECEIVER ERROR: " + e.getMessage()); } });
        } catch (Exception e) { status("RECEIVER ERROR: " + e.getMessage()); }
    }

    public void unregister() {
        if (!receiverRegistered) return;
        try { p2pClient.unregisterReceiver(receiver); } catch (Exception ignored) {}
        receiverRegistered = false;
    }

    public void sendJson(String json) {
        if (connectedDevice == null) { status("WATCH OFFLINE"); return; }
        Message.Builder b = new Message.Builder();
        b.setPayload(json.getBytes(StandardCharsets.UTF_8));
        Message m = b.build();
        p2pClient.send(connectedDevice, m, new SendCallback() {
            @Override public void onSendResult(int resultCode) {
                status(resultCode == 207 ? "WATCH SYNC OK" : "WATCH SEND CODE " + resultCode);
            }
            @Override public void onSendProgress(long progress) { }
        }).addOnFailureListener(new OnFailureListener() { @Override public void onFailure(Exception e) { status("WATCH SEND FAILED: " + e.getMessage()); } });
    }

    private void status(String s) { if (listener != null) listener.onStatus(s); }
}
