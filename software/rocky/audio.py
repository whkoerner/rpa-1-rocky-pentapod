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
from csp.exp002 import Exp002Phrase, decode_phrase as decode_exp002_phrase, load_profile as load_exp002_profile, token_patterns as exp002_token_patterns
from csp.exp003 import Exp003Phrase, decode_phrase as decode_exp003_phrase, load_profile as load_exp003_profile, token_patterns as exp003_token_patterns
from csp.learning import decode_phrase, literal_text

SAMPLE_RATE = 22050


def frequency(note: str) -> float:
    match = re.fullmatch(r"([A-G])(sharp)?([0-8])", note)
    if not match:
        raise ValueError("invalid note")
    name, sharp, octave = match.groups()
    midi = 12 * (int(octave) + 1) + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[name] + bool(sharp)
    return 440 * 2 ** ((midi - 69) / 12)


def _relative_frequency(baseline, semitones):
    return baseline * 2 ** (semitones / 12)


def base_events(output, codec: CspCodec):
    phonology = codec.specification["phonology"]
    if isinstance(output, ConversationOutput) and isinstance(output.phrase, Exp003Phrase):
        if decode_exp003_phrase(output.phrase) != output.canonical_text:
            raise ValueError("EXP-003 translation mismatch")
        profile = load_exp003_profile()
        candidate = profile["candidate"]
        acoustics = candidate["acoustics"]
        timing = acoustics["timing_ms"]
        offsets = {int(key): value for key, value in acoustics["pitch_offsets_semitones"].items()}
        patterns = exp003_token_patterns()
        classes = {row["id"]: row["duration_class"] for row in candidate["tokens"]}
        baseline = float(acoustics.get("reference_baseline_hz", 180.0))
        fallback_baseline = float(acoustics.get("fallback_reference_hz", baseline))
        yield (baseline,), timing["phrase_header"], 0
        yield (_relative_frequency(baseline, -2), _relative_frequency(baseline, 2)), timing["profile_marker"], 0
        for exp_unit in output.phrase.units:
            if exp_unit.kind == "tokens":
                for token in exp_unit.tokens:
                    gesture = timing["short_gesture"] if classes[token] == "short" else timing["root_gesture"]
                    anchor = gesture / len(patterns[token])
                    for degree in patterns[token]:
                        yield (_relative_frequency(baseline, offsets[degree]),), anchor, 0
                    yield (), 0, timing["token_boundary"]
            elif exp_unit.kind == "ct2":
                yield (_relative_frequency(fallback_baseline, -2), _relative_frequency(fallback_baseline, 2)), timing["fallback_marker"], 0
                raw = exp_unit.text.encode("utf-8")
                for byte, digits in zip(raw, exp_unit.fallback.units[0].value):
                    gap = timing["fallback_sentence_punctuation_gap"] if byte in b".!?" else timing["fallback_minor_punctuation_gap"] if byte in b",;:" else timing["fallback_space_gap"] if byte == 32 else timing["fallback_default_gap"]
                    yield tuple(_relative_frequency(fallback_baseline, offsets[d]) for d in digits), timing["fallback_byte"], gap
                yield (), 0, timing["fallback_boundary"]
        return
    header = phonology["phrase_header"]
    yield tuple(frequency(n) for n in header["notes"]), header["duration_ms"], header["rest_after_ms"]
    if isinstance(output, CommunicationOutput):
        timing = phonology["literal_timing"]
        for note in output.notes:
            yield (frequency(note),), timing["note_ms"], timing["inter_note_gap_ms"]
    elif isinstance(output, ConversationOutput) and isinstance(output.phrase, Exp002Phrase):
        if decode_exp002_phrase(output.phrase) != output.canonical_text:
            raise ValueError("EXP-002 translation mismatch")
        profile = load_exp002_profile()["candidate"]
        exp_timing = profile["timing"]
        mapping = {int(key): value for key, value in profile["synthesis_mapping"].items()}
        patterns = exp002_token_patterns()
        yield (frequency("D4"), frequency("B4")), exp_timing["profile_marker_ms"] / 2, exp_timing["profile_marker_ms"] / 2
        ct2_timing = phonology["literal_timing"]
        scale = [frequency(codec.digit_to_note[n]) for n in range(5)]
        for exp_unit in output.phrase.units:
            if exp_unit.kind == "tokens":
                for token in exp_unit.tokens:
                    for degree in patterns[token]:
                        yield (frequency(mapping[degree]),), exp_timing["note_ms"], exp_timing["inter_note_gap_ms"]
                    yield (), 0, exp_timing["token_boundary_ms"]
            else:
                yield (frequency("B3"), frequency("E5")), 50, 50
                for unit in exp_unit.fallback.units:
                    if unit.kind == "token":
                        yield (frequency("D3") * 2 ** {"lower": 0, "initial": 1, "upper": 2}[unit.case],), 50, 50
                        for note in codec.encode_token(unit.value).notes:
                            yield (frequency(note),), ct2_timing["note_ms"], ct2_timing["inter_note_gap_ms"]
                        yield (), 0, ct2_timing["inter_token_gap_ms"]
                    else:
                        raw = literal_text(unit.value).encode("utf-8")
                        yield (frequency("B3"), frequency("E5")), 50, 50
                        for byte, digits in zip(raw, unit.value):
                            gap = 300 if byte in b".!?" else 150 if byte in b",;:" else 100 if byte == 32 else 15
                            yield tuple(scale[d] * 2 ** (voice - 1) for voice, d in enumerate(digits)), 65, gap
                        yield (), 0, 100
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


