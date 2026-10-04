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
from csp.learning import decode_phrase, literal_text

SAMPLE_RATE = 22050


def frequency(note: str) -> float:
    match = re.fullmatch(r"([A-G])(sharp)?([0-8])", note)
    if not match:
        raise ValueError("invalid note")
    name, sharp, octave = match.groups()
    midi = 12 * (int(octave) + 1) + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[name] + bool(sharp)
    return 440 * 2 ** ((midi - 69) / 12)


def base_events(output, codec: CspCodec):
    phonology = codec.specification["phonology"]
    header = phonology["phrase_header"]
    yield tuple(frequency(n) for n in header["notes"]), header["duration_ms"], header["rest_after_ms"]
    if isinstance(output, CommunicationOutput):
        timing = phonology["literal_timing"]
        for note in output.notes:
            yield (frequency(note),), timing["note_ms"], timing["inter_note_gap_ms"]
    elif isinstance(output, ConversationOutput) and output.phrase is not None:
        if decode_phrase(output.phrase) != output.canonical_text:
            raise ValueError("CT2 translation mismatch")
        timing = phonology["literal_timing"]
        scale = [frequency(codec.digit_to_note[n]) for n in range(5)]
        # Distinct CT2 transport marker; existing CSP headers/pitches are unchanged.
        yield (frequency("B3"), frequency("E5")), 100, 100
        for unit in output.phrase.units:
            if unit.kind == "token":
                # Case marker is separate from the stable five-note lexical core.
                yield (frequency("D3") * 2 ** {"lower": 0, "initial": 1, "upper": 2}[unit.case],), 50, 50
                for note in codec.encode_token(unit.value).notes:
                    yield (frequency(note),), timing["note_ms"], timing["inter_note_gap_ms"]
                yield (), 0, timing["inter_token_gap_ms"]
            else:
                raw = literal_text(unit.value).encode("utf-8")
                yield (frequency("B3"), frequency("E5")), 50, 50
                for byte, digits in zip(raw, unit.value):
                    # Even punctuation and spaces retain byte symbols; pauses supplement them.
                    gap = 300 if byte in b".!?" else 150 if byte in b",;:" else 100 if byte == 32 else 15
                    yield tuple(scale[d] * 2 ** (voice - 1) for voice, d in enumerate(digits)), 65, gap
                yield (), 0, 100
    elif isinstance(output, ConversationOutput):
        if decode_text(output.symbols) != output.canonical_text:
            raise ValueError("CT1 translation mismatch")
        # CT1's four ordered voices use octaves 3, 4, 5, 6.
        scale = [frequency(codec.digit_to_note[n]) for n in range(5)]
        for index, digits in enumerate(output.symbols):
            yield tuple(scale[d] * 2 ** (voice - 1) for voice, d in enumerate(digits)), 65, (35 if index % 8 == 7 else 15)
    else:
        raise ValueError("unsupported communication output")


def events(output, codec: CspCodec, duration_multiplier=1):
    if type(duration_multiplier) not in (int, float) or not math.isfinite(duration_multiplier) or not 1 <= duration_multiplier <= 6:
        raise ValueError("duration_multiplier must be between 1 and 6")
    for frequencies, duration, gap in base_events(output, codec):
        yield frequencies, duration * duration_multiplier, gap * duration_multiplier


def estimated_duration(output, codec, duration_multiplier=1):
    return sum(round(SAMPLE_RATE * d / 1000) + round(SAMPLE_RATE * g / 1000) for _, d, g in events(output, codec, duration_multiplier)) / SAMPLE_RATE


def pcm_chunks(output, codec, volume=0.12, duration_multiplier=1, cancelled=lambda: False):
    if type(volume) not in (int, float) or not math.isfinite(volume) or not 0 <= volume <= 0.3:
        raise ValueError("volume must be between 0 and 0.3")
    for frequencies, duration_ms, gap_ms in events(output, codec, duration_multiplier):
        count = round(SAMPLE_RATE * duration_ms / 1000)
        attack = max(1, round(SAMPLE_RATE * 0.012))
        release = max(1, min(round(SAMPLE_RATE * 0.060), count // 2))
        for start in range(0, count, 1024):
            if cancelled():
                return
            samples = array("h")
            for i in range(start, min(start + 1024, count)):
                envelope = min(1, i / attack, (count - 1 - i) / release)
                value = sum(math.sin(2 * math.pi * hz * i / SAMPLE_RATE) for hz in frequencies) / len(frequencies)
                samples.append(round(32767 * volume * envelope * value))
            if sys.byteorder != "little":
                samples.byteswap()
            yield samples.tobytes()
        remaining = round(SAMPLE_RATE * gap_ms / 1000)
        while remaining:
            if cancelled():
                return
            size = min(remaining, 1024)
            yield bytes(size * 2)
            remaining -= size


def synthesize(output, codec: CspCodec, volume=0.12, duration_multiplier=1) -> bytes:
    return b"".join(pcm_chunks(output, codec, volume, duration_multiplier))


def render_wav(path, output, codec, volume, duration_multiplier, cancelled):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        for chunk in pcm_chunks(output, codec, volume, duration_multiplier, cancelled):
            handle.writeframesraw(chunk)


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
