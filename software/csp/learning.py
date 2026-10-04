"""CT2: small stable lexical overlay, with exact UTF-8 fallback; not an audio decoder."""
from dataclasses import dataclass
import re

from .conversation import validate_text

VERSION = "CT2"
# Never reassign these meanings. Pitches remain owned by the released CSP YAML.
WORDS = {
    "hello": "SOCIAL.hello", "goodbye": "SOCIAL.goodbye",
    "yes": "SOCIAL.yes", "no": "SOCIAL.no", "help": "ACTION.help",
    "thank you": "SOCIAL.thank_you", "please": "SOCIAL.please",
    "sorry": "SOCIAL.sorry", "ready": "QUALITY.ready",
    "wait": "ACTION.wait", "repeat": "ACTION.repeat",
    "robot": "ENTITY.robot", "music": "ENTITY.music",
    "computer": "ENTITY.computer", "project": "ENTITY.project",
}
TOKEN_TEXT = {token: word for word, token in WORDS.items()}
# Apostrophes and underscores are word constituents: don't interpret "no" in "no's".
_PATTERN = re.compile(r"(?<![\w'’])(" + "|".join(re.escape(w) for w in sorted(WORDS, key=len, reverse=True)) + r")(?![\w'’])", re.IGNORECASE)


@dataclass(frozen=True)
class Unit:
    kind: str  # token or utf8
    value: str | tuple[tuple[int, ...], ...]
    case: str = "lower"


@dataclass(frozen=True)
class Phrase:
    units: tuple[Unit, ...]
    version: str = VERSION


def byte_symbols(raw: bytes):
    return tuple(tuple((b // (5 ** n)) % 5 for n in (3, 2, 1, 0)) for b in raw)


def literal_text(symbols):
    if type(symbols) is not tuple or not symbols or len(symbols) > 384:
        raise ValueError("invalid CT2 literal length")
    raw = bytearray()
    for digits in symbols:
        if type(digits) is not tuple or len(digits) != 4 or any(type(d) is not int or not 0 <= d <= 4 for d in digits):
            raise ValueError("invalid CT2 UTF-8 digit")
        value = sum(d * 5 ** n for d, n in zip(digits, (3, 2, 1, 0)))
        if value > 255:
            raise ValueError("invalid CT2 byte")
        raw.append(value)
    return raw.decode("utf-8")


def unit_text(unit):
    if type(unit) is not Unit:
        raise ValueError("invalid CT2 unit")
    if unit.kind == "utf8" and unit.case == "lower":
        return literal_text(unit.value)
    if unit.kind != "token" or type(unit.value) is not str or unit.value not in TOKEN_TEXT:
        raise ValueError("unknown CT2 token")
    word = TOKEN_TEXT[unit.value]
    if unit.case == "lower":
        return word
    if unit.case == "initial":
        return word[0].upper() + word[1:]
    if unit.case == "upper":
        return word.upper()
    raise ValueError("invalid CT2 case")


def encode_phrase(text):
    validate_text(text)
    units = []
    position = 0
    for match in _PATTERN.finditer(text):
        surface = match.group()
        word = surface.lower()
        if word not in WORDS:
            continue
        case = next((c for c, s in (("lower", word), ("initial", word[0].upper() + word[1:]), ("upper", word.upper())) if surface == s), None)
        if case is None:  # Mixed case is exact literal fallback, never normalized away.
            continue
        if position < match.start():
            units.append(Unit("utf8", byte_symbols(text[position:match.start()].encode("utf-8"))))
        units.append(Unit("token", WORDS[word], case))
        position = match.end()
    if position < len(text):
        units.append(Unit("utf8", byte_symbols(text[position:].encode("utf-8"))))
    return Phrase(tuple(units))


def decode_phrase(phrase):
    if type(phrase) is not Phrase or phrase.version != VERSION or type(phrase.units) is not tuple or not 1 <= len(phrase.units) <= 384:
        raise ValueError("invalid CT2 version/units")
    return validate_text("".join(unit_text(unit) for unit in phrase.units))
