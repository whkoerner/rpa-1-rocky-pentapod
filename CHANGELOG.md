# Changelog

## 2026-09-30 — Rocky Brain v0.1

- Named the constructed musical language Chordic and retained CSP-1 as its deterministic encoding.
- Added Uno R3 firmware with eight Chordic utterances, two physical controls, safe startup, and a documented serial protocol.
- Added a dependency-free browser console that switches translation mode, displays tokens, and speaks English locally.
- Added beginner wiring/build instructions, JavaScript protocol tests, and hardware acceptance criteria.

All notable changes are recorded here. The project follows semantic versioning for public releases; pre-release hardware remains explicitly experimental.

## [Unreleased]

### Added

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
