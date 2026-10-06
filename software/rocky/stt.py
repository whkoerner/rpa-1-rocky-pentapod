"""Bounded local speech-to-text sidecar for Rocky.

The STT process receives a finite validated WAV file and returns text only. It has
no BrainController, hardware interface, tool authority, or motor path.
"""

from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import wave

from .portability import PortabilityError, load_asset_manifest, sha256_file


SAMPLE_RATE = 16000
MAX_WAV_BYTES = 2_100_000
MAX_TRANSCRIPT_BYTES = 4096


class SpeechToTextError(ValueError):
    pass


def validate_voice_wav(raw: object, *, max_seconds: float = 30.0) -> float:
    """Validate the exact browser/sidecar audio contract and return duration."""
    if type(raw) is not bytes or not raw:
        raise SpeechToTextError("voice input must be nonempty WAV bytes")
    if len(raw) > MAX_WAV_BYTES:
        raise SpeechToTextError("voice WAV exceeds safe byte limit")
    if type(max_seconds) not in (int, float) or not 1 <= float(max_seconds) <= 60:
        raise SpeechToTextError("STT max seconds must be between 1 and 60")
    try:
        with wave.open(BytesIO(raw), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
            compression = handle.getcomptype()
    except (wave.Error, EOFError) as exc:
        raise SpeechToTextError("voice input must be a valid PCM WAV") from exc
    if channels != 1:
        raise SpeechToTextError("voice WAV must be mono")
    if width != 2:
        raise SpeechToTextError("voice WAV must use 16-bit PCM")
    if rate != SAMPLE_RATE:
        raise SpeechToTextError(f"voice WAV must use {SAMPLE_RATE} Hz")
    if compression != "NONE":
        raise SpeechToTextError("voice WAV must be uncompressed PCM")
    if frames <= 0:
        raise SpeechToTextError("voice WAV contains no samples")
    duration = frames / rate
    if duration > float(max_seconds) + (1.0 / rate):
        raise SpeechToTextError(
            f"voice WAV exceeds {float(max_seconds):g} second capture limit"
        )
    return duration


def _strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SpeechToTextError("duplicate STT JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise SpeechToTextError("non-finite STT JSON value")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


def _verified_manifest_asset(manifest_path: Path, asset_id: str, configured_path: object) -> Path:
    """Resolve one checksum-pinned STT file and require config/manifest agreement."""
    manifest_path = Path(manifest_path).expanduser()
    try:
        manifest = load_asset_manifest(manifest_path)
    except PortabilityError as exc:
        raise SpeechToTextError(f"STT asset manifest is invalid: {exc}") from exc
    matches = [asset for asset in manifest["assets"] if asset["id"] == asset_id]
    if len(matches) != 1 or matches[0]["kind"] != "file":
        raise SpeechToTextError(f"STT asset manifest requires one file asset named {asset_id}")
    asset = matches[0]
    if not asset["path"] or not asset["sha256"]:
        raise SpeechToTextError(f"STT asset {asset_id} is not provisioned in the asset manifest")
    target = Path(asset["path"]).expanduser()
    if not target.is_absolute():
        target = manifest_path.parent / target
    if target.is_symlink() or not target.is_file():
        raise SpeechToTextError(f"STT asset {asset_id} is missing or unsafe")
    actual = sha256_file(target)
    if actual != asset["sha256"]:
        raise SpeechToTextError(f"STT asset {asset_id} checksum mismatch")
    if type(configured_path) is not str or not configured_path.strip():
        raise SpeechToTextError(f"configured path for {asset_id} is missing")
    configured = Path(configured_path).expanduser()
    if configured.is_symlink() or not configured.is_file():
        raise SpeechToTextError(f"configured path for {asset_id} is missing or unsafe")
    try:
        same = os.path.normcase(str(configured.resolve())) == os.path.normcase(str(target.resolve()))
    except OSError as exc:
        raise SpeechToTextError(f"could not resolve STT asset {asset_id}") from exc
    if not same:
        raise SpeechToTextError(f"configured path for {asset_id} does not match verified asset manifest")
    return target.resolve()


class WhisperCppTranscriber:
    """Explicitly provisioned whisper.cpp CLI adapter.

    No executable/model is downloaded by Rocky. The child is invoked with an
    argv list and shell=False. Cancellation terminates the active child.
    """

    def __init__(
        self,
        cli_path: Path | str,
        model_path: Path | str,
        *,
        max_seconds: float = 30.0,
        timeout_seconds: float = 90.0,
    ):
        self.cli_path = Path(cli_path).expanduser()
        self.model_path = Path(model_path).expanduser()
        if type(max_seconds) not in (int, float) or not 1 <= float(max_seconds) <= 60:
            raise SpeechToTextError("STT max seconds must be between 1 and 60")
        if type(timeout_seconds) not in (int, float) or not 5 <= float(timeout_seconds) <= 300:
            raise SpeechToTextError("STT timeout must be between 5 and 300 seconds")
        self.max_seconds = float(max_seconds)
        self.timeout_seconds = float(timeout_seconds)
        self._lock = threading.RLock()
        self._process = None
        self.status = "IDLE"
        self.last_duration_seconds = 0.0
        self.last_transcript = ""

    @classmethod
    def from_settings(cls, settings: dict, *, asset_manifest: Path | str | None = None):
        backend = settings.get("stt_backend", "disabled")
        if backend == "disabled":
            return None
        if backend != "whisper-cpp":
            raise SpeechToTextError("unsupported STT backend")
        if asset_manifest is None:
            raise SpeechToTextError(
                "whisper.cpp requires an explicit checksum-verified asset manifest"
            )
        cli_path = _verified_manifest_asset(
            Path(asset_manifest), "whisper_cli", settings.get("whisper_cli_path", "")
        )
        model_path = _verified_manifest_asset(
            Path(asset_manifest), "whisper_model", settings.get("whisper_model_path", "")
        )
        return cls(
            cli_path,
            model_path,
            max_seconds=settings.get("stt_max_seconds", 30),
        )

    def check_available(self):
        if self.cli_path.is_symlink() or self.model_path.is_symlink():
            raise SpeechToTextError("whisper.cpp executable/model paths must not be symbolic links")
        if not str(self.cli_path) or not self.cli_path.is_file():
            raise SpeechToTextError(
                "whisper-cli executable is not provisioned at the configured path"
            )
        if not str(self.model_path) or not self.model_path.is_file():
            raise SpeechToTextError(
                "Whisper model is not provisioned at the configured path"
            )
        return True

    def cancel(self):
        with self._lock:
            process = self._process
            if process is None:
                return False
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            self.status = "CANCELLED"
            return True

    @staticmethod
    def _extract_transcript(payload: object) -> str:
        if type(payload) is not dict:
            raise SpeechToTextError("whisper-cli JSON must be an object")
        rows = payload.get("transcription")
        if type(rows) is not list or len(rows) > 256:
            raise SpeechToTextError("whisper-cli JSON has invalid transcription rows")
        pieces = []
        for row in rows:
            if type(row) is not dict:
                raise SpeechToTextError("whisper-cli transcription row is invalid")
            text = row.get("text")
            if type(text) is not str:
                raise SpeechToTextError("whisper-cli transcription row lacks text")
            pieces.append(text.strip())
        transcript = " ".join(piece for piece in pieces if piece).strip()
        if not transcript:
            raise SpeechToTextError("speech recognizer returned an empty transcript")
        if len(transcript.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
            raise SpeechToTextError("speech transcript exceeds safe size limit")
        if "\x00" in transcript or any(
            ord(char) < 32 and char not in ("\n", "\t") for char in transcript
        ):
            raise SpeechToTextError("speech transcript contains control characters")
        return transcript

    def transcribe_wav(self, raw: bytes) -> dict:
        duration = validate_voice_wav(raw, max_seconds=self.max_seconds)
        self.check_available()
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise SpeechToTextError("speech transcription is already running")
            self.status = "TRANSCRIBING"
        try:
            with tempfile.TemporaryDirectory(prefix="rocky-stt-") as temp:
                root = Path(temp)
                wav_path = root / "input.wav"
                output_prefix = root / "result"
                wav_path.write_bytes(raw)
                argv = [
                    str(self.cli_path),
                    "-m",
                    str(self.model_path),
                    "-f",
                    str(wav_path),
                    "-l",
                    "en",
                    "-oj",
                    "-of",
                    str(output_prefix),
                    "-np",
                    "-nt",
                ]
                with self._lock:
                    self._process = subprocess.Popen(
                        argv,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        shell=False,
                    )
                    process = self._process
                try:
                    stdout, stderr = process.communicate(timeout=self.timeout_seconds)
                except subprocess.TimeoutExpired as exc:
                    self.cancel()
                    raise SpeechToTextError("speech transcription timed out") from exc
                if process.returncode:
                    detail = (stderr or stdout or "").strip().replace("\r", " ").replace("\n", " ")
                    if len(detail) > 500:
                        detail = detail[-500:]
                    raise SpeechToTextError(
                        "whisper-cli failed" + (": " + detail if detail else "")
                    )
                result_path = Path(str(output_prefix) + ".json")
                if not result_path.is_file() or result_path.stat().st_size > 128 * 1024:
                    raise SpeechToTextError("whisper-cli did not produce bounded JSON output")
                payload = _strict_json(result_path.read_text(encoding="utf-8"))
                transcript = self._extract_transcript(payload)
        finally:
            with self._lock:
                self._process = None
        with self._lock:
            self.status = "COMPLETED"
            self.last_duration_seconds = duration
            self.last_transcript = transcript
        return {
            "text": transcript,
            "audio_seconds": round(duration, 3),
            "confidence": None,
            "confidence_source": "not_provided_by_bounded_whisper_cpp_adapter",
        }
