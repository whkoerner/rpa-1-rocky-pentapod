# Rocky Assistant V2 — implementation and evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-assistant-v2`  
**Base:** `feat/exp-003-runtime-consumer` at `010034f2022bd2028ad08ae2e5048ebea651ddad`  
**PR:** #17 (draft)

## Live dependency state verified before work

Rocky PR #16 was verified live as a draft at `010034f2022bd2028ad08ae2e5048ebea651ddad`. Its Actions runs #92 and #93 were green; run #93 passed Windows Python 3.12/3.13, Ubuntu Python 3.12/3.13, and Arduino Uno. Chordic PR #4 was verified live as a draft at `5e4309252eae3392ff2faf28886c759bfc384b56`; Chordic validation run #56 was green. Neither PR was merged because the strict merge gate was not met: both remain experimental/draft and acoustic/manual acceptance is not fully complete.

## Implemented

- hard-coded, inspectable, versioned Five-Law `RockySafetyConstitution`;
- deterministic model-authority denials for law overrides, E-stop/fault clearing, fabricated evidence, charging claims, raw motors/actuators/gait, and limit bypass;
- strict `spoken_text` / `detail_text` / `tool_calls` contract;
- exact arithmetic pre-routing before the model for unambiguous prompts;
- allowlisted safe calculator, unit conversion, and date-difference tools;
- no arbitrary eval/exec/shell/filesystem/network tool surface;
- `normal`, `study`, `coding`, `project` modes;
- detail text kept out of Chordic/audio/physical authority;
- terminal displays detail text separately;
- defaults profile v3 with assistant mode normal;
- regression handling for exact duplicated `/speed N/speed N` paste;
- evaluation manifest separating model/tool/Chordic/audio quality.

## Development failure ledger

| Order | Feature/test | Symptom | Root cause | Fix | Evidence/status |
|---|---|---|---|---|---|
| 1 | First Assistant V2 boundary | Actions #94 failed all four software matrix cells; Arduino stayed green | New Rocky test suite exposed a mismatch in expected denial code and the newly written validator source also contained interpreted control characters | Aligned denial expectation with stricter constitution behavior; then rewrote validator with literal Python escape sequences | Failure preserved; superseded |
| 2 | Safety expectation | Actions #95 still failed Rocky suite | Validator source remained malformed; safety behavior itself was intentionally stricter | Diagnosed source by fetching exact branch file | Failure preserved; superseded |
| 3 | Integrated dual response/tool route | Actions #96 failed Rocky suite | Same malformed validator source was still present in integration head | Replaced `assistant_contracts.py` with escape-safe source | Failure preserved; superseded |
| 4 | Validator fixed | Actions #97 failed Rocky suite | Duplicate-speed regression pattern was over-escaped, so the intended observed paste form was not recognized | Corrected the regex backreference | Failure preserved; superseded |
| 5 | No-op/incorrect regex attempt | Actions #98 failed Rocky suite | First regex edit produced no source-content change | Replaced the exact source line with a literal single backreference | Failure preserved; superseded |
| 6 | Corrected Assistant V2 core | Actions #99 | All four software cells and Arduino Uno passed | No further fix required for this head | GREEN |\n| 7 | Separated benchmark + semantic speech | Actions #100 failed the Rocky suite; Arduino stayed green | Benchmark correctly exposed that the LocalAI production arithmetic pre-router still used the non-semantic word `Answer` even though the dummy provider had been changed | Fixed the production pre-router rather than weakening the benchmark | Failure preserved; superseded |\n| 8 | Production exact-arithmetic speech + benchmark | Actions #101 | Windows 3.12/3.13, Ubuntu 3.12/3.13, and Arduino Uno all passed | No further fix required for this head | GREEN |

## Automated benchmark scope

The benchmark includes exact 8×8, 8×12, order of operations, negatives, fractions, percentages, powers, division by zero, malformed/injection attempts, unit conversion, and date difference. Exact arithmetic prompt cases also assert EXP-003 semantic coverage independently of arithmetic correctness.

Real local-model cases for algebra, calculus, physics, biology, coding, engineering, study summarization, follow-up conversation, and uncertainty are defined but remain NOT RUN in CI. A fixture/dummy provider is not evidence of real-model quality.

## Manual acceptance — NOT RUN

- human listening judgment for `vocal-v1` naturalness;
- human judgment of English translation voice quality;
- speaker-observed active-translation overlap on this Assistant V2 head;
- real local `qwen3:8b` academic/coding benchmark on Windows;
- microphone input (not implemented);
- persistent memory (not implemented);
- web/desktop GUI (not implemented);
- neural TTS backend (not implemented);
- packaging/bootstrap smoke test (not implemented);
- online/Google integrations (not implemented);
- lecture/class recording (not implemented);
- physical locomotion/docking/charging (not implemented).

Waveform, duration, and CI tests must not be described as “sounds natural” or as physical success.
