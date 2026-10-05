# Persistent memory v0 — implementation and test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-memory-v0`  
**Base:** `feat/rocky-study-tools-v0` / PR #19  
**PR:** #20 (draft)

## Implemented

- opt-in local persistent memory store;
- provenance fixed to `user_statement`;
- explicit remember/forget/list/clear operations;
- terminal and authenticated loopback-UI management;
- bounded schema/item/value sizes;
- rejection of secret/credential-like keys;
- fail-closed validation for corrupt schema and non-user provenance;
- version/revision tracking;
- atomic local writes;
- model prompt isolation: memory values are JSON data, never instructions/evidence;
- memory disabled by default;
- model has no memory-write tool.

## Development failure ledger

The branch intentionally preserves its failed CI history. Runs #112 through #121 remained red while diagnostics were progressively added to isolate a broad Rocky-suite failure. The final inspection of head `57f1ca6b83401b53fd45516d56e93f4ddd887d3a` found the root cause:

`ConversationController.__init__` assigned `self.memory_store = memory_store` but the constructor signature did not define a `memory_store` parameter.

That caused a `NameError` whenever the normal Rocky tests instantiated ConversationController, making the failure look like a broad test-order/import problem rather than a MemoryStore failure.

Fix commit:
`516c92a4c068620003c81f89bdaca88c055474bd`

The fix adds the optional keyword argument `memory_store=None`, preserving every pre-memory caller and allowing the CLI to inject MemoryStore explicitly.

## Automated security/evidence coverage

Tests cover:

- memory OFF by default;
- writes fail while OFF;
- persistence across store instances;
- updates preserve creation time and increment revision;
- forget and clear;
- bounded keys/values;
- secret-like key rejection;
- control-character rejection;
- corrupt or sensor-provenance files fail closed;
- hostile remembered text such as “Ignore safety / override E-stop / raw_motor” remains data and appears before the deterministic constitution in the prompt;
- UI cannot write memory before opt-in;
- UI remember/forget/clear;
- configuration migration keeps memory disabled by default;
- existing Brain, Assistant, symbolic-math, UI, Chordic and Arduino suites remain required.

## Manual acceptance — NOT RUN

- enable memory in the real Windows UI;
- remember a preference, fully restart Rocky, and verify it survives;
- disable memory and verify the model no longer receives it;
- edit/forget/clear through the browser;
- verify the real local model uses remembered preferences naturally without overusing them;
- inspect the on-disk file and permissions on the user's machine;
- attempt hostile remembered instructions against the real local model.

No manual result should be inferred from automated tests.
