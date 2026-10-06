# Push-to-talk voice input v0 — test plan

**Date:** 2026-10-05  
**Branch:** `feat/rocky-voice-input-v0`  
**Base:** Memory V0 branch / PR #20  
**Status:** Draft

## Automated scope

Required tests cover:

- valid 16 kHz mono 16-bit PCM WAV duration;
- invalid sample rate;
- stereo input;
- wrong sample width;
- malformed non-WAV input;
- duration limit;
- request byte limit;
- missing local whisper executable/model;
- whisper invocation uses an argv list with `shell=False`;
- shell-like characters in configured paths remain single argv values;
- bounded strict JSON transcript parsing;
- empty/oversized transcript rejection;
- no invented confidence value;
- child-process cancellation;
- token authentication on the STT endpoint;
- STT endpoint disabled by default;
- transcript does not call ConversationController or auto-send;
- Cancel also cancels the STT sidecar;
- existing Brain/Assistant/Study/Memory/UI/Chordic tests remain green;
- Windows Python 3.12/3.13;
- Ubuntu Python 3.12/3.13;
- Arduino Uno.

## Manual acceptance — NOT RUN

- browser requests microphone permission only after Start microphone;
- recording indicator is obvious;
- automatic maximum-duration stop;
- real Windows microphone capture;
- real locally provisioned whisper.cpp model;
- recognition quality in a quiet room;
- recognition quality in a classroom/noisy room;
- transcript appears in input box and can be edited before Send;
- Cancel/STOP during a real transcription;
- offline operation after provisioning;
- CPU latency and power use;
- microphone device selection behavior.

No CI result is evidence that speech recognition is acoustically accurate.

## Checksum-provisioning follow-up

A stacked follow-up adds:

- explicit no-download Windows whisper.cpp provisioning;
- SHA-256 pinning for `whisper_cli` and `whisper_model`;
- runtime requirement for an explicit verified asset manifest whenever STT is enabled;
- rejection of checksum mismatch;
- rejection when configured STT paths disagree with verified manifest paths;
- symlink rejection at the transcriber boundary;
- Windows CI exercising the provisioning script with local fixture files;
- launcher asset-manifest forwarding;
- correction of the Piper setup launcher path discovered during review.

### Still manual NOT RUN

- real whisper.cpp executable provisioning on the user's Windows PC;
- real Whisper model provisioning/license review;
- actual microphone capture;
- quiet-room recognition accuracy;
- classroom/noisy-room accuracy;
- edit/confirm/send behavior with a real transcript;
- Cancel/STOP during real recognition;
- long lecture transcription throughput;
- offline acceptance after provisioning.

The checksum tests do not imply acoustic acceptance.
