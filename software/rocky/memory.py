"""Opt-in, provenance-aware persistent user memory for Rocky.

The language model cannot write this store. Only explicit user-interface actions
call remember/forget/clear. Memory values are user statements, never sensors,
tool results, system instructions, or physical evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re


SCHEMA_VERSION = 1
MAX_ITEMS = 100
MAX_VALUE_BYTES = 512
_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_FORBIDDEN_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "oauth",
    "credential",
    "private_key",
)


class MemoryError(ValueError):
    pass


@dataclass(frozen=True)
class MemoryItem:
    key: str
    value: str
    provenance: str
    created_at: str
    updated_at: str


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise MemoryError("duplicate memory JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise MemoryError("non-finite memory JSON number")

    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
    )


def _validate_key(key: object) -> str:
    if type(key) is not str:
        raise MemoryError("memory key must be a string")
    key = key.strip()
    if not _KEY.fullmatch(key):
        raise MemoryError(
            "memory key must start with a letter and use only letters, numbers, _, . or -"
        )
    lowered = key.lower()
    if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
        raise MemoryError("credential/secret-like keys are not allowed in Rocky memory")
    return key


def _validate_value(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise MemoryError("memory value must be a nonempty string")
    value = value.strip()
    if len(value.encode("utf-8")) > MAX_VALUE_BYTES:
        raise MemoryError(
            f"memory value exceeds {MAX_VALUE_BYTES} UTF-8 bytes"
        )
    if "\x00" in value or any(
        ord(char) < 32 and char not in ("\n", "\t") for char in value
    ):
        raise MemoryError("memory value contains control characters")
    return value


class MemoryStore:
    def __init__(self, path: Path, *, enabled: bool = False):
        self.path = Path(path)
        self.enabled = False
        self.revision = 0
        self._items: dict[str, MemoryItem] = {}
        self._loaded = False
        if enabled:
            self.set_enabled(True)

    def set_enabled(self, enabled: bool):
        if type(enabled) is not bool:
            raise MemoryError("memory enabled state must be boolean")
        if enabled and not self._loaded:
            self._load()
        self.enabled = enabled

    def _load(self):
        if not self.path.exists():
            self._items = {}
            self.revision = 0
            self._loaded = True
            return
        if self.path.stat().st_size > 128 * 1024:
            raise MemoryError("memory file exceeds safe size limit")
        data = _strict_json(self.path.read_text(encoding="utf-8"))
        if type(data) is not dict or set(data) != {
            "schema_version",
            "revision",
            "items",
        }:
            raise MemoryError("invalid memory file shape")
        if data["schema_version"] != SCHEMA_VERSION:
            raise MemoryError("unsupported memory schema version")
        if type(data["revision"]) is not int or data["revision"] < 0:
            raise MemoryError("invalid memory revision")
        if type(data["items"]) is not list or len(data["items"]) > MAX_ITEMS:
            raise MemoryError("invalid memory item list")
        items = {}
        for raw in data["items"]:
            if type(raw) is not dict or set(raw) != {
                "key",
                "value",
                "provenance",
                "created_at",
                "updated_at",
            }:
                raise MemoryError("invalid memory item")
            key = _validate_key(raw["key"])
            value = _validate_value(raw["value"])
            if raw["provenance"] != "user_statement":
                raise MemoryError("unsupported memory provenance")
            if (
                type(raw["created_at"]) is not str
                or type(raw["updated_at"]) is not str
            ):
                raise MemoryError("invalid memory timestamps")
            normalized = key.lower()
            if normalized in items:
                raise MemoryError("duplicate memory key")
            items[normalized] = MemoryItem(
                key,
                value,
                "user_statement",
                raw["created_at"],
                raw["updated_at"],
            )
        self._items = items
        self.revision = data["revision"]
        self._loaded = True

    def _require_enabled(self):
        if not self.enabled:
            raise MemoryError(
                "persistent memory is OFF; enable it explicitly before changing memory"
            )
        if not self._loaded:
            self._load()

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "revision": self.revision,
            "items": [
                asdict(item)
                for item in sorted(self._items.values(), key=lambda row: row.key.lower())
            ],
        }
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def remember(self, key: object, value: object) -> MemoryItem:
        self._require_enabled()
        key = _validate_key(key)
        value = _validate_value(value)
        normalized = key.lower()
        existing = self._items.get(normalized)
        if existing is None and len(self._items) >= MAX_ITEMS:
            raise MemoryError(f"memory is limited to {MAX_ITEMS} items")
        now = _now()
        item = MemoryItem(
            key=key,
            value=value,
            provenance="user_statement",
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._items[normalized] = item
        self.revision += 1
        self._write()
        return item

    def forget(self, key: object) -> bool:
        self._require_enabled()
        key = _validate_key(key)
        removed = self._items.pop(key.lower(), None)
        if removed is None:
            return False
        self.revision += 1
        self._write()
        return True

    def clear(self):
        self._require_enabled()
        self._items.clear()
        self.revision += 1
        self._write()

    def items(self) -> tuple[MemoryItem, ...]:
        if not self.enabled:
            return ()
        if not self._loaded:
            self._load()
        return tuple(
            sorted(self._items.values(), key=lambda item: item.key.lower())
        )

    def prompt_rows(self) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            (item.key, item.value, item.provenance)
            for item in self.items()
        )

    def status(self):
        return {
            "enabled": self.enabled,
            "revision": self.revision if self._loaded else 0,
            "count": len(self._items) if self.enabled and self._loaded else 0,
            "path": str(self.path),
        }
