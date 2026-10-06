# Rocky Lecture/Class Mode V0

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-lecture-mode-v0`, stacked on Connected Mode V0 PR #23.

## Goal

Lecture/Class V0 makes a long class recording technically practical without requiring continuous cloud upload, real-time onboard transcription, or one giant browser-memory buffer.

The target use case is approximately 2 hours 40 minutes (9,600 seconds).

```text
explicit user permission confirmation
  -> visible browser microphone recording
  -> bounded ~30 second mono PCM chunks
  -> token-authenticated 127.0.0.1 upload
  -> local lecture session directory
  -> checksummed manifest
  -> explicit STOP
  -> later local whisper.cpp transcription
  -> timestamped transcript.json + transcript.txt
```

The transcript is a source artifact for later study-note generation. It is not automatically sent to a model, Google Docs, ChatGPT, or any external service.

## Recording privacy boundary

Recording cannot start unless the user checks an explicit permission/consent confirmation and presses **Start visible recording**.

The UI continuously displays a RECORDING indicator, elapsed time, session ID, and local saved duration. There is no wake word, hidden recording, background recording default, or automatic start.

Technical capability is not treated as classroom permission.

## Bounded chunking

Browser Web Audio captures mono samples and resamples each bounded chunk to:

- 16,000 Hz;
- mono;
- 16-bit PCM WAV.

Default chunk size: 30 seconds.  
Hard configurable chunk range: 10–60 seconds.

Each chunk is uploaded independently to Rocky's existing loopback UI server. Browser memory is cleared after each flush instead of retaining an entire multi-hour class.

The server validates every chunk with the same strict PCM contract used by push-to-talk STT.

## Long-session limits and storage

Default lecture limit: 10,800 seconds (3 hours).  
Hard configuration maximum: 14,400 seconds (4 hours).

A 2 h 40 min target class is 9,600 seconds. At mono 16 kHz / 16-bit PCM, raw audio is approximately:

- 32,000 bytes/second;
- 960,000 bytes per 30-second chunk plus WAV headers;
- about 320 chunks for 2 h 40 min;
- about 307.2 MB of PCM payload.

This is intentionally a simple, robust V0 format. A later optional compression stage may reduce storage, but V0 does not add a codec dependency that could make recording less reliable.

## Session manifest

Every session receives a safe generated ID such as:

`lecture-20261005T120000Z-ab12cd34`

Each local session directory contains:

- `manifest.json`;
- `chunk-00001.wav`, `chunk-00002.wav`, ...;
- later, `transcript.json`;
- later, `transcript.txt`.

The manifest records chunk index, start time, duration, byte size, and SHA-256. Transcription re-verifies every chunk before using it. A modified or missing chunk fails closed.

## Deferred transcription

The Windows launcher adds:

**13 — Transcribe recorded lecture session**

Equivalent CLI:

`python -m rocky lecture-transcribe --lecture-session <SESSION_ID>`

Transcription uses the already configured local whisper.cpp adapter. Each small verified chunk is transcribed sequentially; Rocky does not need to fit an entire 2 h 40 min WAV into the STT sidecar at once.

Output contains timestamped segments. Confidence remains null when the bounded whisper.cpp adapter does not provide a real confidence value.

## Failure behavior

- microphone permission is requested before a server recording session is created;
- if Web Audio initialization fails after session creation, Rocky closes the empty server session;
- chunk upload errors stop the browser recording path and still attempt to close the server manifest;
- Rocky's existing STOP action closes an active lecture session before latching stop;
- an empty recording is not falsely marked transcribed;
- session IDs are strictly validated to prevent path traversal;
- transcript generation verifies every chunk checksum/duration first.

## Deliberate V0 limitations

- no speaker identification;
- no diarization;
- no live subtitles;
- no real-time whole-lecture transcription;
- no cloud transcription fallback;
- no Google Docs write;
- no automatic ChatGPT upload;
- no automatic note generation in this milestone;
- no compressed recording format yet;
- browser tab/process must remain running during capture.

These are later layers built on the local source-of-truth recording/session format.

## Manual acceptance still required

- real 2 h 40 min browser recording;
- real classroom microphone quality;
- browser sleep/power behavior during a long lecture;
- actual disk consumption on the user's machine;
- real whisper.cpp transcription of a long session;
- transcription speed/accuracy;
- cancellation/recovery after laptop sleep or browser crash;
- classroom permission/consent for any actual recording.

## Durability hardening follow-up

A stacked follow-up adds explicit upload sequencing and persisted-session recovery without changing the V0 PCM storage format:

- every browser upload carries the active session ID and a monotonically increasing chunk index;
- the server rejects wrong-session, duplicate, and out-of-order chunk uploads before writing audio;
- an interrupted manifest that still says `recording` can be explicitly recovered to `recorded` after the browser/process is gone;
- recovery is never automatic and is marked in the persisted manifest as `recovered_interrupted=true`;
- deletion is explicit, requires a non-recording session, and removes only the validated generated session directory;
- session-directory symlinks are rejected, in addition to existing manifest/chunk symlink rejection;
- deferred transcription verifies contiguous chunk indices and contiguous manifest timing before invoking STT.

These controls make retry/crash behavior inspectable. They do not establish that a real 2 h 40 min browser session survives sleep, power loss, or microphone/device changes; those remain manual acceptance items.
