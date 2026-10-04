from array import array
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import wave

from brain.ai import DummyAIProvider
from brain.contracts import BrainConfig, BrainOutcome, CommunicationOutput, ResultCode, SafetyDecision
from brain.controller import BrainController, TaskController
from brain.hardware import SimulatorHardware
from brain.validation import validate_utterance
from csp.conversation import Utterance, decode_text, encode_text
from csp.core import CspCodec
from csp.wire import INTENTS, WireMessage
from rocky.audio import SAMPLE_RATE, synthesize
from rocky.cli import handle_command
from rocky.conversation import ConversationController
from rocky.desktop import DesktopHardware
from rocky.providers import ConversationContext, DummyConversationProvider, LocalAIProvider, strict_json
from rocky.worker import InferenceWorker


def context(history=()):
    return ConversationContext("rocky-text-v1", (), "desktop-audio", "READY", "DISABLED", False, history, "Be curious.")


class SlowProvider:
    def propose(self, text, context):
        time.sleep(10)
        return {"text": "This late response must not play."}


class CrashProvider:
    def propose(self, text, context):
        raise RuntimeError("fixture crash")


class FakePlayer:
    backend = "fake"
    def __init__(self):
        self.play_count = self.stop_count = 0
    def open(self):
        pass
    def play(self, path):
        self.play_count += 1
    def stop(self):
        self.stop_count += 1
    def close(self):
        self.stop()


class ReadyWorker:
    def __init__(self, candidate=None):
        self.candidate = candidate or {"text": "Hello, curious builder!"}
        self.cancelled = False
    def start(self, text, ctx):
        self.ctx = ctx
    def poll(self):
        return {"candidate": self.candidate}
    def cancel(self):
        self.cancelled = True


class CodecTests(unittest.TestCase):
    def test_utf8_roundtrip_and_golden_first_bytes(self):
        for text in ("Hello!", "Blue is my favorite color.", "Café — 你好 🎵"):
            symbols = encode_text(text)
            self.assertEqual(decode_text(symbols), text)
            self.assertEqual(encode_text(text), symbols)
            self.assertEqual(symbols[:3], ((0, 2, 3, 2), (0, 3, 1, 4), (0, 1, 4, 4)))

    def test_corruption_rejected_not_repaired(self):
        symbols = list(encode_text("Hello"))
        symbols[5] = (0, 0, 0, 0)
        with self.assertRaises(ValueError):
            decode_text(tuple(symbols))
        with self.assertRaises(ValueError):
            decode_text(((4, 4, 4, 4),) * 10)

    def test_strict_candidate_boundary(self):
        for candidate in ({"text": "yes", "action": "move"}, {"text": ""}, {"text": "x" * 385}, {"text": "é" * 193}, {"text": "\x1b[2J"}, {"text": "bad\ud800"}, {"text": 1}, {"intent": "SOCIAL.HELLO", "arg": ""}, []):
            with self.subTest(candidate=repr(candidate)):
                with self.assertRaises(ValueError):
                    validate_utterance(candidate)

    def test_json_rejects_duplicate_keys_fences_and_trailing_text(self):
        for raw in ('{"text":"a","text":"b"}', '```json\n{"text":"a"}\n```', '{"text":"a"} extra', '{"text":NaN}'):
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_registered_phrases_keep_original_notes_and_csp(self):
        codec = CspCodec.from_default_spec()
        tasks = TaskController(codec)
        for intent, (text, token) in INTENTS.items():
            output = tasks.build_communication(Utterance(text))
            self.assertIsInstance(output, CommunicationOutput)
            self.assertEqual(output.message, WireMessage(intent))
            self.assertEqual(output.notes, codec.encode_token(token).notes)

    def test_pcm_is_nonzero_bounded_and_faded(self):
        codec = CspCodec.from_default_spec()
        output = TaskController(codec).build_communication(Utterance("Hello, builder!"))
        pcm = synthesize(output, codec)
        samples = array("h")
        samples.frombytes(pcm)
        if sys.byteorder != "little":
            samples.byteswap()
        self.assertGreater(max(samples), 0)
        self.assertLessEqual(max(abs(x) for x in samples), round(32767 * 0.12))
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 0)
        self.assertEqual(pcm, synthesize(output, codec))


