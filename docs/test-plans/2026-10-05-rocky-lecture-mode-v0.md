# Rocky Lecture/Class Mode V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-lecture-mode-v0`  
**Base:** `feat/rocky-connected-mode-v0`  
**PR:** #24 (draft)

## Automated scope

Tests cover:

- explicit permission confirmation before session creation;
- safe generated session IDs;
- bounded PCM chunk validation;
- local chunk persistence;
- SHA-256 manifest evidence;
- accumulated duration/timestamps;
- session stop state;
- no additional chunk after stop;
- session path traversal rejection;
- deferred per-chunk transcription;
- transcript JSON/text output;
- checksum tamper detection;
- refusal to transcribe an active recording;
- refusal to claim an empty session was transcribed;
- browser UI lecture start/chunk/stop path;
- configuration bounds and the invariant that lecture chunks may not exceed the configured STT clip limit.

## Development ledger

| Order | Run | Result | Notes |
|---|---|---|---|
| 1 | #132 | GREEN | Initial Lecture V0 implementation passed Windows 3.12/3.13, Ubuntu 3.12/3.13, and Arduino Uno. |
| 2 | #133 | GREEN | Hardened head also passed all five required jobs after microphone/session-order, chunk-upload-stop, and empty-transcript fixes. |

## Manual NOT RUN

- real microphone recording in Chrome/Edge on the user's Windows PC;
- real 2 h 40 min recording;
- browser sleep/display-lock behavior;
- real classroom acoustic quality;
- real whisper.cpp lecture transcription;
- transcription duration and accuracy;
- actual note generation from the transcript;
- Google Docs/Drive export;
- classroom/instructor consent verification.

Automated tests do not establish microphone quality, legal permission, or transcription usefulness.
