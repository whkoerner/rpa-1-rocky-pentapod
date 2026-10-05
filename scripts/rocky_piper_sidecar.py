"""Run an explicitly provisioned Piper neural TTS model on loopback for Rocky.

This script is intended for a separate Python environment containing piper-tts.
It never downloads a voice and never binds to a non-loopback interface.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import secrets
import sys
import threading
import wave


MAX_REQUEST_BYTES = 2048
MAX_RESPONSE_BYTES = 12 * 1024 * 1024


class SidecarError(ValueError):
    pass


def token_from_file(path: Path) -> str:
    path = Path(path).expanduser()
    if not path.is_file() or path.is_symlink():
        raise SidecarError("token file is missing or unsafe")
    token = path.read_text(encoding="utf-8").strip()
    if (
        not 32 <= len(token) <= 256
        or not token.isascii()
        or any(char.isspace() for char in token)
    ):
        raise SidecarError("token file is invalid")
    return token


def strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SidecarError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise SidecarError("non-finite JSON number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


class PiperHandler(BaseHTTPRequestHandler):
    server_version = "RockyPiperSidecar/1"
    voice = None
    token = ""
    voice_id = ""
    SynthesisConfig = None
    synthesis_lock = threading.Lock()

    def log_message(self, format, *args):
        return

    def _authorized(self):
        supplied = self.headers.get("X-Rocky-Piper-Token", "")
        return (
            type(supplied) is str
            and len(supplied) == len(type(self).token)
            and secrets.compare_digest(supplied, type(self).token)
        )

    def _headers(self, status, content_type, length):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def _json(self, status, payload):
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def _error(self, status, message):
        self._json(status, {"error": message})

    def do_GET(self):
        if not self._authorized():
            self._error(403, "forbidden")
            return
        if self.path != "/v1/status":
            self._error(404, "not found")
            return
        self._json(
            200,
            {
                "schema_version": 1,
                "ready": True,
                "voice": type(self).voice_id,
            },
        )

    def do_POST(self):
        if not self._authorized():
            self._error(403, "forbidden")
            return
        if self.path != "/v1/synthesize":
            self._error(404, "not found")
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._error(415, "application/json required")
            return
        try:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise SidecarError("Content-Length required")
            length = int(raw_length)
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise SidecarError("request body exceeds safe size")
            payload = strict_json(self.rfile.read(length).decode("utf-8"))
            if type(payload) is not dict or set(payload) != {
                "schema_version",
                "text",
                "length_scale",
                "volume",
            }:
                raise SidecarError("invalid synthesis request fields")
            if payload["schema_version"] != 1:
                raise SidecarError("unsupported synthesis schema")
            text = payload["text"]
            if (
                type(text) is not str
                or not text.strip()
                or len(text.encode("utf-8")) > 384
                or "\x00" in text
                or any(ord(char) < 32 and char not in ("\n", "\t") for char in text)
            ):
                raise SidecarError("invalid synthesis text")
            length_scale = payload["length_scale"]
            volume = payload["volume"]
            if (
                type(length_scale) not in (int, float)
                or not 0.60 <= float(length_scale) <= 1.60
            ):
                raise SidecarError("length_scale is outside safe bounds")
            if (
                type(volume) not in (int, float)
                or not 0.35 <= float(volume) <= 1.50
            ):
                raise SidecarError("volume is outside safe bounds")
            config = type(self).SynthesisConfig(
                length_scale=float(length_scale),
                volume=float(volume),
            )
            output = BytesIO()
            with type(self).synthesis_lock:
                with wave.open(output, "wb") as wav_file:
                    type(self).voice.synthesize_wav(
                        text.strip(), wav_file, syn_config=config
                    )
            audio = output.getvalue()
            if not audio or len(audio) > MAX_RESPONSE_BYTES:
                raise SidecarError("generated Piper audio exceeds safe size")
            self._headers(200, "audio/wav", len(audio))
            self.wfile.write(audio)
        except (SidecarError, UnicodeDecodeError, ValueError) as exc:
            self._error(400, str(exc))
        except Exception as exc:
            self._error(500, f"Piper synthesis failed: {type(exc).__name__}")

    def do_OPTIONS(self):
        self._error(405, "CORS is disabled")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Token-authenticated loopback Piper sidecar for Rocky"
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=5055)
    parser.add_argument("--cuda", action="store_true")
    args = parser.parse_args(argv)

    model = args.model.expanduser()
    if not model.is_file() or model.is_symlink():
        raise SidecarError("Piper model file is missing or unsafe")
    if model.suffix.lower() != ".onnx":
        raise SidecarError("Piper model must be an ONNX file")
    if not 1 <= args.port <= 65535:
        raise SidecarError("port must be 1-65535")
    token = token_from_file(args.token_file)

    try:
        from piper import PiperVoice, SynthesisConfig
    except ImportError as exc:
        raise RuntimeError(
            "piper-tts is not installed in this sidecar Python environment"
        ) from exc

    # Piper loads the adjacent voice configuration itself. No network call or
    # voice download occurs here.
    voice = PiperVoice.load(model, use_cuda=args.cuda)
    PiperHandler.voice = voice
    PiperHandler.token = token
    PiperHandler.voice_id = model.stem
    PiperHandler.SynthesisConfig = SynthesisConfig

    server = ThreadingHTTPServer(("127.0.0.1", args.port), PiperHandler)
    print(
        f"Rocky Piper sidecar ready on 127.0.0.1:{args.port}; "
        f"voice={PiperHandler.voice_id}; no runtime downloads",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
