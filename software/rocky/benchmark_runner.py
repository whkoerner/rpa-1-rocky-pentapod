"""Real local-model benchmark runner for Rocky Assistant V2."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import statistics
import time

from csp.conversation import Utterance
from csp.core import CspCodec
from csp.exp003 import coverage as exp003_coverage
from brain.controller import TaskController

from .assistant_contracts import validate_assistant_candidate
from .audio import estimated_duration
from .providers import ConversationContext
from .symbolic_math import detect_symbolic_request
from .tools import detect_arithmetic_expression


@dataclass(frozen=True)
class BenchmarkSummary:
    total: int
    run: int
    skipped: int
    failed: int
    mean_latency_seconds: float | None
    mean_semantic_coverage_percent: float | None
    total_fallback_spans: int


def _history_size(history):
    return sum(len(value.encode("utf-8")) for _, value in history)


def _bounded_history(history):
    result = list(history)
    while len(result) > 24 or _history_size(result) > 12000:
        del result[:2]
    return result


def _auto_check(case, spoken, detail):
    combined = (spoken + "\n" + detail).lower()
    check = case.get("auto_check")
    if not check:
        return {"configured": False, "passed": None}
    if set(check) == {"contains"}:
        expected = str(check["contains"]).lower()
        return {
            "configured": True,
            "passed": expected in combined,
            "rule": "contains",
            "expected": check["contains"],
        }
    if set(check) == {"contains_any"} and type(check["contains_any"]) is list:
        values = [str(value).lower() for value in check["contains_any"]]
        return {
            "configured": True,
            "passed": any(value in combined for value in values),
            "rule": "contains_any",
            "expected": check["contains_any"],
        }
    return {
        "configured": True,
        "passed": False,
        "rule": "invalid_auto_check",
    }


def run_model_benchmark(
    provider,
    personality: str,
    benchmark: dict,
    *,
    duration_multiplier: float = 2.0,
    default_mode: str = "study",
):
    if type(benchmark) is not dict or type(benchmark.get("model_cases")) is not list:
        raise ValueError("invalid Assistant V2 benchmark")
    codec = CspCodec.from_default_spec()
    tasks = TaskController(codec, "exp003")
    histories: dict[str, list[tuple[str, str]]] = {}
    results = []

    for case in benchmark["model_cases"]:
        case_id = case.get("id", "")
        prompt = case.get("prompt", "")
        if type(case_id) is not str or not case_id or type(prompt) is not str or not prompt:
            raise ValueError("benchmark model case requires id and prompt")
        requires = str(case.get("requires", ""))
        if "supplied source material" in requires.lower():
            results.append(
                {
                    "id": case_id,
                    "topic": case.get("topic", ""),
                    "status": "NOT_RUN_MISSING_SOURCE",
                    "requires": requires,
                }
            )
            continue

        session = str(case.get("session", case_id))
        history = histories.setdefault(session, [])
        mode = str(case.get("mode", default_mode))
        deterministic = (
            detect_arithmetic_expression(prompt) is not None
            or detect_symbolic_request(prompt) is not None
        )
        context = ConversationContext(
            "rocky-benchmark-v1",
            (),
            "benchmark-no-hardware",
            "READY",
            "DISABLED",
            False,
            tuple(history),
            personality,
            "",
            mode,
        )
        started = time.perf_counter()
        try:
            candidate = provider.propose(prompt, context)
            latency = time.perf_counter() - started
            response = validate_assistant_candidate(
                candidate, allow_tool_calls=False
            )
            output = tasks.build_communication(Utterance(response.spoken_text))
            stats = exp003_coverage(output.phrase)
            duration = estimated_duration(
                output, codec, duration_multiplier
            )
            auto_check = _auto_check(
                case, response.spoken_text, response.detail_text
            )
            results.append(
                {
                    "id": case_id,
                    "topic": case.get("topic", ""),
                    "status": "RUN",
                    "route": "deterministic_pre_router"
                    if deterministic
                    else "local_model_or_model_requested_tool",
                    "latency_seconds": round(latency, 3),
                    "spoken_text": response.spoken_text,
                    "detail_text": response.detail_text,
                    "spoken_utf8_bytes": len(
                        response.spoken_text.encode("utf-8")
                    ),
                    "detail_utf8_bytes": len(
                        response.detail_text.encode("utf-8")
                    ),
                    "structured_response_valid": True,
                    "semantic_coverage_percent": stats["semantic_percent"],
                    "fallback_spans": stats["fallback_spans"],
                    "fallback_bytes": stats["fallback_bytes"],
                    "estimated_chordic_seconds": round(duration, 3),
                    "auto_check": auto_check,
                    "factual_correctness_review": "NOT_RATED",
                    "usefulness_review": "NOT_RATED",
                    "personality_review": "NOT_RATED",
                }
            )
            assistant_history = response.spoken_text
            if response.detail_text:
                assistant_history += "\nDetail:\n" + response.detail_text
            history.extend((("user", prompt), ("assistant", assistant_history)))
            histories[session] = _bounded_history(history)
        except Exception as exc:
            latency = time.perf_counter() - started
            results.append(
                {
                    "id": case_id,
                    "topic": case.get("topic", ""),
                    "status": "FAILED",
                    "latency_seconds": round(latency, 3),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    run_rows = [row for row in results if row["status"] == "RUN"]
    summary = BenchmarkSummary(
        total=len(results),
        run=len(run_rows),
        skipped=sum(row["status"].startswith("NOT_RUN") for row in results),
        failed=sum(row["status"] == "FAILED" for row in results),
        mean_latency_seconds=(
            round(statistics.mean(row["latency_seconds"] for row in run_rows), 3)
            if run_rows
            else None
        ),
        mean_semantic_coverage_percent=(
            round(
                statistics.mean(
                    row["semantic_coverage_percent"] for row in run_rows
                ),
                1,
            )
            if run_rows
            else None
        ),
        total_fallback_spans=sum(row["fallback_spans"] for row in run_rows),
    )
    return {
        "schema_version": "1",
        "benchmark_id": benchmark.get("benchmark_id", ""),
        "provider": type(provider).__name__,
        "duration_multiplier": duration_multiplier,
        "summary": summary.__dict__,
        "results": results,
        "review_note": (
            "Automated metrics are evidence for structure, tools, coverage and timing. "
            "Factual correctness, usefulness, personality and listening quality remain "
            "human-review fields unless a case has an explicit auto_check."
        ),
    }


def run_benchmark_file(
    provider,
    personality: str,
    benchmark_path: Path,
    output_path: Path,
    *,
    duration_multiplier: float = 2.0,
):
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    report = run_model_benchmark(
        provider,
        personality,
        benchmark,
        duration_multiplier=duration_multiplier,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output_path)
    return report
