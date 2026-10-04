# Test Result: CV1-DUMMY-001 — Windows DummyAI conversation, translation, and replay

## Configuration

- Date/time: 2026-10-03; exact execution time UNKNOWN; timezone UTC-07:00.
- Operator: project owner/user.
- Local branch: last directly observed immediately before this test was `feat/rocky-conversation-v1`.
- Local commit: exact HEAD was not re-queried during this invocation. The immediately preceding environment capture in the same test session showed `2f6eae7cb3a17087ad1cd9d35bf4196367a889b1`; do not treat later GitHub documentation commits as the locally executed version.
- Working tree: exact status was not re-queried during this invocation. The immediately preceding capture showed a dirty tree containing modified generated package metadata and an untracked nested `rpa-1-rocky-pentapod/` directory.
- Operating system: last directly observed immediately before this test was Microsoft Windows 11 Home, version `10.0.26300`, 64-bit.
- Python: last directly observed immediately before this test was `3.13.16`.
- Runtime: Rocky Conversational Brain V1.
- Provider: explicitly overridden to `dummy` on the command line.
- Model/model ID: not exercised; DummyAI is deterministic test infrastructure, not a real language model. Ollama process state was not recorded.
- Audio backend: terminal reported `winsound`.
- Digital volume: no per-run override was supplied; tracked configuration immediately before the test used `0.12`.
- Audio speed/timing: no user-configurable speed setting was exercised. This noncanonical DummyAI reply uses the CT1 conversation-audio path in the tested V1 implementation, whose symbols are rendered as 65 ms chords with 15 ms rests, extended to 35 ms after every eighth byte.
- Translation mode: automatic English display remained on by default; `/translate` was also exercised manually. `/auto` was not tested.
- Audio output device model: UNKNOWN.
- Hardware/firmware/CAD/electronics revision: N/A for this computer-only test.
- Test-plan source: `docs/build-guides/conversational-brain-v1-build.md`, first conversation and acceptance checklist.
- Safety controls/exclusion zone: no actuators or physical robot hardware were involved.

## Requirement under test

Relevant Conversational Brain V1 acceptance criteria:

- DummyAI creates audio/translation without Ollama running.
- Translation and replay behavior work as documented.

This session demonstrates DummyAI response generation, English display, manual `/translate`, and the replay request path. It does **not** prove that Ollama was not running because process state was not captured. It also does not complete the broader checklist item covering translation toggle, replay, mute, and unmute because `/auto`, `/mute`, and `/unmute` were not exercised.

No real-model requirement is tested by DummyAI.

## Procedure deviations

- Exact branch/HEAD, working-tree status, OS, and Python version were not re-queried in this invocation. The values above are carried only as the immediately preceding observed environment from the same test session and are labeled accordingly.
- Ollama process state was not captured, so “without Ollama running” remains unverified.
- `/auto`, `/mute`, and `/unmute` were not tested.
- No timing measurement was made; “too fast” below is a subjective listening observation, not a measured duration failure.

## Raw evidence

### Exact launch command

```powershell
.\.venv-rocky\Scripts\python.exe -m rocky --provider dummy
```

### Exact interactive inputs

```text
hello rocky
/translate
/replay
/quit
```

### Observed terminal output

The Windows account name and user-specific path prefix are redacted because they are unnecessary to interpret the test.

```text
Rocky Conversational Brain V1 | provider=dummy | audio=winsound
Local output: C:\Users\<REDACTED_USER>\.rpa1\conversation-v1
Type a message to Rocky. Commands:
/help       show commands             /status     brain and backend status
/translate  show last English reply   /auto       toggle automatic translation
/replay     play last reply again     /mute       stop and mute playback
/unmute     enable future playback    /clear      forget session history
/model      show provider/model       /offline    explain local-only operation
/cancel     cancel pending inference  /stop       cancel, silence and latch stop
/reset      operator reset (no replay) /quit      exit
Ctrl+C stops and exits. /listen is reserved for V2; typed input always works.
> hello rocky
Thinking locally... /cancel, /stop and /status remain available.

Rocky: Hello! I am Rocky in dummy test mode. What would you like to build together?
Audio: PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED
> /translate
Rocky: Hello! I am Rocky in dummy test mode. What would you like to build together?
> /replay
OK: PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED
> /quit
```

