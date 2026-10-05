"""Local speech seams. Model text never receives audio-control authority."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import base64
import html
import subprocess
import sys
import threading
import time
from typing import Protocol


class SpeechInput(Protocol):
    def listen_once(self, *, timeout_seconds: float) -> str:
        """Capture one bounded push-to-talk utterance locally; never call hardware."""
        ...


@dataclass(frozen=True)
class ProsodyProfile:
    name: str
    rate: str
    pitch: str
    volume: str


PROSODY = {
    "question": ProsodyProfile("question", "medium", "high", "medium"),
    "excitement": ProsodyProfile("excitement", "fast", "high", "loud"),
    "reassurance": ProsodyProfile("reassurance", "slow", "low", "soft"),
    "technical": ProsodyProfile("technical", "medium", "medium", "medium"),
    "neutral": ProsodyProfile("neutral", "medium", "medium", "medium"),
}


def classify_prosody(text: str) -> ProsodyProfile:
    """Classify delivery in trusted application code from already validated text."""
    if type(text) is not str or not text.strip():
        raise ValueError("speech text must be nonempty")
    lower = text.lower()
    if "!" in text or "amaze amaze" in lower or any(word in lower for word in ("amazing", "excellent", "full good")):
        return PROSODY["excitement"]
    if any(word in lower for word in ("you sad", "sorry", "rocky here", "we team", "scared", "afraid", "support")):
        return PROSODY["reassurance"]
    if text.rstrip().endswith("?") or lower.lstrip().startswith(("question", "what ", "why ", "how ", "where ", "when ", "who ")):
        return PROSODY["question"]
    if any(word in lower for word in ("derivative", "calculus", "equation", "voltage", "current", "circuit", "resistance", "integral", "engineering")):
        return PROSODY["technical"]
    return PROSODY["neutral"]


def build_ssml(text: str, profile: ProsodyProfile | None = None) -> str:
    """Escape model text; only fixed application-owned values become SSML controls."""
    profile = profile or classify_prosody(text)
    if profile not in PROSODY.values():
        raise ValueError("untrusted prosody profile")
    escaped = html.escape(text, quote=False)
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
        f'<prosody rate="{profile.rate}" pitch="{profile.pitch}" volume="{profile.volume}">{escaped}</prosody>'
        '</speak>'
    )


class SpeechRenderer(Protocol):
    status: str
    last_profile: str
    last_duration_seconds: float

    def check_available(self) -> tuple[str, ...]:
        ...

    def start(self, text: str, *, gate: threading.Event | None = None, delay_seconds: float = 0) -> None:
        ...

    def poll(self) -> str:
        ...

    def cancel(self) -> None:
        ...

    def close(self) -> None:
        ...


def _powershell_encoded(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


class WindowsSystemSpeechRenderer:
    """Offline System.Speech renderer using voices already installed in Windows.

    This renderer never downloads voices and never calls a network endpoint. A
    specific voice may be configured, but it must already exist locally.
    """

    def __init__(self, voice_name: str = ""):
        if type(voice_name) is not str or len(voice_name) > 200 or any(ord(c) < 32 for c in voice_name):
            raise ValueError("translation voice must be a printable string up to 200 characters")
        self.voice_name = voice_name
        self.status = "IDLE"
        self.last_profile = ""
        self.last_duration_seconds = 0.0
        self.error = None
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._process = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rocky-voice")
        self._future = None

    @property
    def speaking(self):
        return self._future is not None and not self._future.done()

    def check_available(self) -> tuple[str, ...]:
        if sys.platform != "win32":
            raise RuntimeError("spoken English translation requires Windows System.Speech")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "try {"
            "$names=@($s.GetInstalledVoices()|Where-Object {$_.Enabled}|ForEach-Object {$_.VoiceInfo.Name});"
            "if($names.Count -eq 0){exit 3};"
            "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
            "$names -join [Environment]::NewLine"
            "} finally {$s.Dispose()}"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", _powershell_encoded(script)],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Windows local speech engine is unavailable") from exc
        if result.returncode:
            raise RuntimeError("no enabled local Windows speech voice is available")
        names = tuple(line.strip() for line in result.stdout.decode("utf-8", "replace").splitlines() if line.strip())
        if self.voice_name and self.voice_name not in names:
            raise RuntimeError(f"configured local voice is not installed: {self.voice_name}")
        return names

    def start(self, text: str, *, gate=None, delay_seconds=0) -> None:
        if type(delay_seconds) not in (int, float) or not 0 <= delay_seconds <= 600:
            raise ValueError("invalid speech delay")
        profile = classify_prosody(text)
        ssml = build_ssml(text, profile)
        with self._lock:
            self.cancel()
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rocky-voice")
            self._cancel = threading.Event()
            self.status = "QUEUED"
            self.last_profile = profile.name
            self.last_duration_seconds = 0.0
            self.error = None
            self._future = self._executor.submit(self._run, ssml, gate, float(delay_seconds), self._cancel)

    def _run(self, ssml, gate, delay_seconds, cancelled):
        try:
            if sys.platform != "win32":
                raise RuntimeError("spoken English translation requires Windows System.Speech")
            if gate is not None:
                while not gate.wait(0.05):
                    if cancelled.is_set():
                        return
            if cancelled.wait(delay_seconds):
                return
            ssml_b64 = base64.b64encode(ssml.encode("utf-8")).decode("ascii")
            voice_b64 = base64.b64encode(self.voice_name.encode("utf-8")).decode("ascii")
            script = (
                "Add-Type -AssemblyName System.Speech;"
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                f"$x=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{ssml_b64}'));"
                f"$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice_b64}'));"
                "try {if($v.Length -gt 0){$s.SelectVoice($v)};"
                "$s.SetOutputToDefaultAudioDevice();$s.SpeakSsml($x)} finally {$s.Dispose()}"
            )
            started = time.monotonic()
            with self._lock:
                if cancelled.is_set():
                    return
                self.status = "SPEAKING"
                self._process = subprocess.Popen(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", _powershell_encoded(script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process = self._process
            while process.poll() is None:
                if cancelled.wait(0.05):
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return
            stdout, stderr = process.communicate()
            if process.returncode:
                detail = (stderr or stdout).decode("utf-8", "replace").strip()
                raise RuntimeError("Windows speech synthesis failed" + (": " + detail[-500:] if detail else ""))
            with self._lock:
                if not cancelled.is_set():
                    self.last_duration_seconds = max(0.0, time.monotonic() - started)
                    self.status = "COMPLETED"
        except Exception as exc:
            with self._lock:
                if not cancelled.is_set():
                    self.error = f"Voice failed: {type(exc).__name__}: {exc}"
                    self.status = "FAILED"
        finally:
            with self._lock:
                self._process = None

    def poll(self):
        with self._lock:
            if self.error:
                error, self.error = self.error, None
                raise RuntimeError(error)
            return self.status

    def cancel(self) -> None:
        with self._lock:
            self._cancel.set()
            process = self._process
            if process is not None and process.poll() is None:
                process.terminate()
            self.status = "CANCELLED"

    def close(self) -> None:
        self.cancel()
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
