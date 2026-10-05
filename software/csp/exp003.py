"""Pinned Chordic EXP-003 runtime adapter with explicit lexical fallback and coverage telemetry."""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re

from .conversation import validate_text
from .learning import Phrase, Unit, byte_symbols, unit_text

PROFILE_PATH = Path(__file__).resolve().parents[2] / "experiments" / "chordic" / "exp-003-runtime-v2.json"
VERSION = "EXP-003"
SOURCE_COMMIT = "e618b39150c7f318b7a0da51408062ca9eb43ad9"
_WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")

@dataclass(frozen=True)
class Exp003Unit:
    kind: str
    text: str
    tokens: tuple[str, ...] = ()
    fallback: Phrase | None = None

@dataclass(frozen=True)
class Exp003Phrase:
    units: tuple[Exp003Unit, ...]
    source_commit: str = SOURCE_COMMIT
    version: str = VERSION

@lru_cache(maxsize=1)
def load_profile():
    with PROFILE_PATH.open("r", encoding="utf-8") as handle:
        profile = json.load(handle)
    if type(profile) is not dict or profile.get("schema_version") != "0.3":
        raise ValueError("invalid EXP-003 runtime profile")
    if profile.get("candidate_id") != VERSION or profile.get("export_id") != "EXP-003-runtime-v2":
        raise ValueError("wrong EXP-003 runtime export")
    candidate = profile.get("candidate", {})
    if candidate.get("candidate_id") != VERSION:
        raise ValueError("wrong EXP-003 candidate")
    return profile

def token_patterns():
    result = {}
    for row in load_profile()["candidate"]["tokens"]:
        token = row["id"]
        contour = tuple(row["contour_code"])
        if token in result or len(contour) != 4 or any(type(x) is not int or not 0 <= x <= 4 for x in contour):
            raise ValueError("invalid EXP-003 contour registry")
        result[token] = contour
    return result

@lru_cache(maxsize=1)
def surface_registry():
    profile = load_profile()
    patterns = token_patterns()
    result = {}
    for row in profile["surface_forms"]:
        key = row["text"].lower()
        tokens = tuple(row["tokens"])
        if not key or key in result or not tokens or any(token not in patterns for token in tokens):
            raise ValueError("invalid EXP-003 surface mapping")
        result[key] = tokens
    return result

def _digit_tokens(value):
    return tuple("NUM." + digit for digit in str(value))

def _encode_ct2_fragment(text):
    return Phrase((Unit("utf8", byte_symbols(text.encode("utf-8"))),))

def _decode_ct2_fragment(phrase):
    if type(phrase) is not Phrase or phrase.version != "CT2" or any(unit.kind != "utf8" for unit in phrase.units):
        raise ValueError("invalid EXP-003 CT2 fallback")
    return "".join(unit_text(unit) for unit in phrase.units)

