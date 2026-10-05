"""Session history and inference supervision above the deterministic brain."""

import re

from brain.contracts import BrainOutcome, ConnectionState
from brain.validation import validate_utterance
from .assistant_contracts import AssistantMode, validate_assistant_candidate
from .providers import ConversationContext
from .worker import InferenceWorker
from .translation import decoded_text
from csp.learning import WORDS


_NAME_PATTERNS = (
    re.compile(r"^\s*my\s+name\s+is\s+([A-Za-z][A-Za-z'’-]{0,31})(?:[.!?]|\s*)$", re.IGNORECASE),
    re.compile(r"^\s*call\s+me\s+([A-Za-z][A-Za-z'’-]{0,31})(?:[.!?]|\s*)$", re.IGNORECASE),
)


def explicit_user_name(text):
    """Return only a conservatively extracted, explicitly supplied name."""
    if type(text) is not str:
        return ""
    for pattern in _NAME_PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            name = match.group(1)
            return name[:1].upper() + name[1:]
    return ""


class ConversationController:
    def __init__(self, brain, provider, personality, *, timeout=120, worker=None):
        self.brain = brain
        self.worker = worker or InferenceWorker(provider, timeout)
        self.personality = personality
        self.history = []
        self.pending = None
        self.last_text = None
        self.last_detail_text = ""
        self.last_output = None
        self.translation_enabled = False
        self.user_name = ""
        self.assistant_mode = AssistantMode.NORMAL.value
        self.memory_store = memory_store
        if hasattr(self.brain.hardware, "translation_enabled"):
            self.brain.hardware.translation_enabled = False

    def set_translation(self, enabled):
        if type(enabled) is not bool:
            raise ValueError("translation mode must be boolean")
        hardware = self.brain.hardware
        if enabled:
            checker = getattr(hardware, "check_voice_available", None)
            if checker is None:
                raise RuntimeError("spoken translation backend is unavailable")
            checker()
        self.translation_enabled = enabled
        if hasattr(hardware, "translation_enabled"):
            hardware.translation_enabled = enabled
        if not enabled:
            voice = getattr(hardware, "voice", None)
            if voice is not None:
                voice.cancel()

    def set_mode(self, mode):
        try:
            selected = AssistantMode(mode)
        except ValueError as exc:
            raise ValueError("assistant mode must be normal, study, coding or project") from exc
        if self.pending is not None:
            raise ValueError("BUSY: wait or /cancel before changing assistant mode")
        self.assistant_mode = selected.value

    def memory_status(self):
        if self.memory_store is None:
            return {"enabled": False, "revision": 0, "count": 0, "path": ""}
        return self.memory_store.status()

    def set_memory_enabled(self, enabled):
        if self.memory_store is None:
            raise ValueError("persistent memory store is unavailable")
        self.memory_store.set_enabled(enabled)

    def memory_items(self):
        if self.memory_store is None:
            return ()
        return self.memory_store.items()

    def remember(self, key, value):
        if self.memory_store is None:
            raise ValueError("persistent memory store is unavailable")
        return self.memory_store.remember(key, value)

    def forget(self, key):
        if self.memory_store is None:
            raise ValueError("persistent memory store is unavailable")
        return self.memory_store.forget(key)

    def clear_memory(self):
        if self.memory_store is None:
            raise ValueError("persistent memory store is unavailable")
        self.memory_store.clear()

    def start(self, text):
        if self.pending is not None:
            raise ValueError("BUSY: wait, or use /cancel")
        if type(text) is not str or not text.strip() or len(text.encode("utf-8")) > 1024:
            raise ValueError("input must contain 1–1024 UTF-8 bytes")
        state = self.brain.state
        if state.estop_latched or state.connection_state != ConnectionState.READY:
            raise ValueError("brain is stopped or unavailable; check /status and /reset")
        supplied_name = explicit_user_name(text)
        if supplied_name:
            self.user_name = supplied_name
        memory_rows = self.memory_store.prompt_rows() if self.memory_store is not None else ()
        context = ConversationContext("rocky-text-v2", (), state.backend_id, state.connection_state.value, state.host_motion_mode.value, state.estop_latched, tuple(self.history), self.personality, self.user_name, self.assistant_mode, memory_rows)
        self.worker.start(text, context)
        self.pending = (text, state.session_id, state.revision)

    def poll(self):
        # Desktop adapter is nonblocking and currently has no asynchronous events.
        # Unexpected events fail closed until a correlated event contract is added.
        try:
            events = self.brain.hardware.poll()
            if events:
                raise RuntimeError("unexpected desktop backend event")
        except Exception as exc:
            self.stop()
            return {"error": f"BACKEND_FAILED: {exc}; stop latched"}
        if self.pending is None:
            return None
        text, session, revision = self.pending
        state = self.brain.state
        if state.session_id != session or state.revision != revision or state.estop_latched:
            self.cancel()
            return {"error": "CANCELLED: brain state changed during inference"}
        result = self.worker.poll()
        if result is None:
            return None
        self.pending = None
        if "error" in result:
            return result
        try:
            response = validate_assistant_candidate(
                result["candidate"], allow_tool_calls=False
            )
            utterance = validate_utterance({"text": response.spoken_text})
        except ValueError as exc:
            return {"error": f"INVALID_RESPONSE: {exc}"}
        accepted = self.brain.submit_utterance({"text": response.spoken_text})
        if accepted.outcome not in {BrainOutcome.ACCEPTED, BrainOutcome.COMPLETED}:
            return {"error": accepted.code.value + ": " + accepted.detail}
        translated, version = decoded_text(accepted.communication)
        if translated != response.spoken_text:
            self.stop()
            return {"error": "TRANSLATION_MISMATCH; stopped"}
        self.last_text = translated
        self.last_detail_text = response.detail_text
        self.last_output = accepted.communication
        assistant_history = response.spoken_text
        if response.detail_text:
            assistant_history += "\nDetail:\n" + response.detail_text
        self.history.extend((("user", text), ("assistant", assistant_history)))
        # Bounded, complete turn pairs. No persistent personal memory in V1.
        while len(self.history) > 24 or sum(len(v.encode("utf-8")) for _, v in self.history) > 12000:
            del self.history[:2]
        spoken = False
        if self.translation_enabled:
            speak = getattr(self.brain.hardware, "speak_translation", None)
            if speak is None:
                self.stop()
                return {"error": "TRANSLATION_VOICE_UNAVAILABLE; stopped"}
            try:
                spoken = bool(speak(translated))
            except Exception as exc:
                return {"error": f"TRANSLATION_VOICE_FAILED: {type(exc).__name__}: {exc}"}
            if not spoken and not self.brain.hardware.muted:
                return {"error": "TRANSLATION_VOICE_NOT_QUEUED"}
        return {"text": translated, "detail_text": response.detail_text, "version": version, "delivery": accepted.detail, "spoken": spoken}

    def replay(self):
        if self.pending is not None:
            raise ValueError("BUSY: wait or /cancel before replay")
        if self.last_text is None:
            raise ValueError("no response to replay")
        result = self.brain.submit_utterance({"text": self.last_text})
        if result.outcome in {BrainOutcome.ACCEPTED, BrainOutcome.COMPLETED} and self.translation_enabled:
            speak = getattr(self.brain.hardware, "speak_translation", None)
            if speak is None or (not speak(self.last_text) and not self.brain.hardware.muted):
                raise RuntimeError("translated voice could not be queued for replay")
        return result

    def replay_word(self, text):
        if self.pending is not None:
            raise ValueError("BUSY: wait or /cancel before word replay")
        if text not in WORDS:
            raise ValueError("unsupported dictionary entry; use /dictionary and its exact lowercase spelling")
        return self.brain.submit_utterance({"text": text})

    def cancel(self):
        self.worker.cancel()
        self.pending = None

    def clear(self):
        self.cancel()
        self.history.clear()
        self.last_text = None
        self.last_detail_text = ""
        self.last_output = None
        self.user_name = ""
        # Translation is a session mode, not conversation history, so /clear
        # deliberately leaves self.translation_enabled unchanged.

    def stop(self):
        self.cancel()
        return self.brain.emergency_stop()

    def close(self):
        self.cancel()
        self.brain.close()
