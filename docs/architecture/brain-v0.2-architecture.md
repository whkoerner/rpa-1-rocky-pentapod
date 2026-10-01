# RPA-1 Brain v0.2 — Architecture Freeze

**Date:** 2026-09-30 (America/Los_Angeles)
**Status:** Architecture selected for implementation under the project owner's requested freeze; implementation remains PLANNED. This is not a hardware safety approval.
**Repository reviewed:** `whkoerner/rpa-1-rocky-pentapod`, `main` at `e297b6dd3dc10830ca05957c8bb6ca672324f588`.
**Planning input:** [Brain v0.2 integration plan](brain-v0.2-integration-plan.md), introduced in `b981b70`.
**Requirements:** [requirements-v0.2.md](../requirements/requirements-v0.2.md), especially SAF-002/003/004, INT-001/005/008 and DOC-001/003.

This document makes the earlier plan's interfaces and failure rules precise. Where the plan is less specific or conflicts with this document, this document governs Brain v0.2 software integration. It does not replace mechanical requirements, physical safety gates, or published language encodings. Future models must follow **ARCHITECTURE DECISIONS TO FREEZE** unless the owner explicitly requests an architecture revision. If evidence reveals an unsafe decision, stop the affected work and present the evidence for revision rather than silently changing it.

## 1. Architecture verdict

Keep the current packages. Add a small `software/brain/` package around them. The first Windows demonstration is text to deterministic communication in the existing headless simulator. It requires neither a real LLM nor an Arduino. All six currently registered CSP-1 wire intents are communication-only. `REQUEST.HELP` says “Help.”; it does not manipulate anything. `RESPONSE.YES` is not permission to enable motors.

The required action authority remains:

Local AI → structured semantic request → deterministic BrainController → SafetyValidator → TaskController / MotionController → HardwareInterface → Arduino/MCU → physical hardware.

Strict intent validation occurs before the controller accepts a request. For today's communication path, TaskController selects one communication operation; MotionController is not invoked. Simulation replaces the physical backend behind the same interface. Safety stop and fault handling are independent of AI inference.

Do not require RPA-Link packets for a greeting. CSP-1 carries communication meaning; RPA-Link carries future motion commands and telemetry. Neither the lexical token `ACTION.move` nor a Chordic safety word grants motion authority.

### Alternatives considered

| Option | Decision and reason |
|---|---|
| Small host package plus adapters | Selected: preserves working code and gives Windows a headless, offline path. |
| Make the browser console the v0.2 brain | Rejected: it currently bypasses a Python safety boundary and its serial protocol conflicts with the sketch. |
| Put high-level AI on the Uno | Rejected: the existing Uno project is a button/buzzer endpoint, not the host orchestrator. |
| Rewrite codecs, simulator, or introduce ROS/Docker | Rejected: repository evidence shows integration gaps, not a need for replacement infrastructure. |

## 2. What was inspected and what to reuse

The review covered `README.md`, `pyproject.toml`, all first-party files under `software/`, `firmware/`, `language/`, `interfaces/`, the architecture documents, both requirements versions, all build guides and milestone pages, the Brain v0.1 acceptance plan, and the CI workflow. Installed dependencies inside the tracked `.venv` are not first-party implementation.

| Existing component | Decision | Reason / exact boundary |
|---|---|---|
| `software/csp/core.py`, `wire.py`, `cli.py`, `__init__.py` | Reuse unchanged for source-checkout v0.2 | Use `WireMessage`, `encode`, `decode`, `canonical_text`, `chordic_token`, and `CspCodec.encode_token`. Construction of `WireMessage` alone does **not** validate it. |
| `language/specification/csp_v0_1.yaml`, `CSP1_WIRE_V0_1.md`, `csp1_intents_v0_1.csv` | Reuse unchanged | Preserve note/code assignments, six wire intents, empty arguments and canonical English. Full grammar/semantic IR in YAML is a future specification, not an implemented host request parser. |
| `software/simulation/model.py`, `logger.py`, `config/robot.json` | Reuse unchanged for communication demo | Wrap `SimRobot.handle_csp`; keep joint checks, fixed-step model, contacts, stop/reset and CSV format. All geometry/limits remain simulation placeholders. |
| `software/rpa_link/messages.py`, `udp.py`, interface schema | Preserve current logical envelope and units | Motion transport seam for later work. No socket is needed by the first brain demo. Payload validation is receiver responsibility. |
| `software/rpa_link/fake_hardware.py` | Reuse as a separate watchdog/state-machine test fixture | It reports commanded values with `position_valid=False`. It is neither a physical driver nor the simulated plant. |
| `firmware/rocky_brain_v0_1/` | Preserve as optional communication endpoint | Current `.ino` uses `SAY` at 9600 baud; it has no actuator drivers. |
| `firmware/communicator_v0_1/` | Preserve as a separate historical bench prototype | Different pins, vocabulary and 115200 baud; no serial command receiver. Do not merge sketches. |
| Existing Python and browser protocol tests | Retain as regression tests | Add brain contract tests separately. Existing passes do not establish end-to-end browser/Uno compatibility. |

