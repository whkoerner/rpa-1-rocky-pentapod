"""Lecture/Class V0 bounded recording and deferred transcription tests."""

from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import wave

from rocky.lecture import LectureError, LectureSessionStore


def wav_bytes(seconds=0.1):
    frames = max(1, round(16000 * seconds))
    out = BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * frames)
    return out.getvalue()


class FakeTranscriber:
    def __init__(self):
        self.calls = 0

    def transcribe_wav(self, raw):
        self.calls += 1
        return {
            "text": f"lecture segment {self.calls}",
            "audio_seconds": 0.1,
            "confidence": None,
            "confidence_source": "fixture",
        }


class LectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = LectureSessionStore(
            self.root, max_seconds=600, chunk_max_seconds=10
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_start_requires_explicit_permission_confirmation(self):
        with self.assertRaisesRegex(LectureError, "permission/consent"):
            self.store.start(title="Class", consent_confirmed=False)
        status = self.store.start(title="Class", consent_confirmed=True)
        self.assertEqual(status["state"], "recording")
        self.assertEqual(status["title"], "Class")
        self.assertTrue(status["session_id"].startswith("lecture-"))

    def test_chunk_storage_is_bounded_manifested_and_stoppable(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        raw = wav_bytes()
        first = self.store.add_chunk(session, raw)
        second = self.store.add_chunk(session, raw)
        self.assertEqual(first["chunk_count"], 1)
        self.assertEqual(second["chunk_count"], 2)
        self.assertAlmostEqual(second["total_seconds"], 0.2, places=2)
        stopped = self.store.stop(session)
        self.assertEqual(stopped["state"], "recorded")
        directory = self.store.session_directory(session)
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(len(manifest["chunks"]), 2)
        self.assertEqual(len(manifest["chunks"][0]["sha256"]), 64)
        with self.assertRaisesRegex(LectureError, "not recording"):
            self.store.add_chunk(session, raw)

    def test_invalid_session_id_cannot_escape_root(self):
        with self.assertRaisesRegex(LectureError, "invalid lecture session id"):
            self.store.status("../../outside")

    def test_deferred_transcription_has_timestamps_and_local_outputs(self):
        session = self.store.start(title="Physics", consent_confirmed=True)["session_id"]
        self.store.add_chunk(session, wav_bytes())
        self.store.add_chunk(session, wav_bytes())
        self.store.stop(session)
        transcriber = FakeTranscriber()
        result = self.store.transcribe(session, transcriber)
        self.assertEqual(result["segments"], 2)
        self.assertEqual(transcriber.calls, 2)
        directory = self.store.session_directory(session)
        payload = json.loads((directory / "transcript.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["segments"][0]["start_seconds"], 0.0)
        self.assertAlmostEqual(payload["segments"][0]["end_seconds"], 0.1, places=2)
        self.assertAlmostEqual(payload["segments"][1]["start_seconds"], 0.1, places=2)
        text = (directory / "transcript.txt").read_text(encoding="utf-8")
        self.assertIn("lecture segment 1", text)
        self.assertIn("lecture segment 2", text)
        self.assertEqual(self.store.status(session)["state"], "transcribed")

    def test_transcription_detects_chunk_tampering(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        self.store.add_chunk(session, wav_bytes())
        self.store.stop(session)
        directory = self.store.session_directory(session)
        chunk = directory / "chunk-00001.wav"
        raw = bytearray(chunk.read_bytes())
        raw[-1] ^= 1
        chunk.write_bytes(bytes(raw))
        with self.assertRaisesRegex(LectureError, "checksum mismatch"):
            self.store.transcribe(session, FakeTranscriber())

    def test_recording_must_stop_before_transcription(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        self.store.add_chunk(session, wav_bytes())
        with self.assertRaisesRegex(LectureError, "stop lecture"):
            self.store.transcribe(session, FakeTranscriber())


if __name__ == "__main__":
    unittest.main()
