"""Pinned Chordic EXP-002 runtime adapter with explicit CT2 fallback."""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re

from .conversation import validate_text
from .learning import Phrase, Unit, byte_symbols, unit_text

PROFILE_PATH = Path(__file__).resolve().parents[2] / "experiments" / "chordic" / "exp-002-runtime.json"
VERSION = "EXP-002"

@dataclass(frozen=True)
class Exp002Unit:
    kind: str
    text: str
    tokens: tuple[str, ...] = ()
    fallback: Phrase | None = None

@dataclass(frozen=True)
class Exp002Phrase:
    units: tuple[Exp002Unit, ...]
    source_commit: str
    version: str = VERSION

@lru_cache(maxsize=1)
def load_profile():
    with PROFILE_PATH.open("r", encoding="utf-8") as handle:
        profile = json.load(handle)
    if type(profile) is not dict or profile.get("schema_version") != "0.2":
        raise ValueError("invalid EXP-002 runtime profile")
    if profile.get("candidate", {}).get("candidate_id") != VERSION:
        raise ValueError("wrong EXP-002 candidate id")
    if type(profile.get("source_commit")) is not str or len(profile["source_commit"]) != 40:
        raise ValueError("invalid EXP-002 source commit")
    return profile

def token_patterns():
    result = {}
    for row in load_profile()["candidate"]["tokens"]:
        token = row["id"]
        degrees = tuple(row["scale_degrees"])
        if token in result or not degrees or any(type(d) is not int or not 0 <= d <= 4 for d in degrees):
            raise ValueError("invalid EXP-002 token registry")
        result[token] = degrees
    return result

def registered_cases():
    return tuple(load_profile()["benchmark"]["cases"])

def _registered_map():
    return {row["english"]: tuple(row["tokens"]) for row in registered_cases()}

SURFACE_PATH = Path(__file__).resolve().parents[2] / "experiments" / "chordic" / "exp-002-surfaces.json"

@lru_cache(maxsize=1)
def surface_registry():
    with SURFACE_PATH.open("r", encoding="utf-8") as handle:
        export = json.load(handle)
    if type(export) is not dict or export.get("candidate_id") != VERSION or export.get("export_id") != "EXP-002-surface-runtime-v1":
        raise ValueError("invalid EXP-002 surface export")
    patterns = token_patterns()
    result = {}
    for row in export.get("surface_forms", ()):
        if type(row) is not dict or type(row.get("text")) is not str or not row["text"]:
            raise ValueError("invalid EXP-002 surface row")
        key = row["text"].lower()
        tokens = tuple(row.get("tokens", ()))
        if key in result or not tokens or any(token not in patterns for token in tokens):
            raise ValueError("invalid EXP-002 surface mapping")
        result[key] = tokens
    if not result:
        raise ValueError("empty EXP-002 surface registry")
    return result

@lru_cache(maxsize=1)
def _surface_pattern():
    surfaces = surface_registry()
    return re.compile(
        r"(?<![\w'’])(" + "|".join(re.escape(x) for x in sorted(surfaces, key=len, reverse=True)) + r")(?![\w'’])",
        re.IGNORECASE,
    )

def _encode_ct2_fragment(text: str) -> Phrase:
    """Carry exact UTF-8 fragments, including whitespace-only separators."""
    if type(text) is not str or not text:
        raise ValueError("EXP-002 fallback fragment must be nonempty text")
    return Phrase((Unit("utf8", byte_symbols(text.encode("utf-8"))),))

def _decode_ct2_fragment(phrase: Phrase) -> str:
    if type(phrase) is not Phrase or phrase.version != "CT2" or not phrase.units:
        raise ValueError("invalid EXP-002 CT2 fallback fragment")
    if any(unit.kind != "utf8" for unit in phrase.units):
        raise ValueError("EXP-002 fallback fragment must be exact UTF-8")
    return "".join(unit_text(unit) for unit in phrase.units)

def encode_phrase(text: str) -> Exp002Phrase:
    validate_text(text)
    profile = load_profile()
    patterns = token_patterns()
    registered = _registered_map()
    if text in registered:
        tokens = registered[text]
        if any(token not in patterns for token in tokens):
            raise ValueError("registered EXP-002 case references unknown token")
        return Exp002Phrase((Exp002Unit("tokens", text, tokens=tokens),), profile["source_commit"])
    units = []
    position = 0
    surfaces = surface_registry()
    for match in _surface_pattern().finditer(text):
        surface = match.group()
        tokens = surfaces[surface.lower()]
        if any(token not in patterns for token in tokens):
            continue
        if position < match.start():
            literal = text[position:match.start()]
            units.append(Exp002Unit("ct2", literal, fallback=_encode_ct2_fragment(literal)))
        units.append(Exp002Unit("tokens", surface, tokens=tokens))
        position = match.end()
    if position < len(text):
        literal = text[position:]
        units.append(Exp002Unit("ct2", literal, fallback=_encode_ct2_fragment(literal)))
    if not units:
        units.append(Exp002Unit("ct2", text, fallback=_encode_ct2_fragment(text)))
    phrase = Exp002Phrase(tuple(units), profile["source_commit"])
    if decode_phrase(phrase) != text:
        raise ValueError("EXP-002 adapter round-trip mismatch")
    return phrase

def decode_phrase(phrase: Exp002Phrase) -> str:
    if type(phrase) is not Exp002Phrase or phrase.version != VERSION or not phrase.units:
        raise ValueError("invalid EXP-002 phrase")
    patterns = token_patterns()
    pieces = []
    for unit in phrase.units:
        if type(unit) is not Exp002Unit or not unit.text:
            raise ValueError("invalid EXP-002 unit")
        if unit.kind == "tokens":
            if not unit.tokens or any(token not in patterns for token in unit.tokens) or unit.fallback is not None:
                raise ValueError("invalid EXP-002 token unit")
        elif unit.kind == "ct2":
            if unit.tokens or unit.fallback is None or _decode_ct2_fragment(unit.fallback) != unit.text:
                raise ValueError("invalid EXP-002 fallback unit")
        else:
            raise ValueError("unknown EXP-002 unit kind")
        pieces.append(unit.text)
    return validate_text("".join(pieces))

def learning_rows(phrase: Exp002Phrase):
    decode_phrase(phrase)
    return [
        (unit.text, " ".join(unit.tokens) if unit.kind == "tokens" else "CT2 exact fallback")
        for unit in phrase.units
    ]
