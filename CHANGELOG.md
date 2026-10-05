# Changelog

## 2026-10-03 — Rocky desktop V1.1 (ready for user testing)

- Preserved the newer Windows test history from the original V1 branch after confirming PR #8 was merged.
- Added a Windows launch/repair menu and per-user desktop shortcut creation with quoted paths and environment/model checks.
- Added one validated JSON personality profile, default/example profiles and explicit legacy text compatibility.
- Added configurable 3× note/gap duration, stable CT2 word/phrase patterns, exact UTF-8 fallback, decoded English, dictionary/word replay and learning mode.
- Moved WAV synthesis into cancellable background work; preserved safety checks and stop/reset semantics.
- Added focused tests and Python 3.12/3.13 Windows/Linux CI coverage; no firmware or hardware-control changes.
- Added official-source hardware comparison, portable config examples, configuration-transfer instructions and separate standalone/PC-assisted checklists.
- See [actual validation and unresolved failures](docs/test-plans/rocky-desktop-v1-1.md). No real-model, acoustic-decoding or Pi-performance claim is made.

## 2026-10-01 — Conversational Brain V1 (ready for user testing)

- Added a supervised local Ollama conversation provider, editable persona, bounded session memory and a multi-turn terminal client.
- Added a separately validated desktop text communication capability through the existing brain/safety/task/hardware chain.
- Preserved the six CSP-1 meanings; added reversible CT1 UTF-8 musical text transport for longer replies.
- Added bounded PCM synthesis, built-in Windows playback, optional pygame audio, WAV diagnostics, translation/replay/mute and explicit cancellation/stop/reset.
- Added headless conversation/audio/provider/worker tests, Windows build instructions, architecture decisions and a V2 roadmap.
- Kept Python >=3.10 and distribution name `rpa1-csp`; bumped the combined distribution to 0.2.0. App version is 1.0.0.
- Phone interface deferred; microphone interface prepared for V2. See the [validation record](docs/milestones/conversational-brain-v1.md) for executed tests and outstanding real-device/model checks.

## 2026-09-30 — Rocky Brain v0.1

- Named the constructed musical language Chordic and retained CSP-1 as its deterministic encoding.
- Added Uno R3 firmware with eight Chordic utterances, two physical controls, safe startup, and a documented serial protocol.
- Added a dependency-free browser console that switches translation mode, displays tokens, and speaks English locally.
- Added beginner wiring/build instructions, JavaScript protocol tests, and hardware acceptance criteria.

All notable changes are recorded here. The project follows semantic versioning for public releases; pre-release hardware remains explicitly experimental.

## [Unreleased]

### Added

- Added a source-labeled Rocky Desktop + Chordic debugging/test-evidence ledger preserving CI failures, local/manual failures, fixes, regressions, timing observations, and explicit NOT RUN boundaries from the 2026-10-04 work.
- Minimum deterministic Brain v0.2 host core with strict semantic validation, immutable state/contracts, safety gating, simulated hardware, structured results/logging, and an offline CLI.
- Brain v0.2 contract/integration tests and Windows/Linux CI coverage for CSP, RPA-Link, simulator, and brain host suites.
- Project definition and no-wheel requirement
- Initial system requirements and risk register
- Bio-inspired actuation trade study
- Sophomore-year roadmap and $2,000 program ceiling
- Guarded actuator-comparison test plan
- Arduino musical communicator starter firmware
- CSP-1 musical-language specification

### Decisions

- Electric tendon/series-elastic actuation is the leading full-scale direction.
- Pneumatic and manual low-pressure hydraulic mechanisms are comparison experiments.
- Portfolio Release 1.0 targets a measured 1:3 mobile robot and a full-scale stationary interaction form, not unsupported full-scale walking.

### Fixed

- Quoted the YAML concepts `on`, `yes`, and `no` so YAML 1.1-compatible parsers do not silently convert them to booleans. The all-token round-trip test exposed this defect.