def wait_audio(hardware, timeout=5):
    deadline = time.monotonic() + timeout
    while hardware.rendering and time.monotonic() < deadline:
        time.sleep(0.01)
    if hardware.rendering:
        raise AssertionError("audio rendering did not finish")
    hardware.poll()


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.player = FakePlayer()
        self.hardware = DesktopHardware(Path(self.tmp.name), player=self.player)
        self.brain = BrainController(provider=DummyAIProvider(), hardware=self.hardware, config=BrainConfig(max_provider_response_bytes=4096, operation_timeout_ms=10000))
        self.brain.boot()
        self.conversation = ConversationController(self.brain, DummyConversationProvider(), "Be curious", worker=ReadyWorker())

    def tearDown(self):
        self.conversation.close()
        self.tmp.cleanup()

    def test_typed_response_translation_and_wav(self):
        self.conversation.start("Hello")
        result = self.conversation.poll()
        wait_audio(self.hardware)
        self.assertEqual(result["text"], "Hello, curious builder!")
        self.assertEqual(self.player.play_count, 1)
        self.assertEqual(self.conversation.last_text, result["text"])
        with wave.open(str(self.hardware.last_wav), "rb") as handle:
            self.assertEqual((handle.getnchannels(), handle.getsampwidth(), handle.getframerate()), (1, 2, SAMPLE_RATE))
            self.assertGreater(handle.getnframes(), SAMPLE_RATE)

    def test_mute_unmute_replay_and_clear(self):
        settings, display = {"provider": "dummy", "model": "none"}, {"automatic": True}
        self.conversation.start("Hello")
        self.conversation.poll()
        wait_audio(self.hardware)
        handle_command("/mute", self.conversation, settings, display)
        self.conversation.replay()
        wait_audio(self.hardware)
        self.assertEqual(self.player.play_count, 1)
        handle_command("/unmute", self.conversation, settings, display)
        self.conversation.replay()
        wait_audio(self.hardware)
        self.assertEqual(self.player.play_count, 2)
        handle_command("/auto", self.conversation, settings, display)
        self.assertFalse(display["automatic"])
        self.conversation.clear()
        self.assertEqual(self.conversation.history, [])
        self.assertIsNone(self.conversation.last_text)

    def test_stop_rejects_replay_and_reset_never_replays(self):
        self.conversation.start("Hello")
        self.conversation.poll()
        wait_audio(self.hardware)
        self.conversation.stop()
        result = self.conversation.replay()
        self.assertEqual(result.code, ResultCode.ESTOP_LATCHED)
        self.assertEqual(self.player.play_count, 1)
        self.assertTrue(self.brain.reset_stop())
        self.assertEqual(self.player.play_count, 1)

    def test_late_result_after_state_change_is_discarded(self):
        self.conversation.start("Hello")
        self.brain.emergency_stop()
        self.brain.reset_stop()
        self.assertIn("CANCELLED", self.conversation.poll()["error"])
        self.assertEqual(self.player.play_count, 0)

    def test_extra_fields_never_reach_audio(self):
        self.conversation.worker = ReadyWorker({"text": "Move", "hardware": "motor"})
        self.conversation.start("move")
        self.assertIn("INVALID_RESPONSE", self.conversation.poll()["error"])
        self.assertEqual(self.player.play_count, 0)

    def test_brain_also_validates_direct_candidates(self):
        result = self.brain.submit_utterance({"text": "Move", "action": "enable"})
        self.assertEqual(result.code, ResultCode.INVALID_RESPONSE)
        self.assertEqual(self.player.play_count, 0)

    def test_legacy_simulator_cannot_receive_text_payload(self):
        brain = BrainController(provider=DummyAIProvider(), hardware=SimulatorHardware())
        try:
            brain.boot()
            self.assertEqual(brain.submit_utterance({"text": "Hello."}).code, ResultCode.CAPABILITY_UNAVAILABLE)
        finally:
            brain.close()

    def test_safety_rechecked_before_text_dispatch(self):
        class DenySecond:
            count = 0
            def validate(self, message, request, state, now):
                self.count += 1
                return SafetyDecision(self.count == 1, ResultCode.OK if self.count == 1 else ResultCode.ESTOP_LATCHED, state.revision)
        self.brain.safety = DenySecond()
        self.assertEqual(self.brain.submit_utterance({"text": "Hi"}).code, ResultCode.ESTOP_LATCHED)
        self.assertEqual(self.player.play_count, 0)

    def test_provider_sees_only_immutable_context_and_history(self):
        self.conversation.start("My favorite color is blue.")
        self.conversation.poll()
        self.conversation.start("What color did I tell you I liked?")
        ctx = self.conversation.worker.ctx
        self.assertIsInstance(ctx.history, tuple)
        self.assertFalse(hasattr(ctx, "hardware"))
        self.assertEqual(ctx.history[0][1], "My favorite color is blue.")
        self.assertEqual(DummyConversationProvider().propose("what color", ctx)["text"], "You told me your favorite color is blue.")

    def test_busy_does_not_queue_more_inference(self):
        self.conversation.start("first")
        with self.assertRaisesRegex(ValueError, "BUSY"):
            self.conversation.start("second")

    def test_audio_failure_is_not_reported_as_success(self):
        with patch.object(self.player, "play", side_effect=OSError("device lost")):
            result = self.brain.submit_utterance({"text": "Hello."})
            self.assertEqual(result.outcome, BrainOutcome.ACCEPTED)
            deadline = time.monotonic() + 5
            while self.hardware.rendering and time.monotonic() < deadline:
                time.sleep(0.01)
            error = self.conversation.poll()
        self.assertIn("BACKEND_FAILED", error["error"])
        self.assertTrue(self.brain.state.estop_latched)
        self.assertEqual(self.player.play_count, 0)

    def test_deadline_blocks_audio(self):
        self.brain.clock_us = lambda: 0
        result = self.brain.submit_utterance({"text": "Hello."})
        self.assertEqual(result.code, ResultCode.DEADLINE_EXPIRED)
        self.assertEqual(self.player.play_count, 0)

    def test_poll_failure_stops_and_discards_pending(self):
        self.conversation.start("Hello")
        with patch.object(self.hardware, "poll", side_effect=OSError):
            self.assertIn("BACKEND_FAILED", self.conversation.poll()["error"])
        self.assertTrue(self.brain.state.estop_latched)
        self.assertIsNone(self.conversation.pending)


