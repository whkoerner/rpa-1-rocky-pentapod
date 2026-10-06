"""Long-form lecture recording sessions built from bounded local WAV chunks.

The browser records visibly and uploads small PCM chunks. Chunks are stored
locally and may be transcribed later with the existing whisper.cpp sidecar.
No classroom recording is started without explicit user confirmation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil

from .stt import MAX_WAV_BYTES, SpeechToTextError, validate_voice_wav


SESSION_RE = re.compile(r"^lecture-\d{8}T\d{6}Z-[0-9a-f]{8}$")
DEFAULT_MAX_SECONDS = 10_800.0
DEFAULT_CHUNK_SECONDS = 30.0
MAX_LECTURE_SECONDS = 14_400.0


class LectureError(ValueError):
    pass


def _strict_manifest(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise LectureError("duplicate lecture manifest key")
            result[key] = value
        return result

    def reject_constant(value):
        raise LectureError("non-finite lecture manifest number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


class LectureSessionStore:
    def __init__(
        self,
        root: Path | str,
        *,
        max_seconds: float = DEFAULT_MAX_SECONDS,
        chunk_max_seconds: float = DEFAULT_CHUNK_SECONDS,
    ):
        self.root = Path(root).expanduser()
        if (
            type(max_seconds) not in (int, float)
            or not 600 <= float(max_seconds) <= MAX_LECTURE_SECONDS
        ):
            raise LectureError("lecture max seconds must be between 600 and 14400")
        if (
            type(chunk_max_seconds) not in (int, float)
            or not 10 <= float(chunk_max_seconds) <= 60
        ):
            raise LectureError("lecture chunk seconds must be between 10 and 60")
        self.max_seconds = float(max_seconds)
        self.chunk_max_seconds = float(chunk_max_seconds)

    def _session_path(self, session_id: str) -> Path:
        if type(session_id) is not str or not SESSION_RE.fullmatch(session_id):
            raise LectureError("invalid lecture session id")
        return self.root / session_id

    @staticmethod
    def _manifest_path(session: Path) -> Path:
        return session / "manifest.json"

    def _write_manifest(self, session: Path, manifest: dict):
        raw = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        if len(raw.encode("utf-8")) > 512 * 1024:
            raise LectureError("lecture manifest exceeds safe size")
        temporary = session / "manifest.json.tmp"
        temporary.write_text(raw, encoding="utf-8")
        temporary.replace(self._manifest_path(session))

    def _load_manifest(self, session_id: str) -> tuple[Path, dict]:
        session = self._session_path(session_id)
        if not session.is_dir() or session.is_symlink():
            raise LectureError("lecture session directory not found or unsafe")
        path = self._manifest_path(session)
        if not path.is_file() or path.is_symlink():
            raise LectureError("lecture session manifest not found")
        manifest = _strict_manifest(path.read_text(encoding="utf-8"))
        if (
            type(manifest) is not dict
            or manifest.get("schema_version") != 1
            or manifest.get("session_id") != session_id
            or type(manifest.get("chunks")) is not list
        ):
            raise LectureError("invalid lecture session manifest")
        return session, manifest

    def start(self, *, title: str = "", consent_confirmed: bool = False) -> dict:
        if consent_confirmed is not True:
            raise LectureError(
                "lecture recording requires explicit permission/consent confirmation"
            )
        if (
            type(title) is not str
            or len(title.encode("utf-8")) > 200
            or any(ord(char) < 32 for char in title)
        ):
            raise LectureError("lecture title must be a short printable string")
        now = datetime.now(timezone.utc)
        session_id = (
            "lecture-"
            + now.strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + secrets.token_hex(4)
        )
        self.root.mkdir(parents=True, exist_ok=True)
        session = self._session_path(session_id)
        session.mkdir()
        manifest = {
            "schema_version": 1,
            "session_id": session_id,
            "title": title.strip(),
            "state": "recording",
            "started_utc": now.isoformat(),
            "stopped_utc": "",
            "max_seconds": self.max_seconds,
            "chunk_max_seconds": self.chunk_max_seconds,
            "total_seconds": 0.0,
            "chunks": [],
            "transcript": None,
            "consent_confirmed": True,
            "recovered_interrupted": False,
        }
        self._write_manifest(session, manifest)
        return self.public_status(manifest)

    def public_status(self, manifest: dict) -> dict:
        return {
            "session_id": manifest["session_id"],
            "title": manifest["title"],
            "state": manifest["state"],
            "total_seconds": float(manifest["total_seconds"]),
            "chunk_count": len(manifest["chunks"]),
            "max_seconds": float(manifest["max_seconds"]),
            "chunk_max_seconds": float(manifest["chunk_max_seconds"]),
            "transcript_ready": manifest.get("transcript") is not None,
            "recovered_interrupted": bool(manifest.get("recovered_interrupted", False)),
        }

    def status(self, session_id: str) -> dict:
        _, manifest = self._load_manifest(session_id)
        return self.public_status(manifest)

    def add_chunk(self, session_id: str, raw: bytes, *, index: int | None = None) -> dict:
        session, manifest = self._load_manifest(session_id)
        if manifest["state"] != "recording":
            raise LectureError("lecture session is not recording")
        expected_index = len(manifest["chunks"]) + 1
        if index is None:
            index = expected_index
        if type(index) is not int or index < 1:
            raise LectureError("lecture chunk index must be a positive integer")
        if index < expected_index:
            raise LectureError("duplicate lecture chunk index")
        if index > expected_index:
            raise LectureError("out-of-order lecture chunk index")
        if type(raw) is not bytes or not raw or len(raw) > MAX_WAV_BYTES:
            raise LectureError("lecture chunk exceeds safe WAV byte limit")
        try:
            duration = validate_voice_wav(raw, max_seconds=self.chunk_max_seconds)
        except SpeechToTextError as exc:
            raise LectureError(str(exc)) from exc
        total = float(manifest["total_seconds"]) + duration
        if total > self.max_seconds + 0.001:
            raise LectureError("lecture session exceeds configured maximum duration")
        filename = f"chunk-{index:05d}.wav"
        path = session / filename
        if path.exists():
            raise LectureError("lecture chunk path collision")
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        manifest["chunks"].append(
            {
                "index": index,
                "filename": filename,
                "start_seconds": round(float(manifest["total_seconds"]), 3),
                "duration_seconds": round(duration, 3),
                "bytes": len(raw),
                "sha256": digest,
            }
        )
        manifest["total_seconds"] = round(total, 3)
        self._write_manifest(session, manifest)
        return self.public_status(manifest)

    def stop(self, session_id: str) -> dict:
        session, manifest = self._load_manifest(session_id)
        if manifest["state"] != "recording":
            raise LectureError("lecture session is not recording")
        manifest["state"] = "recorded"
        manifest["stopped_utc"] = datetime.now(timezone.utc).isoformat()
        self._write_manifest(session, manifest)
        return self.public_status(manifest)

    def recover_interrupted(self, session_id: str) -> dict:
        session, manifest = self._load_manifest(session_id)
        if manifest["state"] != "recording":
            raise LectureError("lecture session is not interrupted/recording")
        manifest["state"] = "recorded"
        manifest["stopped_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["recovered_interrupted"] = True
        self._write_manifest(session, manifest)
        return self.public_status(manifest)

    def delete(self, session_id: str) -> dict:
        session, manifest = self._load_manifest(session_id)
        if manifest["state"] == "recording":
            raise LectureError("stop or recover lecture recording before deletion")
        shutil.rmtree(session)
        return {"session_id": session_id, "deleted": True}

    def _verified_chunk(self, session: Path, row: dict) -> bytes:
        if type(row) is not dict:
            raise LectureError("invalid lecture chunk manifest row")
        required = {
            "index",
            "filename",
            "start_seconds",
            "duration_seconds",
            "bytes",
            "sha256",
        }
        if set(row) != required:
            raise LectureError("lecture chunk manifest fields are invalid")
        if type(row["index"]) is not int or row["index"] < 1:
            raise LectureError("invalid lecture chunk index")
        filename = row["filename"]
        if (
            type(filename) is not str
            or filename != f"chunk-{row['index']:05d}.wav"
        ):
            raise LectureError("invalid lecture chunk filename")
        path = session / filename
        if not path.is_file() or path.is_symlink():
            raise LectureError("lecture chunk file is missing or unsafe")
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise LectureError("lecture chunk checksum mismatch")
        try:
            duration = validate_voice_wav(raw, max_seconds=self.chunk_max_seconds)
        except SpeechToTextError as exc:
            raise LectureError(str(exc)) from exc
        if abs(duration - float(row["duration_seconds"])) > 0.01:
            raise LectureError("lecture chunk duration mismatch")
        return raw

    def transcribe(self, session_id: str, transcriber) -> dict:
        if transcriber is None:
            raise LectureError("local lecture transcription backend is unavailable")
        session, manifest = self._load_manifest(session_id)
        if manifest["state"] not in {"recorded", "transcribed"}:
            raise LectureError("stop lecture recording before transcription")
        if manifest["state"] == "transcribed" and manifest.get("transcript"):
            return dict(manifest["transcript"])
        if not manifest["chunks"]:
            raise LectureError("lecture session has no recorded audio chunks")
        segments = []
        text_lines = []
        expected_start = 0.0
        for expected_index, row in enumerate(manifest["chunks"], start=1):
            if type(row) is not dict or row.get("index") != expected_index:
                raise LectureError("lecture chunk manifest sequence is not contiguous")
            try:
                row_start = float(row.get("start_seconds"))
            except (TypeError, ValueError) as exc:
                raise LectureError("invalid lecture chunk start time") from exc
            if abs(row_start - expected_start) > 0.01:
                raise LectureError("lecture chunk manifest timing is not contiguous")
            raw = self._verified_chunk(session, row)
            result = transcriber.transcribe_wav(raw)
            text = result.get("text")
            if type(text) is not str or not text.strip():
                raise LectureError("transcriber returned empty lecture text")
            start = float(row["start_seconds"])
            end = start + float(row["duration_seconds"])
            expected_start = end
            segment = {
                "chunk": int(row["index"]),
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "text": text.strip(),
                "confidence": result.get("confidence"),
                "confidence_source": result.get("confidence_source", "unknown"),
            }
            segments.append(segment)
            text_lines.append(
                f"[{start:0.1f}-{end:0.1f}] {segment['text']}"
            )
        transcript = {
            "schema_version": 1,
            "session_id": session_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "total_seconds": float(manifest["total_seconds"]),
            "segments": segments,
        }
        transcript_path = session / "transcript.json"
        text_path = session / "transcript.txt"
        transcript_path.write_text(
            json.dumps(transcript, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        text_path.write_text("\n".join(text_lines) + ("\n" if text_lines else ""), encoding="utf-8")
        manifest["state"] = "transcribed"
        manifest["transcript"] = {
            "json": transcript_path.name,
            "text": text_path.name,
            "segments": len(segments),
            "created_utc": transcript["created_utc"],
        }
        self._write_manifest(session, manifest)
        return dict(manifest["transcript"])

    def session_directory(self, session_id: str) -> Path:
        session, _ = self._load_manifest(session_id)
        return session
