"""Cancellable desktop audio adapter. Rendering owns no brain or hardware authority."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import time

from brain.contracts import Capability, ConnectionState, EvidenceKind, HardwareReceipt, HardwareStatus, ReceiptStatus
from csp.core import CspCodec
from rpa_link.messages import monotonic_us
from .audio import AudioPlayer, estimated_duration, render_wav
from .speech import WindowsSystemSpeechRenderer


class DesktopHardware:
    backend_id = "desktop-audio"

    def __init__(self, directory: Path, *, backend="auto", volume=0.12, duration_multiplier=1, tone_style="pure", translation_voice="", voice_rate=0, voice_pitch=0, voice_volume=0, player=None, speech_renderer=None):
        self.directory = directory
        self.player = player or AudioPlayer(backend)
        self.voice = speech_renderer or WindowsSystemSpeechRenderer(translation_voice, voice_rate, voice_pitch, voice_volume)
        self.translation_enabled = False
        self.volume = volume
        self.duration_multiplier = duration_multiplier
        self.translation_delay_seconds = 0.75
        self.translation_estimated_speech_seconds = 0.0
        self.translation_min_lead_seconds = 0.75
        self.translation_tail_margin_seconds = 0.75
        self.translation_tone_gain = 0.72
        if tone_style not in {"pure", "resonant", "contour-v1"}:
            raise ValueError("tone_style must be pure, resonant or contour-v1")
        self.tone_style = tone_style
        self._muted = False
        self.ready = self.stopped = False
        self.last_wav = None
        self.codec = CspCodec.from_default_spec()
        self._lock = threading.RLock()
        self._executor = None
        self._cancel = threading.Event()
        self._future = None
        self._generation = 0
        self._playback_started = threading.Event()
        self._playback_started_at = None
        self.error = None
        self.audio_status = "IDLE"
        self.duration = 0

    @property
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, value):
        with self._lock:
            self._muted = bool(value)
            if value:
                self.cancel_audio()

    @property
    def rendering(self):
        return self._future is not None and not self._future.done()

    @property
    def voice_status(self):
        return self.voice.status

    @property
    def speech_duration(self):
        return self.voice.last_duration_seconds

    @property
    def combined_duration(self):
        """Approximate wall time with strict source-first English translation."""
        return max(self.duration, self.translation_delay_seconds + self.speech_duration)

    @property
    def translation_finish_margin(self):
        """Positive means English speech finished after Chordic, as intended."""
        return self.translation_delay_seconds + self.speech_duration - self.duration

    def open(self):
        self.player.open()
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rocky-audio")
        self.error = None
        self.audio_status = "IDLE"
        self.ready = True
        self.stopped = False
        return HardwareStatus(self.backend_id, frozenset({Capability.COMMUNICATION, Capability.TEXT_COMMUNICATION, Capability.LOCAL_STOP}), ConnectionState.READY, "AUDIO_ONLY")

    def cancel_audio(self):
        with self._lock:
            self._cancel.set()
            if self._future is not None:
                self._future.cancel()
            self.voice.cancel()
            self.player.stop()
            self.audio_status = "CANCELLED"

    def check_voice_available(self):
        if self.player.backend == "wav":
            raise RuntimeError("spoken translation cannot play through the diagnostic wav-only backend")
        return self.voice.check_available()

    def speak_translation(self, text):
        """Queue active translation while guaranteeing the planned English finish follows Chordic."""
        with self._lock:
            if not self.translation_enabled or self.muted or self.stopped or not self.ready:
                return False
            if self.player.backend == "wav":
                return False
            gate = self._playback_started
            chordic_duration = self.duration
        # Measure the exact local TTS WAV length outside the hardware lock so Chordic
        # rendering/playback is free to proceed in parallel.
        speech_seconds = float(self.voice.estimate_duration_seconds(text))
        planned_delay = max(
            self.translation_min_lead_seconds,
            chordic_duration - speech_seconds + self.translation_tail_margin_seconds,
        )
        with self._lock:
            if not self.translation_enabled or self.muted or self.stopped or not self.ready:
                return False
            self.translation_estimated_speech_seconds = speech_seconds
            self.translation_delay_seconds = planned_delay
            elapsed = 0.0
            if self._playback_started_at is not None:
                elapsed = max(0.0, time.monotonic() - self._playback_started_at)
            remaining_delay = max(0.0, planned_delay - elapsed)
            self.voice.start(text, gate=gate, delay_seconds=remaining_delay)
            return True

    def dispatch(self, command):
        def receipt(status, reason):
            return HardwareReceipt(command.command_id, command.session_id, self.backend_id, status, reason, EvidenceKind.NONE, monotonic_us())
        with self._lock:
            if not self.ready or self.stopped:
                return receipt(ReceiptStatus.REJECTED, "BACKEND_NOT_OPEN")
            if monotonic_us() > command.deadline_us:
                return receipt(ReceiptStatus.REJECTED, "DEADLINE_EXPIRED")
            # Validate representation and compute estimate before accepting work.
            duration = estimated_duration(command.communication, self.codec, self.duration_multiplier)
            self.cancel_audio()
            self._generation += 1
            cancelled = self._cancel = threading.Event()
            self._playback_started = threading.Event()
            self._playback_started_at = None
            self.duration = duration
            self.translation_delay_seconds = self.translation_min_lead_seconds
            self.translation_estimated_speech_seconds = 0.0
            self.error = None
            self.audio_status = "RENDERING"
            render_volume = self.volume * (self.translation_tone_gain if self.translation_enabled else 1.0)
            self._future = self._executor.submit(self._render, command, cancelled, self._generation, render_volume, self.duration_multiplier)
            return receipt(ReceiptStatus.ACCEPTED, f"AUDIO_QUEUED: estimated playback {duration:.2f}s; not acoustically verified")

    def _render(self, command, cancelled, generation, volume, multiplier):
        temporary = self.directory / f"render-{generation}.tmp.wav"
        try:
            render_wav(temporary, command.communication, self.codec, volume, multiplier, cancelled.is_set, self.tone_style)
            with self._lock:
                if cancelled.is_set() or self.stopped or not self.ready:
                    return
                if monotonic_us() > command.deadline_us:
                    raise RuntimeError("DEADLINE_EXPIRED while rendering; no playback")
                path = self.directory / "last-response.wav"
                temporary.replace(path)
                self.last_wav = path
                if self.muted or self.player.backend == "wav":
                    self.audio_status = "WAV_WRITTEN_MUTED" if self.muted else "WAV_WRITTEN_NO_PLAYBACK"
                else:
                    self.player.play(path)
                    self._playback_started_at = time.monotonic()
                    self._playback_started.set()
                    self.audio_status = "PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED"
        except Exception as exc:
            with self._lock:
                if not cancelled.is_set():
                    self.error = f"Audio failed: {type(exc).__name__}: {exc}"
                    self.audio_status = "FAILED"
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as exc:
                with self._lock:
                    if not cancelled.is_set():
                        self.error = f"Audio temporary-file cleanup failed: {exc}"
                        self.audio_status = "FAILED"

    def poll(self):
        with self._lock:
            if self.error:
                error, self.error = self.error, None
                raise RuntimeError(error)
        self.voice.poll()
        return ()

    def stop(self, reason, *, emergency):
        with self._lock:
            self.stopped = True
            self.cancel_audio()
        return HardwareReceipt(0, "", self.backend_id, ReceiptStatus.COMPLETED, "LOCAL_AUDIO_STOP_REQUESTED: " + reason, EvidenceKind.NONE, monotonic_us())

    def close(self):
        with self._lock:
            self.ready = False
            self.cancel_audio()
            self.player.close()
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        self.voice.close()
