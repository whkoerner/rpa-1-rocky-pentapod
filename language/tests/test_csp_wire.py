from pathlib import Path
import sys
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "software"))

from csp.wire import (  # noqa: E402
    INTENTS,
    WireError,
    WireMessage,
    canonical_text,
    chordic_token,
    decode,
    encode,
)


class CspWireTests(unittest.TestCase):
    def test_all_registered_intents_round_trip(self) -> None:
        for intent in INTENTS:
            with self.subTest(intent=intent):
                message = WireMessage(intent)
                self.assertEqual(decode(encode(message)), message)

    def test_exact_hello_encoding(self) -> None:
        self.assertEqual(encode(WireMessage("SOCIAL.HELLO")), "C1|SOCIAL.HELLO|\n")

    def test_canonical_translation_and_chordic_mapping(self) -> None:
        message = WireMessage("REQUEST.HELP")
        self.assertEqual(canonical_text(message), "Help.")
        self.assertEqual(chordic_token(message), "ACTION.help")

    def test_crlf_serial_line_is_accepted(self) -> None:
        self.assertEqual(decode("C1|RESPONSE.YES|\r\n"), WireMessage("RESPONSE.YES"))

    def test_wrong_version_is_rejected(self) -> None:
        with self.assertRaises(WireError) as caught:
            decode("C2|SOCIAL.HELLO|\n")
        self.assertEqual(caught.exception.code, "VERSION")

    def test_unknown_intent_is_rejected(self) -> None:
        with self.assertRaises(WireError) as caught:
            decode("C1|SOCIAL.HELO|\n")
        self.assertEqual(caught.exception.code, "INTENT")

    def test_lowercase_is_rejected(self) -> None:
        with self.assertRaises(WireError) as caught:
            decode("C1|social.hello|\n")
        self.assertEqual(caught.exception.code, "INTENT")

    def test_missing_field_is_rejected(self) -> None:
        with self.assertRaises(WireError) as caught:
            decode("C1|SOCIAL.HELLO\n")
        self.assertEqual(caught.exception.code, "FORMAT")

    def test_invalid_argument_is_rejected(self) -> None:
        with self.assertRaises(WireError) as caught:
            decode("C1|SOCIAL.HELLO|BAD ARG\n")
        self.assertEqual(caught.exception.code, "ARGUMENT")

    def test_nonempty_argument_is_rejected_in_v0_1(self) -> None:
        with self.assertRaises(WireError) as caught:
            decode("C1|SOCIAL.HELLO|LEFT\n")
        self.assertEqual(caught.exception.code, "ARGUMENT")

    def test_oversized_message_is_rejected(self) -> None:
        raw = "C1|SOCIAL.HELLO|" + ("A" * 60) + "\n"
        with self.assertRaises(WireError) as caught:
            decode(raw)
        self.assertEqual(caught.exception.code, "TOO_LONG")


if __name__ == "__main__":
    unittest.main()
