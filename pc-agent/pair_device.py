#!/usr/bin/env python3
"""Generate a local one-phone pairing URI/QR for PC Remote Deck.

Security behavior:
- Ensures agent_config.json has a strong random token.
- `--rotate` replaces the current token, invalidating the previous phone credential.
- The QR contains the LAN host/port and secret token. Treat the QR as a password and delete it after pairing.
- No credential is uploaded anywhere.
"""
import argparse, json, pathlib, secrets, socket
from urllib.parse import urlencode

ROOT = pathlib.Path(__file__).resolve().parent
CFG_PATH = ROOT / "agent_config.json"
QR_PATH = ROOT / "pairing_qr.png"


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


def load_cfg():
    if CFG_PATH.exists():
        try:
            return json.loads(CFG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"bind":"0.0.0.0","port":8765,"token":"CHANGE_ME","max_clock_skew_seconds":30}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rotate", action="store_true", help="Rotate the credential and invalidate the previous phone link")
    ap.add_argument("--host", default="", help="Override LAN IP/hostname embedded in the pairing URI")
    args = ap.parse_args()

    cfg = load_cfg()
    if args.rotate or not cfg.get("token") or cfg.get("token") == "CHANGE_ME":
        cfg["token"] = secrets.token_urlsafe(32)
    cfg.setdefault("bind", "0.0.0.0")
    cfg.setdefault("port", 8765)
    cfg.setdefault("max_clock_skew_seconds", 30)
    CFG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    host = args.host.strip() or local_ip()
    uri = "pcremotedeck://pair?" + urlencode({"host":host,"port":int(cfg.get("port",8765)),"token":cfg["token"],"profile":"primary-phone"})
    print("PAIRING URI (SECRET):")
    print(uri)
    try:
        import qrcode
        qrcode.make(uri).save(QR_PATH)
        print(f"QR created: {QR_PATH}")
        print("Delete pairing_qr.png after pairing.")
    except Exception:
        print("Optional QR image not created. Install with: pip install qrcode[pil]")
        print("You can still encode the URI above into a QR locally.")


if __name__ == "__main__":
    main()