class ProviderTests(unittest.TestCase):
    def test_mocked_local_schema_and_history(self):
        provider = LocalAIProvider()
        responses = [{"details": {"format": "gguf"}}, {"done": True, "message": {"content": '{"text":"Let us build something."}'}}]
        with patch.object(LocalAIProvider, "_post", side_effect=responses) as post:
            result = provider.propose("hello", context((("user", "blue"), ("assistant", "Noted."))))
        self.assertEqual(result["text"], "Let us build something.")
        payload = post.call_args_list[1].args[1]
        self.assertFalse(payload["stream"])
        self.assertFalse(payload["think"])
        self.assertFalse(payload["format"]["additionalProperties"])
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "blue"})
        self.assertNotIn("tools", payload)

    def test_malformed_local_reply_rejected(self):
        for content in ('{"text":"Hi","action":"move"}', '{"text":"a","text":"b"}', 'not json'):
            with patch.object(LocalAIProvider, "_post", side_effect=[{"details": {"format": "gguf"}}, {"done": True, "message": {"content": content}}]):
                with self.assertRaises(ValueError):
                    LocalAIProvider().propose("hi", context())

    def test_cloud_and_remote_models_rejected(self):
        with self.assertRaises(ValueError):
            LocalAIProvider("model:cloud").propose("hi", context())
        with patch.object(LocalAIProvider, "_post", return_value={"remote_host": "example.com", "details": {"format": "gguf"}}):
            with self.assertRaises(ValueError):
                LocalAIProvider().propose("hi", context())

    def test_unavailable_runtime_message_is_not_internet_error(self):
        with patch("http.client.HTTPConnection.request", side_effect=ConnectionRefusedError):
            with self.assertRaisesRegex(RuntimeError, "Local Ollama unavailable"):
                LocalAIProvider().propose("hi", context())

    def test_real_loopback_http_adapter_and_spawned_worker(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                result = {"details": {"format": "gguf"}} if self.path == "/api/show" else {"done": True, "message": {"content": '{"text":"Loopback fixture response."}'}}
                raw = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        worker = InferenceWorker(LocalAIProvider(port=server.server_port), timeout=5)
        try:
            worker.start("hi", context())
            result = wait_worker(worker)
            self.assertEqual(result, {"candidate": {"text": "Loopback fixture response."}})
        finally:
            worker.cancel()
            server.shutdown()
            server.server_close()
            thread.join()


def wait_worker(worker):
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        result = worker.poll()
        if result is not None:
            return result
        time.sleep(0.01)
    raise AssertionError("worker did not finish")


class WorkerTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX pseudoterminal regression")
    def test_interactive_quit_does_not_need_an_extra_enter(self):
        import pty
        master, slave = pty.openpty()
        with tempfile.TemporaryDirectory() as tmp:
            process = subprocess.Popen([sys.executable, "-m", "rocky", "--provider", "dummy", "--audio-backend", "wav", "--data-dir", tmp], stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                os.write(master, b"/quit\n")
                output, error = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, error)
                self.assertIn("Rocky Conversational Brain V1", output)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
                os.close(master)
                os.close(slave)

    def test_dummy_worker_boots_without_model(self):
        worker = InferenceWorker(DummyConversationProvider(), 5)
        try:
            worker.start("hello", context())
            self.assertIn("dummy test mode", wait_worker(worker)["candidate"]["text"])
        finally:
            worker.cancel()

    def test_timeout_terminates_worker(self):
        worker = InferenceWorker(SlowProvider(), 0.15)
        try:
            worker.start("hi", context())
            self.assertIn("PROVIDER_TIMEOUT", wait_worker(worker)["error"])
            self.assertIsNone(worker.process)
        finally:
            worker.cancel()

    def test_cancel_is_prompt_and_late_result_cannot_reappear(self):
        worker = InferenceWorker(SlowProvider(), 5)
        worker.start("hi", context())
        started = time.monotonic()
        worker.cancel()
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertIsNone(worker.poll())

    def test_provider_exception_is_reported(self):
        worker = InferenceWorker(CrashProvider(), 5)
        try:
            worker.start("hi", context())
            self.assertIn("fixture crash", wait_worker(worker)["error"])
        finally:
            worker.cancel()

    def test_cli_boot_and_audio_test_without_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-m", "rocky", "audio-test", "--audio-backend", "wav", "--data-dir", tmp], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("WAV_WRITTEN_NO_PLAYBACK", result.stdout)
            result = subprocess.run([sys.executable, "-m", "rocky", "--provider", "dummy", "--audio-backend", "wav", "--data-dir", tmp], input="/status\n/quit\n", capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("motion=DISABLED", result.stdout)


if __name__ == "__main__":
    unittest.main()