def _contour_gesture(frequencies, duration_ms, volume, cancelled, timbre=None):
    timbre = timbre or {}
    fundamental_gain = float(timbre.get("fundamental_gain", 0.76))
    subharmonic_gain = float(timbre.get("subharmonic_gain", 0.0))
    second_gain = float(timbre.get("second_harmonic_gain", 0.17))
    third_gain = float(timbre.get("third_harmonic_gain", 0.07))
    vibrato_depth = float(timbre.get("vibrato_depth_radians", 0.035))
    pulse_depth = float(timbre.get("amplitude_pulse_depth", 0.0))
    pulse_hz = float(timbre.get("amplitude_pulse_hz", 1.6))
    normalizer = max(1e-9, fundamental_gain + subharmonic_gain + second_gain + third_gain)
    count = max(1, round(SAMPLE_RATE * duration_ms / 1000))
    anchors = len(frequencies)
    for start in range(0, count, 1024):
        if cancelled():
            return
        samples = array("h")
        for index in range(start, min(start + 1024, count)):
            position = 0 if count <= 1 else index * (anchors - 1) / (count - 1)
            segment = min(anchors - 2, int(position)) if anchors > 1 else 0
            fraction = position - segment if anchors > 1 else 0
            smooth = 0.5 - 0.5 * math.cos(math.pi * fraction)
            if anchors > 1:
                left, right = frequencies[segment], frequencies[segment + 1]
                hz = 2 ** ((1 - smooth) * math.log2(left) + smooth * math.log2(right))
            else:
                hz = frequencies[0]
            t = index / SAMPLE_RATE
            attack = min(1.0, index / max(1, round(SAMPLE_RATE * 0.045)))
            release = min(1.0, (count - 1 - index) / max(1, round(SAMPLE_RATE * 0.065)))
            envelope = max(0.0, min(attack, release))
            vibration = vibrato_depth * math.sin(2 * math.pi * 4.1 * t)
            phase = 2 * math.pi * hz * t + vibration
            pulse = (1.0 - pulse_depth) + pulse_depth * (0.5 + 0.5 * math.sin(2 * math.pi * pulse_hz * t))
            body = (
                fundamental_gain * math.sin(phase)
                + subharmonic_gain * math.sin(0.5 * phase)
                + second_gain * math.sin(2 * phase)
                + third_gain * math.sin(3 * phase)
            ) / normalizer
            samples.append(round(32767 * volume * envelope * pulse * body))
        if sys.byteorder != "little":
            samples.byteswap()
        yield samples.tobytes()




