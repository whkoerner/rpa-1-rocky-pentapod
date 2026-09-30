"""Deterministic token encoder/decoder for CSP-1.

This module intentionally does not generate arbitrary music. Every returned note
belongs to a versioned lexical token and every accepted token passes its checksum.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


class DecodeError(ValueError):
    """Raised when a musical token cannot be decoded without guessing."""


@dataclass(frozen=True)
class TokenEncoding:
    token: str
    class_name: str
    concept: str
    class_index: int
    lexical_code: int
    checksum: int
    notes: tuple[str, ...]


class CspCodec:
    TOKEN_NOTE_COUNT = 5

    def __init__(self, specification: dict[str, Any]) -> None:
        self.specification = specification
        self.classes: dict[str, dict[str, Any]] = specification["classes"]
        self.lexicon: dict[str, dict[str, list[str]]] = specification["lexicon"]
        self.radix = int(specification["token_encoding"]["lexical_radix"])

        pitch_symbols = specification["phonology"]["pitch_symbols"]
        self.digit_to_note = {
            int(value["digit"]): str(value["note"])
            for value in pitch_symbols.values()
        }
        self.note_to_digit = {note: digit for digit, note in self.digit_to_note.items()}

        if set(self.digit_to_note) != set(range(self.radix)):
            raise ValueError("Pitch-symbol digits do not cover the configured radix")

    @classmethod
    def from_file(cls, path: str | Path) -> "CspCodec":
        with Path(path).open("r", encoding="utf-8") as source:
            specification = yaml.safe_load(source)
        return cls(specification)

    @classmethod
    def from_default_spec(cls) -> "CspCodec":
        repository_root = Path(__file__).resolve().parents[2]
        return cls.from_file(
            repository_root / "language" / "specification" / "csp_v0_1.yaml"
        )

    def encode_token(self, token: str) -> TokenEncoding:
        try:
            class_name, concept = token.split(".", maxsplit=1)
        except ValueError as exc:
            raise ValueError("Token must use CLASS.concept syntax") from exc

        if class_name not in self.classes or class_name not in self.lexicon:
            raise ValueError(f"Unknown CSP class: {class_name}")

        concepts = self.lexicon[class_name]["concepts"]
        try:
            lexical_code = concepts.index(concept)
        except ValueError as exc:
            raise ValueError(f"Unknown CSP concept: {token}") from exc

        first_digit, second_digit = divmod(lexical_code, self.radix)
        if first_digit >= self.radix:
            raise ValueError(f"Lexical code is outside the two-digit radix: {token}")

        class_index = int(self.classes[class_name]["index"])
        checksum = (class_index + first_digit + second_digit) % self.radix
        prefix = tuple(str(note) for note in self.classes[class_name]["prefix_notes"])
        notes = prefix + (
            self.digit_to_note[first_digit],
            self.digit_to_note[second_digit],
            self.digit_to_note[checksum],
        )
        return TokenEncoding(
            token=token,
            class_name=class_name,
            concept=concept,
            class_index=class_index,
            lexical_code=lexical_code,
            checksum=checksum,
            notes=notes,
        )

    def decode_token(self, notes: Iterable[str]) -> TokenEncoding:
        note_tuple = tuple(notes)
        if len(note_tuple) != self.TOKEN_NOTE_COUNT:
            raise DecodeError(
                f"Expected {self.TOKEN_NOTE_COUNT} notes, received {len(note_tuple)}"
            )

        prefix = note_tuple[:2]
        matching_classes = [
            class_name
            for class_name, details in self.classes.items()
            if tuple(str(note) for note in details["prefix_notes"]) == prefix
        ]
        if len(matching_classes) != 1:
            raise DecodeError(f"Unknown or ambiguous class prefix: {prefix}")

        class_name = matching_classes[0]
        try:
            first_digit, second_digit, received_checksum = (
                self.note_to_digit[note] for note in note_tuple[2:]
            )
        except KeyError as exc:
            raise DecodeError(f"Unknown lexical pitch: {exc.args[0]}") from exc

        class_index = int(self.classes[class_name]["index"])
        expected_checksum = (class_index + first_digit + second_digit) % self.radix
        if received_checksum != expected_checksum:
            raise DecodeError(
                f"Checksum mismatch: expected {expected_checksum}, received "
                f"{received_checksum}"
            )

        lexical_code = first_digit * self.radix + second_digit
        concepts = self.lexicon[class_name]["concepts"]
        if lexical_code >= len(concepts):
            raise DecodeError(
                f"Unassigned lexical code {lexical_code} in class {class_name}"
            )

        concept = concepts[lexical_code]
        token = f"{class_name}.{concept}"
        return TokenEncoding(
            token=token,
            class_name=class_name,
            concept=concept,
            class_index=class_index,
            lexical_code=lexical_code,
            checksum=expected_checksum,
            notes=note_tuple,
        )

    def tokens(self) -> Iterable[str]:
        for class_name, details in self.lexicon.items():
            for concept in details["concepts"]:
                yield f"{class_name}.{concept}"
