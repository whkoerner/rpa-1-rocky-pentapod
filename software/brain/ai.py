"""AI provider boundary for Brain v0.2.

The default provider is deterministic and offline. It returns only candidate
semantic objects and never receives hardware handles.
"""

from __future__ import annotations

from typing import Protocol

from .contracts import AIContext


class AIProvider(Protocol):
    def propose(self, text: str, context: AIContext) -> object | None:
        """Return a candidate semantic object or None when no mapping exists."""


class DummyAIProvider:
    """Small deterministic provider used for offline Brain v0.2 acceptance."""

    _MAPPINGS = {
        "hello": "SOCIAL.HELLO",
        "hi": "SOCIAL.HELLO",
        "yes": "RESPONSE.YES",
        "no": "RESPONSE.NO",
        "help": "REQUEST.HELP",
        "thanks": "SOCIAL.THANKS",
        "thank you": "SOCIAL.THANKS",
        "goodbye": "SOCIAL.GOODBYE",
        "bye": "SOCIAL.GOODBYE",
    }

    def propose(self, text: str, context: AIContext) -> object | None:
        del context
        normalized = " ".join(text.strip().lower().split())
        intent = self._MAPPINGS.get(normalized)
        if intent is None:
            return None
        return {"intent": intent, "arg": ""}
