"""Wire protocol spoken by the phone controller.

The phone sends plain-text tokens over TCP, separated by whitespace:

    LeftJOY:<x>,<y>      left stick, x and y in [-1.0, 1.0]
    RightJOY:<x>,<y>     right stick
    button,<name>        press a button
    release,<name>       release a button

Button names are listed in ``BUTTONS`` and ``TRIGGERS``. TCP is a byte
stream, so several tokens can arrive in one read and a token can be split
across two reads. ``StreamParser`` takes care of both.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Union

log = logging.getLogger(__name__)

# Phone button name -> vgamepad XUSB_BUTTON attribute.
BUTTONS = {
    "aBtn": "XUSB_GAMEPAD_A",
    "bBtn": "XUSB_GAMEPAD_B",
    "xBtn": "XUSB_GAMEPAD_X",
    "yBtn": "XUSB_GAMEPAD_Y",
    "lbBtn": "XUSB_GAMEPAD_LEFT_SHOULDER",
    "rbBtn": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "lsBtn": "XUSB_GAMEPAD_LEFT_THUMB",
    "rsBtn": "XUSB_GAMEPAD_RIGHT_THUMB",
    "upDir": "XUSB_GAMEPAD_DPAD_UP",
    "downDir": "XUSB_GAMEPAD_DPAD_DOWN",
    "leftDir": "XUSB_GAMEPAD_DPAD_LEFT",
    "rightDir": "XUSB_GAMEPAD_DPAD_RIGHT",
    "startBtn": "XUSB_GAMEPAD_START",
    "backBtn": "XUSB_GAMEPAD_BACK",
}

# Triggers are analog on the Xbox pad; the phone sends them as buttons.
TRIGGERS = {"ltBtn": "left", "rtBtn": "right"}


@dataclass(frozen=True)
class Stick:
    side: str  # "left" or "right"
    x: float
    y: float


@dataclass(frozen=True)
class Button:
    name: str
    pressed: bool


@dataclass(frozen=True)
class Trigger:
    side: str  # "left" or "right"
    pressed: bool


Event = Union[Stick, Button, Trigger]

# Make sure every token starts on its own, even if the sender forgot a space.
_TOKEN_START = re.compile(r"(?=LeftJOY:|RightJOY:|button,|release,)")


def parse_token(token: str) -> Event | None:
    """Parse one token. Returns ``None`` if it is incomplete or unknown."""
    for prefix, side in (("LeftJOY:", "left"), ("RightJOY:", "right")):
        if token.startswith(prefix):
            try:
                x, y = (float(v) for v in token[len(prefix):].split(","))
            except ValueError:
                return None
            return Stick(side, x, y)

    action, _, name = token.partition(",")
    if action not in ("button", "release") or not name:
        return None
    pressed = action == "button"
    if name in TRIGGERS:
        return Trigger(TRIGGERS[name], pressed)
    if name in BUTTONS:
        return Button(name, pressed)
    return None


class StreamParser:
    """Turns raw socket text into events, buffering split tokens."""

    def __init__(self) -> None:
        self._pending = ""
        self.unknown_count = 0

    def feed(self, text: str) -> List[Event]:
        data = _TOKEN_START.sub(" ", self._pending + text)
        tokens = data.split()
        self._pending = ""

        # The last token may be cut off mid-read; hold it back if it
        # doesn't parse yet and there's no whitespace after it.
        if tokens and not data[-1].isspace() and parse_token(tokens[-1]) is None:
            self._pending = tokens.pop()

        events: List[Event] = []
        for token in tokens:
            event = parse_token(token)
            if event is None:
                self.unknown_count += 1
                log.debug("Ignoring unknown token %r", token)
            else:
                events.append(event)
        return events
