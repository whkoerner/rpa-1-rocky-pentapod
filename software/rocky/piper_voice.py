"""Optional token-authenticated loopback Piper neural TTS renderer.

Piper and its voice model live in a separate sidecar environment. Rocky never
downloads a voice at runtime and never imports Piper into the core environment.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
import wave
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from .speech import classify_prosody


MAX_PIPER_WAV_BYTES = 12 * 1024 * 1024
_RATE_SCALE = {-2: 1.30, -1: 1.15, 0: 1.0, 1: 0.88, 2: 0.76}
_VOLUME_SCALE = {-2: 0.65, -1: 0.82, 0: 1.0, 1: 1.15, 2: 1.30}
_PROFILE_RATE = {
    "question": 0.96,
    "excitement": 0.86,
    "reassurance": 1.14,
    "technical": 1.02,
    "neutral": 1.0,
}
_PROFILE_VOLUME = {
    "question": 1.0,
    "excitement": 1.08,
    "reassurance": 0.88,
    "technical": 0.98,
    "neutral": 1.0,
}


class PiperSidecarError(RuntimeError):
    pass


def _strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PiperSidecarError("duplicate Piper JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise PiperSidecarError("non-finite Piper JSON number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


def _validated_token(path: Path) -> str:
    path = Path(path).expanduser()
    if not path.is_file() or path.is_symlink():
        raise PiperSidecarError("Piper sidecar token file is not provisioned safely")
    token = path.read_text(encoding="utf-8").strip()
    if (
        not 32 <= len(token) <= 256
        or not token.isascii()
        or any(char.isspace() for char in token)
    ):
        raise PiperSidecarError("Piper sidecar token is invalid")
    return token


def _wav_duration(raw: bytes) -> float:
    if type(raw) is not bytes or not raw or len(raw) > MAX_PIPER_WAV_BYTES:
        raise PiperSidecarError("Piper WAV exceeds safe size")
    try:
        with wave.open(BytesIO(raw), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
    except wave.Error as exc:
        raise PiperSidecarError("Piper sidecar returned invalid WAV audio") from exc
    if channels != 1 or width != 2 or not 8000 <= rate <= 48000 or frames <= 0:
        raise PiperSidecarError("Piper WAV format is outside supported bounds")
    duration = frames / rate
    if not 0 < duration <= 120:
        raise PiperSidecarError("Piper WAV duration is outside supported bounds")
    return duration


class PiperSidecarSpeechRenderer:
    """SpeechRenderer compatible client for a separately provisioned Piper sidecar."""

    def __init__(
        self,
        port: int,
        token_path: Path | str,
        *,
        voice_name: str = "",
        rate_offset: int = 0,
        pitch_offset: int = 0,
        volume_offset: int = 0,
        timeout_seconds: float = 30.0,
    ):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Piper sidecar port must be 1-65535")
        if type(timeout_seconds) not in (int, float) or not 1 <= float(timeout_seconds) <= 60:
            raise ValueError("Piper sidecar timeout must be 1-60 seconds")
        self.port = port
        self.token_path = Path(token_path).expanduser()
        self.timeout_seconds = float(timeout_seconds)
        self.voice_name = ""
        self.rate_offset = 0
        self.pitch_offset = 0
        self.volume_offset = 0
        self.configure(
            voice_name=voice_name,
            rate_offset=rate_offset,
            pitch_offset=pitch_offset,
            volume_offset=volume_offset,
        )
        self.status = "IDLE"
        self.last_profile = ""
        self.last_duration_seconds = 0.0
        self.error = None
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._process = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rocky-piper-voice")
        self._future = None
        self._prepared = None
        self._temp_path = None

    @property
    def speaking(self):
        return self._future is not None and not self._future.done()

    def _request(self, method: str, route: str, body: bytes | None = None, content_type="application/json"):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=self.timeout_seconds
        )
        headers = {"X-Rocky-Piper-Token": _validated_token(self.token_path)}
        if body is not None:
            headers["Content-Type"] = content_type
        try:
            connection.request(method, route, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(MAX_PIPER_WAV_BYTES + 1)
            if len(raw) > MAX_PIPER_WAV_BYTES:
                raise PiperSidecarError("Piper sidecar response exceeds safe size")
            if response.status != 200:
                detail = raw.decode("utf-8", "replace")[-400:]
                raise PiperSidecarError(
                    f"Piper sidecar HTTP {response.status}"
                    + (": " + detail if detail else "")
                )
            return response.getheader("Content-Type", ""), raw
        except (OSError, http.client.HTTPException) as exc:
            raise PiperSidecarError("Piper loopback sidecar is unavailable") from exc
        finally:
            connection.close()

    def check_available(self) -> tuple[str, ...]:
        content_type, raw = self._request("GET", "/v1/status")
        if "application/json" not in content_type.lower():
            raise PiperSidecarError("Piper status response must be JSON")
        payload = _strict_json(raw.decode("utf-8"))
        if (
            type(payload) is not dict
            or set(payload) != {"schema_version", "ready", "voice"}
            or payload["schema_version"] != 1
            or payload["ready"] is not True
            or type(payload["voice"]) is not str
            or not payload["voice"]
        ):
            raise PiperSidecarError("Piper sidecar status is invalid")
        available = payload["voice"]
        if self.voice_name and self.voice_name != available:
            raise PiperSidecarError(
                f"configured Piper voice does not match loaded sidecar voice: {available}"
            )
        return (available,)

    def configure(
        self,
        *,
        voice_name=None,
        rate_offset=None,
        pitch_offset=None,
        volume_offset=None,
    ):
        if voice_name is not None:
            if (
                type(voice_name) is not str
                or len(voice_name) > 200
                or any(ord(char) < 32 for char in voice_name)
            ):
                raise ValueError("Piper voice name must be a short printable string")
            self.voice_name = voice_name
        for field, value in (
            ("rate_offset", rate_offset),
            ("pitch_offset", pitch_offset),
            ("volume_offset", volume_offset),
        ):
            if value is not None:
                if type(value) is not int or not -2 <= value <= 2:
                    raise ValueError("voice tuning offsets must be integers from -2 to 2")
                if field == "pitch_offset" and value != 0:
                    raise ValueError(
                        "Piper V0 does not expose deterministic pitch shifting; use pitch 0"
                    )
                setattr(self, field, value)
        with getattr(self, "_lock", threading.RLock()):
            if hasattr(self, "_prepared"):
                self._prepared = None

    def _settings_signature(self, text: str):
        profile = classify_prosody(text).name
        length_scale = max(
            0.60,
            min(1.60, _RATE_SCALE[self.rate_offset] * _PROFILE_RATE[profile]),
        )
        volume = max(
            0.35,
            min(1.50, _VOLUME_SCALE[self.volume_offset] * _PROFILE_VOLUME[profile]),
        )
        return profile, round(length_scale, 3), round(volume, 3)

    def _synthesize(self, text: str):
        if type(text) is not str or not text.strip() or len(text.encode("utf-8")) > 384:
            raise ValueError("Piper speech text must contain 1-384 UTF-8 bytes")
        if "\x00" in text or any(ord(char) < 32 and char not in ("\n", "\t") for char in text):
            raise ValueError("Piper speech text contains control characters")
        profile, length_scale, volume = self._settings_signature(text)
        body = json.dumps(
            {
                "schema_version": 1,
                "text": text,
                "length_scale": length_scale,
                "volume": volume,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(body) > 2048:
            raise ValueError("Piper synthesis request exceeds safe size")
        content_type, raw = self._request("POST", "/v1/synthesize", body)
        if "audio/wav" not in content_type.lower():
            raise PiperSidecarError("Piper synthesis response must be audio/wav")
        duration = _wav_duration(raw)
        return profile, length_scale, volume, raw, duration

    def estimate_duration_seconds(self, text: str) -> float:
        profile, length_scale, volume, raw, duration = self._synthesize(text)
        with self._lock:
            self._prepared = (
                text,
                self.voice_name,
                self.rate_offset,
                self.pitch_offset,
                self.volume_offset,
                raw,
                duration,
                profile,
                length_scale,
                volume,
            )
            self.last_duration_seconds = duration
            self.last_profile = profile
        return duration

    def _take_prepared(self, text: str):
        with self._lock:
            prepared = self._prepared
            if (
                prepared is not None
                and prepared[:5]
                == (
                    text,
                    self.voice_name,
                    self.rate_offset,
                    self.pitch_offset,
                    self.volume_offset,
                )
            ):
                self._prepared = None
                return prepared
        profile, length_scale, volume, raw, duration = self._synthesize(text)
        return (
            text,
            self.voice_name,
            self.rate_offset,
            self.pitch_offset,
            self.volume_offset,
            raw,
            duration,
            profile,
            length_scale,
            volume,
        )

    def start(self, text: str, *, gate=None, delay_seconds=0):
        if type(delay_seconds) not in (int, float) or not 0 <= float(delay_seconds) <= 600:
            raise ValueError("invalid speech delay")
        self.cancel()
        prepared = self._take_prepared(text)
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="rocky-piper-voice"
                )
            self._cancel = threading.Event()
            cancelled = self._cancel
            self.status = "QUEUED"
            self.last_duration_seconds = float(prepared[6])
            self.last_profile = prepared[7]
            self.error = None
            self._future = self._executor.submit(
                self._run, prepared[5], gate, float(delay_seconds), cancelled
            )

    def _play_command(self, path: str):
        if os.name == "nt":
            path_b64 = base64.b64encode(path.encode("utf-8")).decode("ascii")
            script = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_b64}'));"
                "$s=New-Object System.Media.SoundPlayer $p;"
                "try {$s.Load();$s.PlaySync()} finally {$s.Dispose()}"
            )
            encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
            return [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded,
            ]
        ffplay = shutil.which("ffplay")
        if ffplay:
            return [ffplay, "-nodisp", "-autoexit", "-loglevel", "error", path]
        raise PiperSidecarError(
            "Piper V0 playback requires Windows SoundPlayer or ffplay"
        )

    def _run(self, raw: bytes, gate, delay_seconds: float, cancelled):
        path = None
        try:
            if gate is not None:
                while not gate.wait(0.05):
                    if cancelled.is_set():
                        return
            if cancelled.wait(delay_seconds):
                return
            fd, path = tempfile.mkstemp(prefix="rocky-piper-", suffix=".wav")
            os.close(fd)
            Path(path).write_bytes(raw)
            with self._lock:
                if cancelled.is_set():
                    return
                self._temp_path = path
                self.status = "SPEAKING"
                self._process = subprocess.Popen(
                    self._play_command(path),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                )
                process = self._process
            while process.poll() is None:
                if cancelled.wait(0.05):
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1)
                    return
            stdout, stderr = process.communicate()
            if process.returncode:
                detail = (stderr or stdout).decode("utf-8", "replace").strip()
                raise PiperSidecarError(
                    "Piper playback failed" + (": " + detail[-500:] if detail else "")
                )
            with self._lock:
                if not cancelled.is_set():
                    self.status = "COMPLETED"
        except Exception as exc:
            with self._lock:
                if not cancelled.is_set():
                    self.error = f"Voice failed: {type(exc).__name__}: {exc}"
                    self.status = "FAILED"
        finally:
            with self._lock:
                self._process = None
                self._temp_path = None
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass

    def poll(self):
        with self._lock:
            if self.error:
                error, self.error = self.error, None
                raise RuntimeError(error)
            return self.status

    def cancel(self):
        with self._lock:
            if hasattr(self, "_cancel"):
                self._cancel.set()
            process = self._process
            if process is not None and process.poll() is None:
                process.terminate()
            self.status = "CANCELLED"

    def close(self):
        self.cancel()
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
