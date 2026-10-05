# Rocky Neural English Voice V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-piper-voice-v0`  
**Base:** `feat/rocky-lecture-notes-v0`  
**PR:** #26 (draft)

## Automated scope

Tests verify:

- token-authenticated loopback sidecar status;
- loaded voice identity;
- returned WAV is used for measured duration;
- synthesis request speed/volume stay bounded;
- contextual question profile is selected deterministically;
- prepared WAV is reused instead of synthesizing twice;
- non-zero Piper pitch setting is rejected;
- bad token fails closed;
- configured voice mismatch fails closed;
- control-character/oversize speech is rejected before network;
- System.Speech remains the default configuration;
- Piper port/timeout/path configuration is bounded;
- Piper ONNX voice can be represented as a checksum-verifiable optional portability asset.

## CI evidence

Actions runs **#137** and **#138** both passed:

- Windows Python 3.12;
- Windows Python 3.13;
- Ubuntu Python 3.12;
- Ubuntu Python 3.13;
- Arduino Uno.

A final run is required after adding explicit sidecar provisioning/docs.

## Manual NOT RUN

- Piper installation;
- voice model provisioning;
- actual Piper synthesis;
- speaker playback;
- subjective voice naturalness;
- subjective contextual inflection;
- active translation timing by ear;
- cancellation with a real Piper process;
- license review for the selected voice model.
