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
import threading
import time
import sys

from brain.ai import DummyAIProvider
from brain.contracts import BrainConfig, BrainOutcome, ConnectionState
from brain.controller import BrainController, JsonlEventLogger
from .audio import SAMPLE_RATE
from .conversation import ConversationController
from .desktop import DesktopHardware
from .providers import DummyConversationProvider, LocalAIProvider

HELP = """Type a message to Rocky. Commands:
/help       show commands             /status     brain and backend status
/translate  show last English reply   /auto       toggle automatic translation
/replay     play last reply again     /mute       stop and mute playback
/unmute     enable future playback    /clear      forget session history
/model      show provider/model       /offline    explain local-only operation
/cancel     cancel pending inference  /stop       cancel, silence and latch stop
/reset      operator reset (no replay) /quit      exit
Ctrl+C stops and exits. /listen is reserved for V2; typed input always works."""

NO_INPUT = object()


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
    defaults = json.loads(root.joinpath("rocky.json").read_text(encoding="utf-8"))
    if args.config:
        custom = json.loads(args.config.read_text(encoding="utf-8"))
        if type(custom) is not dict or set(custom) - set(defaults):
            raise ValueError("unknown configuration fields")
        defaults.update(custom)
    for key in defaults:
        value = getattr(args, key, None)
        if value is not None:
            defaults[key] = value
    if defaults["provider"] not in {"local", "dummy"} or defaults["audio_backend"] not in {"auto", "winsound", "pygame", "wav"}:
        raise ValueError("invalid provider/audio backend")
    if type(defaults["port"]) is not int or not 1 <= defaults["port"] <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")
    for key, low, high in (("volume", 0, 0.3), ("timeout", 1, 600)):
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
        print(f"{state.backend_id}: {state.connection_state.value}; motion={state.host_motion_mode.value}; stop={state.estop_latched}; muted={hardware.muted}; thinking={conversation.pending is not None}")
    elif line == "/translate":
        print("Rocky: " + (conversation.last_text or "No response yet."))
    elif line == "/auto":
        display["automatic"] = not display["automatic"]
        print("Automatic translation: " + str(display["automatic"]))
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
        print("Session history cleared; pending inference cancelled. Local WAV remains until replaced.")
    elif line == "/model":
        print(f"provider={settings['provider']}; model={settings['model'] if settings['provider'] == 'local' else 'none (deterministic diagnostic)'}")
    elif line == "/offline":
        print("AI connects only to 127.0.0.1. No downloads or cloud fallback. Disable Ollama cloud, then disconnect internet to verify. This command does not test your network.")
    elif line == "/cancel":
        conversation.cancel()
        print("Pending inference cancelled.")
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
    display = {"automatic": True}
    print(HELP)
    print("> ", end="", flush=True)
    while True:
        result = conversation.poll()
        if result:
            if "error" in result:
                print("\n" + result["error"])
            else:
                print("\nRocky: " + (result["text"] if display["automatic"] else "[Chordic response; /translate for English]"))
                print("Audio: " + result["delivery"])
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
    parser = argparse.ArgumentParser(description="Rocky Conversational Brain V1")
    parser.add_argument("command", nargs="?", choices=("chat", "audio-test"), default="chat")
    parser.add_argument("--provider", choices=("local", "dummy"))
    parser.add_argument("--model")
    parser.add_argument("--port", type=int)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--audio-backend", choices=("auto", "winsound", "pygame", "wav"))
    parser.add_argument("--volume", type=float)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--personality", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".rpa1" / "conversation-v1")
    args = parser.parse_args(argv)
    conversation = None
    brain = None
    try:
        settings = configuration(args)
        personality = args.personality.read_text(encoding="utf-8") if args.personality else resources.files("rocky").joinpath("config", "personality.txt").read_text(encoding="utf-8")
        if len(personality.encode("utf-8")) > 8192:
            raise ValueError("personality exceeds 8192 bytes")
        hardware = DesktopHardware(args.data_dir, backend=settings["audio_backend"], volume=settings["volume"])
        brain = BrainController(provider=DummyAIProvider(), hardware=hardware, config=BrainConfig(max_provider_response_bytes=4096, operation_timeout_ms=10000), event_logger=JsonlEventLogger(args.data_dir / "events.jsonl"))
        if brain.boot().connection_state != ConnectionState.READY:
            print('Audio backend could not open. Windows: check output device; Linux: install .[audio]. Use --audio-backend wav to diagnose without speakers.')
            return 2
        if args.command == "audio-test":
            result = brain.submit_text("hello")
            print(result.code.value + ": " + result.detail)
            print(f"WAV: {hardware.last_wav}")
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
        print(f"Rocky Conversational Brain V1 | provider={settings['provider']} | audio={hardware.player.backend}")
        print(f"Local output: {args.data_dir}")
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