### Small changes needed, in order of need

1. **Navigation:** link this freeze from the README, index and earlier plan (this change).
2. **Packaging:** keep distribution name `rpa1-csp`, Python `>=3.10`, and `software/` package discovery. Add an optional `serial` dependency group when the Python serial adapter is implemented. No rename or new required model/GUI dependency.
3. **Headless config loading:** the adapter loads packaged `simulation/config/robot.json` directly with `importlib.resources`; do not import `simulation.app`, which imports pygame. A shared loader may later be extracted without altering model behavior.
4. **Before wheel-only deployment:** fix `CspCodec.from_default_spec()` resource loading. It currently assumes `language/specification/` exists two parents above its source file; `pyproject.toml` only declares simulator JSON package data. Keep one authoritative YAML and include it at build time; prove installed-wheel loading outside the checkout. Editable full-checkout installs are the initial supported route.
5. **Before browser reuse:** align `brain_web/app.js`, `protocol.js`, tests and the old acceptance page with an explicitly chosen firmware version. Keep the browser outside v0.2 acceptance until then.
6. **Before motion integration:** harden RPA-Link receiver validation and simulator indexing under targeted tests as described below. These fixes are not prerequisites for communication-only v0.2.
7. **CI / portability follow-up:** add simulator and RPA-Link suites, then brain suites, to Windows and Linux jobs. The inspected workflow currently runs Python language tests, browser tests and Arduino compilation on Ubuntu, not the full host suite on Windows.

## 3. Conflicts, duplication and gaps found in actual code

| Finding | Consequence and disposition |
|---|---|
| Browser opens 115200 baud, sends `PLAY`, `STOP`, `MODE MUSICAL/TRANSLATED`, and parses `EVENT|...`. Current Brain v0.1 sketch opens 9600 baud, accepts `SAY`, `MODE COMM/TRANSLATE`, and prints `CSP-1:`, `ENGLISH:`, `MODE:`. | These are incompatible protocols. Browser tests only verify their own assumptions. The current sketch/build guide is the first serial adapter target; do not copy the browser protocol into the brain. |
| `csp1_wire.cpp/.h` exist, but `.ino` does not include/call `csp1Decode`. | Sending `C1|...` directly to this sketch will not execute a phrase. Use the adapter's fixed `SAY` mapping. Wiring the decoder into firmware is optional later, not required now. |
| `docs/test-plans/brain-v0.1-acceptance.md` expects eight phrases, translated/musical modes and a STOP command. Current sketch/build guide have six phrases and no STOP. | Mark the old checklist as incompatible evidence when using this freeze. Do not claim it passes; reconcile it in a later serial/browser repair. |
| Two Uno sketches and repeated phrase tables in Python/C++/CSV/browser | Separate prototypes and cross-language representations, not grounds for a rewrite. Python `csp.wire.INTENTS` is the runtime semantic registry; YAML is the lexical authority. Extend consistency tests when modifying either. |
| Simulator owns a gait and `IDLE/ENABLED/STOPPED`; fake hardware owns `DISABLED/READY/ACTIVE/SAFE_STOP/ESTOP`. | Different responsibilities. Do not let both schedule motion or independently authorize it. Keep native modes visible and adapt them explicitly. |
| Fake controller does not enforce sender/destination policy, duplicate/out-of-order sequence rejection, joint bounds, or duplicate joint IDs; JSON schema covers only the envelope. | Useful fixture, insufficient physical safety boundary. Add receiver validation before motion integration. TTL tests do not prove network-age/replay protection. |
| `SimRobot.set_joint_target` and `toggle_contact` use Python indexing; negative indices select limbs/joints. Existing no-motion test compares `snapshot()[:-1]`. | Adapter must validate indices before future motion; add regression checks for negative indices and compare the entire snapshot in new brain tests. Do not expose these mutators to AI. |
| `README.md` still describes Linux/ROS 2; `.venv/` and `software/rpa1_csp.egg-info/` are tracked. | README wording is not a dependency requirement. Recreate each platform's environment; do not copy the Windows virtual environment to Pi. Remove generated tracked files and add ignore rules in a separate cleanup. |
| No host `brain` package, Python serial driver, sensor freshness model or completion contract exists. | These are real additions, not renamed versions of existing code. |

