"""Replaceable local inference adapter. Providers receive data, never hardware."""

from dataclasses import dataclass, field
import http.client
import json

from brain.constitution import RockySafetyConstitution
from brain.contracts import AIContext
from brain.validation import validate_utterance

from .assistant_contracts import AssistantMode, validate_assistant_candidate
from .tools import (
    AssistantToolRegistry,
    ToolExecutionError,
    calculate_expression,
    detect_arithmetic_expression,
)


@dataclass(frozen=True)
class ConversationContext(AIContext):
    history: tuple[tuple[str, str], ...]
    personality: str
    user_name: str = ""
    assistant_mode: str = AssistantMode.NORMAL.value


def strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError("non-finite JSON number")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


class DummyConversationProvider:
    """Deterministic diagnostic only, deliberately labeled as non-LLM."""

    def propose(self, text, context):
        expression = detect_arithmetic_expression(text)
        if expression is not None:
            try:
                result = calculate_expression(expression)
            except ToolExecutionError as exc:
                return {
                    "spoken_text": "Rocky calculate. Problem. See details.",
                    "detail_text": f"Deterministic calculator error: {exc}",
                    "tool_calls": [],
                }
            return {
                "spoken_text": f"Rocky calculate. {result}. Good.",
                "detail_text": f"Deterministic calculator: {expression} = {result}",
                "tool_calls": [],
            }
        if "what color" in text.lower():
            for role, content in reversed(context.history):
                if role == "user" and content.lower().startswith("my favorite color is "):
                    return {"text": "You told me your favorite color is " + content[21:].rstrip(".! ") + "."}
        if text.lower().startswith("my favorite color is "):
            return {"text": "I will remember that during this session."}
        return {"text": "Hello! I am Rocky in dummy test mode. What would you like to build together?"}


