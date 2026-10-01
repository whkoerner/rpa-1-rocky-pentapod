# RPA-1 Brain v0.2 Integration Plan

**Date:** 2026-09-30  
**Status:** PLAN ONLY — implementation is the next stage  
**Target:** functional Windows Brain v0.2 today, portable to Raspberry Pi later  
**Scope of this change:** connect existing project pieces with the smallest new orchestration layer; do not redesign CSP-1, Chordic, RPA-Link, the simulator, or Brain v0.1 firmware.

## 1. Repository findings

### Already implemented and reusable

| Area | Existing implementation | What it already provides | Reuse decision |
|---|---|---|---|
| CSP-1 lexical Chordic codec | `software/csp/core.py` + `language/specification/csp_v0_1.yaml` | Deterministic token-to-note encoding, reverse decoding, checksum validation, versioned vocabulary | **Reuse directly. Do not rewrite.** |
| CSP-1 semantic wire message | `software/csp/wire.py` | Six registered semantic intents, syntax validation, deterministic `C1|INTENT|ARG` encoding/decoding, canonical English text, mapping to existing Chordic tokens | **Reuse directly as the semantic-intent boundary for v0.2.** |
| CSP-1 tests | `language/tests/` | Codec round-trip, wire validation, and firmware consistency checks | **Keep as regression tests.** |
| Computer simulator | `software/simulation/` | Five-limb deterministic model, joint limits, contact states, simple gait timing, software stop behavior, CSV logging, direct CSP-1 input handling, pygame front end | **Reuse as the first hardware target.** |
| Simulator tests | `software/simulation/tests/` | Determinism, joint-limit stop, E-stop/reset behavior, support-contact checks, CSP fail-closed behavior, logging | **Keep as safety regression tests.** |
| Hardware-independent command boundary | `interfaces/rpa_link/README.md`, `software/rpa_link/` | Versioned messages, modes, heartbeat/timeouts, software E-stop semantics, UDP transport, fake controller | **Reuse as the lower-level motion/hardware boundary; do not replace it.** |
| Fake hardware controller | `software/rpa_link/fake_hardware.py` | DISABLED/READY/ACTIVE/SAFE_STOP/ESTOP state machine, watchdogs, command validation, telemetry without invented sensor readings | **Reuse for hardware-independent safety tests.** |
| Brain v0.1 Arduino firmware | `firmware/rocky_brain_v0_1/` | Two-button translation/communication demo, passive buzzer Chordic output, fixed English translation, serial command shell | **Preserve as a v0.1 prototype and optional output device. Do not turn it into the v0.2 host brain.** |
| Brain v0.1 build/test docs | `docs/build-guides/brain-v0.1-build.md` | Beginner wiring, Arduino IDE steps, serial commands, acceptance checklist | **Reuse when optional Uno testing is added.** |
| Brain v0.2 requirements | `docs/requirements/requirements-v0.2.md` | Offline requirement, AI safety boundary, CSP/Chordic behavior, local operation, future motion/manipulation constraints | **Treat as the requirements baseline.** |

### Partially implemented

1. **Simulation exists, but it is not yet behind one common Brain v0.2 hardware interface.** The pygame app talks directly to `SimRobot`.
2. **RPA-Link exists, but the simulator is not yet connected to the RPA-Link adapter/fake-controller path described in its interface document.**
3. **CSP-1 semantic intent validation exists, but there is no host-side brain orchestrator that accepts user text and routes a validated intent through safety before any hardware-facing action.**
4. **Brain v0.1 can receive fixed serial text commands, but it is not a general Brain v0.2 serial hardware adapter.**
5. **A binary microcontroller serial frame is documented in `interfaces/rpa_link/README.md`, but it is intentionally not implemented yet.**

### Missing for Brain v0.2

The repository currently has no implementation named or equivalent to:

- `AIProvider`
- `DummyAIProvider`
- `BrainController`
- host-side `SafetyValidator`
- common `HardwareInterface`
- simulator adapter implementing that interface
- Brain v0.2 CLI entry point
- end-to-end Brain v0.2 integration tests
- optional Python serial adapter for the Uno

These are the smallest missing pieces. They should be added around the existing code rather than replacing it.

## 2. Smallest Brain v0.2 architecture

The v0.2 host brain should be a small Python package under `software/brain/`.

