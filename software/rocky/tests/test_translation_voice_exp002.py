import contextlib
import io
from pathlib import Path
import statistics
import tempfile
import unittest

from brain.ai import DummyAIProvider
from brain.contracts import BrainConfig
from brain.controller import BrainController, TaskController
from csp.core import CspCodec
from csp.exp002 import Exp002Phrase, decode_phrase, encode_phrase, load_profile, token_patterns
from csp.conversation import Utterance
from rocky.audio import estimated_duration
from rocky.cli import handle_command
from rocky.conversation import ConversationController, explicit_user_name
from rocky.desktop import DesktopHardware
from rocky.speech import PROSODY, build_ssml, classify_prosody, tuned_profile
from test_conversation import FakePlayer, ReadyWorker, wait_audio


class FakeVoice:
    def __init__(self):
        self.status = "IDLE"
        self.last_profile = ""
        self.last_duration_seconds = 0.0
        self.available_checks = 0
        self.starts = []
        self.cancel_count = 0
        self.fail_on_poll = False
        self.voice_name = ""
        self.rate_offset = 0
        self.pitch_offset = 0
        self.volume_offset = 0

    def check_available(self):
        self.available_checks += 1
        return ("Fixture Voice",)

    def configure(self, **values):
        for key, value in values.items():
            if key.endswith("_offset") and (type(value) is not int or not -2 <= value <= 2):
                raise ValueError("voice tuning offsets must be integers from -2 to 2")
            setattr(self, key, value)

    def start(self, text, *, gate=None, delay_seconds=0):
        self.starts.append((text, delay_seconds, gate is not None))
        self.last_profile = classify_prosody(text).name
        self.status = "QUEUED"

    def poll(self):
        if self.fail_on_poll:
            self.fail_on_poll = False
            raise RuntimeError("fixture voice failure")
        return self.status

    def cancel(self):
        self.cancel_count += 1
        self.status = "CANCELLED"

    def close(self):
        self.cancel()


class Exp002RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.codec = CspCodec.from_default_spec()
        self.tasks = TaskController(self.codec, "exp002")
        self.profile = load_profile()

    def test_runtime_export_is_pinned_to_chordic_main_and_collision_free(self):
        self.assertEqual(self.profile["source_repository"], "whkoerner/chordic-language")
        self.assertEqual(self.profile["source_commit"], "56347cf73111d2d708b5919cd01b563826795108")
        patterns = token_patterns()
        self.assertEqual(len(patterns), len(set(patterns.values())))
        for first, second in (
            ("SOCIAL.YES", "SOCIAL.NO"),
            ("GRAM.Q", "GRAM.NEG"),
            ("ACTION.HELP", "ACTION.STOP"),
            ("QUALITY.GOOD", "QUALITY.BAD"),
        ):
            self.assertNotEqual(patterns[first], patterns[second])

    def test_all_registered_benchmark_meanings_round_trip(self):
        for case in self.profile["benchmark"]["cases"]:
            with self.subTest(case=case["id"]):
                phrase = encode_phrase(case["english"])
                self.assertIsInstance(phrase, Exp002Phrase)
                self.assertEqual(decode_phrase(phrase), case["english"])
                self.assertEqual(tuple(case["tokens"]), phrase.units[0].tokens)

    def test_free_form_uses_composition_plus_explicit_exact_ct2_fallback(self):
        for text in ("Rocky help xylophone.", "Rocky help you.", "Rocky ready. Good."):
            with self.subTest(text=text):
                phrase = encode_phrase(text)
                self.assertEqual(decode_phrase(phrase), text)
                self.assertTrue(any(unit.kind == "tokens" for unit in phrase.units))
                self.assertTrue(any(unit.kind == "ct2" for unit in phrase.units))
                fallback = [unit for unit in phrase.units if unit.kind == "ct2"]
                self.assertTrue(all(unit.fallback is not None for unit in fallback))
                self.assertTrue(any(unit.text.isspace() for unit in fallback))

    def test_normal_benchmark_reproduces_exp002_speed_target_at_unchanged_3x(self):
        durations = []
        for case in self.profile["benchmark"]["cases"]:
            if case["class"] != "normal":
                continue
            output = self.tasks.build_communication(Utterance(case["english"]))
            self.assertIsInstance(output.phrase, Exp002Phrase)
            durations.append(estimated_duration(output, self.codec, 3))
        expected = self.profile["benchmark"]["measured_results"]["normal"]["candidate"]
        self.assertAlmostEqual(statistics.mean(durations), expected["mean_seconds"], places=3)
        self.assertAlmostEqual(max(durations), expected["max_seconds"], places=3)
        self.assertEqual(sum(value > 10 for value in durations), expected["count_over_10_seconds"])

    def test_ct2_remains_available_as_legacy_profile(self):
        legacy = TaskController(self.codec, "ct2").build_communication(Utterance("Unsupported calculus phrase."))
        self.assertNotIsInstance(legacy.phrase, Exp002Phrase)