## 4. Exact responsibility boundaries

| Component | Owns | Must not do |
|---|---|---|
| `AIProvider` | Translate bounded user text plus a read-only context snapshot into a candidate object, or return no match / provider error. | Receive hardware handles, choose trusted IDs/timeouts, mutate RobotState, generate notes or sensor values, execute tools/drivers, assert confirmed physical success. |
| Intent validation | Enforce exact object shape and types, then call existing CSP wire validation. Return a validated `WireMessage` or a stable rejection code. | Guess unknown intent names, ignore extra fields, authorize a request based only on valid syntax. |
| `BrainController` | Allocate IDs, own state updates, orchestrate provider/validation/safety/task/dispatch, correlate results, log outcomes and handle faults. Recheck current safety state immediately before dispatch. | Contain serial/GPIO/pygame code or treat AI prose as telemetry. |
| `RobotState` | Immutable snapshots of observed backend state, host safety latch, capabilities, pending operation and evidence freshness. Only controller applies validated events. | Alias live simulator objects or let requested/commanded values masquerade as observed measurements. |
| `SafetyValidator` | Pure deterministic policy over validated intent, current snapshot, trusted origin and current monotonic time; deny missing capability, unhealthy backend, latch, expired request or required stale feedback. | Call AI, perform I/O, own another hardware watchdog, clear stops automatically. |
| `TaskController` | Select allowlisted finite tasks and track their lifecycle. Initially one communication task, immediately routed to hardware after safety. Later sequence/cancel verified motion primitives. | Invent movement for greetings/help, interpret free-form code, own low-level trajectories or bypass safety between task steps. |
| `MotionController` | Later convert approved motion primitives into bounded RPA-Link setpoints; own host trajectory/gait scheduling with cancellation and feedback. | Be a second general AI planner, drive pins, infer support contacts as physical facts, or replace MCU watchdogs. No implementation needed for today's six intents. |
| `HardwareInterface` | Typed dispatch, backend capabilities/status, bounded polling, stop and close; implementation handles transport and reports evidence. One backend owns each endpoint. | Decide semantic meaning, perform AI planning, retry uncertain actions silently or claim physical success from a write. |
| Simulator | Existing deterministic plant/model, simulated contact/position, local joint and stop checks. Adapter supplies evidence explicitly labeled simulated. | Prove physical stability, load capacity, sensor readings or actuator performance. |
| Arduino/MCU | Current Uno: buttons, stored tones and serial shell. Future motion MCU: local control, feedback, limits, watchdogs and physical stop input. | Run the high-level brain or rely on host responsiveness as its only motion safety control. |

Dependency direction: `brain.ai` sees only immutable context/contracts. Controller depends on protocols and pure validation/safety. Concrete adapters import existing `csp`, `simulation` or transport modules. CLI constructs dependencies. No existing package needs to import `brain` to retain its standalone functionality.

## 5. Minimum stable contracts before a real LLM

The following are normative v0.2 design contracts, **not code already implemented**. Standard-library dataclasses, enums and typing protocols are enough. Avoid a plugin framework or additional schema dependency.

### AI and intent input

`AIProvider.propose(text: str, context: AIContext) -> object | None`

`AIContext` contains only request schema version `brain-request-v0.2`, the allowlisted intent names and an immutable summary of observed state. Providers are injected; `DummyAIProvider` is the default. `None` means no supported interpretation. Provider errors are reported separately.

A successful candidate must be exactly `{"intent": "SOCIAL.HELLO", "arg": ""}` in shape: a plain dict with exactly `intent` and `arg`, both plain strings. No extra fields, action lists, confidence-based authorization, driver names, nested payloads, timing, state updates or raw wire data. The provider adapter parses one bounded JSON object for an LLM; reject duplicate keys, code fences, trailing text and invalid JSON rather than repairing them. Schema version is supplied by the host context, not silently negotiated by generated text.

