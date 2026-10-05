"""Portable Rocky asset verification and explicit user-data backup.

Model weights and virtual environments are deliberately excluded. External file
assets can be pinned by SHA-256 without Rocky downloading them.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


ASSET_SCHEMA_VERSION = 1
BACKUP_SCHEMA_VERSION = 1
BACKUP_FORMAT = "rocky-user-backup-v1"
MAX_BACKUP_SOURCE_BYTES = 512 * 1024
_ALLOWED_BACKUP_NAMES = {
    "settings/rocky.json",
    "settings/personality.json",
    "settings/personality.txt",
    "memory/memory-v1.json",
}


class PortabilityError(ValueError):
    pass


def _strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PortabilityError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise PortabilityError("non-finite JSON number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sha256(value: object, *, allow_empty: bool = False) -> str:
    if value == "" and allow_empty:
        return ""
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise PortabilityError("sha256 must be 64 lowercase hexadecimal characters")
    return value


def load_asset_manifest(path: Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 128 * 1024:
        raise PortabilityError("asset manifest is missing or too large")
    data = _strict_json(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {
        "schema_version",
        "manifest_id",
        "assets",
    }:
        raise PortabilityError("invalid asset manifest shape")
    if data["schema_version"] != ASSET_SCHEMA_VERSION:
        raise PortabilityError("unsupported asset manifest schema")
    if data["manifest_id"] != "rocky-assets-v1":
        raise PortabilityError("unexpected asset manifest id")
    if type(data["assets"]) is not list or len(data["assets"]) > 32:
        raise PortabilityError("asset manifest must contain at most 32 assets")
    seen = set()
    for asset in data["assets"]:
        if type(asset) is not dict or set(asset) != {
            "id",
            "kind",
            "required",
            "reference",
            "path",
            "sha256",
        }:
            raise PortabilityError("invalid asset entry")
        asset_id = asset["id"]
        if (
            type(asset_id) is not str
            or not asset_id
            or len(asset_id) > 64
            or not asset_id.replace("_", "").replace("-", "").isalnum()
        ):
            raise PortabilityError("invalid asset id")
        if asset_id in seen:
            raise PortabilityError("duplicate asset id")
        seen.add(asset_id)
        if asset["kind"] not in {"file", "ollama_model", "windows_voice"}:
            raise PortabilityError("unsupported asset kind")
        if type(asset["required"]) is not bool:
            raise PortabilityError("asset required must be boolean")
        for field in ("reference", "path"):
            value = asset[field]
            if type(value) is not str or len(value) > 1000 or any(ord(c) < 32 for c in value):
                raise PortabilityError(f"invalid asset {field}")
        if asset["kind"] == "file":
            if asset["path"]:
                _validate_sha256(asset["sha256"])
            else:
                _validate_sha256(asset["sha256"], allow_empty=True)
        elif asset["sha256"]:
            # Runtime-managed model/voice identities are not file-verifiable here.
            raise PortabilityError(
                "runtime-managed assets must not claim an unverified file checksum"
            )
        if asset["kind"] != "file" and not asset["reference"]:
            raise PortabilityError("runtime-managed asset requires reference")
    return data


def verify_asset_manifest(path: Path) -> dict:
    manifest_path = Path(path)
    data = load_asset_manifest(manifest_path)
    base = manifest_path.parent
    rows = []
    failed = 0
    for asset in data["assets"]:
        row = {
            "id": asset["id"],
            "kind": asset["kind"],
            "required": asset["required"],
        }
        if asset["kind"] != "file":
            row.update(
                {
                    "status": "RUNTIME_REFERENCE",
                    "reference": asset["reference"],
                    "verified": False,
                }
            )
            rows.append(row)
            continue
        if not asset["path"]:
            status = "MISSING_REQUIRED_PATH" if asset["required"] else "NOT_CONFIGURED"
            if asset["required"]:
                failed += 1
            row.update({"status": status, "verified": False})
            rows.append(row)
            continue
        target = Path(asset["path"]).expanduser()
        if not target.is_absolute():
            target = (base / target).resolve()
        if not target.is_file():
            failed += 1
            row.update({"status": "MISSING_FILE", "verified": False})
            rows.append(row)
            continue
        actual = sha256_file(target)
        expected = asset["sha256"]
        ok = actual == expected
        if not ok:
            failed += 1
        row.update(
            {
                "status": "VERIFIED" if ok else "CHECKSUM_MISMATCH",
                "verified": ok,
                "sha256": actual,
                "size_bytes": target.stat().st_size,
            }
        )
        rows.append(row)
    return {
        "manifest_id": data["manifest_id"],
        "failed": failed,
        "assets": rows,
    }


def _backup_source(path: Path, archive_name: str):
    path = Path(path)
    if archive_name not in _ALLOWED_BACKUP_NAMES:
        raise PortabilityError("backup archive path is not allowlisted")
    if not path.is_file():
        return None
    if path.is_symlink():
        raise PortabilityError("backup source must not be a symbolic link")
    size = path.stat().st_size
    if size > MAX_BACKUP_SOURCE_BYTES:
        raise PortabilityError("backup source exceeds bounded size")
    raw = path.read_bytes()
    return {
        "archive_name": archive_name,
        "raw": raw,
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def export_user_backup(
    *,
    settings_path: Path,
    personality_path: Path,
    memory_path: Path,
    output_path: Path,
) -> dict:
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".zip":
        raise PortabilityError("backup output must use .zip")
    personality_path = Path(personality_path)
    personality_name = (
        "settings/personality.txt"
        if personality_path.suffix.lower() == ".txt"
        else "settings/personality.json"
    )
    sources = [
        _backup_source(Path(settings_path), "settings/rocky.json"),
        _backup_source(personality_path, personality_name),
        _backup_source(Path(memory_path), "memory/memory-v1.json"),
    ]
    sources = [source for source in sources if source is not None]
    if not sources:
        raise PortabilityError("no Rocky user files were available to back up")
    if len({source["archive_name"] for source in sources}) != len(sources):
        raise PortabilityError("duplicate backup archive path")

    manifest = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "format": BACKUP_FORMAT,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [
            {
                "path": source["archive_name"],
                "size_bytes": source["size_bytes"],
                "sha256": source["sha256"],
            }
            for source in sources
        ],
        "excludes": [
            "model weights",
            "voice/STT model files",
            "virtual environments",
            "conversation audio/logs",
            "OAuth/API credentials",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            )
            for source in sources:
                archive.writestr(source["archive_name"], source["raw"])
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return verify_user_backup(output_path)


def verify_user_backup(path: Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise PortabilityError("backup is missing or exceeds safe archive size")
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if (
            len(names) != len(set(names))
            or "manifest.json" not in names
            or any(
                name == ""
                or name.startswith("/")
                or "\\" in name
                or ".." in Path(name).parts
                for name in names
            )
        ):
            raise PortabilityError("backup contains unsafe archive paths")
        if set(names) - (_ALLOWED_BACKUP_NAMES | {"manifest.json"}):
            raise PortabilityError("backup contains non-Rocky files")
        manifest_raw = archive.read("manifest.json")
        if len(manifest_raw) > 128 * 1024:
            raise PortabilityError("backup manifest is too large")
        manifest = _strict_json(manifest_raw.decode("utf-8"))
        if type(manifest) is not dict or set(manifest) != {
            "schema_version",
            "format",
            "created_at",
            "files",
            "excludes",
        }:
            raise PortabilityError("invalid backup manifest shape")
        if (
            manifest["schema_version"] != BACKUP_SCHEMA_VERSION
            or manifest["format"] != BACKUP_FORMAT
            or type(manifest["files"]) is not list
            or len(manifest["files"]) > 3
        ):
            raise PortabilityError("invalid backup manifest")
        expected_names = {"manifest.json"}
        rows = []
        for item in manifest["files"]:
            if type(item) is not dict or set(item) != {"path", "size_bytes", "sha256"}:
                raise PortabilityError("invalid backup file record")
            name = item["path"]
            if name not in _ALLOWED_BACKUP_NAMES:
                raise PortabilityError("backup file is not allowlisted")
            _validate_sha256(item["sha256"])
            if type(item["size_bytes"]) is not int or item["size_bytes"] < 0:
                raise PortabilityError("invalid backup file size")
            raw = archive.read(name)
            actual = hashlib.sha256(raw).hexdigest()
            if len(raw) != item["size_bytes"] or actual != item["sha256"]:
                raise PortabilityError("backup checksum or size mismatch")
            expected_names.add(name)
            rows.append(
                {
                    "path": name,
                    "size_bytes": len(raw),
                    "sha256": actual,
                    "verified": True,
                }
            )
        if set(names) != expected_names:
            raise PortabilityError("backup contents do not match manifest")
    return {
        "format": BACKUP_FORMAT,
        "verified": True,
        "files": rows,
    }
