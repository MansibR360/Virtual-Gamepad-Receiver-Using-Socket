import unittest

from gamepad_receiver.controller import apply_deadzone
from gamepad_receiver.protocol import Button, Stick, StreamParser, Trigger, parse_token


class ParseTokenTest(unittest.TestCase):
    def test_sticks(self):
        self.assertEqual(parse_token("LeftJOY:0.5,-0.25"), Stick("left", 0.5, -0.25))
        self.assertEqual(parse_token("RightJOY:-1,1"), Stick("right", -1.0, 1.0))

    def test_buttons_and_triggers(self):
        self.assertEqual(parse_token("button,aBtn"), Button("aBtn", True))
        self.assertEqual(parse_token("release,upDir"), Button("upDir", False))
        self.assertEqual(parse_token("button,rtBtn"), Trigger("right", True))

    def test_rejects_junk(self):
        for token in ("LeftJOY:0.5", "LeftJOY:a,b", "button,nope", "button,", "hello"):
            self.assertIsNone(parse_token(token), token)


class StreamParserTest(unittest.TestCase):
    def test_original_app_format(self):
        # The original app sends a trailing space after each command.
        parser = StreamParser()
        self.assertEqual(parser.feed("button,aBtn "), [Button("aBtn", True)])
        self.assertEqual(parser.feed("LeftJOY:0.1,0.2 "), [Stick("left", 0.1, 0.2)])

    def test_coalesced_reads(self):
        parser = StreamParser()
        events = parser.feed("LeftJOY:0.1,0.2 RightJOY:0.3,0.4 button,xBtn release,xBtn ")
        self.assertEqual(len(events), 4)

    def test_missing_separator(self):
        parser = StreamParser()
        events = parser.feed("button,aBtnrelease,aBtn")
        self.assertEqual(events, [Button("aBtn", True), Button("aBtn", False)])

    def test_token_split_across_reads(self):
        parser = StreamParser()
        self.assertEqual(parser.feed("button,aBtn LeftJOY:0.5"), [Button("aBtn", True)])
        self.assertEqual(parser.feed(",0.5 "), [Stick("left", 0.5, 0.5)])

    def test_unknown_tokens_are_counted_not_fatal(self):
        parser = StreamParser()
        self.assertEqual(parser.feed("garbage button,bBtn "), [Button("bBtn", True)])
        self.assertEqual(parser.unknown_count, 1)


class DeadzoneTest(unittest.TestCase):
    def test_inside_deadzone_is_centered(self):
        self.assertEqual(apply_deadzone(0.05, -0.03, 0.1), (0.0, 0.0))

    def test_full_tilt_stays_full(self):
        x, y = apply_deadzone(1.0, 0.0, 0.1)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 0.0)

    def test_out_of_range_is_clamped(self):
        x, y = apply_deadzone(3.0, 3.0, 0.0)
        self.assertLessEqual(x * x + y * y, 1.0 + 1e-9)


if __name__ == "__main__":
    unittest.main()