`validate_candidate(candidate: object) -> WireMessage` rejects shape/type errors before constructing the message, then uses `decode(encode(message))` to exercise existing semantic/length rules. Never call private CSP validators or maintain another copy of the six-intent registry. Invalid candidates never call the normal hardware dispatch method.

Trusted host configuration bounds input bytes, provider response bytes, provider time and operation time. Those limits must be finite and validated at startup; missing limits fail startup. Their tuning is configuration, not an LLM-selected value or a hardware performance claim.

### Host records and results

| Record | Required content and semantics |
|---|---|
| `RequestContext` | Host-generated `session_id`, increasing `request_id`, `origin` (`provider` or `operator`), local `received_us`, local `deadline_us`. AI cannot set these. One normal operation in flight initially; a new one receives `BUSY`, not an unbounded queue. |
| `SafetyDecision` | `allowed: bool`, stable `code`, state revision checked. A denied/expired decision never dispatches. Stop invalidates previously approved work. |
| `CommunicationOutput` | Validated `WireMessage`, encoded CSP line including LF, canonical text, Chordic token and note tuple computed through existing functions. All derived fields are host-owned. |
| `HardwareCommand` | Host-generated `command_id`, session/request correlation, deadline and a typed communication payload. No generic `execute(dict)`/raw-bytes escape hatch. Motion will use a distinct typed payload and capability; its schema is deferred. |
| `HardwareReceipt` | Command/session/backend identity, status (`ACCEPTED`, `REJECTED`, `UNKNOWN`, `COMPLETED`), reason, evidence kind (`simulated`, `device_report`, `none`), and local receipt time. `ACCEPTED` is not `COMPLETED`. A serial write alone is `UNKNOWN` about device execution. |
| `BrainResult` | Request ID, outcome (`REJECTED`, `ACCEPTED`, `COMPLETED`, `FAILED`, `UNKNOWN`, `CANCELLED`), stable code, optional canonical communication output, optional hardware receipt and resulting state revision. The CLI renders this; provider text is never the status authority. |

Minimum codes: `NO_MATCH`, `INVALID_RESPONSE`, `UNSUPPORTED_INTENT`, `PROVIDER_FAILED`, `PROVIDER_TIMEOUT`, `BUSY`, `DEADLINE_EXPIRED`, `CAPABILITY_UNAVAILABLE`, `BACKEND_UNAVAILABLE`, `BACKEND_FAILED`, `ESTOP_LATCHED`, `STALE_FEEDBACK`, `INTERNAL_ERROR`. Preserve CSP `WireError.code` as diagnostic detail.

### RobotState and hardware operations

RobotState stores session/revision, backend identity, connection state (`DISCONNECTED`, `CONNECTING`, `READY`, `FAULT`), capability set, native backend mode, host motion mode using existing RPA-Link `Mode`, host E-stop latch, latest fault, last validated communication and its result, and pending command ID. An empty capability set never means unrestricted access.

Each observation carries value, unit, source/backend identity, validity, local receipt time and whether it is simulated. Sensor-specific maximum age is trusted configuration; absent measurement or age policy is unusable for motion. Preserve a source timestamp/sequence if available, but never compare monotonic clocks across devices. Requested target, commanded target, simulated position and measured position remain distinct fields. The fake controller's `position_valid=False` remains false.

Minimum hardware protocol:

```python
open() -> HardwareStatus
dispatch(command: HardwareCommand) -> HardwareReceipt
poll() -> tuple[HardwareEvent, ...]
stop(reason: str, *, emergency: bool) -> HardwareReceipt
close() -> None
```

`HardwareStatus` returns backend identity, capabilities, connection state, native mode and observations. `HardwareEvent` is a typed status/receipt/fault event, never arbitrary provider data. `open`, `dispatch`, `stop` and `close` have configured finite I/O deadlines; `poll` is nonblocking and bounded. Adapters validate events before the controller uses them. `stop` is repeatable and prioritized over normal work, but a return value must distinguish a local latch from device acknowledgement.

The simulator initially advertises `COMMUNICATION` and `LOCAL_STOP`, not brain-controlled motion. The Uno adapter advertises only `COMMUNICATION`; it does not advertise motion, remotely confirmed playback completion or remotely interruptible playback.

