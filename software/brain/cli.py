"""Windows-friendly offline Brain v0.2 entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .ai import DummyAIProvider
from .controller import BrainController, JsonlEventLogger
from .hardware import SimulatorHardware


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RPA-1 Brain v0.2 offline simulator")
    parser.add_argument(
        "--text",
        default="hello",
        help="text for the deterministic DummyAIProvider (default: hello)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path.home() / ".rpa1" / "brain-v0.2.jsonl",
        help="JSONL event log path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    hardware = SimulatorHardware()
    controller = BrainController(
        provider=DummyAIProvider(),
        hardware=hardware,
        event_logger=JsonlEventLogger(args.log),
    )
    try:
        state = controller.boot()
        print("RPA-1 Brain v0.2")
        print(f"backend: {state.backend_id}")
        print(f"connection: {state.connection_state.value}")
        print(f"native_mode: {state.native_mode}")
        print(f"host_motion_mode: {state.host_motion_mode.value}")
        print(f"estop_latched: {state.estop_latched}")
        print("provider: DummyAIProvider")
        print(f"log: {args.log}")

        result = controller.submit_text(args.text)
        print(f"request_id: {result.request_id}")
        print(f"outcome: {result.outcome.value}")
        print(f"code: {result.code.value}")
        if result.safety is not None:
            print(f"safety: {'ALLOWED' if result.safety.allowed else 'DENIED'}")
        if result.communication is not None:
            print(f"intent: {result.communication.message.intent}")
            print(f"csp: {result.communication.csp_line.rstrip()}")
            print(f"english: {result.communication.canonical_text}")
            print(f"chordic_token: {result.communication.chordic_token}")
            print(f"chordic_notes: {' '.join(result.communication.notes)}")
        if result.receipt is not None:
            print(f"receipt: {result.receipt.status.value}")
            print(f"evidence: {result.receipt.evidence_kind.value}")
            print(f"receipt_reason: {result.receipt.reason}")
        elif result.detail:
            print(f"detail: {result.detail}")
        return 0 if result.outcome.value in {"ACCEPTED", "COMPLETED"} else 2
    finally:
        controller.close()


if __name__ == "__main__":
    raise SystemExit(main())
