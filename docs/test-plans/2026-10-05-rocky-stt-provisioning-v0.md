# Rocky STT provisioning V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-stt-provisioning-v0`  
**Base:** real-model benchmark v0.2 stacked head

## Automated scope

The branch is intended to prove that enabled whisper.cpp recognition cannot silently use an unpinned executable/model.

Automated cases cover:

- enabled STT rejects a missing asset manifest;
- correct CLI/model SHA-256 and matching configured paths are accepted;
- tampered CLI bytes are rejected by checksum;
- configured CLI path differing from the verified manifest is rejected;
- direct transcriber availability rejects symbolic-link executable/model paths;
- the Windows setup script updates only user settings/manifest metadata using already-present fixture files;
- the setup script computes the expected SHA-256 values;
- the setup script makes no download request;
- launcher uses the real `scripts\Setup-Piper.ps1` path and the new `scripts\Setup-WhisperCpp.ps1` path;
- existing Voice Input V0 WAV/process/transcript limits remain required;
- all Rocky, browser protocol, Windows 3.12/3.13, Ubuntu 3.12/3.13, and Arduino jobs remain required.

## Manual NOT RUN

- real whisper.cpp binary;
- real Whisper GGML model;
- model-license review;
- Windows microphone capture;
- real transcript accuracy;
- classroom/noisy-room performance;
- transcript edit/confirm UX with live speech;
- cancellation/STOP during a real recognizer process;
- offline recognition after real provisioning;
- CPU/GPU latency and power draw;
- long lecture transcription.

CI fixture files are not a substitute for real microphone/model acceptance.
