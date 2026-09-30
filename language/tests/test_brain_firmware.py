from pathlib import Path
import re
import sys
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "software"))

from csp import CspCodec  # noqa: E402


class BrainFirmwareLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.codec = CspCodec.from_default_spec()
        cls.firmware = (
            REPOSITORY_ROOT
            / "firmware"
            / "rocky_brain_v0_1"
            / "rocky_brain_v0_1.ino"
        ).read_text(encoding="utf-8")

    def firmware_notes(self, array_name: str) -> tuple[str, ...]:
        match = re.search(
            rf"const NoteEvent {array_name}\[\] PROGMEM = \{{(.*?)\}};",
            self.firmware,
            re.DOTALL,
        )
        self.assertIsNotNone(match, f"Missing firmware array {array_name}")
        return tuple(re.findall(r"\{NOTE_([A-Z0-9]+),", match.group(1)))

    @staticmethod
    def macro_note(note: str) -> str:
        return note.replace("Fsharp", "FS").upper()

    def expected_notes(self, tokens: list[str]) -> tuple[str, ...]:
        return tuple(
            self.macro_note(note)
            for token in tokens
            for note in self.codec.encode_token(token).notes
        )

    def test_firmware_phrases_match_csp_specification(self) -> None:
        cases = {
            "NOTES_HELLO": ["SOCIAL.hello"],
            "NOTES_YES": ["SOCIAL.yes"],
            "NOTES_NO": ["SOCIAL.no"],
            "NOTES_THANK_YOU": ["SOCIAL.thank_you"],
            "NOTES_AMAZE": ["SOCIAL.amaze"],
            "NOTES_PLEASE_REPEAT": [
                "GRAM.imperative",
                "SOCIAL.please",
                "ACTION.repeat",
            ],
            "NOTES_NOT_UNDERSTOOD": [
                "GRAM.declarative",
                "GRAM.negation",
                "ACTION.understand",
                "GRAM.agent_role",
                "ENTITY.self",
            ],
            "NOTES_STOP": ["SAFETY.warning", "SAFETY.stop_now"],
        }
        for array_name, tokens in cases.items():
            with self.subTest(array_name=array_name):
                self.assertEqual(
                    self.firmware_notes(array_name), self.expected_notes(tokens)
                )


if __name__ == "__main__":
    unittest.main()
