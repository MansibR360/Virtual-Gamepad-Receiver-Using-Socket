"""TCP server: each connected phone gets its own virtual controller."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Callable, Dict, Optional

from .protocol import StreamParser

log = logging.getLogger(__name__)

DISCOVERY_REQUEST = b"GAMEPAD_RECEIVER_DISCOVER"
DISCOVERY_REPLY = "GAMEPAD_RECEIVER_HERE {port} {name}"


class GamepadServer:
    def __init__(
        self,
        pad_factory: Callable[[], object],
        host: str = "0.0.0.0",
        port: int = 65432,
        max_players: int = 4,
    ) -> None:
        self.pad_factory = pad_factory
        self.host = host
        self.port = port
        self.max_players = max_players
        self.players: Dict[int, object] = {}  # player slot -> pad
        self._server: Optional[asyncio.base_events.Server] = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        async with self._server:
            await self._server.serve_forever()

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    def _free_slot(self) -> Optional[int]:
        for slot in range(1, self.max_players + 1):
            if slot not in self.players:
                return slot
        return None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        slot = self._free_slot()
        if slot is None:
            log.warning("Rejected %s: all %d controller slots are in use", peer, self.max_players)
            writer.close()
            return

        pad = self.pad_factory()
        self.players[slot] = pad
        log.info("Player %d connected from %s:%s", slot, *peer[:2])

        parser = StreamParser()
        try:
            while data := await reader.read(1024):
                events = parser.feed(data.decode("utf-8", errors="ignore"))
                for event in events:
                    log.debug("P%d %s", slot, event)
                    pad.apply(event)
                if events:
                    pad.update()
        except (ConnectionError, OSError) as e:
            log.warning("Player %d connection lost: %s", slot, e)
        finally:
            pad.release_all()
            del self.players[slot]
            writer.close()
            log.info("Player %d disconnected", slot)


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """Answers LAN broadcast probes so a phone can find the PC without
    the user typing an IP address."""

    def __init__(self, tcp_port: int) -> None:
        self.reply = DISCOVERY_REPLY.format(port=tcp_port, name=socket.gethostname()).encode()

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if data.strip() == DISCOVERY_REQUEST:
            self.transport.sendto(self.reply, addr)
            log.debug("Answered discovery probe from %s", addr[0])


async def start_discovery(tcp_port: int, udp_port: int) -> asyncio.DatagramTransport:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _DiscoveryProtocol(tcp_port), local_addr=("0.0.0.0", udp_port)
    )
    return transport


def lan_addresses() -> list[str]:
    """Best-effort list of this PC's LAN IPv4 addresses, for the banner."""
    addresses = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is sent
            addresses.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(info[4][0])
    except OSError:
        pass
    return sorted(a for a in addresses if not a.startswith("127."))
