#!/usr/bin/env python3
"""PC Remote Deck V8 Pro Agent bootstrap.

This file intentionally wraps the existing pc_agent.py instead of duplicating its
legacy action implementation. Existing V6/V7 commands continue through the original
execute() path; Pro actions are handled by pro_engine.ProEngine.
"""
import os
import sys
from http.server import ThreadingHTTPServer

import pc_agent as base
from pro_engine import ProEngine, NEW_ACTIONS

ENGINE = ProEngine(base)

# Preserve legacy behavior, then layer V8 behavior on top.
base.execute = ENGINE.execute
base.dashboard = ENGINE.dashboard_wrapper
base.notify = ENGINE.notify_proxy
base.ALLOWED.update(NEW_ACTIONS)
base.Handler.server_version = "PCRemoteDeck/8"


def main():
    if os.name != "nt":
        print("This agent is intended for Windows.", file=sys.stderr)
        return 2
    if base.CFG.get("token") == "CHANGE_ME":
        print("SECURITY STOP: run generate_token.py or pair_device.py first.")
        return 3

    ENGINE.event_bus.emit("PC_CONNECTED", {
        "agent": "PC Remote Deck V8 Pro",
        "host": os.environ.get("COMPUTERNAME", "WINDOWS-PC"),
    })
    base.notify("info", "Agent", "PC Remote Deck V8 Pro started")

    srv = ThreadingHTTPServer(
        (base.CFG.get("bind", "0.0.0.0"), int(base.CFG.get("port", 8765))),
        base.Handler,
    )
    print(
        f"PC Remote Deck V8 Pro agent listening on "
        f"{base.CFG.get('bind')}:{base.CFG.get('port')}"
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ENGINE.event_bus.emit("PC_DISCONNECTED", {"reason": "AGENT STOPPED"}, "WARNING")
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
