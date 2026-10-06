"""Bounded whisper.cpp sidecar tests; no real model or microphone required."""

from io import BytesIO
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import wave

from rocky.stt import (
    MAX_WAV_BYTES,
    SAMPLE_RATE,
    SpeechToTextError,
    WhisperCppTranscriber,
    validate_voice_wav,
)


def write_asset_manifest(path, cli, model, *, cli_sha=None, model_sha=None):
    cli_sha = cli_sha or hashlib.sha256(cli.read_bytes()).hexdigest()
    model_sha = model_sha or hashlib.sha256(model.read_bytes()).hexdigest()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manifest_id": "rocky-assets-v1",
                "assets": [
                    {
                        "id": "whisper_cli",
                        "kind": "file",
                        "required": False,
                        "reference": "fixture whisper-cli",
                        "path": str(cli),
                        "sha256": cli_sha,
                    },
                    {
                        "id": "whisper_model",
                        "kind": "file",
                        "required": False,
                        "reference": "fixture model",
                        "path": str(model),
                        "sha256": model_sha,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def wav_bytes(seconds=0.25, *, rate=SAMPLE_RATE, channels=1, width=2):
    frames = max(1, int(rate * seconds))
    raw = BytesIO()
    with wave.open(raw, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(b"\x00" * frames * channels * width)
    return raw.getvalue()


class FakeProcess:
    def __init__(self, argv, **kwargs):
        self.argv = argv
        self.kwargs = kwargs
        self.returncode = None
        self.terminated = False
        self.killed = False
        prefix = Path(argv[argv.index("-of") + 1])
        Path(str(prefix) + ".json").write_text(
            json.dumps(
                {
                    "transcription": [
                        {"text": " hello "},
                        {"text": "Rocky"},
                    ]
                }
            ),
            encoding="utf-8",
        )

    def communicate(self, timeout=None):
        self.returncode = 0
        return ("", "")

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


class SttValidationTests(unittest.TestCase):
    def test_valid_wav_contract_and_duration(self):
        self.assertAlmostEqual(validate_voice_wav(wav_bytes(0.5)), 0.5, places=2)

    def test_wrong_rate_channels_width_and_garbage_fail_closed(self):
        bad = (
            wav_bytes(rate=8000),
            wav_bytes(channels=2),
            wav_bytes(width=1),
            b"not a wav",
        )
        for raw in bad:
            with self.subTest(size=len(raw)), self.assertRaises(SpeechToTextError):
                validate_voice_wav(raw)

    def test_duration_and_byte_bounds(self):
        with self.assertRaisesRegex(SpeechToTextError, "capture limit"):
            validate_voice_wav(wav_bytes(1.2), max_seconds=1)
        with self.assertRaisesRegex(SpeechToTextError, "byte limit"):
            validate_voice_wav(b"x" * (MAX_WAV_BYTES + 1))

    def test_whisper_cli_uses_argv_without_shell_and_returns_no_fake_confidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cli = root / "whisper-cli;whoami"
            model = root / "model;rm-anything.bin"
            cli.touch()
            model.touch()
            created = []

            def factory(argv, **kwargs):
                process = FakeProcess(argv, **kwargs)
                created.append(process)
                return process

            transcriber = WhisperCppTranscriber(cli, model, max_seconds=2)
            with patch("rocky.stt.subprocess.Popen", side_effect=factory):
                result = transcriber.transcribe_wav(wav_bytes(0.25))

            self.assertEqual(result["text"], "hello Rocky")
            self.assertIsNone(result["confidence"])
            self.assertEqual(result["confidence_source"], "not_provided_by_bounded_whisper_cpp_adapter")
            self.assertEqual(len(created), 1)
            process = created[0]
            self.assertIs(process.kwargs["shell"], False)
            self.assertEqual(process.argv[0], str(cli))
            self.assertIn(str(model), process.argv)
            self.assertNotIn("sh", process.argv)
            self.assertNotIn("cmd.exe", process.argv)

    def test_enabled_stt_requires_matching_checksum_verified_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cli = root / "whisper-cli.exe"
            model = root / "model.bin"
            cli.write_bytes(b"reviewed-cli-fixture")
            model.write_bytes(b"reviewed-model-fixture")
            settings = {
                "stt_backend": "whisper-cpp",
                "whisper_cli_path": str(cli),
                "whisper_model_path": str(model),
                "stt_max_seconds": 30,
            }
            with self.assertRaisesRegex(SpeechToTextError, "asset manifest"):
                WhisperCppTranscriber.from_settings(settings)
            manifest = root / "assets.json"
            write_asset_manifest(manifest, cli, model)
            transcriber = WhisperCppTranscriber.from_settings(
                settings, asset_manifest=manifest
            )
            self.assertEqual(transcriber.cli_path, cli.resolve())
            self.assertEqual(transcriber.model_path, model.resolve())
            self.assertTrue(transcriber.check_available())

            cli.write_bytes(b"tampered-after-manifest")
            with self.assertRaisesRegex(SpeechToTextError, "checksum mismatch"):
                WhisperCppTranscriber.from_settings(settings, asset_manifest=manifest)

    def test_manifest_and_configured_stt_paths_must_agree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cli = root / "whisper-cli.exe"
            other_cli = root / "other-cli.exe"
            model = root / "model.bin"
            cli.write_bytes(b"cli")
            other_cli.write_bytes(b"other")
            model.write_bytes(b"model")
            manifest = root / "assets.json"
            write_asset_manifest(manifest, cli, model)
            settings = {
                "stt_backend": "whisper-cpp",
                "whisper_cli_path": str(other_cli),
                "whisper_model_path": str(model),
                "stt_max_seconds": 30,
            }
            with self.assertRaisesRegex(SpeechToTextError, "does not match"):
                WhisperCppTranscriber.from_settings(settings, asset_manifest=manifest)

    def test_paths_must_be_explicitly_provisioned(self):
        transcriber = WhisperCppTranscriber("missing-whisper-cli", "missing-model.bin")
        with self.assertRaisesRegex(SpeechToTextError, "not provisioned"):
            transcriber.check_available()

    def test_cancel_terminates_only_active_sidecar_process(self):
        transcriber = WhisperCppTranscriber("missing", "missing")
        process = FakeProcess.__new__(FakeProcess)
        process.returncode = None
        process.terminated = False
        process.killed = False
        process.poll = lambda: process.returncode

        def terminate():
            process.terminated = True
            process.returncode = -15

        process.terminate = terminate
        process.wait = lambda timeout=None: process.returncode
        process.kill = lambda: setattr(process, "killed", True)
        transcriber._process = process
        self.assertTrue(transcriber.cancel())
        self.assertTrue(process.terminated)
        self.assertFalse(process.killed)
        self.assertEqual(transcriber.status, "CANCELLED")

    def test_transcript_json_is_strict_and_bounded(self):
        with self.assertRaises(SpeechToTextError):
            WhisperCppTranscriber._extract_transcript({"transcription": [{"text": ""}]})
        with self.assertRaises(SpeechToTextError):
            WhisperCppTranscriber._extract_transcript({"transcription": "hello"})
        with self.assertRaises(SpeechToTextError):
            WhisperCppTranscriber._extract_transcript(
                {"transcription": [{"text": "x" * 5000}]}
            )


if __name__ == "__main__":
    unittest.main()
