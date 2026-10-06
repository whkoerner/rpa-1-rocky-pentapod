# Rocky local STT provisioning V0

**Date:** 2026-10-05  
**Status:** Draft implementation stacked on the real-model benchmark v0.2 branch.

## Goal

Move Voice Input V0 from an adapter-only foundation toward a provisionable, auditable Windows setup without bundling whisper.cpp or model weights into Git.

The recognition boundary remains:

```text
explicit push-to-talk / finalized lecture PCM chunk
  -> bounded 16 kHz mono 16-bit WAV
  -> WhisperCppTranscriber
  -> checksum-verified local whisper-cli + local GGML model
  -> bounded transcript text
  -> user review for push-to-talk OR deferred lecture transcript
```

Speech-to-text has no BrainController, hardware, gait, motor, connected-mode, shell, or arbitrary filesystem authority.

## Explicit provisioning

Windows launcher option **16 — Configure local whisper.cpp voice input** runs `scripts/Setup-WhisperCpp.ps1`.

The setup helper:

- never downloads whisper.cpp;
- never downloads a Whisper model;
- requires the user to select an already obtained/reviewed `whisper-cli` executable and model file;
- rejects directories and link/reparse targets;
- computes SHA-256 for both files;
- writes the exact paths and hashes to the editable `~/.rpa1/settings/assets.json` entries `whisper_cli` and `whisper_model`;
- only after the manifest is written, enables `stt_backend=whisper-cpp` and writes the same paths to the user's Rocky settings.

The manifest is written before enabling STT. A partial failure therefore leaves either STT disabled or an already populated manifest rather than enabled STT pointing at unpinned assets.

## Runtime verification

When `stt_backend=whisper-cpp`, `WhisperCppTranscriber.from_settings` now requires an explicit asset manifest.

For both `whisper_cli` and `whisper_model`, Rocky requires:

- exactly one file entry with the expected asset ID;
- a non-empty path and lowercase SHA-256;
- a real non-symlink file;
- current file SHA-256 equal to the manifest value;
- configured Rocky path resolving to the same file as the manifest path.

A checksum or path mismatch fails closed before recognition starts.

The Windows launcher supplies the editable asset manifest to Rocky commands automatically when present. Direct CLI users who enable whisper.cpp must also provide `--asset-manifest`.

## Execution boundary

The existing transcriber behavior is preserved:

- `subprocess.Popen` receives a fixed argv list with `shell=False`;
- input is a temporary bounded WAV;
- language is explicitly English for V0;
- output must be bounded strict JSON;
- no confidence value is invented;
- cancellation terminates only the active recognizer child;
- model files remain outside Git.

## Separate evidence categories

Automated checksum/path/process tests establish provisioning and software-boundary behavior only.

They do **not** establish:

- microphone capture on the user's PC;
- recognition accuracy;
- classroom-noise performance;
- a particular Whisper model's quality or license;
- CPU/GPU speed;
- long-lecture transcription runtime.

Those remain manual acceptance items.