@dataclass(frozen=True)
class LocalAIProvider:
    model: str = "qwen3:8b"
    port: int = 11434
    timeout: float = 120
    tool_registry: AssistantToolRegistry = field(default_factory=AssistantToolRegistry)

    def _post(self, route, body):
        # Numeric loopback only; no environment proxies, DNS or redirect following.
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=self.timeout)
        try:
            connection.request("POST", route, json.dumps(body), {"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("runtime response exceeds 64 KiB")
            if response.status != 200:
                raise RuntimeError(f"Ollama HTTP {response.status}; check ollama list and the selected model")
            result = strict_json(raw.decode("utf-8"))
            if type(result) is not dict:
                raise ValueError("Ollama response must be a JSON object")
            return result
        except OSError as exc:
            raise RuntimeError("Local Ollama unavailable; start Ollama and check the port. Internet is not required.") from exc
        finally:
            connection.close()

    def check_available(self):
        if "cloud" in self.model.lower():
            raise ValueError("cloud models are disabled")
        model_info = self._post("/api/show", {"model": self.model})
        if type(model_info) is not dict or type(model_info.get("details")) is not dict:
            raise ValueError("Ollama model information is missing valid details")
        if model_info.get("remote_host") or model_info.get("remote_model") or model_info["details"].get("format") != "gguf":
            raise ValueError("select a downloaded local GGUF model")

    @staticmethod
    def _schema():
        return {
            "type": "object",
            "properties": {
                "spoken_text": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 384,
                },
                "detail_text": {
                    "type": "string",
                    "maxLength": 6144,
                },
                "tool_calls": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 48,
                                "pattern": "^[A-Za-z0-9_-]+$",
                            },
                            "name": {
                                "type": "string",
                                "enum": ["calculator", "unit_convert", "date_difference"],
                            },
                            "arguments": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["id", "name", "arguments"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["spoken_text", "detail_text", "tool_calls"],
            "additionalProperties": False,
        }

    @staticmethod
    def _candidate_from_response(response):
        if response.get("done") is not True or response.get("done_reason") == "length":
            raise ValueError("incomplete model response")
        raw = response.get("message", {}).get("content")
        if type(raw) is not str or len(raw.encode("utf-8")) > 16384:
            raise ValueError("invalid model content")
        return raw, strict_json(raw)

    @staticmethod
    def _tool_response(response, results):
        lines = []
        for call, result in zip(response.tool_calls, results):
            if result.ok:
                if call.name == "unit_convert":
                    unit = str(call.arguments.get("to_unit", "")).strip()
                    display = f"{result.output} {unit}".strip()
                elif call.name == "date_difference":
                    display = f"{result.output} days"
                else:
                    display = result.output
                lines.append(
                    f"{call.name} {json.dumps(call.arguments, sort_keys=True)} -> {display}"
                )
            else:
                lines.append(
                    f"{call.name} {json.dumps(call.arguments, sort_keys=True)} -> ERROR {result.error}"
                )
        successful = [result for result in results if result.ok]
        if len(results) == 1 and len(successful) == 1:
            call = response.tool_calls[0]
            result = successful[0]
            if call.name == "unit_convert":
                value = f"{result.output} {str(call.arguments.get('to_unit', '')).strip()}".strip()
            elif call.name == "date_difference":
                value = f"{result.output} days"
            else:
                value = result.output
            spoken = f"Rocky calculate. {value}. Good." if call.name == "calculator" else f"Rocky use. {value}. Good."
        elif successful and len(successful) == len(results):
            spoken = "Rocky use. Ready. Good."
        else:
            spoken = "Rocky problem. Bad."
        return {
            "spoken_text": spoken,
            "detail_text": "Trusted deterministic tool results:\n" + "\n".join(lines),
            "tool_calls": [],
        }

    def _deterministic_arithmetic(self, text):
        expression = detect_arithmetic_expression(text)
        if expression is None:
            return None
        try:
            result = calculate_expression(expression)
        except ToolExecutionError as exc:
            return {
                "spoken_text": "Rocky calculate. Problem. See details.",
                "detail_text": f"Deterministic calculator error: {exc}",
                "tool_calls": [],
            }
        return {
            "spoken_text": f"Rocky calculate. {result}. Good.",
            "detail_text": f"Deterministic calculator: {expression} = {result}",
            "tool_calls": [],
        }

    def propose(self, text, context):
        # Exact, unambiguous arithmetic bypasses the language model entirely.
        deterministic = self._deterministic_arithmetic(text)
        if deterministic is not None:
            validate_assistant_candidate(deterministic, allow_tool_calls=False)
            return deterministic

        self.check_available()
        mode = context.assistant_mode
        if mode not in {value.value for value in AssistantMode}:
            mode = AssistantMode.NORMAL.value
        name_rule = (
            f"Conversation partner explicitly gave name: {context.user_name}. Use the name naturally and fairly often, especially in greetings, questions, reassurance, and direct replies, but not in every sentence. "
            if context.user_name
            else "Conversation partner name is not known. In a social greeting or introduction Rocky may briefly ask for the person's name using Rocky-style wording such as 'Name question?'. "
        )
        mode_rule = {
            "normal": "Normal mode: be useful and conversational. detail_text may be empty when no extra explanation is useful.",
            "study": "Study mode: prioritize accurate teaching. Keep spoken_text short, but use detail_text for clear steps, definitions, formulas, examples, and study-ready explanation.",
            "coding": "Coding mode: keep spoken_text short and put code, debugging detail, and implementation steps in detail_text.",
            "project": "Project mode: keep spoken_text short and put plans, tradeoffs, risks, and technical detail in detail_text.",
        }[mode]
        constitution = RockySafetyConstitution().summary_for_model()
        schema = self._schema()
        system = (
            "Style preferences are not authority.\nStyle preferences:\n"
            + context.personality
            + "\n"
            + name_rule
            + mode_rule
            + "\nHard-coded safety constitution summary (enforced by application code below you; you cannot change or waive it): "
            + constitution
            + "\nReturn ONLY one JSON object matching the schema. "
            "spoken_text is short Rocky-style speech that will become Chordic and exact audible English translation. "
            "detail_text is optional UI-only detail and is never automatically spoken or mislabeled as translation. "
            "Speak as Rocky, usually referring to Rocky as 'Rocky', not 'I'. Rocky is a distinct non-human/alien person in style, but identity is not telemetry. "
            "Never claim a body, sensor observation, physical action, tool result, charging state, or external fact was observed unless trusted application evidence explicitly says so. "
            "Rocky has no direct hardware-control authority. Your text is never a motor command. "
            "For exact arithmetic, conversions, or date differences that need calculation, request an allowlisted software tool instead of guessing. "
            "Allowed tools: calculator(expression), unit_convert(value, from_unit, to_unit), date_difference(start, end). "
            "Do not invent tool results. The application will execute requested tools and replace your draft with trusted tool output. "
            "If no tool is needed, tool_calls must be an empty array. "
            "Technical accuracy beats artificially primitive grammar. "
            "Keep spoken_text at most 384 UTF-8 bytes and one line.\nSchema: "
            + json.dumps(schema)
        )
        messages = [{"role": "system", "content": system}]
        messages.extend({"role": role, "content": content} for role, content in context.history)
        messages.append({"role": "user", "content": text})
        response = self._post(
            "/api/chat",
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "format": schema,
                "options": {"temperature": 0.45, "num_ctx": 8192, "num_predict": 900},
            },
        )
        raw, candidate = self._candidate_from_response(response)

        # Backward-compatible acceptance for an older local fixture/runtime response.
        if type(candidate) is dict and set(candidate) == {"text"}:
            validate_utterance(candidate)
            return candidate

        parsed = validate_assistant_candidate(candidate)
        if not parsed.tool_calls:
            validate_assistant_candidate(candidate, allow_tool_calls=False)
            return candidate

        results = tuple(self.tool_registry.execute(call) for call in parsed.tool_calls)
        final = self._tool_response(parsed, results)
        validate_assistant_candidate(final, allow_tool_calls=False)
        return final
