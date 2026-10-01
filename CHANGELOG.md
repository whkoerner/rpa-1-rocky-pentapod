# Changelog

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
