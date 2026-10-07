# Virtual Gamepad Receiver

[![tests](https://github.com/MansibR360/Virtual-Gamepad-Receiver-Using-Socket/actions/workflows/tests.yml/badge.svg)](https://github.com/MansibR360/Virtual-Gamepad-Receiver-Using-Socket/actions/workflows/tests.yml)

**Turn any phone into an Xbox 360 controller for your PC, over Wi-Fi.**

The receiver runs on a Windows PC and listens for joystick and button input from a phone app. It drives a real virtual XInput controller, so every game and emulator that supports an Xbox pad works without any changes. It was originally built as the controller backend for [Project MAYA](https://mansibyasir.cloud/maya/), my Android cloud-gaming platform.

```
 ┌──────────────┐   TCP :65432    ┌──────────────────────┐   ViGEmBus    ┌─────────┐
 │  Phone app   │ ──────────────▶ │  gamepad_receiver    │ ────────────▶ │  Game   │
 │  (on-screen  │  "LeftJOY:…"    │  parse → deadzone →  │  virtual X360 │ (XInput)│
 │   gamepad)   │  "button,aBtn"  │  one pad per player  │  controller   │         │
 └──────────────┘ ◀────────────── └──────────────────────┘               └─────────┘
                   UDP :65433 auto-discovery
```

## Features

- **Up to 4 players:** each connected phone gets its own virtual controller, like plugging in four pads
- **Full Xbox layout:** both sticks, A/B/X/Y, bumpers, triggers, stick clicks, D-pad, Start and Back
- **Safe disconnects:** if a phone drops off Wi-Fi, all its buttons are released and sticks re-centered, so your character doesn't keep running
- **Radial deadzone:** removes thumb drift without losing full-tilt range
- **LAN auto-discovery:** phones can find the PC with a UDP broadcast instead of typing an IP address
- **Robust stream parsing:** handles TCP packets that merge or split commands
- **Dry-run mode:** test everything without installing the controller driver
- **Phone simulator:** a script that acts as a phone for testing

## Requirements

- Windows 10 or 11
- Python 3.9+
- [ViGEmBus driver](https://github.com/nefarius/ViGEmBus/releases) (the `vgamepad` installer can also set it up)

## Quick start

```bash
git clone https://github.com/MansibR360/Virtual-Gamepad-Receiver-Using-Socket.git
cd Virtual-Gamepad-Receiver-Using-Socket
pip install -r requirements.txt
python -m gamepad_receiver
```

```
  Gamepad Receiver 2.0.0
  Connect your phone to  192.168.1.20:65432
  Up to 4 controllers · Ctrl+C to stop
```

Point the phone app at the address shown. Make sure Windows Firewall allows Python on private networks.

### Options

| Flag | Default | Description |
|---|---|---|
| `--port` | `65432` | TCP port for controllers |
| `--players` | `4` | Maximum phones at once (1–4) |
| `--deadzone` | `0.08` | Stick deadzone, 0–0.5 |
| `--discovery-port` | `65433` | UDP port for auto-discovery |
| `--no-discovery` | off | Don't answer discovery probes |
| `--dry-run` | off | Log inputs instead of driving a controller |
| `-v`, `--verbose` | off | Log every input event |

### Try it without a phone

```bash
python -m gamepad_receiver --dry-run
python tools/phone_simulator.py        # in a second terminal
```

The simulator finds the receiver on your network, spins the left stick in a circle, taps the face buttons and pulls both triggers.

## Protocol

Any client can drive the receiver by sending whitespace-separated text tokens over TCP:

| Token | Meaning |
|---|---|
| `LeftJOY:<x>,<y>` | Left stick, `x` and `y` in `-1.0 … 1.0` |
| `RightJOY:<x>,<y>` | Right stick |
| `button,<name>` | Press a button |
| `release,<name>` | Release a button |

Button names: `aBtn` `bBtn` `xBtn` `yBtn` `lbBtn` `rbBtn` `ltBtn` `rtBtn` `lsBtn` `rsBtn` `upDir` `downDir` `leftDir` `rightDir` `startBtn` `backBtn`

**Discovery:** broadcast `GAMEPAD_RECEIVER_DISCOVER` to UDP port 65433. The receiver replies with `GAMEPAD_RECEIVER_HERE <tcp-port> <pc-name>`.

## Project structure

```
gamepad_receiver/
├── protocol.py     # Token parser and stream buffering
├── controller.py   # Virtual Xbox pad, deadzone, release-on-disconnect
├── server.py       # Async TCP server, player slots, UDP discovery
└── cli.py          # Command-line interface
tools/phone_simulator.py
tests/              # Parser, deadzone and multi-player server tests
```

## Development

```bash
python -m unittest discover -s tests -t .
```

The tests use a fake controller, so they run anywhere, with no driver needed.

## License

[MIT](LICENSE) © Mansib Yasir
