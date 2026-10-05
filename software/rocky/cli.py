"""Windows-first multi-turn terminal client. Inference never owns the input loop."""

import argparse
import codecs
from collections import deque
from importlib import resources
import json
import math
import os
from pathlib import Path
import queue
import re
import threading
import time
import sys

from brain.ai import DummyAIProvider
from brain.contracts import BrainConfig, BrainOutcome, ConnectionState
from brain.controller import BrainController, JsonlEventLogger, TaskController
from .audio import SAMPLE_RATE
from .conversation import ConversationController
from .desktop import DesktopHardware
from .providers import DummyConversationProvider, LocalAIProvider, strict_json
from .personality import load_personality
from .translation import decoded_text, learning_rows, representation_summary
from csp.learning import WORDS

HELP = """Type a message to Rocky. Commands:
/help       show commands             /status     brain/backend/language status
/translate on|off|status  persistent English display + local spoken translation
/translate  decode the last reply once (backward compatible)
/language [exp003|exp002|ct2|ct1]  show/change future Chordic conversation profile
/mode [normal|study|coding|project]  choose assistant response mode
/replay     replay last tones; also voice when persistent translation is on
/mute       stop/silence tones + voice /unmute    enable future playback
/clear      forget history; translation mode persists
/model      show provider/model       /offline    explain local-only operation
/cancel     cancel inference/audio    /stop       cancel, silence and latch stop
/reset      operator reset (no replay) /quit      exit
/dictionary show CT2 starter words    /word thank you  replay one CT2 entry
/learn      use 3x timing + token view /speed 1..6 change duration multiplier
/tokens     inspect last representation /auto      legacy display-only toggle
/tone [pure|resonant|contour-v1|vocal-v1]  A/B Chordic timbre
/voice status|list|select NAME|rate N|pitch N|volume N   tune local English voice (-2..2)
Ctrl+C stops and exits. /listen is reserved for V2; typed input always works."""

NO_INPUT = object()

_SPEED_DUPLICATE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)/speed\s+\1$")


def parse_speed_command(line):
    """Parse /learn or /speed, recovering only the observed exact duplicate paste."""
    if line == "/learn":
        return 3.0
    if not line.startswith("/speed "):
        raise ValueError("speed command must be /speed N")
    raw = line[7:].strip()
    duplicate = _SPEED_DUPLICATE.fullmatch(raw)
    if duplicate:
        raw = duplicate.group(1)
    try:
        speed = float(raw)
    except ValueError as exc:
        raise ValueError("speed must be a duration multiplier from 1 to 6") from exc
    if not math.isfinite(speed) or not 1 <= speed <= 6:
        raise ValueError("speed must be a duration multiplier from 1 to 6")
    return speed