class ProsodyTests(unittest.TestCase):
    def test_deterministic_prosody_categories(self):
        cases = {
            "Question. Rocky think yes. Question difficult.": "question",
            "Amaze amaze amaze!": "excitement",
            "You sad. Sad not good. Rocky here. We team.": "reassurance",
            "Derivative measures change.": "technical",
            "Rocky ready.": "neutral",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(classify_prosody(text).name, expected)

    def test_bounded_voice_tuning_preserves_context_profile(self):
        tuned = tuned_profile(PROSODY["question"], -1, 1, 0)
        self.assertEqual(tuned.name, "question")
        self.assertEqual((tuned.rate, tuned.pitch, tuned.volume), ("slow", "x-high", "medium"))
        with self.assertRaises(ValueError):
            tuned_profile(PROSODY["neutral"], 3, 0, 0)

    def test_model_text_cannot_inject_ssml_controls(self):
        raw = "Rocky says </prosody><audio src='https://example.invalid/x'/> amaze!"
        ssml = build_ssml(raw, PROSODY["excitement"])
        self.assertNotIn("<audio ", ssml)
        self.assertNotIn("</prosody><audio", ssml)
        self.assertIn("&lt;/prosody&gt;", ssml)
        self.assertIn("&lt;audio", ssml)


class PersistentTranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.player = FakePlayer()
        self.voice = FakeVoice()
        self.hardware = DesktopHardware(Path(self.temp.name), player=self.player, speech_renderer=self.voice, duration_multiplier=3)
        self.brain = BrainController(
            provider=DummyAIProvider(),
            hardware=self.hardware,
            config=BrainConfig(max_provider_response_bytes=4096, operation_timeout_ms=10000),
        )
        self.brain.task_controller = TaskController(self.hardware.codec, "exp002")
        self.brain.boot()
        self.worker = ReadyWorker({"text": "Rocky ready. Good."})
        self.conversation = ConversationController(self.brain, None, "Rocky style", worker=self.worker)
        self.settings = {"provider": "dummy", "model": "none", "text_encoding": "exp002"}
        self.display = {"automatic": False}

    def tearDown(self):
        self.conversation.close()
        self.temp.cleanup()

    def turn(self, prompt, response):
        self.worker.candidate = {"text": response}
        self.conversation.start(prompt)
        result = self.conversation.poll()
        self.assertNotIn("error", result)
        wait_audio(self.hardware)
        return result

    def test_translation_overlaps_chordic_after_actual_playback_start(self):
        handle_command("/translate on", self.conversation, self.settings, self.display)
        self.turn("one", "Rocky ready. Good.")
        text, delay, gated = self.voice.starts[-1]
        self.assertEqual(text, "Rocky ready. Good.")
        self.assertEqual(delay, 0)
        self.assertTrue(gated)
        self.voice.last_duration_seconds = 5.0
        self.hardware.duration = 8.0
        self.assertEqual(self.hardware.combined_duration, 8.0)

    def test_explicit_session_name_capture_and_clear(self):
        self.assertEqual(explicit_user_name("My name is wyatt"), "Wyatt")
        self.assertEqual(explicit_user_name("Call me Wyatt."), "Wyatt")
        self.assertEqual(explicit_user_name("I am sad"), "")
        self.conversation.start("My name is wyatt")
        self.assertEqual(self.conversation.user_name, "Wyatt")
        self.assertEqual(self.worker.ctx.user_name, "Wyatt")
        self.conversation.poll()
        self.conversation.clear()
        self.assertEqual(self.conversation.user_name, "")

    def test_translation_on_persists_two_turns_then_off_stops_voice(self):
        handle_command("/translate on", self.conversation, self.settings, self.display)
        first = self.turn("one", "Rocky ready. Good.")
        second = self.turn("two", "Rocky help you.")
        self.assertTrue(first["spoken"])
        self.assertTrue(second["spoken"])
        self.assertEqual([item[0] for item in self.voice.starts], ["Rocky ready. Good.", "Rocky help you."])
        self.assertTrue(self.conversation.translation_enabled)
        handle_command("/translate off", self.conversation, self.settings, self.display)
        third = self.turn("three", "Rocky done.")
        self.assertFalse(third["spoken"])
        self.assertEqual(len(self.voice.starts), 2)
        self.assertFalse(self.conversation.translation_enabled)

    def test_status_and_clear_preserve_session_mode(self):
        handle_command("/translate on", self.conversation, self.settings, self.display)
        self.turn("one", "Rocky ready.")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            handle_command("/translate status", self.conversation, self.settings, self.display)
        self.assertIn("ON", out.getvalue())
        handle_command("/clear", self.conversation, self.settings, self.display)
        self.assertTrue(self.conversation.translation_enabled)
        self.assertTrue(self.hardware.translation_enabled)
        self.assertEqual(self.conversation.history, [])

    def test_mute_cancel_stop_reset_and_unmute_control_voice(self):
        handle_command("/translate on", self.conversation, self.settings, self.display)
        handle_command("/mute", self.conversation, self.settings, self.display)
        muted = self.turn("muted", "Rocky quiet.")
        self.assertFalse(muted["spoken"])
        self.assertEqual(len(self.voice.starts), 0)
        handle_command("/unmute", self.conversation, self.settings, self.display)
        self.turn("speak", "Rocky speaks.")
        self.assertEqual(len(self.voice.starts), 1)
        before_cancel = self.voice.cancel_count
        handle_command("/cancel", self.conversation, self.settings, self.display)
        self.assertGreater(self.voice.cancel_count, before_cancel)
        before_stop = len(self.voice.starts)
        handle_command("/stop", self.conversation, self.settings, self.display)
        self.assertTrue(self.brain.state.estop_latched)
        handle_command("/reset", self.conversation, self.settings, self.display)
        self.assertFalse(self.brain.state.estop_latched)
        self.assertEqual(len(self.voice.starts), before_stop)

    def test_replay_replays_voice_only_when_translation_is_on(self):
        handle_command("/translate on", self.conversation, self.settings, self.display)
        self.turn("one", "Rocky ready.")
        count = len(self.voice.starts)
        handle_command("/replay", self.conversation, self.settings, self.display)
        self.assertEqual(len(self.voice.starts), count + 1)
        handle_command("/translate off", self.conversation, self.settings, self.display)
        handle_command("/replay", self.conversation, self.settings, self.display)
        self.assertEqual(len(self.voice.starts), count + 1)

    def test_voice_error_is_surfaced_and_latches_stop(self):
        handle_command("/translate on", self.conversation, self.settings, self.display)
        self.turn("one", "Rocky ready.")
        self.voice.fail_on_poll = True
        result = self.conversation.poll()
        self.assertIn("BACKEND_FAILED", result["error"])
        self.assertTrue(self.brain.state.estop_latched)

    def test_tone_and_voice_commands_are_bounded(self):
        handle_command("/tone resonant", self.conversation, self.settings, self.display)
        self.assertEqual(self.hardware.tone_style, "resonant")
        with self.assertRaises(ValueError):
            handle_command("/tone whale", self.conversation, self.settings, self.display)
        handle_command("/voice rate -1", self.conversation, self.settings, self.display)
        self.assertEqual(self.voice.rate_offset, -1)
        with self.assertRaises(ValueError):
            handle_command("/voice pitch 3", self.conversation, self.settings, self.display)

    def test_language_command_switches_future_profile_without_deleting_ct2(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            handle_command("/language", self.conversation, self.settings, self.display)
        self.assertIn("exp002", out.getvalue())
        handle_command("/language ct2", self.conversation, self.settings, self.display)
        self.assertEqual(self.brain.task_controller.text_encoding, "ct2")
        handle_command("/language exp002", self.conversation, self.settings, self.display)
        self.assertEqual(self.brain.task_controller.text_encoding, "exp002")


if __name__ == "__main__":
    unittest.main()
