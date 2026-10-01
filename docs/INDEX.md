# RPA-1 Project Index

This page is the simplest way to navigate the project. It does not replace the requirements, risk register, roadmap, or test records.

**Current milestone:** M0 — Repository and Communication  
**Current release status:** Pre-release

## Start here

1. [Current milestone](milestones/M0-repository-communication.md)
2. [Current build guide](build-guides/brain-v0.1-build.md)
3. [Requirements](requirements/requirements-v0.2.md)
4. [Risk register](risk-register/risk-register.md)
5. [Chordic / CSP-1](../language/README.md)
6. [Roadmap](roadmap/sophomore-year-roadmap.md)

## Current work

| Item | Status | Main file |
|---|---|---|
| Brain v0.2 host integration | PLANNED — architecture frozen | [Architecture freeze](architecture/brain-v0.2-architecture.md) |
| Rocky Brain v0.1 | READY TO TEST | [Build guide](build-guides/brain-v0.1-build.md) |
| Computer-only Simulation v0.1 | READY TO TEST | [Build guide](build-guides/simulation-v0.1-build.md) |
| Chordic / CSP-1 | IN PROGRESS | [Language overview](../language/README.md) |
| Actuator comparison | PLANNED | [Test plan](test-plans/actuator-comparison-test.md) |

## Status labels

- **PLANNED** — defined, but implementation has not started.
- **IN PROGRESS** — currently being built or changed.
- **READY TO TEST** — implementation exists, but required acceptance testing is incomplete.
- **VERIFIED** — stated acceptance criteria passed and a test result is linked.
- **RELEASED** — verified and intentionally included in a staged RPA-1 release.
- **BLOCKED** — optional extra label when work cannot continue until a stated problem is resolved.

Do not use **VERIFIED** without a linked test result. Do not use **RELEASED** just because code or hardware exists.

## Engineering documents

- [Requirements](requirements/requirements-v0.2.md)
- [Architecture](architecture/)
- [Roadmap](roadmap/sophomore-year-roadmap.md)
- [Risk register](risk-register/risk-register.md)
- [Test plans](test-plans/)
- [BOM](../bom/)

## Implementation

- [Firmware](../firmware/)
- [Software](../software/)
- [Computer-only simulator](../software/simulation/)
- [Electronics](../electronics/)
- [Hardware](../hardware/)
- [CAD](../cad/)
- [Interfaces](../interfaces/)
- [Perception](../perception/)

## Language

- [Chordic overview](../language/README.md)
- [CSP-1 specification](../language/specification/csp_v0_1.yaml)
- [Language tests](../language/tests/)

## Build guides

Each active build should use the same basic format and link to the authoritative safety, wiring, firmware, and test files instead of duplicating them.

- [Rocky Brain v0.1](build-guides/brain-v0.1-build.md)
- [Computer-only Simulation v0.1](build-guides/simulation-v0.1-build.md)
- [Build-guide template](build-guides/BUILD-GUIDE-TEMPLATE.md)

## Milestones

- [Milestone dashboard](milestones/README.md)
- [M0 — Repository and Communication](milestones/M0-repository-communication.md)

Future milestone pages should be added when that milestone becomes active. Until then, the [roadmap](roadmap/sophomore-year-roadmap.md) remains authoritative.
