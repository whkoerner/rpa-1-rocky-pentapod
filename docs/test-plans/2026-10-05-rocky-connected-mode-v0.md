# Rocky Connected Mode V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-connected-mode-v0`  
**Base:** `feat/rocky-portability-v0`  
**PR:** #23 (draft)

## Implemented automated boundary

- OFFLINE default;
- model schema omits connected tool names while OFFLINE;
- fixed read-only connected capability allowlist;
- numeric loopback-only gateway client;
- local token-file requirement;
- strict bounded request/response JSON;
- request correlation;
- explicit `connected_tool_result` provenance;
- content-minimized audit log;
- audit failure is fail-closed;
- terminal and browser OFFLINE/ONLINE controls;
- no model-visible connected write capability;
- no raw motor/shell/arbitrary URL tool.

## Development ledger

| Order | Run | Symptom | Root cause | Fix | Status |
|---|---|---|---|---|---|
| 1 | #129 | All four Rocky software matrix cells failed; Arduino stayed green | Existing browser-UI test double predated `connected_status()`, while the real UI now queries connected state during status/tuning rendering | Added the connected-state seam to the UI test double and made disabling connected mode a safe no-op for providers without a gateway; enabling remains fail-closed | Failure preserved; superseded |
| 2 | #130 | Windows 3.12/3.13, Ubuntu 3.12/3.13, and Arduino Uno all passed | Test double/runtime seam fixed; audit persistence also tightened to fail closed | No further runtime fix required | GREEN |

## Manual NOT RUN

- real gateway process;
- real Google Drive search/read;
- real Calendar read;
- real web search;
- OAuth authorization/revocation;
- Windows firewall/loopback behavior with a real gateway;
- user review of connected-mode UI;
- network loss during a real request;
- account write actions (not implemented).
