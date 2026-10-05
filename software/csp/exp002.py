"""Pinned Chordic EXP-002 runtime adapter with explicit CT2 fallback."""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re

from .conversation import validate_text
from .learning import Phrase, encode_phrase as encode_ct2_phrase, decode_phrase as decode_ct2_phrase

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

_SURFACES = {
    "thank you": ("SOCIAL.THANK_YOU",), "fist my bump": ("SOCIAL.FIST_BUMP",),
    "do not": ("GRAM.NEG",), "don't": ("GRAM.NEG",),
    "yes": ("SOCIAL.YES",), "no": ("SOCIAL.NO",), "hello": ("SOCIAL.HELLO",),
    "goodbye": ("SOCIAL.GOODBYE",), "help": ("ACTION.HELP",), "stop": ("ACTION.STOP",),
    "wait": ("ACTION.WAIT",), "come": ("ACTION.COME",), "go": ("ACTION.GO",),
    "good": ("QUALITY.GOOD",), "bad": ("QUALITY.BAD",), "ready": ("QUALITY.READY",),
    "like": ("MENTAL.LIKE",), "understand": ("MENTAL.UNDERSTAND",),
    "happen": ("EVENT.HAPPEN",), "happened": ("GRAM.PAST", "EVENT.HAPPEN"),
    "find": ("ACTION.FIND",), "found": ("GRAM.PAST", "ACTION.FIND"),
    "need": ("STATE.NEED",), "fix": ("ACTION.FIX",), "please": ("SOCIAL.PLEASE",),
    "sorry": ("SOCIAL.SORRY",), "repeat": ("ACTION.REPEAT",), "what": ("QUESTION.WHAT",),
    "now": ("TIME.NOW",), "amaze": ("EMOTION.AMAZE",), "voice": ("ENTITY.VOICE",),
    "fear": ("EMOTION.FEAR",), "scary": ("GRAM.VERY", "EMOTION.FEAR"),
    "robot": ("ENTITY.ROBOT",), "music": ("ENTITY.MUSIC",), "computer": ("ENTITY.COMPUTER",),
    "project": ("ENTITY.PROJECT",), "watch": ("ACTION.WATCH",),
    "watched": ("GRAM.PAST", "ACTION.WATCH"), "crew": ("ENTITY.CREW",),
    "die": ("EVENT.DIE",), "died": ("GRAM.PAST", "EVENT.DIE"), "say": ("ACTION.SAY",),
    "said": ("GRAM.PAST", "ACTION.SAY"), "rocky": ("ENTITY.ROCKY",),
    "grace": ("ENTITY.GRACE",), "earth": ("ENTITY.EARTH",), "space": ("ENTITY.SPACE",),
    "more": ("QUANT.MORE",), "less": ("QUANT.LESS",), "i": ("PRON.I",),
    "you": ("PRON.YOU",), "we": ("PRON.WE",), "it": ("PRON.IT",),
    "this": ("PRON.THIS",), "that": ("PRON.THAT",), "not": ("GRAM.NEG",),
    "will": ("GRAM.FUT",), "should": ("GRAM.SHOULD",), "very": ("GRAM.VERY",),
    "and": ("GRAM.AND",), "if": ("GRAM.IF",), "here": ("LOC.HERE",),
    "where": ("LOC.WHERE",),
}
_PATTERN = re.compile(
    r"(?<![\w'’])(" + "|".join(re.escape(x) for x in sorted(_SURFACES, key=len, reverse=True)) + r")(?![\w'’])",
    re.IGNORECASE,
)

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
    for match in _PATTERN.finditer(text):
        surface = match.group()
        tokens = _SURFACES[surface.lower()]
        if any(token not in patterns for token in tokens):
            continue
        if position < match.start():
            literal = text[position:match.start()]
            units.append(Exp002Unit("ct2", literal, fallback=encode_ct2_phrase(literal)))
        units.append(Exp002Unit("tokens", surface, tokens=tokens))
        position = match.end()
    if position < len(text):
        literal = text[position:]
        units.append(Exp002Unit("ct2", literal, fallback=encode_ct2_phrase(literal)))
    if not units:
        units.append(Exp002Unit("ct2", text, fallback=encode_ct2_phrase(text)))
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
            if unit.tokens or unit.fallback is None or decode_ct2_phrase(unit.fallback) != unit.text:
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