### User-reported listening and quality observations

> “Everything sounded fine, the noises were a little too fast. Im not very fond of the sound but its good for a beta test”

Interpretation of that report:

- The session produced audible output acceptable for beta testing.
- The operator perceived the musical response as too fast.
- The operator did not prefer the current sound/timbre/style.
- These are subjective design observations, not evidence of a runtime fault.
- The comment applies to the session overall; it does not independently timestamp or isolate the first playback versus replay.

## Results

| Trial | Input | Expected | Observed | Result | Notes |
|---:|---|---|---|---|---|
| 1 | Launch with `--provider dummy` | Dummy diagnostic starts without requiring real-model inference. | Banner reported `provider=dummy`, `audio=winsound`; CLI accepted input. | **PASS** | This does not establish Ollama was stopped. |
| 2 | `hello rocky` | Deterministic DummyAI reply is accepted, displayed, and playback requested. | Exact reply: `Hello! I am Rocky in dummy test mode. What would you like to build together?`; terminal reported `PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED`; user reported the session sounded fine overall. | **PASS** | User listening report supplies audibility evidence for the session; software receipt alone would not. |
| 3 | `/translate` | Last accepted English reply is displayed exactly. | Same DummyAI reply was displayed. | **PASS** | Tests the manual translation command, not the `/auto` toggle. |
| 4 | `/replay` | Last accepted reply is sent to playback again. | Terminal reported `OK: PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED`. | **PASS (software path)** | User reported audible output overall, but did not separately identify the replay sound as a distinct observation. |
| 5 | `/quit` | Client exits cleanly to PowerShell. | PowerShell prompt returned with no visible error. | **PASS** | — |

## Faults, interventions, and near misses

No runtime error was visible in the supplied terminal evidence.

The software messages `PLAYBACK_REQUESTED_NOT_ACOUSTICALLY_VERIFIED` are not treated as proof of acoustic output by themselves. The separate user report supports that audio was heard during the session.

The user reported that the noises were “a little too fast” and that they were “not very fond of the sound,” while also calling it acceptable for a beta test. Preserve this as a design-quality observation for later Chordic/audio iteration. No playback-speed or timbre change is made by this documentation-only test record.

## Conclusion

- Overall test result: **PASS**
- Supported claims:
  - The Windows V1 client launched with the DummyAI provider and `winsound`.
  - DummyAI returned the exact displayed deterministic test response.
  - Audio playback was requested for the response and the user reported audible output during the session.
  - `/translate` displayed the last accepted English reply exactly.
  - `/replay` reached the playback-request path.
  - `/quit` returned cleanly to PowerShell.
- Acceptance status:
  - “DummyAI creates audio/translation without Ollama running”: **PARTIAL**, because DummyAI audio/translation worked but Ollama process state was not recorded.
  - “Translation toggle, replay, mute and unmute work”: **PARTIAL**, because `/translate` and replay were exercised, but `/auto`, mute, and unmute were not.
- Claims not supported:
  - Real local-model conversation or response quality.
  - Real-model memory/favorite-color recall.
  - Ollama model identity or model ID.
  - Proof that Ollama was stopped.
  - Network-disconnected operation.
  - Independent acoustic confirmation of replay distinct from the initial sound.
  - Mute/unmute, automatic translation toggle, stop/reset, Raspberry Pi, or physical-robot behavior.
  - A measured audio-speed defect; the speed comment is subjective user feedback.
- Required changes: none authorized by this test-record task. Retain the speed/sound-style feedback for a separately authorized audio/language design change.
- Next cheapest experiment: exercise the real local model with the build-guide multi-turn conversation and capture model identity plus exact replies.
