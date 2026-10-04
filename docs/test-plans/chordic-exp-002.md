# Chordic EXP-002 Rocky integration evidence

**Date:** 2026-10-04  
**Status:** Experimental integration test only  
**Chordic source:** `whkoerner/Chordic-Language` PR #1, commit `65e04f31cd7d53f75efe2d00583270835cabb92b`  
**Rocky baseline:** `fceb7fe8cbcc5b42d3db0e208f6a323f79e2670a`

## Architecture

Chordic remains the authoritative language repository. Rocky stores only a pinned, read-only subset under `experiments/chordic/exp-002-snapshot.json` so its existing timing and Brain infrastructure can test a known Chordic revision without a runtime cross-repository dependency.

No production Brain, SafetyValidator, TaskController, hardware adapter, CT1, CT2, launcher, or audio implementation is changed by EXP-002 integration work.

The existing safety path remains:

`AIProvider → validated response/request → BrainController → SafetyValidator → Task/Communication layer`

The new focused Brain test sends a registered benchmark utterance through `BrainController.submit_utterance` into the existing communication-only simulator and confirms host motion remains disabled.

## Timing evidence

The focused test uses Rocky's real `TaskController`, CT2 encoder, `CspCodec`, and `rocky.audio.estimated_duration` for the English baseline at the existing 3× learning-speed multiplier.

For the 17 required normal-conversation cases:

| Metric | Current Rocky CT2 | Chordic EXP-002 |
| --- | ---: | ---: |
| Mean | 8.030 s | **6.794 s** |
| Maximum | 10.875 s | **8.400 s** |
| Cases >10 s | 1 | **0** |
| Cases ≤10 s | 94.1% | **100%** |

The Chordic candidate calculation uses the same 140 ms note, 35 ms inter-note gap, 100 ms token boundary, and 3× multiplier represented by the pinned source profile. Playback has not simply been accelerated.

## Tests added

`software/rocky/tests/test_chordic_exp002.py` verifies:

- the snapshot is pinned to the exact Chordic PR #1 commit and labels itself non-authoritative;
- current Rocky CT2 timing reproduces the recorded 17-case baseline;
- the compact candidate puts all 17 normal cases at or below 10 seconds without changing the multiplier;
- registered benchmark mappings round-trip without duplicate token sequences;
- a benchmark utterance traverses the existing Brain/Safety/Task communication path while motion remains disabled.

The normal Rocky CI matrix will also rerun all pre-existing language, RPA-Link, simulator, Brain, Rocky desktop/conversation/learning, browser protocol, and Arduino compilation checks.

## Deliberate limitations

This integration does **not** replace Rocky CT2, make EXP-002 the production playback codec, or make the AI provider choose hardware behavior. It does not claim microphone recognition, human recognition, human production accuracy, or noise tolerance.

The candidate is not yet wired into `/word`, `/dictionary`, or `/learn`; those existing commands continue to exercise the released CT2 starter overlay. Multi-turn context omission is also not enabled in production. Those should wait until the short candidate forms survive acoustic/listener testing.

## Manual tests still needed

- listen to generated candidate forms at 1× and 3×;
- microphone recognition experiments for short distance-1 neighbors;
- human production/listener confusion testing across pitch ranges;
- multi-turn/context-omission experiment using session history;
- broader free-conversation timing beyond the fixed benchmark.
