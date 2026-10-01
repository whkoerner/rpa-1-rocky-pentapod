"""V2 input seam: implementations must return text to ConversationController.start."""

from typing import Protocol


class SpeechInput(Protocol):
    def listen_once(self, *, timeout_seconds: float) -> str:
        """Capture one bounded push-to-talk utterance locally; never call hardware."""
        ...
