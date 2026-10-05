# Rocky Assistant V2 architecture

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-assistant-v2`; stacked on EXP-003 PR #16.  
**Safety constitution:** `rocky-safety-constitution-v1`

## Purpose

Assistant V2 expands Rocky from a short conversational demo toward a useful study/project assistant without weakening the frozen Brain v0.2 authority boundary. The implementation deliberately separates assistant correctness, software-tool execution, Chordic representation, audio playback, and future physical action.

## Authority and data flow

```text
typed user text
  -> ConversationController
  -> supervised AIProvider worker
       -> deterministic exact-math pre-router when unambiguous
       -> otherwise local model may request an allowlisted SOFTWARE tool
  -> strict AssistantResponse validation
       spoken_text
       detail_text
       tool_calls (draft only; must be resolved before parent acceptance)
  -> spoken_text only
  -> BrainController
  -> SafetyValidator
  -> TaskController / EXP-003
  -> HardwareInterface (current desktop audio only)

detail_text -> terminal/UI display + bounded conversation history only
```

The model never receives a HardwareInterface, BrainController, motor API, E-stop reset, filesystem shell, arbitrary Python evaluator, or trusted evidence constructor. Final model/tool output cannot contain unresolved tool calls before it crosses the parent conversation boundary.

## Five-Law safety constitution

`software/brain/constitution.py` contains the hard-coded, versioned `RockySafetyConstitution`. It is application code, not a prompt. The model receives only a readable summary.

The deterministic policy denies model requests to disable/rewrite/ignore the laws, override or clear E-stop, clear physical faults, manufacture sensor evidence, declare charging complete, bypass limits, or issue raw motor/actuator/gait commands. Model-authored sensor, tool, and device claims are not promoted to trusted evidence. Physical model actions are denied, and physical requests fail closed under E-stop.

The existing Brain/Safety path remains authoritative for communication. Future navigation, docking, gait, and charging must add deterministic control layers beneath this policy; they are not implemented here.

## Dual response contract

Assistant V2 introduces:

- `spoken_text`: at most 384 UTF-8 bytes, one line, Rocky-style, passed through the existing Brain/Safety/EXP-003/audio path.
- `detail_text`: up to 6144 UTF-8 bytes, UI/history only. It may contain study steps, equations, code, citations, and longer explanations. It is not Chordic and is not labeled as English translation.
- `tool_calls`: at most four strict requests. They are untrusted until the application executes an allowlisted software tool. Final accepted assistant output must contain zero unresolved calls.

Legacy `{"text": ...}` candidates remain temporarily accepted for V1 fixtures/migration.

## Exact reasoning/tool layer

The first allowlisted tools are:

- safe calculator: exact fractions, order of operations, negatives, bounded integer powers, modulo, and square root;
- unit conversion for a bounded registry of length/mass/time/volume/temperature units;
- ISO date difference.

There is no `eval`, `exec`, shell, filesystem, network, or import tool. The calculator parses a bounded Python AST and rejects all unsupported syntax, code injection, filesystem access, shell attempts, excessive exponent sizes, excessive expression complexity, non-finite/huge values, malformed expressions, and division by zero.

Unambiguous arithmetic such as “what is 8 times 8?” bypasses the language model entirely. This directly addresses the real failure where EXP-003 had 100% semantic coverage but the model said 32. Coverage and correctness are separate metrics.

The exact arithmetic spoken form is intentionally compositional and EXP-003-friendly, for example:

`Rocky calculate. 64. Good.`

The detail pane records the exact deterministic expression/result.

## Assistant modes

The bounded modes are `normal`, `study`, `coding`, and `project`. They change response presentation priorities, not authority. Study/coding/project mode can request richer `detail_text` while keeping speech short.

## Defaults and migration

The reviewed defaults remain local provider, `qwen3:8b`, EXP-003, `vocal-v1`, duration multiplier 2, and translation enabled. Assistant mode defaults to `normal`; defaults profile version is bumped to 3.

## Terminal regression

The observed `/speed 2` followed by `2/speed 2` symptom is handled narrowly: only an exact duplicated `/speed N/speed N` form is normalized. Mixed concatenations such as `/speed 2/stop` fail instead of silently swallowing a safety command. Root cause is still best described as an input/paste concatenation symptom; the regression guard prevents it from crashing speed parsing.

## Evaluation policy

`experiments/assistant/assistant-v2-benchmark-v0.1.json` keeps model quality, tool quality, Chordic quality, and audio quality separate. CI executes deterministic tool and Chordic checks. Real-model academic/coding/conversation cases remain NOT RUN until a reviewed local model is exercised. Human listening remains NOT RUN unless a person actually listens.

## Deferred scope

This milestone does not implement persistent memory, microphone input, a localhost web UI, neural English TTS, online Google integrations, lecture recording, packaging/bootstrap, walking, docking, charging, or raw physical autonomy. Those remain later milestones after the Assistant V2 correctness boundary is stable.