```text
User text
   |
   v
AIProvider
   |  returns structured candidate intent only
   v
CSP-1 semantic validation
software/csp/wire.py
   |
   v
BrainController
   |
   v
SafetyValidator
   |
   +--> canonical English text
   +--> existing Chordic token / note encoding
   |
   v
HardwareInterface
   |
   +--> SimulatorHardware  ---> existing software/simulation/
   |
   +--> later SerialHardware ---> Arduino / MCU
```

For movement later, the hardware-facing implementation should route motion through the existing RPA-Link message/state-machine layer instead of inventing a second low-level protocol.

### Rule: AI never operates hardware

An AI provider may only produce a candidate semantic object such as:

```python
{"intent": "SOCIAL.HELLO", "arg": ""}
```

It must never return GPIO pins, PWM, joint angles, serial bytes, UDP packets, RPA-Link actuator commands, or direct simulator mutations.

The candidate intent must be converted to the existing `WireMessage` and pass `software/csp/wire.py` validation before `BrainController` accepts it.

## 3. Minimal new modules for the next stage

Only add what is needed for the acceptance test.

```text
software/brain/
    __init__.py
    ai.py
    controller.py
    safety.py
    hardware.py
    cli.py
    tests/
        __init__.py
        test_brain_v0_2.py
```

### `ai.py`

Define:

- `AIProvider` protocol or abstract interface
- `DummyAIProvider` deterministic offline implementation

The dummy provider should recognize only a tiny fixed set that maps to the six existing CSP-1 semantic intents. Unknown text must fail closed or return a clearly defined unknown result; it must not guess a hardware action.

No real model dependency is required for Brain v0.2 acceptance.

### `controller.py`

Define `BrainController` as the only top-level orchestrator.

Responsibilities:

1. receive user text
2. ask the selected `AIProvider` for a structured candidate
3. construct/validate the existing `csp.wire.WireMessage`
4. call `SafetyValidator`
5. derive existing canonical English via `csp.wire.canonical_text()`
6. derive the existing Chordic token via `csp.wire.chordic_token()`
7. derive existing Chordic notes via `csp.core.CspCodec`
8. send the validated result to a `HardwareInterface`
9. return a deterministic result object suitable for printing/logging/testing

The controller must not contain device-specific code.

### `safety.py`

For this stage, `SafetyValidator` should be deliberately small.

It must:

- accept only already-registered CSP-1 semantic intents
- reject malformed or unknown intents
- reject any AI output containing direct hardware fields/commands
- ensure no motion command is invented from a social/help intent
- fail closed on validation exceptions

Do not duplicate the simulator joint-limit checks or RPA-Link watchdog/E-stop state machine; those remain lower-level safety layers.

### `hardware.py`

Define a narrow `HardwareInterface` method for Brain v0.2, for example a method that accepts a validated brain output/event.

Implement `SimulatorHardware` using the existing simulator rather than creating a new simulator.

For the current six CSP-1 intents, the adapter should feed the existing CSP message to `SimRobot.handle_csp()`. These v0.2 starter intents are communication-only and must not create movement.

A later motion-capable adapter should use RPA-Link.

A `SerialHardware` adapter is optional for today's goal. If implemented, keep it separate and optional so importing/running Brain v0.2 does not require an Arduino or pyserial.

### `cli.py`

Provide one simple Windows-friendly module entry point, for example:

```powershell
python -m brain.cli
```

Default behavior:

- `DummyAIProvider`
- simulator hardware
- no network
- no Arduino
- no real AI model

The CLI should print the accepted semantic intent, CSP-1 wire form, English translation, Chordic token/notes, safety decision, and simulator acknowledgement/state without claiming physical hardware activity.

## 4. Deterministic state and logging

For v0.2, deterministic brain state should be explicit and small. At minimum track:

- last validated semantic intent
- last canonical English text
- last Chordic token
- selected hardware backend
- last safety decision/error
- sequential command/event ID

Use deterministic structures and existing simulator logging where possible.

Do not add a database. A simple log line or standard-library JSONL/CSV file is enough if logging is added in the next stage.

## 5. Windows/Raspberry Pi portability rules

Brain v0.2 host code must:

- require Python 3.10+ as already declared by `pyproject.toml`
- use `pathlib`, not hard-coded Windows paths
- avoid Windows-only APIs
- avoid Raspberry Pi GPIO in the brain package
- keep hardware access behind `HardwareInterface`
- run fully offline with `DummyAIProvider`
- make any real AI provider replaceable and optional
- make serial support optional
- keep CSP-1, Chordic, safety, and simulator behavior local

