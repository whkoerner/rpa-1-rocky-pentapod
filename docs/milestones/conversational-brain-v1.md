# Rocky Conversational Brain V1 — release and validation record

**Date:** 2026-10-01  
**Status:** V1 READY FOR USER TESTING  
**Application version:** 1.0.0  
**Distribution version:** `rpa1-csp` 0.2.0  
**Branch:** `feat/rocky-conversation-v1`  
**Base:** `e0eafc3`  
**Start:** [Windows build guide](../build-guides/conversational-brain-v1-build.md)

## What this version provides

Multi-turn typed conversation through a replaceable local Ollama provider, editable original persona, bounded session history, deterministic musical encoding, Windows speaker playback, optional Linux audio, exact terminal translation, replay/mute, and supervised cancellation. A separate DummyAI diagnostic needs no model. There is no motor, sensor, Arduino, microphone or phone requirement.

## Version history

| Stage | Location | Meaning |
|---|---|---|
| Brain v0.1 | `firmware/rocky_brain_v0_1/` | Historical Uno button/buzzer communicator; still available. |
| Brain v0.2 architecture | Commit `daf6acd`, `docs/architecture/brain-v0.2-architecture.md` | Authoritative deterministic authority/evidence boundaries. |
| Brain v0.2 implementation | Commit `e0eafc3`, `software/brain/` | Six-intent offline simulator foundation. |
| Conversational Brain V1 | Feature branch, PR and logical commits | Adds desktop text/audio capability around that foundation. |
| V2 | Roadmap below | Planned only; not duplicated source folders. |

The V1 source, tests and decision records are preserved in Git commits and a review PR. Use `git log --oneline main..feat/rocky-conversation-v1` before merge to inspect them. No release tag or VERIFIED claim is made before the manual acceptance checks. The 0.2.0 distribution number versions the combined Python package; “Conversational Brain V1” versions this application feature, not the complete physical robot.

## Executed evidence

Environment: Linux, Python 3.12.14, Node 24.19.0. No sound output device or local language model was available for listening/model-quality acceptance.

| Executed check | Result |
|---|---|
| `python -m pip install -e .` | Successful editable source installation |
| `python -m unittest discover -s language/tests -v` | 16 passed |
| `python -m unittest discover -s software/rpa_link/tests -v` | 10 passed |
| `python -m unittest discover -s software/simulation/tests -v` | 9 passed |
| `python -m unittest discover -s software/brain/tests -v` | 12 passed |
| `python -m unittest discover -s software/rocky/tests -v` | 30 passed |
| `node software/brain_web/protocol.test.js` | Passed |
| `python -m rocky audio-test --audio-backend wav` with temporary output directory | Valid WAV produced, no playback claimed |
| Interactive dummy CLI, WAV backend | Started; favorite-color statement followed by recall returned blue across separate turns |

New tests exercise UTF-8/CRC round trips, fixed-phrase compatibility, invalid candidate shapes, malformed JSON, nonzero amplitude-bounded PCM, WAV metadata, text/audio/translation integration, replay/mute, late-state cancellation, no text capability on simulator, two safety checks, no hardware in provider context, worker timeout/termination/crash, missing runtime and a real loopback HTTP fixture through a spawned worker. The HTTP fixture validates transport plumbing; it is not a language model or a response-quality benchmark.

The interactive terminal check exposed a shutdown hang caused by a background thread blocked in `input()`. Replaced interactive input with native nonblocking console polling and added a POSIX pseudoterminal regression proving `/quit` needs no extra Enter. Windows console uses `msvcrt`; Windows CI's pipe test does not substitute for manual console acceptance. The initial thread-based interactive approach was abandoned for this concrete lifecycle reason.

## Not executed / still required

- Windows standalone audio and DummyAI conversation playback have user evidence from 2026-10-03; real-model Windows conversational playback remains required. See [CV1-AUDIO-001](../test-plans/2026-10-03-conversational-brain-v1-windows-audio.md) and [CV1-DUMMY-001](../test-plans/2026-10-03-conversational-brain-v1-windows-dummy.md).
- Real Qwen3 testing now has one successful first-turn user observation, followed by a full-system crash during the second turn. Multi-turn real-model acceptance therefore remains **FAILED/UNVERIFIED**; favorite-color recall was not reached. See [CV1-QWEN-001](../test-plans/2026-10-03-conversational-brain-v1-qwen3-first-multiturn.md). The pre-test `qwen3:8b` inventory ID was `500a1f067a9f`.
- Network-disconnected real-model restart.
- Raspberry Pi installation, inference or audio.
- Arduino compile/physical test: `arduino-cli` is not installed in the execution environment; the existing GitHub compilation job is retained. Firmware was not changed.
- Fresh wheel-only installation: not supported by the pre-existing CSP YAML resource path. Use the documented source checkout.

## GitHub CI evidence