class TerminalInput:
    """Poll the native console without leaving a thread locked inside input()."""

    def __init__(self):
        self.buffer = ""
        self.lines = deque()
        self.eof = False
        self.decoder = codecs.getincrementaldecoder(sys.stdin.encoding or "utf-8")(errors="replace")
        self.extended_key = False
        self.overlong = False
        self.inbox = None
        if os.name == "nt" and not sys.stdin.isatty():
            # Windows pipes cannot use select. A bounded reader exits on quit/EOF.
            self.inbox = queue.Queue(maxsize=1)
            def read_pipe():
                while True:
                    line = sys.stdin.readline(2048)
                    self.inbox.put(line.rstrip("\r\n") if line else None)
                    if not line or line.strip() == "/quit":
                        return
            threading.Thread(target=read_pipe, daemon=True).start()

    def poll(self):
        if self.inbox is not None:
            try:
                return self.inbox.get_nowait()
            except queue.Empty:
                return NO_INPUT
        if self.lines:
            return self.lines.popleft()
        if self.eof:
            return None
        if os.name == "nt":
            import msvcrt
            # A finite batch keeps operator/worker service responsive during paste.
            for _ in range(256):
                if not msvcrt.kbhit():
                    break
                char = msvcrt.getwch()
                if self.extended_key:
                    self.extended_key = False
                    continue
                if char in ("\x00", "\xe0"):
                    self.extended_key = True
                elif char == "\x03":
                    raise KeyboardInterrupt
                elif char == "\x1a":
                    self.eof = True
                    return None
                elif char in ("\r", "\n"):
                    print(flush=True)
                    line, self.buffer = self.buffer, ""
                    if self.overlong:
                        self.overlong = False
                        raise ValueError("input line exceeds terminal buffer")
                    return line.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
                elif char == "\b":
                    if self.buffer:
                        self.buffer = self.buffer[:-1]
                        print("\b \b", end="", flush=True)
                elif char.isprintable() or 0xD800 <= ord(char) <= 0xDFFF:
                    if len(self.buffer) < 4096:
                        self.buffer += char
                        msvcrt.putwch(char)
                    else:
                        self.overlong = True
            return NO_INPUT
        import select
        if not select.select([sys.stdin], [], [], 0)[0]:
            return NO_INPUT
        raw = os.read(sys.stdin.fileno(), 4096)
        if not raw:
            self.eof = True
            tail, self.buffer = self.buffer, ""
            return tail if tail else None
        self.buffer += self.decoder.decode(raw)
        parts = self.buffer.split("\n")
        self.buffer = parts.pop()
        if self.overlong:
            if not parts:
                self.buffer = ""
                return NO_INPUT
            parts.pop(0)
            self.overlong = False
            self.lines.extend(line.rstrip("\r") for line in parts)
            raise ValueError("input line exceeds terminal buffer")
        self.lines.extend(line.rstrip("\r") for line in parts)
        if len(self.buffer) > 4096:
            self.buffer = ""
            self.overlong = True
        return self.lines.popleft() if self.lines else NO_INPUT


