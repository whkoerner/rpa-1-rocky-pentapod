# Rocky Neural English Voice V0 — Piper Sidecar

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-piper-voice-v0`, stacked on Lecture Notes V0 PR #25.

## Goal

Improve the naturalness of Rocky's audible English translation without destabilizing the working System.Speech path or installing neural-TTS dependencies into the core Rocky environment.

Windows System.Speech remains the default.

Piper is an explicit opt-in sidecar.

## Why a persistent sidecar

The current Open Home Foundation Piper documentation supports loading a local ONNX voice through the Python API and writing a complete WAV with `PiperVoice.synthesize_wav`.

Piper's own CLI documentation notes that repeatedly invoking the CLI is slower because it reloads the model for each call and recommends a persistent server for repeated use.

References reviewed 2026-10-05:

- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md
- https://pypi.org/project/piper-tts/

PyPI reported `piper-tts 1.8.0` released 2026-09-04 with Windows x86-64 wheels and Python 3.12/3.13 compatibility.

## Architecture

```text
validated spoken_text
  -> DesktopHardware active-translation scheduler
  -> PiperSidecarSpeechRenderer
  -> token-authenticated HTTP to 127.0.0.1:<port>
  -> separate .venv-rocky-piper process
  -> pre-provisioned Piper ONNX voice loaded once
  -> complete bounded WAV
  -> exact duration measurement
  -> same WAV cached for scheduled playback
```

Rocky never imports Piper in the core runtime.

The sidecar:

- binds only to numeric loopback `127.0.0.1`;
- requires a local token for status and synthesis;
- loads one pre-provisioned ONNX model once;
- never downloads a voice;
- accepts bounded text/speed/volume only;
- serializes model synthesis;
- returns bounded mono PCM WAV.

## Active translation compatibility

The scheduler needs English duration before deciding when English should begin.

For Piper:

1. `estimate_duration_seconds(spoken_text)` asks the sidecar for a complete WAV;
2. Rocky validates the WAV and measures its real frame duration;
3. the WAV is cached with the exact text and tuning signature;
4. the normal overlap scheduler computes the English start delay;
5. `start(...)` reuses that exact cached WAV rather than synthesizing again;
6. playback remains cancellable.

This means English timing is based on the actual audio that will play.

## Contextual delivery

Piper V0 retains application-owned deterministic prosody classification.

The categories remain:

- question;
- excitement;
- reassurance;
- technical;
- neutral.

Piper V0 maps these categories to bounded `length_scale` and volume changes. User rate/volume offsets are also bounded.

Piper V0 does **not** pretend to implement deterministic pitch shifting. Non-zero pitch offset is rejected explicitly instead of being silently ignored.

Piper's neural model and punctuation may still produce its own natural pitch/prosody; that must be judged by listening.

## Playback

On Windows, the returned WAV is played by a separate PowerShell/SoundPlayer process so English can overlap Chordic without stealing Rocky's Chordic audio player's slot.

On other platforms, V0 can use `ffplay` if explicitly present. Windows remains the primary accepted platform.

Cancellation terminates the playback process and removes the temporary WAV.

## Configuration

New settings:

- `translation_voice_backend = "system-speech"` (default)
- `piper_sidecar_port = 5055`
- `piper_sidecar_token_path = ""`
- `piper_sidecar_timeout_seconds = 30`

Select `piper-sidecar` only after the separate sidecar is provisioned.

## Explicit provisioning

Windows launcher menu option:

**15 — Setup optional Piper neural voice sidecar**

This invokes `scripts/Setup-Piper.ps1`.

The script:

- creates/reuses a separate `.venv-rocky-piper`;
- installs exactly `piper-tts==1.8.0`;
- verifies the installed package version;
- creates/reuses a random local sidecar token;
- does **not** download a voice;
- does **not** change Rocky settings;
- does **not** start a service.

The user must explicitly choose a voice, review its model license, provision its ONNX/config files, and add the ONNX checksum to Rocky's editable asset manifest.

The sidecar is then launched explicitly with `scripts/rocky_piper_sidecar.py`.

## Licensing

The Piper engine/package currently reports GPL-3.0-or-later. Voice models may have separate licenses. Packaging/distribution must review both before bundling anything.

No voice model is included in this repository.

## Manual acceptance required

Automated waveform/protocol tests cannot establish naturalness.

Still NOT RUN:

- actual `piper-tts==1.8.0` provisioning on the user's Windows PC;
- real selected voice model;
- human comparison against System.Speech;
- question/excitement/reassurance/technical delivery by ear;
- active-overlap listening;
- cancellation during real neural playback;
- CPU/RAM synthesis cost;
- long-session stability.