The same Python package should therefore be movable to Raspberry Pi with configuration/backend changes rather than a brain rewrite.

## 6. Reuse boundaries

Do **not** rewrite these in the Brain v0.2 implementation:

- `software/csp/core.py`
- `software/csp/wire.py`
- `language/specification/csp_v0_1.yaml`
- `software/simulation/model.py`
- `software/simulation/logger.py`
- `software/rpa_link/messages.py`
- `software/rpa_link/fake_hardware.py`
- `software/rpa_link/udp.py`
- Brain v0.1 firmware unless a small compatibility fix is actually required

If an integration problem is found, add an adapter first. Change an existing subsystem only when a test proves the adapter cannot solve it cleanly.

## 7. End-of-day Brain v0.2 acceptance test

The implementation is accepted on Windows only when the following can be demonstrated with **no internet, no AI model, and no Arduino connected**.

### Setup

From PowerShell in the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

If pygame is needed for the visual simulator separately:

```powershell
python -m pip install -e ".[simulation]"
```

### Existing regression tests

```powershell
python -m unittest discover -s language/tests -v
python -m unittest discover -s software/rpa_link/tests -v
python -m unittest discover -s software/simulation/tests -v
```

### New Brain v0.2 tests

After the next stage implements `software/brain/`:

```powershell
python -m unittest discover -s software/brain/tests -v
```

The tests must prove at least:

1. Dummy text such as `hello` becomes a structured candidate intent.
2. The candidate becomes the registered `SOCIAL.HELLO` semantic intent.
3. Invalid/unknown semantic intent fails closed before hardware dispatch.
4. `BrainController` calls `SafetyValidator` before `HardwareInterface`.
5. Existing CSP-1 wire encoding is used; no duplicate protocol is introduced.
6. Existing canonical English is `Hello.`.
7. Existing Chordic token is `SOCIAL.hello`.
8. Existing Chordic note encoding comes from `CspCodec`.
9. Simulator backend accepts the validated CSP message.
10. The communication intent does not move any simulator joint.
11. The full path works with no network, real model, or Arduino.
12. A fake/spy hardware backend can prove rejected intents never reach hardware dispatch.

### Manual end-to-end command

The next stage should make this command available:

```powershell
python -m brain.cli
```

For input:

```text
hello
```

the output should clearly show a path equivalent to:

```text
provider: DummyAIProvider
intent: SOCIAL.HELLO
safety: ACCEPTED
csp1: C1|SOCIAL.HELLO|
english: Hello.
chordic_token: SOCIAL.hello
chordic_notes: <notes produced by existing CspCodec>
hardware: simulator
simulator: accepted
```

The exact note names must be read from the existing codec at runtime, not copied into new brain code.

### Optional Arduino acceptance

Arduino support is not required for the no-hardware acceptance test.

If a serial adapter is added later, disconnecting the Uno must not prevent simulator mode from starting. The first Arduino integration should initially reuse the existing Brain v0.1 serial command vocabulary only where compatible; do not pretend Brain v0.1 firmware is a motion controller.

## 8. Definition of done for Brain v0.2 today

Brain v0.2 is functionally complete for this stage when:

- all existing regression suites still run
- the new brain integration tests run
- `python -m brain.cli` works offline with `DummyAIProvider`
- the validated flow reaches the existing simulator
- unknown/invalid AI output is rejected before hardware dispatch
- the AI provider cannot directly issue hardware commands
- CSP-1 and Chordic come from the existing modules/specification
- no Arduino is required
- no internet is required
- no ROS, Docker, cloud API, motor driver, or computer-vision dependency is added

## 9. Next-stage implementation order

Implement in this order so failures are easy to isolate:

1. create `software/brain/ai.py` with `AIProvider` and deterministic `DummyAIProvider`
2. create `software/brain/safety.py`
3. create `software/brain/hardware.py` with `HardwareInterface` and `SimulatorHardware`
4. create `software/brain/controller.py`
5. create `software/brain/cli.py`
6. add `software/brain/tests/test_brain_v0_2.py`
7. run all four Python test suites
8. manually run `python -m brain.cli` with simulator backend
9. only after that consider optional serial/Uno integration

This order preserves the architecture rule:

```text
AI -> structured semantic intent -> deterministic brain controller
   -> safety validation -> task/hardware boundary
   -> existing lower-level controller/simulator
```

No AI output is permitted to bypass validation or directly operate hardware.
