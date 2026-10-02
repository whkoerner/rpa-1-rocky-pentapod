"""Computer audio HardwareInterface. No serial, GPIO, motor, or sensor access."""

from pathlib import Path

from brain.contracts import (
    Capability, ConnectionState, EvidenceKind, HardwareReceipt, HardwareStatus, ReceiptStatus,
)
from csp.core import CspCodec
from rpa_link.messages import monotonic_us
from .audio import AudioPlayer, synthesize, write_wav


class DesktopHardware:
    backend_id = "desktop-audio"

    def __init__(self, directory: Path, *, backend="auto", volume=0.12, player=None):
        self.directory = directory
        self.player = player or AudioPlayer(backend)
        self.volume = volume
        self.muted = False
        self.ready = False
        self.stopped = False
        self.last_wav = None
        self.codec = CspCodec.from_default_spec()

    def open(self):
        self.player.open()
        self.ready = True
        self.stopped = False
        return HardwareStatus(self.backend_id, frozenset({Capability.COMMUNICATION, Capability.TEXT_COMMUNICATION, Capability.LOCAL_STOP}), ConnectionState.READY, "AUDIO_ONLY")

    def dispatch(self, command):
        def receipt(status, reason):
            return HardwareReceipt(command.command_id, command.session_id, self.backend_id, status, reason, EvidenceKind.NONE, monotonic_us())
        if not self.ready or self.stopped:
            return receipt(ReceiptStatus.REJECTED, "BACKEND_NOT_OPEN")
        if monotonic_us() > command.deadline_us:
            return receipt(ReceiptStatus.REJECTED, "DEADLINE_EXPIRED")
        pcm = synthesize(command.communication, self.codec, self.volume)
        self.player.stop()
        path = self.directory / "last-response.wav"
        write_wav(path, pcm)
        if self.stopped or monotonic_us() > command.deadline_us:
            return receipt(ReceiptStatus.REJECTED, "DEADLINE_EXPIRED")
        self.last_wav = path
        if self.muted or self.player.backend == "wav":
            return receipt(ReceiptStatus.COMPLETED, "WAV_WRITTEN_MUTED" if self.muted else "WAV_WRITTEN_NO_PLAYBACK")
        self.player.play(path)
        return receipt(ReceiptStatus.ACCEPTED, "PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED")

    def poll(self):
        return ()

    def stop(self, reason, *, emergency):
        self.stopped = True
        self.player.stop()
        return HardwareReceipt(0, "", self.backend_id, ReceiptStatus.COMPLETED, "LOCAL_AUDIO_STOP_REQUESTED: " + reason, EvidenceKind.NONE, monotonic_us())

    def close(self):
        self.ready = False
        self.player.close()
