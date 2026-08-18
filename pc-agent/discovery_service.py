#!/usr/bin/env python3
"""Local LAN discovery responder for PC Remote Deck V6.

This service never sends tokens or secrets. It only tells a Companion on the same LAN
that a PC Remote Deck agent is present and which command port it uses.
"""
import json, os, socket

DISCOVERY_PORT = 8766
MESSAGE = b"PC_REMOTE_DECK_DISCOVER_V6"
AGENT_PORT = 8765


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", DISCOVERY_PORT))
    print(f"PC Remote Deck discovery listening UDP {DISCOVERY_PORT}")
    while True:
        data, addr = s.recvfrom(2048)
        if data.strip() != MESSAGE:
            continue
        payload = json.dumps({
            "service": "PC_REMOTE_DECK_V6",
            "host": os.environ.get("COMPUTERNAME", "WINDOWS-PC"),
            "port": AGENT_PORT,
            "requiresPairing": True,
        }).encode("utf-8")
        s.sendto(payload, addr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