def _vocal_gesture(frequencies, duration_ms, volume, cancelled, state, profile, timbre):
    """Phase-continuous, low-register vocal carrier for EXP-003 contours."""
    count = max(1, round(SAMPLE_RATE * duration_ms / 1000))
    anchors = len(frequencies)
    attack = max(1, round(SAMPLE_RATE * float(profile.get("attack_ms", 55)) / 1000))
    release = max(1, round(SAMPLE_RATE * float(profile.get("release_ms", 85)) / 1000))
    micro = float(profile.get("max_micro_pitch_jitter_semitones", 0.12))
    drift = float(profile.get("phrase_drift_semitones", 0.18))
    fundamental_gain = float(timbre.get("fundamental_gain", 0.72))
    subharmonic_gain = float(timbre.get("subharmonic_gain", 0.20))
    second_gain = min(0.08, float(timbre.get("second_harmonic_gain", 0.07)))
    third_gain = min(0.02, float(timbre.get("third_harmonic_gain", 0.01)))
    pulse_depth = float(timbre.get("amplitude_pulse_depth", 0.035))
    pulse_hz = float(timbre.get("amplitude_pulse_hz", 1.6))
    normalizer = max(1e-9, fundamental_gain + subharmonic_gain + second_gain + third_gain)
    phase = float(state.get("phase", 0.0))
    sub_phase = float(state.get("sub_phase", 0.0))
    sample_index = int(state.get("sample_index", 0))
    for start in range(0, count, 1024):
        if cancelled():
            return
        samples = array("h")
        for local_index in range(start, min(start + 1024, count)):
            position = 0 if count <= 1 else local_index * (anchors - 1) / (count - 1)
            segment = min(anchors - 2, int(position)) if anchors > 1 else 0
            fraction = position - segment if anchors > 1 else 0
            smooth = 0.5 - 0.5 * math.cos(math.pi * fraction)
            if anchors > 1:
                left, right = frequencies[segment], frequencies[segment + 1]
                base_hz = 2 ** ((1 - smooth) * math.log2(left) + smooth * math.log2(right))
            else:
                base_hz = frequencies[0]
            t = (sample_index + local_index) / SAMPLE_RATE
            pitch_motion = (
                drift * math.sin(2 * math.pi * 0.31 * t + 0.37)
                + micro * (
                    0.58 * math.sin(2 * math.pi * 2.17 * t + 0.61)
                    + 0.42 * math.sin(2 * math.pi * 3.79 * t + 1.13)
                )
            )
            hz = base_hz * 2 ** (pitch_motion / 12)
            phase += 2 * math.pi * hz / SAMPLE_RATE
            sub_phase += math.pi * hz / SAMPLE_RATE
            envelope = min(1.0, local_index / attack, (count - 1 - local_index) / release)
            envelope = max(0.0, envelope)
            pulse = (1.0 - pulse_depth) + pulse_depth * (0.5 + 0.5 * math.sin(2 * math.pi * pulse_hz * t + 0.4))
            # Soft glottal-like carrier: low, rounded, and intentionally light on upper harmonics.
            glottal = math.tanh(1.35 * (math.sin(phase) + 0.16 * math.sin(2 * phase)))
            body = (
                fundamental_gain * glottal
                + subharmonic_gain * math.sin(sub_phase)
                + second_gain * math.sin(2 * phase + 0.2)
                + third_gain * math.sin(3 * phase + 0.35)
            ) / normalizer
            # Deterministic low-level aspiration prevents a perfectly sterile oscillator tone.
            aspiration = 0.008 * (
                math.sin(2 * math.pi * 71.0 * t + 0.7 * math.sin(2 * math.pi * 1.1 * t))
                + 0.5 * math.sin(2 * math.pi * 113.0 * t + 0.2)
            )
            value = max(-1.0, min(1.0, pulse * body + aspiration))
            samples.append(round(32767 * volume * envelope * value))
        if sys.byteorder != "little":
            samples.byteswap()
        yield samples.tobytes()
    state["phase"] = phase % (2 * math.pi)
    state["sub_phase"] = sub_phase % (2 * math.pi)
    state["sample_index"] = sample_index + count


def _silence_chunks(duration_ms, cancelled):
    remaining = round(SAMPLE_RATE * duration_ms / 1000)
    while remaining:
        if cancelled():
            return
        size = min(remaining, 1024)
        yield bytes(size * 2)
        remaining -= size