`BrainController.submit_text(text) -> BrainResult` executes the normal path. `BrainController.emergency_stop(reason)` is a separate operator/fault path that does not call AI. `reset_stop()` is an explicit operator operation after health checks, clears queued work and returns to disabled; it never starts a task. AI cannot request reset, arm or enable in this version.

Before connecting a real LLM, isolate inference in a supervised worker with bounded messages/deadlines; the controller must continue stop handling and polling while inference runs. Discard late results after timeout, cancellation, state/session change or stop. Do not hold the controller lock while waiting for inference or serial I/O. A Python type protocol is an architecture boundary, not a security sandbox for arbitrary executable plugins: load trusted providers only, give the model no execution tools or device handles, and keep the MCU's independent protections.

## 6. Connect existing CSP-1 and Chordic

After validation and safety, derive output in this exact order:

1. `csp.wire.encode(message)` provides the canonical `C1|INTENT|ARG\n` line.
2. `csp.wire.canonical_text(message)` provides the English meaning.
3. `csp.wire.chordic_token(message)` provides the existing lexical token.
4. `CspCodec.encode_token(token).notes` provides the notes.
5. TaskController selects communication dispatch; HardwareInterface adapts delivery.

For `SOCIAL.HELLO`, the result is `Hello.`, token `SOCIAL.hello` and the codec's runtime notes. No copied note list in the new brain. Displaying those notes is enough for initial acceptance; no host audio or speech package is required. Free English is not losslessly reversible; only registered meanings have exact mappings. Future motion requests need their own reviewed typed schema; do not force actuator data into the currently empty CSP argument.

## 7. Connect the existing simulation

`SimulatorHardware` owns one `SimRobot` instance. It loads existing JSON without pygame, starts IDLE with disabled actuators/unknown contacts, and passes only the validated encoded line into `handle_csp`. On `True`, return `COMPLETED` with evidence `simulated`, meaning only “simulator communication state updated.” On `False` or exception, report failure and trip/latch as applicable. Compare the full before/after motion snapshot; a greeting must not arm, change a joint, set contact or start a gait.

Keep simulation time separate from wall/monotonic time. Existing fixed-step updates and logger can remain unchanged. Brain logs use a configurable writable directory and JSONL with request/result IDs; existing CSV is optional plant-state evidence, not the brain event log.

Map IDLE to host DISABLED, ENABLED to ACTIVE only for explicit simulation tests, and STOPPED to SAFE_STOP unless an explicit emergency event has latched ESTOP. Preserve the host latch until operator reset; a native mode change alone cannot clear it. These mappings do not claim the simulator already implements all RPA-Link modes.

The existing pygame app remains a standalone v0.1 test harness. Starting it separately creates another robot, not a view of the brain-owned model. A later visual adapter must display the same model/snapshot and send trusted operator requests through the controller. Do not add another gait implementation to make the first demo visual.

Later motion integration must have one trajectory owner: adapt/extract the current gait into MotionController while preserving its regression behavior, and use the simulator only as the plant for that path. Disable the simulator's autonomous gait in externally commanded mode. RPA-Link fake hardware may guard/validate commands in tests; map joint IDs and microradians to the model's degrees explicitly in the adapter. It must not fabricate plant positions or contacts.

## 8. Connect Arduino and serial

Add optional `brain/serial_hardware.py` after the simulator path works. Import pyserial only when selected. Use a configured port (`COM...` on Windows, device path on Linux), **9600 baud, 8N1, LF**, one serial owner, finite read/write timeouts and bounded line buffers. Close Arduino Serial Monitor/browser access first.

Fixed compatibility mapping, derived from the current sketch:

| Validated semantic intent | Uno command |
|---|---|
| `SOCIAL.HELLO` | `SAY HELLO\n` |
| `RESPONSE.YES` | `SAY YES\n` |
| `RESPONSE.NO` | `SAY NO\n` |
| `REQUEST.HELP` | `SAY HELP\n` |
| `SOCIAL.THANKS` | `SAY THANK_YOU\n` |
| `SOCIAL.GOODBYE` | `SAY GOODBYE\n` |

On open, allow a bounded reset/startup period, discard old buffered input, send `STATUS` and require the expected firmware identity and a recognized `MODE:` line before READY. Wrong identity, no reply or unexpected reboot fails the session. Do not automatically replay a pending phrase on reconnect. Mode controls are trusted UI operations and map to `MODE COMM` / `MODE TRANSLATE`, separate from motion mode.

