# Rocky real local-model benchmark v0.2 — harness and acceptance

**Date:** 2026-10-05  
**Branch:** `feat/rocky-real-model-benchmark-v0-2`  
**Base:** Lecture durability V0 stacked head  

## Purpose

This benchmark is designed to be run on the user's reviewed local model. CI uses fixture providers only to test the harness; CI results are not real-model quality evidence.

## Cases

The v0.2 matrix keeps algebra, calculus, physics, biology, coding, electrical-engineering explanation, study summarization, normal conversation, session follow-up, uncertainty, long and short responses, and adds explicit 8x8, 8x12, fraction, percentage, malformed-input, persistent-memory recall, hostile-memory safety, and engineering-calculation cases.

Persistent-memory model cases create a temporary opt-in `MemoryStore`, write the explicit benchmark fact, reopen the store from disk, then pass only its provenance-aware prompt rows to the provider. This verifies the persistence boundary used by the harness without changing the user's real memory file.

## Measured fields

For every executed case the report records:

- response-contract validity;
- spoken/detail UTF-8 lengths;
- deterministic vs model/tool route;
- provider-turn latency;
- total benchmark-turn latency;
- model latency as the transparent local-provider round trip for non-deterministic cases (not isolated GPU kernel time);
- EXP-003 semantic coverage;
- fallback spans/bytes;
- estimated Chordic duration;
- explicit auto-check result where configured;
- human review placeholders for factual correctness, usefulness, and personality.

Summary fields include failure rate and auto-check failure count.

## Audio separation

The real-model benchmark does **not** play audio. Therefore English duration, active overlap, and total audio wall time are present as null fields with `NOT_RUN_NO_PLAYBACK_IN_MODEL_BENCHMARK`. They must be measured by the separate Windows audio acceptance flow rather than fabricated from text or Chordic timing.

## Manual NOT RUN until user PC

- real reviewed local-model execution of v0.2;
- human factual correctness grading;
- human usefulness grading;
- personality consistency grading;
- persistent-memory recall against the user's actual configured store after a real Rocky restart;
- English voice duration and overlap measurements;
- human Chordic/English listening quality.

Run from the Windows launcher benchmark option or with `python -m rocky benchmark --provider local`. Preserve the JSON report as test evidence rather than converting subjective fields to PASS automatically.
