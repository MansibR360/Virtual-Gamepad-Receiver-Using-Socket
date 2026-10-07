"""Pretend to be a phone controller, to test the receiver without the app.

    python tools/phone_simulator.py            # find the receiver on the LAN
    python tools/phone_simulator.py 192.168.1.20

Spins the left stick in a circle, taps A, B, X, Y, and pulls both triggers.
"""

import math
import socket
import sys
import time

DISCOVERY_PORT = 65433
DEFAULT_PORT = 65432


def discover(timeout: float = 2.0):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(b"GAMEPAD_RECEIVER_DISCOVER", ("255.255.255.255", DISCOVERY_PORT))
        try:
            data, (ip, _) = s.recvfrom(256)
        except socket.timeout:
            return None
    _, port, name = data.decode().split(" ", 2)
    print(f"Found receiver '{name}' at {ip}:{port}")
    return ip, int(port)


def main() -> None:
    if len(sys.argv) > 1:
        target = (sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT)
    else:
        target = discover() or ("127.0.0.1", DEFAULT_PORT)

    with socket.create_connection(target) as s:
        print(f"Connected to {target[0]}:{target[1]}")
        send = lambda msg: s.sendall(msg.encode())  # noqa: E731

        for i in range(120):
            angle = i / 120 * 2 * math.pi
            send(f"LeftJOY:{math.cos(angle):.3f},{math.sin(angle):.3f} ")
            time.sleep(1 / 60)
        send("LeftJOY:0,0 ")

        for name in ("aBtn", "bBtn", "xBtn", "yBtn", "ltBtn", "rtBtn"):
            send(f"button,{name} ")
            time.sleep(0.15)
            send(f"release,{name} ")
            time.sleep(0.1)
    print("Done.")


if __name__ == "__main__":
    main()
