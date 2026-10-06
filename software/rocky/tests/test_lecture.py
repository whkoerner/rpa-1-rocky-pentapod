"""Lecture/Class V0 bounded recording and deferred transcription tests."""

from io import BytesIO
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from rocky.lecture import LectureError, LectureSessionStore
from rocky.stt import MAX_WAV_BYTES


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

    def test_chunk_sequence_rejects_duplicate_and_out_of_order_retries(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        raw = wav_bytes()
        self.store.add_chunk(session, raw, index=1)
        with self.assertRaisesRegex(LectureError, "duplicate"):
            self.store.add_chunk(session, raw, index=1)
        with self.assertRaisesRegex(LectureError, "out-of-order"):
            self.store.add_chunk(session, raw, index=3)
        status = self.store.add_chunk(session, raw, index=2)
        self.assertEqual(status["chunk_count"], 2)

    def test_malformed_oversized_and_total_duration_limits_fail_closed(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        with self.assertRaises(LectureError):
            self.store.add_chunk(session, b"not-a-wave", index=1)
        with self.assertRaisesRegex(LectureError, "byte limit"):
            self.store.add_chunk(session, b"x" * (MAX_WAV_BYTES + 1), index=1)
        with patch("rocky.lecture.validate_voice_wav", side_effect=[599.5, 1.0]):
            self.store.add_chunk(session, b"RIFF-a", index=1)
            with self.assertRaisesRegex(LectureError, "maximum duration"):
                self.store.add_chunk(session, b"RIFF-b", index=2)

    def test_manifest_persists_and_interrupted_session_can_be_recovered(self):
        session = self.store.start(title="Recovery", consent_confirmed=True)["session_id"]
        self.store.add_chunk(session, wav_bytes(), index=1)
        reopened = LectureSessionStore(self.root, max_seconds=600, chunk_max_seconds=10)
        before = reopened.status(session)
        self.assertEqual(before["state"], "recording")
        recovered = reopened.recover_interrupted(session)
        self.assertEqual(recovered["state"], "recorded")
        self.assertTrue(recovered["recovered_interrupted"])
        with self.assertRaisesRegex(LectureError, "not interrupted"):
            reopened.recover_interrupted(session)

    def test_delete_requires_finalized_session_and_removes_only_session_directory(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        directory = self.store.session_directory(session)
        with self.assertRaisesRegex(LectureError, "before deletion"):
            self.store.delete(session)
        self.store.stop(session)
        result = self.store.delete(session)
        self.assertTrue(result["deleted"])
        self.assertFalse(directory.exists())
        with self.assertRaises(LectureError):
            self.store.status(session)

    def test_invalid_session_id_cannot_escape_root(self):
        with self.assertRaisesRegex(LectureError, "invalid lecture session id"):
            self.store.status("../../outside")

    @unittest.skipIf(os.name == "nt", "symlink creation is not reliable on Windows CI")
    def test_session_directory_symlink_is_rejected(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        original = self.root / session
        outside = self.root.parent / (session + "-outside")
        if outside.exists():
            shutil.rmtree(outside)
        shutil.move(str(original), str(outside))
        os.symlink(outside, original, target_is_directory=True)
        try:
            with self.assertRaisesRegex(LectureError, "directory.*unsafe"):
                self.store.status(session)
        finally:
            original.unlink(missing_ok=True)
            shutil.rmtree(outside, ignore_errors=True)

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

    def test_transcription_rejects_manifest_chunk_reordering(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        self.store.add_chunk(session, wav_bytes(), index=1)
        self.store.add_chunk(session, wav_bytes(), index=2)
        self.store.stop(session)
        directory = self.store.session_directory(session)
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["chunks"].reverse()
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(LectureError, "sequence"):
            self.store.transcribe(session, FakeTranscriber())

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

    def test_empty_recording_is_not_falsely_transcribed(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        self.store.stop(session)
        with self.assertRaisesRegex(LectureError, "no recorded audio"):
            self.store.transcribe(session, FakeTranscriber())

    def test_recording_must_stop_before_transcription(self):
        session = self.store.start(consent_confirmed=True)["session_id"]
        self.store.add_chunk(session, wav_bytes())
        with self.assertRaisesRegex(LectureError, "stop lecture"):
            self.store.transcribe(session, FakeTranscriber())


if __name__ == "__main__":
    unittest.main()
