# Test Result: CV1-AUDIO-001 — Windows audio diagnostic heard

## Configuration

- Date/time: 2026-10-03; exact execution time UNKNOWN; timezone UTC-07:00.
- Operator: project owner/user.
- Local branch: `feat/rocky-conversation-v1`.
- Local commit: `2f6eae7cb3a17087ad1cd9d35bf4196367a889b1`.
- Working tree: DIRTY. `git status --short` showed modified generated package metadata (`software/rpa1_csp.egg-info/SOURCES.txt`, `requires.txt`, `top_level.txt`) and an untracked nested `rpa-1-rocky-pentapod/` directory. No modified application source file was listed in the supplied output.
- Operating system: Microsoft Windows 11 Home, version `10.0.26300`, 64-bit.
- Python: `3.13.16`.
- Runtime: Rocky Conversational Brain V1, `audio-test` command.
- AI runtime/model: not exercised by this test. Tracked configuration named provider `local` and model `qwen3:8b`, but no Ollama model ID was collected and no real-model inference is claimed.
- Audio backend: tracked setting `auto`; the implementation at the tested commit maps `auto` to Windows `winsound` on `win32`.
- Digital volume: `0.12`.
- Audio speed/timing: no user-configurable speed setting exists in the tested `rocky.json`. The registered CSP path uses the versioned phonology timing: 300 ms phrase header, 150 ms rest after the header, 140 ms per literal note, and 35 ms inter-note gap.
- Translation mode: not exercised.
- Audio output device model: UNKNOWN.
- Hardware revision: N/A for this computer-only audio diagnostic.
- Firmware revision: N/A.
- CAD/electronics revision: N/A.
- Test-plan source: `docs/build-guides/conversational-brain-v1-build.md`, Acceptance checklist.
- Safety controls/exclusion zone: no actuators or physical robot hardware were involved. System speaker volume setting was not recorded.

## Requirement under test

Primary acceptance criterion:

- Conversational Brain V1 manual acceptance: **`audio-test` is actually heard**, from the build guide acceptance checklist.

No numbered v0.2 requirement is marked VERIFIED by this listening test alone. It is supporting evidence for the desktop musical-output path, but it does not by itself verify real-model conversation, translation, offline operation, or the broader interaction requirements.

## Procedure deviations

- The test was executed from a dirty working tree rather than a clean checkout. The supplied status output identified only generated package metadata plus an untracked nested repository directory; because the tree was not clean, this record preserves both the HEAD commit and dirty-state evidence rather than treating the commit as a byte-for-byte description of the entire local directory.
- Exact execution time was not captured.
- Speaker/headphone make, output-device selection, and system volume were not captured.
- No model, translation, network-isolation, or conversation behavior was exercised.

## Raw evidence

### Exact command

```powershell
git branch --show-current; git rev-parse HEAD; git status --short; Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture; .\.venv-rocky\Scripts\python.exe --version; Get-Content software\rocky\config\rocky.json; .\.venv-rocky\Scripts\python.exe -m rocky audio-test
```

### Observed terminal output

The Windows account name in the WAV path is redacted because it is not needed for engineering interpretation.

```text
feat/rocky-conversation-v1
2f6eae7cb3a17087ad1cd9d35bf4196367a889b1
 M software/rpa1_csp.egg-info/SOURCES.txt
 M software/rpa1_csp.egg-info/requires.txt
 M software/rpa1_csp.egg-info/top_level.txt
?? rpa-1-rocky-pentapod/

Python 3.13.16
OK: PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED
WAV: C:\Users\<REDACTED_USER>\.rpa1\conversation-v1\last-response.wav
Caption                    Version      OSArchitecture
-------                    -------      --------------
Microsoft Windows 11 Home  10.0.26300   64-bit
{
  "provider": "local",
  "model": "qwen3:8b",
  "port": 11434,
  "timeout": 120,
  "audio_backend": "auto",
  "volume": 0.12
}
```

### User-reported listening observation

> “I heard the audio.”

This observation is recorded only as evidence that the operator heard the diagnostic playback. It does not establish model inference, speech recognition, acoustic decoding, response quality, or offline operation.

## Results

| Trial | Input | Expected | Measured | Result | Notes |
|---:|---|---|---|---|---|
| 1 | `.\.venv-rocky\Scripts\python.exe -m rocky audio-test` | Build-guide criterion: the audio diagnostic is actually heard. | CLI reported `PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED`, wrote `last-response.wav`, and the user separately reported hearing the audio. | **PASS** | The software receipt alone would not prove audibility; the separate user listening report supplies that observation. |

## Faults, interventions, and near misses

No runtime error was shown for the audio diagnostic.

The message `PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED` is intentionally conservative and is not treated as a failure. It records that software requested playback without claiming acoustic sensing. The user's separate listening observation is the evidence used for the manual audibility criterion.

The dirty working tree is retained as a test-condition limitation. No cleanup or code repair is performed by this documentation change.

## Conclusion

- Overall result: **PASS**
- Supported claims:
  - On the supplied Windows 11 / Python 3.13.16 environment, the V1 `audio-test` reached the playback-request path and produced a WAV path.
  - The user reported actually hearing the diagnostic audio.
  - The build-guide acceptance criterion **“`audio-test` is actually heard”** is satisfied for this recorded test environment and local state.
- Claims not supported:
  - Real `qwen3:8b` inference or any other real-model conversation.
  - Ollama model identity, quantization, latency, or response quality.
  - DummyAI conversation behavior or translation.
  - Replay, mute/unmute, stop/reset, or favorite-color recall.
  - Internet-disconnected operation.
  - Raspberry Pi or physical-robot audio.
  - Calibrated loudness, sound level, or human learnability of Chordic.
- Required changes: none from this test result.
- Next cheapest experiment: run the interactive DummyAI acceptance check and verify response text, `/translate`, `/replay`, and audible playback without Ollama.