def _exp003_contour_chunks(output, codec, volume, duration_multiplier, cancelled):
    if decode_exp003_phrase(output.phrase) != output.canonical_text:
        raise ValueError("EXP-003 translation mismatch")
    profile = load_exp003_profile()
    candidate = profile["candidate"]
    acoustics = candidate["acoustics"]
    timing = acoustics["timing_ms"]
    offsets = {int(key): value for key, value in acoustics["pitch_offsets_semitones"].items()}
    patterns = exp003_token_patterns()
    classes = {row["id"]: row["duration_class"] for row in candidate["tokens"]}
    baseline = float(acoustics.get("reference_baseline_hz", 180.0))
    fallback_baseline = float(acoustics.get("fallback_reference_hz", baseline))
    timbre = acoustics.get("timbre", {})
    for chunk in _contour_gesture((baseline,), timing["phrase_header"] * duration_multiplier, volume, cancelled, timbre):
        yield chunk
    marker = (_relative_frequency(baseline, -2), _relative_frequency(baseline, 2))
    for chunk in _contour_gesture(marker, timing["profile_marker"] * duration_multiplier, volume, cancelled, timbre):
        yield chunk
    for unit in output.phrase.units:
        if unit.kind == "tokens":
            for token in unit.tokens:
                gesture = timing["short_gesture"] if classes[token] == "short" else timing["root_gesture"]
                freqs = tuple(_relative_frequency(baseline, offsets[d]) for d in patterns[token])
                for chunk in _contour_gesture(freqs, gesture * duration_multiplier, volume, cancelled, timbre):
                    yield chunk
                for chunk in _silence_chunks(timing["token_boundary"] * duration_multiplier, cancelled):
                    yield chunk
        elif unit.kind == "ct2":
            fallback_marker = (_relative_frequency(fallback_baseline, -2), _relative_frequency(fallback_baseline, 2))
            for chunk in _contour_gesture(fallback_marker, timing["fallback_marker"] * duration_multiplier, volume, cancelled, timbre):
                yield chunk
            raw = unit.text.encode("utf-8")
            for byte, digits in zip(raw, unit.fallback.units[0].value):
                gap = timing["fallback_sentence_punctuation_gap"] if byte in b".!?" else timing["fallback_minor_punctuation_gap"] if byte in b",;:" else timing["fallback_space_gap"] if byte == 32 else timing["fallback_default_gap"]
                freqs = tuple(_relative_frequency(fallback_baseline, offsets[d]) for d in digits)
                for chunk in _contour_gesture(freqs, timing["fallback_byte"] * duration_multiplier, volume, cancelled, timbre):
                    yield chunk
                for chunk in _silence_chunks(gap * duration_multiplier, cancelled):
                    yield chunk
            for chunk in _silence_chunks(timing["fallback_boundary"] * duration_multiplier, cancelled):
                yield chunk




def _exp003_vocal_chunks(output, codec, volume, duration_multiplier, cancelled):
    if decode_exp003_phrase(output.phrase) != output.canonical_text:
        raise ValueError("EXP-003 translation mismatch")
    profile_data = load_exp003_profile()
    candidate = profile_data["candidate"]
    acoustics = candidate["acoustics"]
    timing = acoustics["timing_ms"]
    offsets = {int(key): value for key, value in acoustics["pitch_offsets_semitones"].items()}
    patterns = exp003_token_patterns()
    classes = {row["id"]: row["duration_class"] for row in candidate["tokens"]}
    baseline = float(acoustics.get("reference_baseline_hz", 120.0))
    fallback_baseline = float(acoustics.get("fallback_reference_hz", baseline))
    timbre = acoustics.get("timbre", {})
    renderer = acoustics.get("renderer_profiles", {}).get("vocal-v1", {})
    state = {"phase": 0.0, "sub_phase": 0.0, "sample_index": 0}

    for chunk in _vocal_gesture((baseline,), timing["phrase_header"] * duration_multiplier, volume, cancelled, state, renderer, timbre):
        yield chunk
    marker = (_relative_frequency(baseline, -2), _relative_frequency(baseline, 2))
    for chunk in _vocal_gesture(marker, timing["profile_marker"] * duration_multiplier, volume, cancelled, state, renderer, timbre):
        yield chunk

    for unit in output.phrase.units:
        if unit.kind == "tokens":
            for token in unit.tokens:
                gesture = timing["short_gesture"] if classes[token] == "short" else timing["root_gesture"]
                freqs = tuple(_relative_frequency(baseline, offsets[d]) for d in patterns[token])
                for chunk in _vocal_gesture(freqs, gesture * duration_multiplier, volume, cancelled, state, renderer, timbre):
                    yield chunk
                for chunk in _silence_chunks(timing["token_boundary"] * duration_multiplier, cancelled):
                    yield chunk
        elif unit.kind == "ct2":
            marker = (_relative_frequency(fallback_baseline, -2), _relative_frequency(fallback_baseline, 2))
            for chunk in _vocal_gesture(marker, timing["fallback_marker"] * duration_multiplier, volume, cancelled, state, renderer, timbre):
                yield chunk
            raw = unit.text.encode("utf-8")
            for byte, digits in zip(raw, unit.fallback.units[0].value):
                gap = timing["fallback_sentence_punctuation_gap"] if byte in b".!?" else timing["fallback_minor_punctuation_gap"] if byte in b",;:" else timing["fallback_space_gap"] if byte == 32 else timing["fallback_default_gap"]
                freqs = tuple(_relative_frequency(fallback_baseline, offsets[d]) for d in digits)
                for chunk in _vocal_gesture(freqs, timing["fallback_byte"] * duration_multiplier, volume, cancelled, state, renderer, timbre):
                    yield chunk
                for chunk in _silence_chunks(gap * duration_multiplier, cancelled):
                    yield chunk
            for chunk in _silence_chunks(timing["fallback_boundary"] * duration_multiplier, cancelled):
                yield chunk