The current firmware prints the token **before** playing and has no request ID, ACK or DONE. A button can produce the same text as a host command. Therefore `CSP-1:` is an unsolicited device report, not reliable command-correlated completion. A successful write may be logged as sent, but the command receipt remains execution `UNKNOWN`. Never report “buzzer played” from it. A later small firmware extension can add correlated acceptance/completion if required; hearing sound or elapsed time is not machine-confirmed playback.

The sketch blocks during tone playback and cannot process an immediate STOP; closing serial does not guarantee silence. `stop` latches the host and drops pending work, reporting remote stop unsupported/unknown. This backend has no motor capability and must never be treated as the motion MCU. Keep its existing buttons and buzzer working.

Future motion MCU serial support uses the existing RPA-Link logical envelope, with independent local watchdogs and disabled startup. The documented COBS/CRC16 binary sketch is not a finished protocol: numeric type IDs, payload layouts, length limits, exact CRC variant/coverage, boot/session identity, sequence/replay policy and ACK correlation need a dedicated specification and golden vectors before motor use. Preserve current JSON meanings; version incompatible changes. Do not pretend the current Uno understands this transport.

## 9. Failure behavior

All failures record request/command ID, backend, reason and evidence; no failure fabricates success. Safety stop is allowed after rejection even though normal dispatch is forbidden. No automatic retry of an action with uncertain execution. After any stop/restart, discard queued and late work; explicit recovery returns disabled.

| Failure | Immediate deterministic behavior | Recovery |
|---|---|---|
| AI crash | Fail request `PROVIDER_FAILED`; normal dispatch never occurs. Keep stop/status service alive. If future motion is active, cancel task and request safe stop. | Restart provider explicitly; new request, no replay. |
| AI hang / deadline | `PROVIDER_TIMEOUT`; invalidate request and ignore late worker result. | Restore provider health; new request. |
| Malformed AI response | `INVALID_RESPONSE`; no normal hardware call, no repair/guess. | User can submit a new valid request. |
| Unsupported intent | `UNSUPPORTED_INTENT`; reject before task selection. A known lexical word is not a registered capability. | Implement/review a new schema/capability in a later stage, or use a supported request. |
| Python exception | At the supervisor boundary, fail affected request, latch fault, cancel pending work and attempt bounded stop/close; preserve the original error even if cleanup fails. | Explicit restart/reset after diagnosis. A killed process cannot guarantee cleanup; future MCU watchdog must stop locally. |
| Lost serial connection | Mark backend DISCONNECTED, invalidate observations, execution UNKNOWN for in-flight command; no automatic fallback to simulated success. | Reopen, identify, start a new session disabled; never replay. |
| MCU reset | Boot banner/identity change, unexpected startup status or link-health timeout invalidates session and pending receipts. Current Uno has no reliable boot counter. | Fresh handshake and operator recovery. Future motion MCU must boot disabled and require explicit enable. |
| Stale sensor value | Mark unusable using local age/validity. Reject tasks requiring it; safe-stop any task that depends on it. | Fresh valid feedback plus explicit recovery. Communication does not require invented joint feedback. |
| Simulator failure | `BACKEND_FAILED`, stop/trip if reachable, latch backend fault; no successful result. | Recreate model in disabled initial state explicitly. |
| Emergency stop | Immediately latch host ESTOP, cancel task/inference results, clear pending work, invoke prioritized backend stop and block normal dispatch. Physical stop must act independently on future hardware. | Human reset only after healthy connection and local conditions, including released physical stop where present; remain disabled. |

Neither a software exception handler nor Chordic `SAFETY.stop_now` substitutes for physical E-stop. Physical controlled-stop/hold/power-isolation choices remain subject to SAF-001 and SAF-011 and measured mechanism behavior; this document chooses no actuator reaction.

## 10. Windows and Raspberry Pi portability

Keep Python `>=3.10`; test the selected interpreter on both platforms. This review ran Python 3.12.14 on Linux, not Windows or Pi. No Pi memory, inference speed, battery life or benchmark claim is made.

