"""Bounded PCM synthesis and platform-specific, nonblocking playback adapters."""

from array import array
import math
from pathlib import Path
import re
import sys
import wave

from brain.contracts import CommunicationOutput, ConversationOutput
from csp.core import CspCodec
from csp.conversation import decode_text

SAMPLE_RATE = 22050


def frequency(note: str) -> float:
    match = re.fullmatch(r"([A-G])(sharp)?([0-8])", note)
    if not match:
        raise ValueError("invalid note")
    name, sharp, octave = match.groups()
    midi = 12 * (int(octave) + 1) + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[name] + bool(sharp)
    return 440 * 2 ** ((midi - 69) / 12)


def events(output, codec: CspCodec):
    phonology = codec.specification["phonology"]
    header = phonology["phrase_header"]
    yield tuple(frequency(n) for n in header["notes"]), header["duration_ms"], header["rest_after_ms"]
    if isinstance(output, CommunicationOutput):
        timing = phonology["literal_timing"]
        for note in output.notes:
            yield (frequency(note),), timing["note_ms"], timing["inter_note_gap_ms"]
    elif isinstance(output, ConversationOutput):
        if decode_text(output.symbols) != output.canonical_text:
            raise ValueError("CT1 translation mismatch")
        # CT1's four ordered voices use octaves 3, 4, 5, 6.
        scale = [frequency(codec.digit_to_note[n]) for n in range(5)]
        for index, digits in enumerate(output.symbols):
            yield tuple(scale[d] * 2 ** (voice - 1) for voice, d in enumerate(digits)), 65, (35 if index % 8 == 7 else 15)
    else:
        raise ValueError("unsupported communication output")


def synthesize(output, codec: CspCodec, volume: float = 0.12) -> bytes:
    if not math.isfinite(volume) or not 0 <= volume <= 0.3:
        raise ValueError("volume must be between 0 and 0.3")
    samples = array("h")
    for frequencies, duration_ms, gap_ms in events(output, codec):
        count = round(SAMPLE_RATE * duration_ms / 1000)
        attack = max(1, round(SAMPLE_RATE * 0.012))
        release = max(1, min(round(SAMPLE_RATE * 0.060), count // 2))
        for i in range(count):
            envelope = min(1, i / attack, (count - 1 - i) / release)
            value = sum(math.sin(2 * math.pi * hz * i / SAMPLE_RATE) for hz in frequencies) / len(frequencies)
            samples.append(round(32767 * volume * envelope * value))
        samples.extend([0] * round(SAMPLE_RATE * gap_ms / 1000))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def write_wav(path: Path, pcm: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)


class AudioPlayer:
    def __init__(self, backend: str = "auto"):
        self.backend = ("winsound" if sys.platform == "win32" else "pygame") if backend == "auto" else backend
        self._module = None

    def open(self):
        if self.backend == "wav":
            return
        if self.backend == "winsound":
            import winsound
            self._module = winsound
        elif self.backend == "pygame":
            try:
                import pygame.mixer
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
                self._module = pygame.mixer
            except (ImportError, RuntimeError) as exc:
                raise RuntimeError('Audio unavailable. Install: python -m pip install -e ".[audio]"') from exc
        else:
            raise ValueError("unknown audio backend")

    def play(self, path: Path):
        if self.backend == "winsound":
            self._module.PlaySound(str(path), self._module.SND_FILENAME | self._module.SND_ASYNC | self._module.SND_NODEFAULT)
        elif self.backend == "pygame":
            self._module.music.load(str(path))
            self._module.music.play()

    def stop(self):
        if self._module is None:
            return
        if self.backend == "winsound":
            self._module.PlaySound(None, 0)
        elif self.backend == "pygame":
            self._module.music.stop()
            self._module.music.unload()

    def close(self):
        self.stop()
        if self.backend == "pygame" and self._module is not None:
            self._module.quit()
