import asyncio
import unittest

from gamepad_receiver.protocol import Button, Stick
from gamepad_receiver.server import GamepadServer


class FakePad:
    def __init__(self):
        self.events = []
        self.updates = 0
        self.released = False

    def apply(self, event):
        self.events.append(event)

    def update(self):
        self.updates += 1

    def release_all(self):
        self.released = True


class ServerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pads = []

        def factory():
            pad = FakePad()
            self.pads.append(pad)
            return pad

        self.server = GamepadServer(factory, host="127.0.0.1", port=0, max_players=2)
        await self.server.start()

    async def asyncTearDown(self):
        await self.server.close()

    async def connect(self):
        return await asyncio.open_connection("127.0.0.1", self.server.port)

    async def settle(self):
        await asyncio.sleep(0.05)

    async def test_events_reach_the_pad(self):
        _, writer = await self.connect()
        writer.write(b"LeftJOY:0.5,0.5 button,aBtn ")
        await writer.drain()
        await self.settle()
        self.assertEqual(self.pads[0].events, [Stick("left", 0.5, 0.5), Button("aBtn", True)])
        writer.close()

    async def test_each_phone_gets_its_own_pad(self):
        _, w1 = await self.connect()
        _, w2 = await self.connect()
        await self.settle()
        self.assertEqual(len(self.pads), 2)
        self.assertEqual(sorted(self.server.players), [1, 2])
        w1.close()
        w2.close()

    async def test_extra_phone_is_rejected(self):
        conns = [await self.connect() for _ in range(3)]
        await self.settle()
        self.assertEqual(len(self.pads), 2)
        # The third connection is closed by the server.
        self.assertEqual(await asyncio.wait_for(conns[2][0].read(), 1), b"")
        for _, w in conns:
            w.close()

    async def test_disconnect_releases_everything(self):
        _, writer = await self.connect()
        writer.write(b"button,aBtn ")
        await writer.drain()
        await self.settle()
        writer.close()
        await self.settle()
        self.assertTrue(self.pads[0].released)
        self.assertEqual(self.server.players, {})


if __name__ == "__main__":
    unittest.main()