| Dependency / platform behavior | Isolation rule |
|---|---|
| Paths and data files | `pathlib`, UTF-8, packaged resources, explicit writable log path; no current-directory or drive-letter assumptions in core logic. Full source checkout initially required for default CSP spec lookup. |
| Serial ports, permissions, USB reset | Serial adapter/config only. Port chosen by operator; no platform-specific name in controller. Linux device permissions handled at setup, not by running the whole brain privileged. |
| Pygame, display and audio | Optional visual frontend only. Headless core imports/run must work without pygame or a display. Browser speech availability does not establish offline speech support. |
| UDP sockets | Existing optional `rpa_link.udp`, loopback default. Offline core must start with networking unavailable. No cloud or LAN service required. |
| Time | Inject local monotonic clock for timeouts/tests; separate deterministic simulation clock. Wall-clock dates only for logs. |
| LLM runtime / CPU architecture | Optional provider package and locally provisioned model; installation/model download may occur beforehand. No startup download or network fallback. Choose/test a model later on actual hardware. |
| GPIO, PWM, MCU-specific code | Remain in firmware/drivers behind hardware boundary; never in AI or controller. |
| Environment | Recreate venv and reinstall declared dependencies on each OS/architecture. Do not transfer the tracked Windows `.venv`. |

## 11. New code actually needed

Preserve the earlier plan's package location and add only these responsibilities:

| Proposed file | Purpose / timing |
|---|---|
| `software/brain/__init__.py` | Package entry; no device/network side effects on import. |
| `software/brain/ai.py` | AIProvider and fixed offline DummyAIProvider; supervised LLM adapter later. |
| `software/brain/contracts.py` | Immutable request/output/result/state records and enums from this freeze; RobotState can live here rather than a separate state service. |
| `software/brain/validation.py` | Strict candidate shape/type wrapper around existing CSP validation. |
| `software/brain/safety.py` | Deterministic policy and explicit rejection reasons. |
| `software/brain/controller.py` | BrainController, state transitions, minimal communication TaskController, fault handling and structured event logging. No separate task framework now. |
| `software/brain/hardware.py` | HardwareInterface and headless SimulatorHardware initially. Split adapters only when needed. |
| `software/brain/cli.py` | Composition, input/status/stop/reset, configurable backend/log path and honest output. |
| `software/brain/tests/test_brain_v0_2.py` | Fake providers, spy hardware, injected clock, end-to-end and fault tests. |
| `software/brain/serial_hardware.py` | Optional later Uno compatibility adapter; no motion implementation. |

Do not add a MotionController implementation or serial binary codec just to satisfy a directory diagram. Their ownership and extension boundaries are fixed above; algorithms and hardware payload details await a real need.

## 12. Too early, and omissions that would force a rewrite

Defer real LLM selection, arbitrary language translation, speech/clap inputs, phone app, persistent memory/database, LiDAR/SLAM, realistic physics, inverse kinematics, door/chair/origami tasks, custom network services and motor drivers. No ROS, Docker or cloud dependency. A full GUI and UDP bridge are not prerequisites for the first brain run.

Resolve now: strict request schema, immutable state with provenance/freshness, distinct accepted/completed/unknown results, request/session correlation, cancellable provider boundary, finite I/O deadlines, capability checks, independent stop path, package-resource strategy and a single motion authority. Omitting these would couple AI to drivers, confuse simulation with hardware evidence or require redesign when commands become asynchronous. Resolve binary framing and measured safety limits before real motion, not during this communication stage.

## ARCHITECTURE DECISIONS TO FREEZE

1. **AF-01 — Keep the repository structure and protocols.** Add `software/brain/`; reuse current `csp`, `simulation` and `rpa_link`. Do not reassign CSP lexical codes or replace RPA-Link.
2. **AF-02 — AI proposes; deterministic code authorizes.** Exact two-field candidate validation precedes controller acceptance, safety precedes every normal dispatch, and only task/motion code can select hardware operations. No AI hardware handles/tools, telemetry mutation, stop reset or enable authority.
3. **AF-03 — First acceptance is offline communication in simulation.** DummyAIProvider, the six existing empty-argument wire intents and the existing headless model; no movement, network, model, Arduino or pygame requirement.
4. **AF-04 — Freeze contracts and evidence semantics.** Use Section 5's input shape, lifecycle, IDs, state provenance, capability flags, bounded operations and accepted/completed/unknown distinctions. Never call a simulated or unconfirmed result physical success.
5. **AF-05 — One controller and one owner per responsibility.** Controller alone updates host state; TaskController sequences tasks; later MotionController alone schedules host motion; hardware/simulator/MCU enforce their local limits. Avoid competing gait or safety authorities.
6. **AF-06 — Stop and recovery never depend on AI.** Stops invalidate pending work and remain latched until explicit operator recovery. No restart/reconnect/reset automatically starts motion. Future MCU watchdog and physical E-stop are independent.
7. **AF-07 — Adapter-only platform access.** Windows and Pi share core Python code. Serial, UDP, GUI/audio, local model runtime and MCU drivers remain optional isolated boundaries. Full-checkout install first; fix resource packaging before wheel-only deployment.
8. **AF-08 — Preserve the current Uno as a communication endpoint.** First serial adapter targets 9600-baud `SAY` protocol. Existing browser and dormant CSP decoder are not proof of serial interoperability; no motor, remote STOP or correlated playback-completion capability is claimed.
9. **AF-09 — Extend only with evidence.** Motion schemas, binary wire details, limits and model selection are future reviewed work. A failing test justifies a narrow subsystem fix, not a repository rewrite. Changes to these frozen decisions require the owner's explicit architecture revision.