def encode_phrase(text):
    validate_text(text)
    profile = load_profile()
    surfaces = surface_registry()
    ignored = set(profile["ignore_forms"])
    words = list(_WORD.finditer(text))
    units = []
    cursor = 0
    i = 0
    while i < len(words):
        word = words[i]
        if cursor < word.start():
            gap = text[cursor:word.start()]
            units.append(Exp003Unit("tokens" if "?" in gap else "format", gap, tokens=(("GRAM.Q",) if "?" in gap else ())))
        matched = None
        for count in range(min(4, len(words) - i), 0, -1):
            start = words[i].start()
            end = words[i + count - 1].end()
            surface = text[start:end]
            tokens = surfaces.get(surface.lower())
            if tokens is not None:
                matched = (count, surface, tokens, end)
                break
        if matched is not None:
            count, surface, tokens, end = matched
            units.append(Exp003Unit("tokens", surface, tokens=tokens))
            cursor = end
            i += count
            continue
        surface = word.group()
        lower = surface.lower()
        number_rule = profile["number_rule"]
        spoken_units = number_rule.get("spoken_units", {})
        spoken_tens = number_rule.get("spoken_tens", {})
        if surface.isdigit() and len(surface) <= number_rule["max_digits"]:
            units.append(Exp003Unit("tokens", surface, tokens=tuple("NUM." + digit for digit in surface)))
            cursor = word.end()
            i += 1
            continue
        if lower in spoken_tens:
            value = spoken_tens[lower]
            end_index = i
            if i + 1 < len(words):
                next_lower = words[i + 1].group().lower()
                if next_lower in spoken_units and 1 <= spoken_units[next_lower] <= 9:
                    value += spoken_units[next_lower]
                    end_index = i + 1
            end = words[end_index].end()
            number_text = text[word.start():end]
            units.append(Exp003Unit("tokens", number_text, tokens=_digit_tokens(value)))
            cursor = end
            i = end_index + 1
            continue
        if lower in spoken_units:
            units.append(Exp003Unit("tokens", surface, tokens=_digit_tokens(spoken_units[lower])))
        elif lower in ignored:
            units.append(Exp003Unit("grammar", surface))
        else:
            units.append(Exp003Unit("ct2", surface, fallback=_encode_ct2_fragment(surface)))
        cursor = word.end()
        i += 1
    if cursor < len(text):
        tail = text[cursor:]
        units.append(Exp003Unit("tokens" if "?" in tail else "format", tail, tokens=(("GRAM.Q",) if "?" in tail else ())))
    if not units:
        units.append(Exp003Unit("format", text))
    phrase = Exp003Phrase(tuple(units))
    if decode_phrase(phrase) != text:
        raise ValueError("EXP-003 adapter round-trip mismatch")
    return phrase

def decode_phrase(phrase):
    if type(phrase) is not Exp003Phrase or phrase.version != VERSION or not phrase.units:
        raise ValueError("invalid EXP-003 phrase")
    patterns = token_patterns()
    pieces = []
    for unit in phrase.units:
        if type(unit) is not Exp003Unit:
            raise ValueError("invalid EXP-003 unit")
        if unit.kind == "tokens":
            if any(token not in patterns for token in unit.tokens) or unit.fallback is not None:
                raise ValueError("invalid EXP-003 semantic unit")
        elif unit.kind in {"grammar", "format"}:
            if unit.tokens or unit.fallback is not None:
                raise ValueError("invalid EXP-003 framing unit")
        elif unit.kind == "ct2":
            if unit.tokens or unit.fallback is None or _decode_ct2_fragment(unit.fallback) != unit.text:
                raise ValueError("invalid EXP-003 fallback unit")
        else:
            raise ValueError("unknown EXP-003 unit kind")
        pieces.append(unit.text)
    return validate_text("".join(pieces))

def coverage(phrase):
    decode_phrase(phrase)
    semantic_tokens = sum(len(unit.tokens) for unit in phrase.units)
    fallback = [unit for unit in phrase.units if unit.kind == "ct2"]
    semantic_bytes = sum(len(unit.text.encode("utf-8")) for unit in phrase.units if unit.kind in {"tokens", "grammar"} and unit.text.strip())
    fallback_bytes = sum(len(unit.text.encode("utf-8")) for unit in fallback)
    denominator = semantic_bytes + fallback_bytes
    semantic_percent = 100.0 if not denominator else 100.0 * semantic_bytes / denominator
    return {
        "semantic_tokens": semantic_tokens,
        "fallback_spans": len(fallback),
        "fallback_bytes": fallback_bytes,
        "semantic_percent": round(semantic_percent, 1),
        "fallback_percent": round(100.0 - semantic_percent, 1),
    }

def learning_rows(phrase):
    decode_phrase(phrase)
    rows = []
    for unit in phrase.units:
        if unit.kind == "tokens" and unit.tokens:
            rows.append((unit.text, " ".join(unit.tokens)))
        elif unit.kind == "ct2":
            rows.append((unit.text, "CT2 exact fallback"))
    return rows
