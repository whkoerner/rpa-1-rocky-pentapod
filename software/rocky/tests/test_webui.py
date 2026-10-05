"""Security and behavior tests for the loopback Rocky browser UI."""

import http.client
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest

from rocky.webui import LocalWebUI, build_server


class FakeVoice:
    def __init__(self):
        self.voice_name = ""
        self.rate_offset = 0
        self.pitch_offset = 0
        self.volume_offset = 0

    def configure(
        self,
        *,
        voice_name=None,
        rate_offset=None,
        pitch_offset=None,
        volume_offset=None,
    ):
        if voice_name is not None:
            self.voice_name = voice_name
        if rate_offset is not None:
            self.rate_offset = rate_offset
        if pitch_offset is not None:
            self.pitch_offset = pitch_offset
        if volume_offset is not None:
            self.volume_offset = volume_offset


class FakeHardware:
    def __init__(self):
        self.muted = False
        self.audio_status = "IDLE"
        self.voice_status = "IDLE"
        self.duration_multiplier = 2
        self.tone_style = "vocal-v1"
        self.volume = 0.12
        self.duration = 0.0
        self.speech_duration = 0.0
        self.translation_delay_seconds = 0.75
        self.combined_duration = 0.0
        self.translation_finish_margin = 0.0
        self.voice = FakeVoice()
        self.cancelled = 0

    def cancel_audio(self):
        self.cancelled += 1


class FakeConversation:
    def __init__(self):
        hardware = FakeHardware()
        state = SimpleNamespace(
            backend_id="desktop-audio",
            connection_state="READY",
            host_motion_mode="DISABLED",
            estop_latched=False,
        )
        self.brain = SimpleNamespace(
            hardware=hardware,
            state=state,
            task_controller=SimpleNamespace(text_encoding="exp003"),
            reset_stop=lambda: True,
        )
        self.assistant_mode = "normal"
        self.translation_enabled = False
        self.pending = None
        self.last_output = None
        self.started = []
        self.stopped = False
        self.memory_enabled = False
        self.memory = {}

    def memory_status(self):
        return {
            "enabled": self.memory_enabled,
            "revision": len(self.memory),
            "count": len(self.memory) if self.memory_enabled else 0,
            "path": "fixture-memory.json",
        }

    def set_memory_enabled(self, enabled):
        if type(enabled) is not bool:
            raise ValueError("bad memory state")
        self.memory_enabled = enabled

    def memory_items(self):
        if not self.memory_enabled:
            return ()
        return tuple(
            SimpleNamespace(
                key=key,
                value=value,
                provenance="user_statement",
                created_at="fixture",
                updated_at="fixture",
            )
            for key, value in sorted(self.memory.items())
        )

    def remember(self, key, value):
        if not self.memory_enabled:
            raise ValueError("memory off")
        self.memory[key] = value
        return SimpleNamespace(
            key=key,
            value=value,
            provenance="user_statement",
            created_at="fixture",
            updated_at="fixture",
        )

    def forget(self, key):
        return self.memory.pop(key, None) is not None

    def clear_memory(self):
        self.memory.clear()

    def start(self, text):
        if type(text) is not str or not text.strip():
            raise ValueError("bad text")
        self.started.append(text)
        self.pending = ("turn",)

    def poll(self):
        return None

    def set_mode(self, mode):
        if mode not in {"normal", "study", "coding", "project"}:
            raise ValueError("bad mode")
        self.assistant_mode = mode

    def set_translation(self, enabled):
        if type(enabled) is not bool:
            raise ValueError("bad translation")
        self.translation_enabled = enabled

    def replay(self):
        return SimpleNamespace(code="OK", detail="replayed")

    def cancel(self):
        self.pending = None

    def stop(self):
        self.stopped = True
        self.brain.state.estop_latched = True
        self.pending = None

    def clear(self):
        self.pending = None


class WebUITests(unittest.TestCase):
    def app(self, path=None):
        settings = {
            "provider": "local",
            "model": "qwen3:8b",
            "assistant_mode": "normal",
            "duration_multiplier": 2,
            "tone_style": "vocal-v1",
            "volume": 0.12,
            "translation_enabled": False,
            "memory_enabled": False,
            "translation_voice": "",
            "voice_rate": 0,
            "voice_pitch": 0,
            "voice_volume": 0,
        }
        return LocalWebUI(FakeConversation(), settings, settings_path=path)

    def test_settings_are_bounded_and_no_physical_controls_exist(self):
        app = self.app()
        app.apply_settings(
            {
                "mode": "study",
                "duration_multiplier": 2.5,
                "tone_style": "contour-v1",
                "volume": 0.1,
                "translation_enabled": True,
                "translation_voice": "Local Voice",
                "voice_rate": 1,
                "voice_pitch": -1,
                "voice_volume": 2,
            }
        )
        status = app.status()
        self.assertEqual(status["tuning"]["mode"], "study")
        self.assertEqual(status["tuning"]["duration_multiplier"], 2.5)
        self.assertEqual(status["tuning"]["tone_style"], "contour-v1")
        with self.assertRaisesRegex(ValueError, "unsupported setting"):
            app.apply_settings({"raw_motor_power": 1})
        with self.assertRaises(ValueError):
            app.apply_settings({"volume": 1.0})

    def test_memory_requires_opt_in_and_is_manageable(self):
        app = self.app()
        with self.assertRaises(ValueError):
            app.memory_action(
                {"action": "remember", "key": "favorite_color", "value": "blue"}
            )
        app.apply_settings({"memory_enabled": True})
        result = app.memory_action(
            {"action": "remember", "key": "favorite_color", "value": "blue"}
        )
        self.assertEqual(result["items"][0]["provenance"], "user_statement")
        self.assertEqual(result["items"][0]["value"], "blue")
        app.memory_action({"action": "forget", "key": "favorite_color"})
        self.assertEqual(app.memory()["items"], [])
        app.memory_action(
            {"action": "remember", "key": "class", "value": "biology"}
        )
        app.memory_action({"action": "clear"})
        self.assertEqual(app.memory()["items"], [])

    def test_export_import_and_save_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings" / "rocky.json"
            app = self.app(path)
            exported = app.export_settings()
            exported["rocky_ui_tuning"]["mode"] = "coding"
            app.import_settings(exported)
            self.assertEqual(app.conversation.assistant_mode, "coding")
            app.save_profile()
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["assistant_mode"], "coding")

    def test_loopback_http_rejects_unauthorized_mutation_and_cors(self):
        app = self.app()
        server = build_server(app, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", "/")
            response = connection.getresponse()
            page = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("Content-Security-Policy", response.headers)
            self.assertIn("Rocky", page)
            self.assertNotIn("https://", page)
            self.assertNotIn("http://", page)

            connection.request("GET", "/api/status")
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 403)

            connection.request(
                "GET",
                "/api/status",
                headers={"X-Rocky-Token": app.token},
            )
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 200)

            body = json.dumps({"text": "hello"})
            connection.request(
                "POST",
                "/api/chat",
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 403)

            connection.request(
                "POST",
                "/api/chat",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Rocky-Token": app.token,
                },
            )
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 202)
            self.assertEqual(app.conversation.started, ["hello"])

            bad = json.dumps({"raw_motor_power": 1})
            connection.request(
                "POST",
                "/api/settings",
                body=bad,
                headers={
                    "Content-Type": "application/json",
                    "X-Rocky-Token": app.token,
                },
            )
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 400)

            connection.request("OPTIONS", "/api/chat")
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 405)
            self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