[Run 36840140172](https://github.com/whkoerner/rpa-1-rocky-pentapod/actions/runs/36840140172), testing commit `4def72b09b767f27df5311f94f9295d1aaaffb78`, passed the Windows and Ubuntu software/protocol checks and the Arduino Uno compilation check. Both Python runners use 3.12. The POSIX pseudoterminal regression is intentionally skipped on Windows; Windows pipe/worker tests passed. CI does not test physical speakers, an actual model, a disconnected network or Uno hardware.

The local `arduino-cli` limitation above remains true; compilation was performed by GitHub's existing workflow. This CI record was added in a documentation-only follow-up commit. The implementation remains exactly the tested `4def72b` source.


## Manual user evidence

| Date | Test | Environment | Result | Evidence |
|---|---|---|---|---|
| 2026-10-03 | CV1-AUDIO-001 — Windows audio diagnostic | Windows 11 Home `10.0.26300` 64-bit; Python `3.13.16`; local branch `feat/rocky-conversation-v1` at `2f6eae7` with recorded dirty-tree state | **PASS** | [Dated test record](../test-plans/2026-10-03-conversational-brain-v1-windows-audio.md). CLI requested playback and the user separately reported hearing the audio. This verifies only the build-guide `audio-test` audibility criterion. |
| 2026-10-03 | CV1-DUMMY-001 — Windows DummyAI conversation | Same Windows/Python test session; exact HEAD not re-queried during this invocation; `--provider dummy`; terminal reported `audio=winsound` | **PASS** for the executed procedure; related acceptance items remain **PARTIAL** | [Dated test record](../test-plans/2026-10-03-conversational-brain-v1-windows-dummy.md). Dummy reply, `/translate`, replay request, audible session, and clean quit were observed. User reported audio was too fast and did not prefer the current sound, but acceptable for beta testing. Ollama process state, `/auto`, mute, and unmute were not tested. |
| 2026-10-03 | CV1-MODEL-001 — Ollama model inventory | Local Ollama inventory; branch/commit not re-queried in this invocation | **PASS** for inventory capture | [Dated test record](../test-plans/2026-10-03-conversational-brain-v1-ollama-model-inventory.md). `qwen3:8b` ID `500a1f067a9f` (5.2 GB) and `gemma4:26b` ID `001e5dafc3c7` (18 GB) were reported. No inference is claimed. |
| 2026-10-03 | CV1-QWEN-001 — Qwen3 real-model multi-turn | `qwen3:8b`; exact local HEAD not re-queried during invocation | **FAIL** | [Dated test record](../test-plans/2026-10-03-conversational-brain-v1-qwen3-first-multiturn.md). First response worked and was judged good but took 30+ seconds; tones were reported too fast. Second prompt froze the laptop and the whole computer crashed; no second response was produced. |

The terminal's `PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED` receipt is not treated as acoustic evidence by itself. The PASS results above depend on separately recorded user listening observations where stated. DummyAI manual translation and the replay request path have evidence. Real-model testing has one successful first turn but failed on the second turn with a user-reported full-system crash, so multi-turn real-model acceptance is not verified. Automatic translation toggle, mute/unmute, offline, Raspberry Pi, and physical-robot checks remain open.

## Manual gate for Wyatt

Follow the [build guide's acceptance checklist](../build-guides/conversational-brain-v1-build.md#acceptance-checklist). The standalone `audio-test` audibility criterion now has linked user evidence in [CV1-AUDIO-001](../test-plans/2026-10-03-conversational-brain-v1-windows-audio.md); the remaining manual criteria stay open. Record commit (`git rev-parse HEAD`), Python version, Windows version, model ID (`ollama list`), RAM/GPU, and pass/fail observations. Change status to VERIFIED only after the relevant manual checks pass. Never copy assumed timing, sound levels or physical behavior into the results.

## V2 — five highest-value next improvements

1. Add measured offline push-to-talk speech recognition behind `SpeechInput`; feed text into the same conversation path.
2. Add a small authenticated LAN translation client with explicit binding and no public exposure by default.
3. Replace verbose text transport where possible with reviewed Chordic semantic compositions and measured prosody/listening tests; retain CT1 compatibility.
4. Add opt-in persistent memory with inspection/deletion and a clear separation between user statements and observed facts.
5. Benchmark smaller models and audio on the selected Raspberry Pi; repair installed-wheel resource packaging and validate Windows/Linux deployments before sensor-grounded expansion.

Acoustic tone recognition/classification could later use ordinary signal processing or a small trained model with a measured dataset. No conversational model is trained from scratch. Motion, environmental sensing and autonomous manipulation require separate reviewed safety work.

## Known limitations

CT1 is reversible musical text transport, not an acoustic recognition implementation or mature semantic spoken language. Long responses sound long; replies are bounded to 384 UTF-8 bytes. Real-model accuracy and personality need user testing. A prompt cannot guarantee factual truth; generated speech never becomes telemetry. Context expires after up to 12 turns. Phone/voice operation is deferred. Windows/Pi hardware acceptance remains open.