def pcm_chunks(output, codec, volume=0.12, duration_multiplier=1, cancelled=lambda: False, tone_style="pure"):
    if type(volume) not in (int, float) or not math.isfinite(volume) or not 0 <= volume <= 0.3:
        raise ValueError("volume must be between 0 and 0.3")
    if tone_style not in {"pure", "resonant", "contour-v1", "vocal-v1"}:
        raise ValueError("tone_style must be pure, resonant, contour-v1 or vocal-v1")
    if isinstance(output, ConversationOutput) and isinstance(output.phrase, Exp003Phrase):
        if tone_style == "contour-v1":
            yield from _exp003_contour_chunks(output, codec, volume, duration_multiplier, cancelled)
            return
        if tone_style == "vocal-v1":
            yield from _exp003_vocal_chunks(output, codec, volume, duration_multiplier, cancelled)
            return
    for frequencies, duration_ms, gap_ms in events(output, codec, duration_multiplier):
        count = round(SAMPLE_RATE * duration_ms / 1000)
        attack_seconds = 0.085 if tone_style == "resonant" else 0.012
        release_seconds = 0.150 if tone_style == "resonant" else 0.060
        attack = max(1, round(SAMPLE_RATE * attack_seconds))
        release = max(1, min(round(SAMPLE_RATE * release_seconds), count // 2))
        for start in range(0, count, 1024):
            if cancelled():
                return
            samples = array("h")
            for i in range(start, min(start + 1024, count)):
                envelope = min(1, i / attack, (count - 1 - i) / release)
                if frequencies:
                    if tone_style == "pure":
                        value = sum(math.sin(2 * math.pi * hz * i / SAMPLE_RATE) for hz in frequencies) / len(frequencies)
                    else:
                        t = i / SAMPLE_RATE
                        vibration = 0.10 * math.sin(2 * math.pi * 3.2 * t)
                        pulse = 0.94 + 0.06 * math.sin(2 * math.pi * 1.35 * t)
                        voices = []
                        for hz in frequencies:
                            phase = 2 * math.pi * hz * t + vibration
                            body = 0.22 * math.sin(0.5 * phase)
                            voices.append((0.72 * math.sin(phase) + body + 0.20 * math.sin(2 * phase) + 0.06 * math.sin(3 * phase)) / 1.20)
                        value = pulse * sum(voices) / len(voices)
                else:
                    value = 0.0
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


def synthesize(output, codec: CspCodec, volume=0.12, duration_multiplier=1, tone_style="pure") -> bytes:
    return b"".join(pcm_chunks(output, codec, volume, duration_multiplier, tone_style=tone_style))


def render_wav(path, output, codec, volume, duration_multiplier, cancelled, tone_style="pure"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        for chunk in pcm_chunks(output, codec, volume, duration_multiplier, cancelled, tone_style):
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
