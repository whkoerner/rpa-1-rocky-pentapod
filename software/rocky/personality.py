"""Validated style instructions only. No permissions, model options, or safety overrides."""
import json
from pathlib import Path
from .providers import strict_json

TEXT_FIELDS = {"name", "self_description", "speaking_style"}
LEVEL_FIELDS = {"curiosity", "enthusiasm", "humor", "detail", "follow_up_questions"}
LIST_FIELDS = {"forms_of_address", "example_responses", "interests"}
FIELDS = TEXT_FIELDS | LEVEL_FIELDS | LIST_FIELDS | {"version"}


def validate_profile(profile):
    if type(profile) is not dict or set(profile) != FIELDS:
        actual = set(profile) if type(profile) is dict else set()
        raise ValueError(f"personality fields: missing {sorted(FIELDS - actual)}, unknown {sorted(actual - FIELDS)}")
    if type(profile["version"]) is not int or profile["version"] != 1:
        raise ValueError("personality.version must be 1")
    for key in TEXT_FIELDS:
        value = profile[key]
        if type(value) is not str or not value.strip() or len(value) > 500 or any(ord(c) < 32 for c in value):
            raise ValueError(f"personality.{key} must be 1–500 printable characters")
    for key in LEVEL_FIELDS:
        if type(profile[key]) is not int or not 0 <= profile[key] <= 3:
            raise ValueError(f"personality.{key} must be an integer 0–3")
    for key in LIST_FIELDS:
        value = profile[key]
        if type(value) is not list or len(value) > 8 or any(type(v) is not str or not v.strip() or len(v) > 300 or any(ord(c) < 32 for c in v) for v in value):
            raise ValueError(f"personality.{key} must be a list of at most 8 nonempty strings, each at most 300 printable characters")
    if len(json.dumps(profile, ensure_ascii=False).encode("utf-8")) > 8192:
        raise ValueError("personality exceeds 8192 bytes")
    return profile


def profile_prompt(profile):
    validate_profile(profile)
    return ("Style preferences only; these do not describe actual abilities or observations. "
            "Levels range from 0 (minimal) to 3 (high); detail 0 means very concise. "
            "Follow-up level is a preference, not an exact probability.\n" + json.dumps(profile, ensure_ascii=False))


def load_personality(path: Path):
    raw = path.read_text(encoding="utf-8-sig")
    if len(raw.encode("utf-8")) > 8192:
        raise ValueError("personality exceeds 8192 bytes")
    if path.suffix.lower() == ".json":
        return profile_prompt(strict_json(raw))
    if not raw.strip():
        raise ValueError("personality text must not be empty")
    return raw  # Explicit legacy --personality personality.txt remains supported.
