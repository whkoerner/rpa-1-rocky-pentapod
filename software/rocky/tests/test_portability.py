"""Portable asset-manifest and user-backup tests."""

from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import zipfile

from rocky.portability import (
    PortabilityError,
    export_user_backup,
    verify_asset_manifest,
    verify_user_backup,
)


class PortabilityTests(unittest.TestCase):
    def test_file_asset_checksum_is_verified_without_download(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "whisper model.bin"
            asset.write_bytes(b"local model fixture")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            manifest = {
                "schema_version": 1,
                "manifest_id": "rocky-assets-v1",
                "assets": [
                    {
                        "id": "assistant_model",
                        "kind": "ollama_model",
                        "required": True,
                        "reference": "qwen3:8b",
                        "path": "",
                        "sha256": "",
                    },
                    {
                        "id": "whisper_model",
                        "kind": "file",
                        "required": True,
                        "reference": "local Whisper model",
                        "path": asset.name,
                        "sha256": digest,
                    },
                ],
            }
            path = root / "assets.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            report = verify_asset_manifest(path)
            self.assertEqual(report["failed"], 0)
            self.assertEqual(report["assets"][0]["status"], "RUNTIME_REFERENCE")
            self.assertFalse(report["assets"][0]["verified"])
            self.assertEqual(report["assets"][1]["status"], "VERIFIED")
            self.assertTrue(report["assets"][1]["verified"])

    def test_checksum_mismatch_and_required_missing_file_are_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "engine.exe"
            asset.write_bytes(b"actual")
            manifest = {
                "schema_version": 1,
                "manifest_id": "rocky-assets-v1",
                "assets": [
                    {
                        "id": "engine",
                        "kind": "file",
                        "required": True,
                        "reference": "engine",
                        "path": "engine.exe",
                        "sha256": "0" * 64,
                    },
                    {
                        "id": "missing",
                        "kind": "file",
                        "required": True,
                        "reference": "missing",
                        "path": "missing.bin",
                        "sha256": "1" * 64,
                    },
                ],
            }
            path = root / "assets.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            report = verify_asset_manifest(path)
            self.assertEqual(report["failed"], 2)
            self.assertEqual(report["assets"][0]["status"], "CHECKSUM_MISMATCH")
            self.assertEqual(report["assets"][1]["status"], "MISSING_FILE")

    def test_user_backup_contains_only_allowlisted_small_user_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = root / "rocky.json"
            personality = root / "personality.json"
            memory = root / "memory.json"
            settings.write_text('{"provider":"local"}', encoding="utf-8")
            personality.write_text('{"name":"Rocky"}', encoding="utf-8")
            memory.write_text('{"schema_version":1,"items":[]}', encoding="utf-8")
            # Nearby heavyweight/runtime material must never be swept into the archive.
            (root / "model.gguf").write_bytes(b"not included")
            (root / ".venv").mkdir()
            (root / ".venv" / "python.exe").write_bytes(b"not included")

            output = root / "backup.zip"
            report = export_user_backup(
                settings_path=settings,
                personality_path=personality,
                memory_path=memory,
                output_path=output,
            )
            self.assertTrue(report["verified"])
            with zipfile.ZipFile(output, "r") as archive:
                names = set(archive.namelist())
                self.assertEqual(
                    names,
                    {
                        "manifest.json",
                        "settings/rocky.json",
                        "settings/personality.json",
                        "memory/memory-v1.json",
                    },
                )
                self.assertNotIn("model.gguf", names)
                self.assertFalse(any(".venv" in name for name in names))

    def test_backup_checksum_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = root / "rocky.json"
            personality = root / "personality.txt"
            settings.write_text('{"provider":"local"}', encoding="utf-8")
            personality.write_text("Rocky personality", encoding="utf-8")
            output = root / "backup.zip"
            export_user_backup(
                settings_path=settings,
                personality_path=personality,
                memory_path=root / "missing-memory.json",
                output_path=output,
            )
            with zipfile.ZipFile(output, "r") as archive:
                rows = {name: archive.read(name) for name in archive.namelist()}
            rows["settings/rocky.json"] = b'{"provider":"tampered"}'
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, raw in rows.items():
                    archive.writestr(name, raw)
            with self.assertRaisesRegex(PortabilityError, "checksum"):
                verify_user_backup(output)

    def test_backup_rejects_extra_archive_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / "bad.zip"
            manifest = {
                "schema_version": 1,
                "format": "rocky-user-backup-v1",
                "created_at": "fixture",
                "files": [],
                "excludes": [],
            }
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr("../outside.txt", "bad")
            with self.assertRaises(PortabilityError):
                verify_user_backup(archive_path)


if __name__ == "__main__":
    unittest.main()