def configuration(args):
    root = resources.files("rocky").joinpath("config")
    defaults = strict_json(root.joinpath("rocky.json").read_text(encoding="utf-8"))
    if args.config:
        custom = strict_json(args.config.read_text(encoding="utf-8-sig"))
        if type(custom) is not dict or set(custom) - set(defaults):
            raise ValueError("settings must be an object with known fields: " + ", ".join(sorted(defaults)))
        legacy_generated = (
            "defaults_profile_version" not in custom
            and custom.get("duration_multiplier") == 3
            and custom.get("text_encoding") == "exp002"
            and custom.get("tone_style") == "resonant"
        )
        if legacy_generated:
            custom = dict(custom)
            custom.pop("duration_multiplier", None)
            custom.pop("text_encoding", None)
            custom.pop("tone_style", None)
            custom["defaults_profile_version"] = defaults["defaults_profile_version"]
        defaults.update(custom)
    if type(defaults["personality_profile"]) is not str or not defaults["personality_profile"]:
        raise ValueError("personality_profile must be a nonempty file path")
    profile = Path(defaults["personality_profile"])
    if not profile.is_absolute():
        # A profile supplied by a custom file is relative to that file, not the CWD.
        base = args.config.parent if args.config and "personality_profile" in custom else Path(str(root))
        profile = base / profile
    defaults["personality_profile"] = str(profile.resolve())
    if type(defaults["text_encoding"]) is not str or defaults["text_encoding"] not in {"ct1", "ct2", "exp002", "exp003"}:
        raise ValueError("text_encoding must be ct1, ct2, exp002 or exp003")
    if type(defaults["assistant_mode"]) is not str or defaults["assistant_mode"] not in {"normal", "study", "coding", "project"}:
        raise ValueError("assistant_mode must be normal, study, coding or project")
    for key in defaults:
        value = getattr(args, key, None)
        if value is not None:
            defaults[key] = value
    if type(defaults["provider"]) is not str or defaults["provider"] not in {"local", "dummy"} or type(defaults["audio_backend"]) is not str or defaults["audio_backend"] not in {"auto", "winsound", "pygame", "wav"}:
        raise ValueError("invalid provider/audio backend")
    if defaults["tone_style"] not in {"pure", "resonant", "contour-v1", "vocal-v1"}:
        raise ValueError("tone_style must be pure, resonant, contour-v1 or vocal-v1")
    if type(defaults["translation_enabled"]) is not bool:
        raise ValueError("translation_enabled must be true or false")
    if type(defaults["defaults_profile_version"]) is not int or defaults["defaults_profile_version"] < 1:
        raise ValueError("defaults_profile_version must be a positive integer")
    if type(defaults["translation_voice"]) is not str or len(defaults["translation_voice"]) > 200 or any(ord(c) < 32 for c in defaults["translation_voice"]):
        raise ValueError("invalid translation_voice")
    for key in ("voice_rate", "voice_pitch", "voice_volume"):
        if type(defaults[key]) is not int or not -2 <= defaults[key] <= 2:
            raise ValueError(f"{key} must be an integer from -2 to 2")
    if type(defaults["port"]) is not int or not 1 <= defaults["port"] <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")
    for key, low, high in (("volume", 0, 0.3), ("timeout", 1, 600), ("duration_multiplier", 1, 6)):
        value = defaults[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
    if type(defaults["model"]) is not str or not defaults["model"] or len(defaults["model"]) > 200 or not defaults["model"].isascii() or any(c.isspace() for c in defaults["model"]):
        raise ValueError("invalid model name")
    return defaults


def handle_command(line, conversation, settings, display):
    brain = conversation.brain
    hardware = brain.hardware
    if line == "/quit":
        return False
    if line == "/help":
        print(HELP)
    elif line == "/status":
        state = brain.state
        print(f"{state.backend_id}: {state.connection_state.value}; motion={state.host_motion_mode.value}; stop={state.estop_latched}; muted={hardware.muted}; thinking={conversation.pending is not None}; audio={hardware.audio_status}; voice={hardware.voice_status}; translation={conversation.translation_enabled}; language={brain.task_controller.text_encoding}; mode={conversation.assistant_mode}; name={conversation.user_name or 'unknown'}; tone={hardware.tone_style}; duration_multiplier={hardware.duration_multiplier}")
    elif line in {"/translate on", "/translate off", "/translate status"}:
        if line == "/translate status":
            print("Persistent translation: " + ("ON" if conversation.translation_enabled else "OFF") + f"; voice={hardware.voice_status}")
        else:
            enabled = line.endswith(" on")
            conversation.set_translation(enabled)
            print("Persistent translation: " + ("ON; English will display and actively overlap Chordic while finishing after it, until /translate off." if enabled else "OFF; current/pending English voice cancelled."))
    elif line == "/translate":
        if conversation.last_output is None:
            print("No response yet.")
        else:
            text, version = decoded_text(conversation.last_output)
            print(f"Decoded English ({version}; not microphone decoding): {text}")
    elif line == "/auto":
        display["automatic"] = not display.get("automatic", False)
        print("Legacy display-only translation: " + str(display["automatic"]) + ". Use /translate on for persistent display + spoken English.")
    elif line == "/language" or line.startswith("/language "):
        if conversation.pending is not None:
            raise ValueError("BUSY: wait or /cancel before changing language profile")
        if line == "/language":
            print("Language profile: " + brain.task_controller.text_encoding)
        else:
            profile = line[10:].strip().lower()
            if profile not in {"exp003", "exp002", "ct2", "ct1"}:
                raise ValueError("language must be exp003, exp002, ct2 or ct1")
            brain.task_controller.text_encoding = profile
            settings["text_encoding"] = profile
            print("Language profile: " + profile + " (applies to future replies; CT2 remains available for compatibility/fallback).")
    elif line == "/mode" or line.startswith("/mode "):
        if line == "/mode":
            print("Assistant mode: " + conversation.assistant_mode)
        else:
            mode = line[6:].strip().lower()
            conversation.set_mode(mode)
            settings["assistant_mode"] = mode
            print("Assistant mode: " + mode + ". Spoken replies stay short; detail appears in the UI/terminal when useful.")
    elif line == "/tone" or line.startswith("/tone "):
        if line == "/tone":
            print("Chordic tone style: " + hardware.tone_style)
        else:
            style = line[6:].strip().lower()
            if style not in {"pure", "resonant", "contour-v1", "vocal-v1"}:
                raise ValueError("tone style must be pure, resonant, contour-v1 or vocal-v1")
            hardware.tone_style = style
            settings["tone_style"] = style
            print("Chordic tone style: " + style + ". Applies to future playback/replay.")
    elif line in {"/voice", "/voice status"}:
        voice = hardware.voice
        print(f"Voice: {voice.voice_name or '[Windows default]'}; rate={voice.rate_offset}; pitch={voice.pitch_offset}; volume={voice.volume_offset}")
    elif line == "/voice list":
        print("\n".join(hardware.voice.check_available()))
    elif line.startswith("/voice select "):
        name = line[len("/voice select "):].strip()
        if not name:
            raise ValueError("voice name required")
        hardware.voice.configure(voice_name=name)
        settings["translation_voice"] = name
        print("Voice selected: " + name)
    elif line.startswith("/voice rate ") or line.startswith("/voice pitch ") or line.startswith("/voice volume "):
        _, field, raw = line.split(maxsplit=2)
        value = int(raw)
        hardware.voice.configure(**{field + "_offset": value})
        settings["voice_" + field] = value
        print(f"Voice {field}: {value}")
    elif line == "/dictionary":
        for word, token in WORDS.items():
            print(f"{word}: {token} = {' '.join(hardware.codec.encode_token(token).notes)}")
    elif line == "/tokens":
        if conversation.last_output is None:
            print("No response yet.")
        else:
            for text, token in learning_rows(conversation.last_output):
                print(f"{text!r}: {token}")
    elif line.startswith("/word "):
        result = conversation.replay_word(line[6:])
        print(result.code.value + ": " + result.detail)
    elif line == "/learn" or line.startswith("/speed "):
        speed = parse_speed_command(line)
        hardware.duration_multiplier = speed
        if line == "/learn":
            display["learning"] = True
            display["automatic"] = True
        print(f"Next playback: notes and gaps x{speed:g}; pitch/volume unchanged. /replay to hear it.")
    elif line == "/replay":
        result = conversation.replay()
        print(result.code.value + ": " + result.detail)
    elif line in {"/mute", "/unmute"}:
        hardware.muted = line == "/mute"
        if hardware.muted:
            hardware.player.stop()
        print("Muted: " + str(hardware.muted))
    elif line == "/clear":
        conversation.clear()
        hardware.cancel_audio()
        print("Session history cleared; pending inference/audio cancelled. Persistent translation remains " + ("ON." if conversation.translation_enabled else "OFF.") + " Local WAV remains until replaced.")
    elif line == "/model":
        print(f"provider={settings['provider']}; model={settings['model'] if settings['provider'] == 'local' else 'none (deterministic diagnostic)'}")
    elif line == "/offline":
        print("AI connects only to 127.0.0.1. Spoken translation uses installed Windows System.Speech voices. No TTS cloud fallback or silent voice download. Disable Ollama cloud, then disconnect internet to verify; this command itself does not test your network.")
    elif line == "/cancel":
        conversation.cancel()
        hardware.cancel_audio()
        print("Inference and audio cancelled; stop is not latched.")
    elif line == "/stop":
        conversation.stop()
        print("Stopped and latched. Use /reset to recover.")
    elif line == "/reset":
        conversation.cancel()
        print("Reset to disabled." if brain.reset_stop() else "Reset unavailable; inspect /status.")
    elif line == "/listen":
        print("Voice input is prepared for V2 only. Type your message.")
    else:
        print("Unknown command. Use /help.")
    return True


def terminal(conversation, settings):
    terminal_input = TerminalInput()
    display = {"automatic": False}
    print(HELP)
    print("> ", end="", flush=True)
    last_audio_status = None
    last_voice_status = None
    while True:
        status = conversation.brain.hardware.audio_status
        if status != last_audio_status and status not in {"IDLE", "RENDERING"}:
            print("\nAudio: " + status, flush=True)
        last_audio_status = status
        voice_status = conversation.brain.hardware.voice_status
        if voice_status != last_voice_status and voice_status not in {"IDLE", "QUEUED", "SPEAKING", "CANCELLED"}:
            print("\nEnglish voice: " + voice_status, flush=True)
            if voice_status == "COMPLETED":
                hardware = conversation.brain.hardware
                margin = hardware.translation_finish_margin
                relation = "target met" if margin >= 0 else f"Chordic outlasted English by {-margin:.2f}s"
                print(f"Durations: Chordic estimated={hardware.duration:.2f}s; spoken English measured={hardware.speech_duration:.2f}s; translation start={hardware.translation_delay_seconds:.2f}s after Chordic begins; overlap wall estimate={hardware.combined_duration:.2f}s; {relation}", flush=True)
        last_voice_status = voice_status
        result = conversation.poll()
        if result:
            if "error" in result:
                print("\n" + result["error"])
            else:
                show_english = conversation.translation_enabled or display.get("automatic", False)
                print(f"\nDecoded English ({result['version']}): " + (result["text"] if show_english else "[hidden; /translate for last English or /translate on for persistent English + voice]"))
                print("Representation: " + representation_summary(conversation.last_output))
                if result.get("detail_text"):
                    print("Details:\n" + result["detail_text"])
                print("Audio: " + result["delivery"])
                if conversation.translation_enabled:
                    print("English voice: " + (f"active overlap queued; target start {conversation.brain.hardware.translation_delay_seconds:.2f}s after Chordic begins; measured local TTS audio {conversation.brain.hardware.translation_estimated_speech_seconds:.2f}s" if result.get("spoken") else "suppressed by mute"))
                if conversation.brain.hardware.duration > 30:
                    print("Long playback: fallback is exact but not fluent speech. /cancel or /word hello for short practice.")
                if display.get("learning") and (conversation.translation_enabled or display.get("automatic", False)):
                    for text, token in learning_rows(conversation.last_output):
                        print(f"{text!r}: {token}")
            print("> ", end="", flush=True)
        try:
            line = terminal_input.poll()
        except ValueError as exc:
            print(str(exc))
            continue
        if line is NO_INPUT:
            time.sleep(0.03)
            continue
        if line is None:
            return
        line = line.strip()
        try:
            if line.startswith("/"):
                if not handle_command(line, conversation, settings, display):
                    return
                print("> ", end="", flush=True)
            elif line:
                conversation.start(line)
                print("Thinking locally... /cancel, /stop and /status remain available.", flush=True)
        except (ValueError, RuntimeError) as exc:
            print(str(exc), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rocky Assistant V2")
    parser.add_argument("command", nargs="?", choices=("chat", "web", "audio-test", "check"), default="chat")
    parser.add_argument("--provider", choices=("local", "dummy"))
    parser.add_argument("--model")
    parser.add_argument("--port", type=int)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--audio-backend", choices=("auto", "winsound", "pygame", "wav"))
    parser.add_argument("--volume", type=float)
    parser.add_argument("--duration-multiplier", type=float)
    parser.add_argument("--text-encoding", choices=("ct1", "ct2", "exp002", "exp003"))
    parser.add_argument("--assistant-mode", choices=("normal", "study", "coding", "project"))
    parser.add_argument("--ui-port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--tone-style", choices=("pure", "resonant", "contour-v1", "vocal-v1"))
    parser.add_argument("--translation-voice")
    parser.add_argument("--voice-rate", type=int)
    parser.add_argument("--voice-pitch", type=int)
    parser.add_argument("--voice-volume", type=int)
    user_config = Path.home() / ".rpa1" / "settings" / "rocky.json"
    parser.add_argument("--config", type=Path, default=user_config if user_config.is_file() else None)
    parser.add_argument("--personality", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".rpa1" / "conversation-v1")
    args = parser.parse_args(argv)
    conversation = None
    brain = None
    try:
        settings = configuration(args)
        personality = load_personality(args.personality or Path(settings["personality_profile"]))
        if args.command == "check":
            if settings["provider"] == "local":
                LocalAIProvider(settings["model"], settings["port"], min(settings["timeout"], 5)).check_available()
            print("Configuration and selected provider checks passed; no inference/audio acceptance implied.")
            return 0
        hardware = DesktopHardware(args.data_dir, backend=settings["audio_backend"], volume=settings["volume"], duration_multiplier=settings["duration_multiplier"], tone_style=settings["tone_style"], translation_voice=settings["translation_voice"], voice_rate=settings["voice_rate"], voice_pitch=settings["voice_pitch"], voice_volume=settings["voice_volume"])
        brain = BrainController(provider=DummyAIProvider(), hardware=hardware, config=BrainConfig(max_provider_response_bytes=4096, operation_timeout_ms=10000), event_logger=JsonlEventLogger(args.data_dir / "events.jsonl"))
        brain.task_controller = TaskController(hardware.codec, settings["text_encoding"])
        if brain.boot().connection_state != ConnectionState.READY:
            print('Audio backend could not open. Windows: check output device; Linux: install .[audio]. Use --audio-backend wav to diagnose without speakers.')
            return 2
        if args.command == "audio-test":
            result = brain.submit_text("hello")
            print(result.code.value + ": " + result.detail)
            while hardware.rendering:
                hardware.poll()
                time.sleep(0.03)
            hardware.poll()
            print(hardware.audio_status)
            print(f"WAV: {hardware.last_wav}; estimated playback {hardware.duration:.2f}s")
            if result.outcome not in {BrainOutcome.ACCEPTED, BrainOutcome.COMPLETED}:
                return 2
            if hardware.player.backend != "wav":
                import wave
                with wave.open(str(hardware.last_wav), "rb") as handle:
                    duration = handle.getnframes() / SAMPLE_RATE
                time.sleep(duration + 0.1)
            return 0
        provider = DummyConversationProvider() if settings["provider"] == "dummy" else LocalAIProvider(settings["model"], settings["port"], settings["timeout"])
        conversation = ConversationController(brain, provider, personality, timeout=settings["timeout"])
        conversation.set_mode(settings["assistant_mode"])
        if settings["translation_enabled"]:
            if sys.platform == "win32" and hardware.player.backend != "wav":
                conversation.set_translation(True)
            elif sys.platform != "win32":
                print("Persistent spoken translation default is ON for Windows; this platform has no supported local speech backend, so translation remains OFF.")
        print(f"Rocky Assistant V2 | provider={settings['provider']} | audio={hardware.player.backend}")
        print(f"Local output: {args.data_dir}")
        if args.command == "web":
            from .webui import serve_local_web_ui
            serve_local_web_ui(
                conversation,
                settings,
                port=args.ui_port,
                settings_path=args.config or user_config,
                open_browser=not args.no_browser,
            )
        else:
            terminal(conversation, settings)
        return 0
    except KeyboardInterrupt:
        if conversation:
            conversation.stop()
        print("\nStopped.")
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Startup/runtime error: {exc}")
        return 2
    finally:
        if conversation:
            conversation.close()
        elif brain:
            brain.close()


if __name__ == "__main__":
    raise SystemExit(main())
