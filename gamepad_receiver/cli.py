"""Command-line entry point: ``python -m gamepad_receiver``."""

from __future__ import annotations

import argparse
import asyncio
import functools
import logging
import sys

from . import __version__
from .controller import LoggingPad, VirtualPad
from .server import GamepadServer, lan_addresses, start_discovery

log = logging.getLogger("gamepad_receiver")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="gamepad-receiver",
        description="Turn phones into Xbox 360 controllers for this PC.",
    )
    p.add_argument("--host", default="0.0.0.0", help="address to listen on (default: all interfaces)")
    p.add_argument("--port", type=int, default=65432, help="TCP port for controllers (default: 65432)")
    p.add_argument("--players", type=int, default=4, choices=range(1, 5), metavar="1-4",
                   help="maximum phones connected at once, one virtual pad each (default: 4)")
    p.add_argument("--deadzone", type=float, default=0.08,
                   help="stick deadzone from 0 to 0.5 (default: 0.08)")
    p.add_argument("--discovery-port", type=int, default=65433,
                   help="UDP port for LAN auto-discovery (default: 65433)")
    p.add_argument("--no-discovery", action="store_true", help="don't answer LAN discovery probes")
    p.add_argument("--dry-run", action="store_true",
                   help="log inputs instead of driving a virtual controller (no driver needed)")
    p.add_argument("-v", "--verbose", action="store_true", help="log every input event")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)
    if not 0 <= args.deadzone <= 0.5:
        p.error("--deadzone must be between 0 and 0.5")
    return args


def make_pad_factory(args: argparse.Namespace):
    if args.dry_run:
        return functools.partial(LoggingPad, args.deadzone)
    try:
        import vgamepad  # noqa: F401
    except Exception as e:  # vgamepad raises a plain Exception when ViGEmBus is missing
        sys.exit(
            f"Could not load the virtual controller driver: {e}\n"
            "Install ViGEmBus (https://github.com/nefarius/ViGEmBus/releases) and run "
            "`pip install vgamepad`, or try --dry-run to test without it."
        )
    return functools.partial(VirtualPad.create, args.deadzone)


async def run(args: argparse.Namespace) -> None:
    server = GamepadServer(make_pad_factory(args), args.host, args.port, args.players)
    await server.start()

    print(f"\n  Gamepad Receiver {__version__}{'  [dry run]' if args.dry_run else ''}")
    for ip in lan_addresses() or ["<this PC's IP>"]:
        print(f"  Connect your phone to  {ip}:{server.port}")
    print(f"  Up to {args.players} controllers · Ctrl+C to stop\n")

    discovery = None
    if not args.no_discovery:
        try:
            discovery = await start_discovery(server.port, args.discovery_port)
        except OSError as e:
            log.warning("LAN discovery disabled: %s", e)

    try:
        await server.serve_forever()
    finally:
        if discovery is not None:
            discovery.close()


def main(argv=None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        sys.exit(f"Could not listen on port {args.port}: {e}")
