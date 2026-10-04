"""Session history and inference supervision above the deterministic brain."""

from brain.contracts import BrainOutcome, ConnectionState
from brain.validation import validate_utterance
from .providers import ConversationContext
from .worker import InferenceWorker
from .translation import decoded_text
from csp.learning import WORDS


class ConversationController:
    def __init__(self, brain, provider, personality, *, timeout=120, worker=None):
        self.brain = brain
        self.worker = worker or InferenceWorker(provider, timeout)
        self.personality = personality
        self.history = []
        self.pending = None
        self.last_text = None
        self.last_output = None

    def start(self, text):
        if self.pending is not None:
            raise ValueError("BUSY: wait, or use /cancel")
        if type(text) is not str or not text.strip() or len(text.encode("utf-8")) > 1024:
            raise ValueError("input must contain 1–1024 UTF-8 bytes")
        state = self.brain.state
        if state.estop_latched or state.connection_state != ConnectionState.READY:
            raise ValueError("brain is stopped or unavailable; check /status and /reset")
        context = ConversationContext("rocky-text-v1", (), state.backend_id, state.connection_state.value, state.host_motion_mode.value, state.estop_latched, tuple(self.history), self.personality)
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
            utterance = validate_utterance(result["candidate"])
        except ValueError as exc:
            return {"error": f"INVALID_RESPONSE: {exc}"}
        accepted = self.brain.submit_utterance(result["candidate"])
        if accepted.outcome not in {BrainOutcome.ACCEPTED, BrainOutcome.COMPLETED}:
            return {"error": accepted.code.value + ": " + accepted.detail}
        translated, version = decoded_text(accepted.communication)
        if translated != utterance.text:
            self.stop()
            return {"error": "TRANSLATION_MISMATCH; stopped"}
        self.last_text = translated
        self.last_output = accepted.communication
        self.history.extend((("user", text), ("assistant", utterance.text)))
        # Bounded, complete turn pairs. No persistent personal memory in V1.
        while len(self.history) > 24 or sum(len(v.encode("utf-8")) for _, v in self.history) > 12000:
            del self.history[:2]
        return {"text": translated, "version": version, "delivery": accepted.detail}

    def replay(self):
        if self.pending is not None:
            raise ValueError("BUSY: wait or /cancel before replay")
        if self.last_text is None:
            raise ValueError("no response to replay")
        return self.brain.submit_utterance({"text": self.last_text})

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
        self.last_output = None

    def stop(self):
        self.cancel()
        return self.brain.emergency_stop()

    def close(self):
        self.cancel()
        self.brain.close()
