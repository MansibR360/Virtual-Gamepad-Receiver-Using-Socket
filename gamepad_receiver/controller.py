"""Drives a virtual Xbox 360 controller from protocol events."""

from __future__ import annotations

import logging
import math

from .protocol import BUTTONS, Button, Event, Stick, Trigger

log = logging.getLogger(__name__)


def apply_deadzone(x: float, y: float, deadzone: float) -> tuple[float, float]:
    """Radial deadzone: small stick drift reads as centered, and the rest of
    the range is rescaled so full tilt is still 1.0."""
    x = max(-1.0, min(1.0, x))
    y = max(-1.0, min(1.0, y))
    magnitude = math.hypot(x, y)
    if magnitude <= deadzone:
        return 0.0, 0.0
    if magnitude > 1.0:
        x, y, magnitude = x / magnitude, y / magnitude, 1.0
    scale = (magnitude - deadzone) / (1.0 - deadzone) / magnitude
    return x * scale, y * scale


class VirtualPad:
    """One virtual controller. Wraps a vgamepad ``VX360Gamepad``."""

    def __init__(self, gamepad, xusb_buttons, deadzone: float = 0.08) -> None:
        self._pad = gamepad
        self._buttons = {name: getattr(xusb_buttons, attr) for name, attr in BUTTONS.items()}
        self.deadzone = deadzone

    @classmethod
    def create(cls, deadzone: float = 0.08) -> "VirtualPad":
        import vgamepad as vg  # Windows + ViGEmBus only, so import lazily

        return cls(vg.VX360Gamepad(), vg.XUSB_BUTTON, deadzone)

    def apply(self, event: Event) -> None:
        if isinstance(event, Stick):
            x, y = apply_deadzone(event.x, event.y, self.deadzone)
            if event.side == "left":
                self._pad.left_joystick_float(x_value_float=x, y_value_float=y)
            else:
                self._pad.right_joystick_float(x_value_float=x, y_value_float=y)
        elif isinstance(event, Trigger):
            value = 255 if event.pressed else 0
            if event.side == "left":
                self._pad.left_trigger(value=value)
            else:
                self._pad.right_trigger(value=value)
        elif isinstance(event, Button):
            button = self._buttons[event.name]
            if event.pressed:
                self._pad.press_button(button=button)
            else:
                self._pad.release_button(button=button)

    def update(self) -> None:
        self._pad.update()

    def release_all(self) -> None:
        """Center the sticks and let go of everything, so nothing stays
        held in-game when the phone drops off the network."""
        self._pad.reset()
        self._pad.update()


class LoggingPad:
    """Stand-in for ``VirtualPad`` that only logs. Used by ``--dry-run``."""

    def __init__(self, deadzone: float = 0.08) -> None:
        self.deadzone = deadzone

    def apply(self, event: Event) -> None:
        if isinstance(event, Stick):
            x, y = apply_deadzone(event.x, event.y, self.deadzone)
            log.info("%s stick  x=%+.2f y=%+.2f", event.side, x, y)
        else:
            log.info("%s", event)

    def update(self) -> None:
        pass

    def release_all(self) -> None:
        log.info("released all inputs")