## 13. Seven implementation milestones

These are software implementation increments, not replacements for the project's M0/hardware release gates.

| # | Focus | Acceptance gate |
|---|---|---|
| 1 | Contracts, strict validation and DummyAIProvider | All six fixed text mappings round-trip through existing CSP functions; malformed/type/extra-field/nonempty-argument/unknown inputs reject. No model or hardware import. |
| 2 | BrainController, RobotState, SafetyValidator and minimal communication task | Spy backend proves safety precedes dispatch, denied requests never dispatch, stale approvals are invalidated and IDs/results remain correlated. |
| 3 | SimulatorHardware and full communication path | `hello` updates existing SimRobot communication state and returns simulated evidence; every joint/contact/enable/gait field remains unchanged. Works headlessly. |
| 4 | CLI, local logs and Windows instructions | `python -m brain.cli` runs with installed dependencies and internet disconnected; shows provider, intent, safety, CSP, English, notes and simulated receipt. Unknown input rejects clearly. This is the first usable Windows Brain v0.2. |
| 5 | Fault handling and portability gate before LLM | Provider crash/hang/late reply, backend error, stop/reset, stale feedback and shutdown tests; Windows/Linux suite coverage; installed-resource check before wheel deployment. Stop remains responsive with blocked inference. |
| 6 | Optional Uno serial backend | Mock serial covers exact mapping, identity, timeout, unplug/reset and no replay; bench-test current sketch separately. Receipt never claims confirmed playback. Simulator still works without pyserial/Uno. |
| 7 | Optional local LLM provider | Locally provisioned model produces the same schema under worker deadlines; no internet fallback, no new hardware permissions. Repeat malformed-output/stop tests. Record actual machine observations only. |

## 14. Verify this documentation stage

No brain implementation or hardware behavior changes in this stage. Review the diff: only this document and its navigation/supersession links should change.

In a freshly updated checkout on Windows, use a new environment name because this repository currently tracks `.venv`. Run from the repository root:

```powershell
py -3.12 -m venv .venv-brain-review
.\.venv-brain-review\Scripts\python.exe -m pip install -e .
.\.venv-brain-review\Scripts\python.exe -m unittest discover -s language/tests -v
.\.venv-brain-review\Scripts\python.exe -m unittest discover -s software/rpa_link/tests -v
.\.venv-brain-review\Scripts\python.exe -m unittest discover -s software/simulation/tests -v
node software/brain_web/protocol.test.js
git diff --check
```

Python 3.12 is an example interpreter choice consistent with current CI, not a claim that later versions fail. If Node is not installed, the browser-only check can wait. Do not commit the new environment. Dependency installation may need internet; runtime acceptance must work after disconnection.

**Checks actually run during this review:** at the reviewed source revision, Linux Python 3.12.14 with `PYTHONPATH=software`: language suite **16 passed**, simulator suite **9 passed**, RPA-Link suite **10 passed**. Node v24.19.0: `protocol.test.js` passed. These are 35 Python tests plus the browser protocol script. No Windows run, Pi run, GUI run, wheel install, Arduino compile/upload, serial bench test or hardware safety test was performed. Existing test success does not resolve the protocol mismatch in Section 3. The future brain commands/tests above remain unavailable until implemented.

**Next implementation step:** milestone 1, followed by the smallest controller-to-simulator path. Do not start by downloading an LLM.
