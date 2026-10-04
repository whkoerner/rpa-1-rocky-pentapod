"""Cancellable desktop audio adapter. Rendering owns no brain or hardware authority."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

from brain.contracts import Capability, ConnectionState, EvidenceKind, HardwareReceipt, HardwareStatus, ReceiptStatus
from csp.core import CspCodec
from rpa_link.messages import monotonic_us
from .audio import AudioPlayer, estimated_duration, render_wav


class DesktopHardware:
    backend_id = "desktop-audio"

    def __init__(self, directory: Path, *, backend="auto", volume=0.12, duration_multiplier=1, player=None):
        self.directory = directory
        self.player = player or AudioPlayer(backend)
        self.volume = volume
        self.duration_multiplier = duration_multiplier
        self._muted = False
        self.ready = self.stopped = False
        self.last_wav = None
        self.codec = CspCodec.from_default_spec()
        self._lock = threading.RLock()
        self._executor = None
        self._cancel = threading.Event()
        self._future = None
        self._generation = 0
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
            self.player.stop()
            self.audio_status = "CANCELLED"

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
            self.duration = duration
            self.error = None
            self.audio_status = "RENDERING"
            self._future = self._executor.submit(self._render, command, cancelled, self._generation, self.volume, self.duration_multiplier)
            return receipt(ReceiptStatus.ACCEPTED, f"AUDIO_QUEUED: estimated playback {duration:.2f}s; not acoustically verified")

    def _render(self, command, cancelled, generation, volume, multiplier):
        temporary = self.directory / f"render-{generation}.tmp.wav"
        try:
            render_wav(temporary, command.communication, self.codec, volume, multiplier, cancelled.is_set)
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
