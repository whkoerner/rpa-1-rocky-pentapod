# Rocky local web UI v0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-local-web-ui-v0`  
**Base:** Assistant V2 branch `feat/rocky-assistant-v2`  
**PR:** #18 (draft)

## Implemented

- localhost browser chat through the existing `ConversationController`;
- spoken/detail separation in the page;
- EXP-003 semantic coverage/fallback and timing/status display;
- assistant mode and bounded audio/voice tuning;
- replay/cancel/STOP/reset/clear;
- profile save plus settings export/import;
- Windows launcher option 9;
- server binds only to `127.0.0.1`;
- random per-launch token required for every API route;
- no CORS and no external page dependencies;
- tests that reject physical-style tuning fields.

## Development failure ledger

| Order | Run | Symptom | Root cause | Fix | Final status |
|---|---|---|---|---|---|
| 1 | #103 | Windows 3.12/3.13 and Arduino passed; Ubuntu 3.12/3.13 failed the full Rocky suite | A Linux-only existing launcher test still expected the old `Rocky Conversational Brain V1` startup banner after the UI branch renamed the product banner to `Rocky Assistant V2` | Added diagnostic isolation rather than guessing | Preserved failure |
| 2 | #104 | Ubuntu still failed; Windows cells passed | Same platform-specific full-suite interaction; UI API security was additionally hardened so all API endpoints require the per-launch token | Kept hardening and isolated new UI tests | Preserved failure |
| 3 | #105 | All three new UI tests passed individually on Ubuntu, but the full suite failed | Diagnostics proved the server/settings tests were not failing. Repository scan localized the only POSIX-only Rocky test to the stale startup-banner assertion | Updated that assertion to the new Assistant V2 banner | Preserved failure |
| 4 | #106 | Windows 3.12/3.13, Ubuntu 3.12/3.13, and Arduino Uno all passed | Stale POSIX test fixed; no runtime workaround needed | Removed temporary diagnostic CI steps after this proof | GREEN |\n| 5 | #107 | Normal CI matrix after diagnostic-step removal: Windows 3.12/3.13, Ubuntu 3.12/3.13, Arduino Uno all passed | No hidden diagnostic dependency remained | No code change required | GREEN |

Run #107 is the required clean normal-matrix proof after the temporary diagnostic steps were removed.

## Automated evidence

The normal Rocky suite covers the web UI alongside all existing Brain, safety, EXP-003, translation, launcher, protocol, and audio tests. The UI-specific tests verify:

- physical-style setting `raw_motor_power` is rejected;
- speed/volume/mode/renderer/voice settings stay bounded;
- export/import and atomic profile save work;
- a real loopback HTTP server serves the packaged page;
- unauthenticated API GET and POST calls are rejected;
- authorized local chat is accepted;
- CORS is not enabled;
- CSP and frame protections are present.

## Manual acceptance — NOT RUN

- opening menu option 9 on the user's Windows machine;
- real local `qwen3:8b` conversation through the browser;
- browser layout/comfort at the user's preferred window size;
- audible Chordic renderer tuning through real speakers;
- English voice selection and naturalness;
- subjective active-translation overlap;
- save-profile persistence across a real Rocky relaunch;
- long study/detail responses in the browser.

No manual listening or UI-quality claim should be inferred from CI.
