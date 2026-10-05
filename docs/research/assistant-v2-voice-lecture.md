# Assistant V2 voice, speech-input, and lecture feasibility

**Research date:** 2026-10-05  
**Status:** architecture research only; no new runtime dependency installed

This note intentionally follows the stable Assistant V2 correctness milestone. It does not claim listening quality, transcription accuracy, or hardware performance that was not measured on Rocky's Windows machine.

## English translation TTS

### Current baseline

Windows System.Speech remains the known-working offline baseline. It already produces a local WAV whose duration can be measured before playback, fits the active-overlap scheduler, and has been heard successfully in earlier manual acceptance. It is functional but may sound robotic.

### Piper candidate

The maintained Piper line is now the Open Home Foundation project `OHF-Voice/piper1-gpl`; the earlier `rhasspy/piper` repository is archived and points to it. Current Piper provides local neural TTS, a Python API, WAV synthesis, streaming output, voice selection, and speed/variation controls.

Sources:
- https://github.com/OHF-Voice/piper1-gpl
- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
- https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md
- https://github.com/rhasspy/piper

**Recommended experiment:** keep Piper in an optional voice sidecar/environment, provision a reviewed voice model explicitly, record the engine/model/checksum/license in a manifest, synthesize to a complete WAV first, measure exact duration, then hand the WAV to Rocky's existing cancellable playback/overlap layer. Do not add silent downloads or cloud fallback.

**License note:** the current engine repository is GPL-3.0. Distribution implications and each chosen voice model's own license must be reviewed before packaging. This note is not a legal conclusion.

## Chordic acoustic experiments

WORLD is an established speech analysis/manipulation/resynthesis system that exposes F0, spectral envelope, and aperiodicity. PyWORLD provides a Python wrapper and synthesis API. Praat-Parselmouth exposes Praat analysis/manipulation from Python and installs on Windows/Linux/macOS.

Sources:
- https://github.com/mmorise/World
- https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder
- https://parselmouth.readthedocs.io/
- https://github.com/YannickJadoul/Parselmouth

**Recommended use:** experimental sidecar only. Feed deterministic EXP-003 timing/contours into controlled F0/formant/timbre experiments without changing token semantics. Compare generated WAVs against `vocal-v1` with objective duration/frequency tests, then require human listening before any “more natural” claim.

## Bounded push-to-talk STT

Two strong local candidates remain practical:

- `whisper.cpp`: C/C++ implementation, Windows/Linux and other platforms, CPU/GPU paths, quantization, local model files, and offline transcription.
- `faster-whisper`: Python/CTranslate2 implementation intended for efficient Whisper inference with quantization support.

Sources:
- https://github.com/ggml-org/whisper.cpp
- https://github.com/SYSTRAN/faster-whisper

**First safe milestone:** push-to-talk only. Record a finite microphone clip with an obvious recording indicator; stop/cancel remains responsive; save/transcribe locally; display the transcript and confidence/diagnostics when available; require an explicit user send/edit step or feed the final transcript through exactly the same validated ConversationController path as typed input. There is no voice-to-motor path.

For Rocky's main Windows install, do not place a large STT stack in the core environment yet. A sidecar executable or separate voice environment keeps failures and model weights isolated.

## Lecture/class mode feasibility

A 2 h 40 min lecture is **technically practical** as deferred processing. Duration is 9,600 seconds.

Approximate audio storage:
- mono 16 kHz, 16-bit PCM WAV: about 307 MB;
- 24 kbps compressed audio: about 28.8 MB;
- 32 kbps compressed audio: about 38.4 MB;
- 48 kbps compressed audio: about 57.6 MB.

These are codec-rate/storage estimates, not measured Rocky recordings.

### Recommended budget architecture

```text
explicit RECORD start
  -> local microphone capture
  -> visible recording indicator + elapsed time
  -> compressed local audio + timestamps
  -> explicit STOP
  -> transfer/use PC when convenient
  -> local Whisper-family transcription
  -> timestamped raw transcript
  -> cleanup/sectioning
  -> Assistant V2 study-mode detail pipeline
  -> outline / concepts / formulas / examples / flashcards / questions
  -> optional explicitly authorized Google Drive/Docs export later
```

Deferred PC transcription is preferred over forcing real-time onboard transcription. It reduces onboard compute, heat, power draw, and hardware cost while preserving the long-term workflow.

### NOT RUN / unknown

- transcription real-time factor on the user's current Windows PC;
- model size/accuracy tradeoff on the user's hardware;
- microphone placement/noise performance in a real classroom;
- battery consumption on a future body;
- 2 h 40 min end-to-end capture;
- Piper voice quality;
- Piper cancellation behavior in a Rocky sidecar;
- WORLD/PyWORLD/Parselmouth subjective Chordic naturalness.

## Privacy/permission boundary

Lecture recording must be explicit and visibly indicated. Rocky should never enter a hidden continuous-recording mode by default. Classroom/institution/instructor consent rules vary; technical capability must not be treated as permission.

## Recommended next experimental sequence

1. Keep System.Speech as production baseline.
2. Add a separate optional voice sidecar manifest/provisioning design.
3. Prototype Piper-to-WAV offline and compare measured duration/cancellation behavior.
4. Prototype finite-file Whisper transcription before microphone integration.
5. Add push-to-talk only after file transcription is deterministic and cancellable.
6. Prototype long lecture capture/deferred transcription after short recordings are stable.
