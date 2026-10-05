"""Loopback-only Rocky Assistant browser UI.

This is only a user-interface adapter around ConversationController. It exposes
no shell, arbitrary filesystem access, raw hardware API, or model-to-motor path.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
import math
import os
from pathlib import Path
import secrets
import threading
import webbrowser

from csp.exp003 import Exp003Phrase, coverage as exp003_coverage

from .providers import strict_json
from .translation import representation_summary


RECOMMENDED_TUNING = {
    "mode": "normal",
    "duration_multiplier": 2.0,
    "tone_style": "vocal-v1",
    "volume": 0.12,
    "translation_enabled": True,
    "voice_rate": 0,
    "voice_pitch": 0,
    "voice_volume": 0,
    "memory_enabled": False,
}

_ALLOWED_TUNING = frozenset(
    {
        "mode",
        "duration_multiplier",
        "tone_style",
        "volume",
        "translation_enabled",
        "translation_voice",
        "voice_rate",
        "voice_pitch",
        "voice_volume",
        "memory_enabled",
    }
)


def _number(value, low, high, field):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{field} must be between {low} and {high}")
    return value


def _enum_value(value):
    return getattr(value, "value", value)


class LocalWebUI:
    def __init__(self, conversation, settings, *, settings_path: Path | None = None):
        self.conversation = conversation
        self.settings = settings
        self.settings_path = settings_path
        self.token = secrets.token_urlsafe(24)
        self.lock = threading.RLock()

    @property
    def hardware(self):
        return self.conversation.brain.hardware

    def _tuning(self):
        hardware = self.hardware
        voice = getattr(hardware, "voice", None)
        return {
            "mode": self.conversation.assistant_mode,
            "duration_multiplier": float(hardware.duration_multiplier),
            "tone_style": hardware.tone_style,
            "volume": float(hardware.volume),
            "translation_enabled": bool(self.conversation.translation_enabled),
            "translation_voice": getattr(voice, "voice_name", "") if voice else "",
            "voice_rate": int(getattr(voice, "rate_offset", 0)) if voice else 0,
            "voice_pitch": int(getattr(voice, "pitch_offset", 0)) if voice else 0,
            "voice_volume": int(getattr(voice, "volume_offset", 0)) if voice else 0,
            "memory_enabled": bool(self.conversation.memory_status()["enabled"]),
        }

    def status(self):
        with self.lock:
            state = self.conversation.brain.state
            hardware = self.hardware
            result = {
                "backend": state.backend_id,
                "connection": _enum_value(state.connection_state),
                "motion": _enum_value(state.host_motion_mode),
                "estop_latched": bool(state.estop_latched),
                "busy": self.conversation.pending is not None,
                "muted": bool(hardware.muted),
                "audio_status": hardware.audio_status,
                "voice_status": hardware.voice_status,
                "provider": self.settings.get("provider", ""),
                "model": self.settings.get("model", ""),
                "language": self.conversation.brain.task_controller.text_encoding,
                "memory": self.conversation.memory_status(),
                "tuning": self._tuning(),
                "timing": {
                    "chordic_seconds": float(getattr(hardware, "duration", 0.0)),
                    "english_seconds": float(getattr(hardware, "speech_duration", 0.0)),
                    "english_start_seconds": float(
                        getattr(hardware, "translation_delay_seconds", 0.0)
                    ),
                    "overlap_wall_seconds": float(
                        getattr(hardware, "combined_duration", 0.0)
                    ),
                    "english_finish_margin_seconds": float(
                        getattr(hardware, "translation_finish_margin", 0.0)
                    ),
                },
            }
            if self.conversation.last_output is not None:
                result["representation"] = representation_summary(
                    self.conversation.last_output
                )
                phrase = getattr(self.conversation.last_output, "phrase", None)
                if isinstance(phrase, Exp003Phrase):
                    result["chordic_coverage"] = exp003_coverage(phrase)
            return result

    def chat(self, payload):
        if type(payload) is not dict or set(payload) != {"text"}:
            raise ValueError("chat request must contain exactly text")
        with self.lock:
            self.conversation.start(payload["text"])
            return {"accepted": True, "busy": True}

    def poll(self):
        with self.lock:
            result = self.conversation.poll()
            if result is None:
                return {"pending": self.conversation.pending is not None}
            if "error" in result:
                return {"pending": False, **result, "status": self.status()}
            enriched = dict(result)
            enriched["pending"] = False
            enriched["representation"] = (
                representation_summary(self.conversation.last_output)
                if self.conversation.last_output is not None
                else ""
            )
            phrase = getattr(self.conversation.last_output, "phrase", None)
            if isinstance(phrase, Exp003Phrase):
                enriched["chordic_coverage"] = exp003_coverage(phrase)
            enriched["status"] = self.status()
            return enriched

    def apply_settings(self, payload):
        if type(payload) is not dict or not payload:
            raise ValueError("settings request must be a nonempty object")
        unknown = set(payload) - _ALLOWED_TUNING
        if unknown:
            raise ValueError("unsupported setting: " + ", ".join(sorted(unknown)))
        hardware = self.hardware
        with self.lock:
            if "mode" in payload:
                if type(payload["mode"]) is not str:
                    raise ValueError("mode must be a string")
                self.conversation.set_mode(payload["mode"])
                self.settings["assistant_mode"] = self.conversation.assistant_mode
            if "duration_multiplier" in payload:
                value = _number(
                    payload["duration_multiplier"], 1, 6, "duration_multiplier"
                )
                hardware.duration_multiplier = value
                self.settings["duration_multiplier"] = value
            if "volume" in payload:
                value = _number(payload["volume"], 0, 0.3, "volume")
                hardware.volume = value
                self.settings["volume"] = value
            if "tone_style" in payload:
                value = payload["tone_style"]
                if value not in {"pure", "resonant", "contour-v1", "vocal-v1"}:
                    raise ValueError("invalid tone_style")
                hardware.tone_style = value
                self.settings["tone_style"] = value
            if "translation_enabled" in payload:
                value = payload["translation_enabled"]
                if type(value) is not bool:
                    raise ValueError("translation_enabled must be boolean")
                self.conversation.set_translation(value)
                self.settings["translation_enabled"] = value
            if "memory_enabled" in payload:
                value = payload["memory_enabled"]
                if type(value) is not bool:
                    raise ValueError("memory_enabled must be boolean")
                self.conversation.set_memory_enabled(value)
                self.settings["memory_enabled"] = value
            voice_kwargs = {}
            for field in ("voice_rate", "voice_pitch", "voice_volume"):
                if field in payload:
                    value = payload[field]
                    if type(value) is not int or not -2 <= value <= 2:
                        raise ValueError(f"{field} must be an integer from -2 to 2")
                    voice_kwargs[field.removeprefix("voice_") + "_offset"] = value
                    self.settings[field] = value
            if "translation_voice" in payload:
                value = payload["translation_voice"]
                if (
                    type(value) is not str
                    or len(value) > 200
                    or any(ord(c) < 32 for c in value)
                ):
                    raise ValueError("invalid translation_voice")
                voice_kwargs["voice_name"] = value
                self.settings["translation_voice"] = value
            if voice_kwargs:
                hardware.voice.configure(**voice_kwargs)
            return self.status()

    def action(self, payload):
        if type(payload) is not dict or set(payload) != {"action"}:
            raise ValueError("action request must contain exactly action")
        action = payload["action"]
        if type(action) is not str:
            raise ValueError("action must be a string")
        with self.lock:
            if action == "replay":
                receipt = self.conversation.replay()
                return {
                    "ok": True,
                    "code": _enum_value(receipt.code),
                    "detail": receipt.detail,
                }
            if action == "mute":
                self.hardware.muted = True
            elif action == "unmute":
                self.hardware.muted = False
            elif action == "cancel":
                self.conversation.cancel()
                self.hardware.cancel_audio()
            elif action == "stop":
                self.conversation.stop()
            elif action == "reset":
                self.conversation.cancel()
                if not self.conversation.brain.reset_stop():
                    raise RuntimeError("reset unavailable; inspect status")
            elif action == "clear":
                self.conversation.clear()
                self.hardware.cancel_audio()
            elif action == "save_profile":
                self.save_profile()
            elif action == "reset_recommended":
                self.apply_settings(dict(RECOMMENDED_TUNING))
            else:
                raise ValueError("unsupported UI action")
            return {"ok": True, "status": self.status()}

    def memory(self):
        with self.lock:
            return {
                "status": self.conversation.memory_status(),
                "items": [
                    {
                        "key": item.key,
                        "value": item.value,
                        "provenance": item.provenance,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at,
                    }
                    for item in self.conversation.memory_items()
                ],
            }

    def memory_action(self, payload):
        if type(payload) is not dict or "action" not in payload:
            raise ValueError("memory request requires action")
        action = payload["action"]
        with self.lock:
            if action == "remember":
                if set(payload) != {"action", "key", "value"}:
                    raise ValueError("remember requires exactly action, key, value")
                item = self.conversation.remember(payload["key"], payload["value"])
                result = {"remembered": item.key}
            elif action == "forget":
                if set(payload) != {"action", "key"}:
                    raise ValueError("forget requires exactly action and key")
                result = {"forgot": bool(self.conversation.forget(payload["key"]))}
            elif action == "clear":
                if set(payload) != {"action"}:
                    raise ValueError("clear requires exactly action")
                self.conversation.clear_memory()
                result = {"cleared": True}
            else:
                raise ValueError("memory action must be remember, forget or clear")
            return {**result, **self.memory()}

    def export_settings(self):
        with self.lock:
            return {"schema_version": 1, "rocky_ui_tuning": self._tuning()}

    def import_settings(self, payload):
        if (
            type(payload) is not dict
            or set(payload) != {"schema_version", "rocky_ui_tuning"}
            or payload["schema_version"] != 1
            or type(payload["rocky_ui_tuning"]) is not dict
        ):
            raise ValueError("invalid Rocky UI settings export")
        return self.apply_settings(payload["rocky_ui_tuning"])

    def save_profile(self):
        if self.settings_path is None:
            raise RuntimeError("no user settings path is configured")
        with self.lock:
            path = self.settings_path
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_text(
                json.dumps(self.settings, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
            return path


class RockyWebServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, RockyWebHandler)


class RockyWebHandler(BaseHTTPRequestHandler):
    server_version = "RockyLocalUI/0"

    def log_message(self, format, *args):
        return

    def _host_ok(self):
        host = self.headers.get("Host", "")
        name = host.rsplit(":", 1)[0].strip("[]").lower()
        return name in {"127.0.0.1", "localhost"}

    def _headers(self, status, content_type="application/json; charset=utf-8", length=0):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
            "connect-src 'self'; img-src 'none'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'",
        )
        self.end_headers()

    def _json(self, status, payload):
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._headers(status, length=len(raw))
        self.wfile.write(raw)

    def _error(self, status, exc):
        self._json(status, {"error": f"{type(exc).__name__}: {exc}"})

    def _read_json(self):
        if self.headers.get("X-Rocky-Token") != self.server.app.token:
            raise PermissionError("missing or invalid local UI token")
        if not self.headers.get("Content-Type", "").lower().startswith(
            "application/json"
        ):
            raise ValueError("Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length required")
        length = int(raw_length)
        if not 0 < length <= 8192:
            raise ValueError("request body must be 1-8192 bytes")
        return strict_json(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        if not self._host_ok():
            self._error(400, ValueError("loopback Host required"))
            return
        if (
            self.path not in {"/", "/favicon.ico"}
            and self.headers.get("X-Rocky-Token") != self.server.app.token
        ):
            self._error(403, PermissionError("missing or invalid local UI token"))
            return
        try:
            if self.path == "/":
                page = (
                    resources.files("rocky")
                    .joinpath("webui.html")
                    .read_text(encoding="utf-8")
                    .replace("__ROCKY_TOKEN__", json.dumps(self.server.app.token))
                )
                raw = page.encode("utf-8")
                self._headers(200, "text/html; charset=utf-8", len(raw))
                self.wfile.write(raw)
            elif self.path == "/api/status":
                self._json(200, self.server.app.status())
            elif self.path == "/api/poll":
                self._json(200, self.server.app.poll())
            elif self.path == "/api/export":
                self._json(200, self.server.app.export_settings())
            elif self.path == "/api/memory":
                self._json(200, self.server.app.memory())
            elif self.path == "/favicon.ico":
                self._headers(204, length=0)
            else:
                self._error(404, ValueError("not found"))
        except (OSError, ValueError, RuntimeError) as exc:
            self._error(400, exc)

    def do_POST(self):
        if not self._host_ok():
            self._error(400, ValueError("loopback Host required"))
            return
        try:
            payload = self._read_json()
            if self.path == "/api/chat":
                self._json(202, self.server.app.chat(payload))
            elif self.path == "/api/settings":
                self._json(200, self.server.app.apply_settings(payload))
            elif self.path == "/api/action":
                self._json(200, self.server.app.action(payload))
            elif self.path == "/api/import":
                self._json(200, self.server.app.import_settings(payload))
            elif self.path == "/api/memory":
                self._json(200, self.server.app.memory_action(payload))
            else:
                self._error(404, ValueError("not found"))
        except PermissionError as exc:
            self._error(403, exc)
        except (OSError, ValueError, RuntimeError) as exc:
            self._error(400, exc)

    def do_OPTIONS(self):
        self._error(405, ValueError("CORS is disabled"))


def build_server(app, port):
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("UI port must be 0-65535")
    return RockyWebServer(("127.0.0.1", port), app)


def serve_local_web_ui(
    conversation,
    settings,
    *,
    port=8765,
    settings_path: Path | None = None,
    open_browser=True,
):
    app = LocalWebUI(conversation, settings, settings_path=settings_path)
    server = build_server(app, port)
    host, actual_port = server.server_address
    url = f"http://{host}:{actual_port}/"
    print("Rocky local UI: " + url)
    print("Loopback only. Closing this process closes the UI.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
