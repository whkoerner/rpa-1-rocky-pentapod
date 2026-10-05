# Rocky push-to-talk voice input v0

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-voice-input-v0`, stacked on Memory V0 PR #20.

## Goal

Voice Input V0 adds explicit, bounded English push-to-talk without creating a voice-to-hardware path or making microphone access continuous.

```text
user clicks Start microphone
  -> browser permission prompt / finite local capture
  -> mono 16 kHz 16-bit PCM WAV
  -> token-authenticated loopback POST
  -> strict WAV validation
  -> explicitly provisioned local whisper.cpp `whisper-cli`
  -> bounded transcript
  -> browser text box
  -> USER REVIEWS / EDITS
  -> user presses Send
  -> existing ConversationController
  -> validated Assistant pipeline
```

The transcript is never automatically submitted.

## Privacy and control

- microphone capture starts only after an explicit user click;
- recording state and elapsed time are visible;
- capture stops explicitly or automatically at the configured maximum;
- default maximum is 30 seconds and the hard configuration maximum is 60 seconds;
- browser microphone tracks are stopped after each capture;
- there is no wake word or continuous listening;
- STOP/Cancel also request cancellation of an active STT child process;
- STT receives audio and returns text only; it has no BrainController, HardwareInterface, tool authority, memory-write authority, or motor API.

## Local/offline STT boundary

The first backend is `whisper.cpp` via `whisper-cli`.

Rocky does **not** download the executable or a model. Both must be provisioned explicitly and configured with local paths:

- `stt_backend = whisper-cpp`
- `whisper_cli_path`
- `whisper_model_path`

Default is `stt_backend = disabled`.

The adapter invokes the executable with an argument list and `shell=False`. It requests ordinary JSON output, English language, no progress printing, and no timestamp text in stdout. A subprocess timeout is enforced and the process can be terminated/killed on cancellation.

## Audio contract

The loopback endpoint accepts only:

- `Content-Type: audio/wav`
- authenticated per-launch Rocky UI token;
- mono;
- 16-bit PCM;
- 16,000 Hz;
- nonempty audio;
- duration within configured limit;
- bounded request size.

The browser captures with Web Audio, downsamples locally to 16 kHz mono, and encodes PCM WAV before upload. No cloud media API is used by Rocky.

## Transcript contract

The bounded adapter accepts only a JSON object with a `transcription` array containing text rows. It concatenates bounded text, rejects empty/control-character/oversized output, and reports:

- transcript text;
- captured audio duration;
- `confidence = null`;
- `confidence_source = not_provided_by_bounded_whisper_cpp_adapter`.

Rocky does not fabricate a confidence value when the bounded adapter does not have one.

## Same assistant authority path

Voice input never calls the model directly. The browser places the transcript in the existing text box and focuses it. Only the normal Send action starts a conversation turn, which uses the same ConversationController, AssistantResponse validation, BrainController, SafetyValidator and Task/Communication path as typed input.

## Deliberate limitations

- no continuous listening;
- no wake word;
- no automatic send;
- no speaker identification;
- no background recording;
- no cloud fallback;
- no silent model download;
- no claim of recognition accuracy until real microphone testing;
- no lecture-length recording in this milestone.

Long lecture/class capture remains a later, separately consented recording workflow.
