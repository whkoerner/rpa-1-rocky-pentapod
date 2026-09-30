from pathlib import Path
import sys
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "software"))

from csp import CspCodec, DecodeError  # noqa: E402


class CspCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.codec = CspCodec.from_default_spec()

    def test_every_assigned_token_round_trips(self) -> None:
        tokens = list(self.codec.tokens())
        self.assertGreaterEqual(len(tokens), 100)
        for token in tokens:
            with self.subTest(token=token):
                encoded = self.codec.encode_token(token)
                decoded = self.codec.decode_token(encoded.notes)
                self.assertEqual(decoded.token, token)

    def test_known_hello_encoding(self) -> None:
        self.assertEqual(
            self.codec.encode_token("SOCIAL.hello").notes,
            ("E4", "A4", "D4", "D4", "Fsharp4"),
        )

    def test_checksum_failure_is_not_guessed(self) -> None:
        encoded = self.codec.encode_token("SOCIAL.hello")
        corrupted = encoded.notes[:-1] + ("B4",)
        with self.assertRaisesRegex(DecodeError, "Checksum mismatch"):
            self.codec.decode_token(corrupted)

    def test_unknown_prefix_is_not_guessed(self) -> None:
        with self.assertRaisesRegex(DecodeError, "Unknown or ambiguous class prefix"):
            self.codec.decode_token(("B4", "B4", "D4", "D4", "D4"))


if __name__ == "__main__":
    unittest.main()
