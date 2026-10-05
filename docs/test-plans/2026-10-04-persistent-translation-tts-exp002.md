# Persistent translation voice + EXP-002 desktop integration — 2026-10-04

Status: **IMPLEMENTED ON DRAFT PR #14 / AUTOMATED CI IN PROGRESS / SUBJECTIVE WINDOWS LISTENING NOT RUN**

Branch: `feat/persistent-translation-tts-exp002`  
Starting Rocky SHA: `0b14ee0ce3cf32b200d27672a4e81be5833f0b5d`  
Chordial authority pin: `whkoerner/chordic-language@56347cf73111d2d708b5919cd01b563826795108`  
Draft PR: #14, **do not merge before manual Windows acceptance**.

## Hypothesis

The desktop's long free-form tone delays are caused by arbitrary English falling into CT2 literal/fallback encoding. Translation also behaved as a one-shot/display option rather than a persistent listening mode. A production-selectable EXP-002 runtime profile should reduce routine tonal duration without changing the playback multiplier, while a separate local English TTS path can make decoded English audible when the user explicitly enables persistent translation.

The language model must remain data-only. It does not receive an audio object, hardware object, SSML authority, or a way to bypass Brain/SafetyValidator.

## Implementation

### Persistent translation mode

- `/translate on` validates that a local voice is available, then enables a session-persistent mode.
- While enabled, every subsequent validated Rocky reply displays decoded English and queues local spoken English after the Chordic tones.
- `/translate off` disables the mode and cancels current/pending English voice output.
- `/translate status` reports mode and voice state.
- Bare `/translate` retains the prior useful behavior: decode the last response once.
- `/auto` remains a legacy display-only toggle and does not silently become voice mode.
- `/clear` clears history and last-response state but intentionally **does not disable persistent translation**. Translation is a session preference, not conversation memory.
- `/replay` replays the tones and, only while persistent translation is on, requeues the corresponding English voice.
- `/mute`, `/cancel`, and `/stop` cancel both tone and voice playback. `/reset` recovers the stopped backend without replaying cancelled audio.

### Local English TTS

Backend: Windows `System.Speech.Synthesis.SpeechSynthesizer`, invoked locally through `powershell.exe`.

Properties:
- uses enabled voices already installed in Windows;
- no cloud TTS endpoint;
- no network fallback;
- no model/voice download performed by Rocky;
- `/translate on` fails readably if no enabled local Windows voice is available;
- validated English text is escaped before insertion into SSML;
- only application-owned, finite prosody profiles can emit SSML controls;
- cancellation terminates the local speech process;
- speech failures surface through the same backend polling path and latch stop rather than reporting false success.

No new TTS Python package is required. If Windows has no enabled local speech voice, installation/enabling must be performed explicitly by the operator in Windows; Rocky will not silently download one.

Deterministic delivery classes:
- question
- excitement
- reassurance/support
- technical
- neutral

These tests verify classification/control generation and injection resistance. They **do not prove that a voice sounds natural**.

### EXP-002 production path

`Chordic-Language` remains authoritative. Rocky now carries a pinned runtime export containing the authoritative candidate and benchmark data from Chordic main at `56347cf...`.

Profiles:
- `/language exp002` — compact EXP-002 composition, now the default desktop conversation profile.
- `/language ct2` — legacy/compatibility CT2.
- `/language ct1` — legacy CT1.

Registered benchmark meanings use the authoritative token sequences directly. Free-form text is segmented into reusable known EXP-002 concepts where possible. Unsupported spans are explicitly carried as exact CT2 fallback; they are not silently assigned a new meaning. The adapter verifies exact reconstruction of the original validated text.

No benchmark sentence receives an opaque whole-sentence code.

### Personality and safety

The provider no longer identifies Rocky in ordinary conversation as "a desktop conversation program." The immutable system instructions instead preserve the capability facts: Rocky has no physical devices, sensor evidence, measurements, repair capability, action tools, or direct hardware-control authority in this desktop conversation unless verified application evidence exists.

The profile keeps third-person Rocky, terse/telegraphic speech, warmth, curiosity, loyalty, playfulness, technical capability, and the engineering/electronics/mathematics/science/space/music/learning/problem-solving interests. `speaking_style` is 495 characters, under the 500-character schema limit.

The architectural authority boundary remains:

`AIProvider -> validated response/request -> BrainController -> SafetyValidator -> Task/Communication -> hardware/audio adapter`

## Timing evidence

All tonal figures use the existing **3x playback multiplier**; no speed reduction was used to manufacture the result.

| Population | CT2 baseline | EXP-002 | Result |
| --- | ---: | ---: | --- |
| Normal benchmark mean (17 cases) | 8.030 s | 6.794 s | improved |
| Normal benchmark maximum | 10.875 s | 8.400 s | improved |
| Normal cases <= 10 s | 94.1% (16/17) | 100% (17/17) | target met |
| Common-expression mean | 4.421 s | 3.738 s | improved |
| Spoken English duration | N/A | **NOT RUN manually** | measured at runtime after actual voice playback |
| Combined tones + spoken English | N/A | **NOT RUN manually** | reported separately |

The prior manually observed arbitrary-CT2 examples (~14.07 s, 50.84 s, 35.06 s, 24.32 s) remain valid evidence for why a compositional production path is needed. They are not EXP-002 benchmark durations.

## Automated tests added

Focused regressions cover:
- runtime export pin and exact token-pattern collision freedom;
- protected yes/no, question/negation, help/stop, good/bad distinctions;
- every registered benchmark meaning exact round-trip;
- free-form composition plus explicit exact CT2 fallback;
- normal benchmark 6.794 s mean / 8.400 s max / zero >10 s at unchanged 3x;
- CT2 remains selectable;
- question/excitement/reassurance/technical/neutral prosody classification;
- model text cannot inject SSML/audio tags;
- persistent translation across two turns without reenabling;
- translation off prevents later voice invocation;
- translation status and `/clear` persistence;
- mute/unmute/cancel/stop/reset/replay voice behavior;
- voice errors surface and stop is latched;
- language profile switching.

Existing Brain v0.2, provider, safety, Dummy diagnostic, check-no-audio, CT1/CT2, browser protocol, launcher, and Arduino coverage remain required.

## Failed CI and debugging ledger for PR #14

| Run | Head | Observation | Root cause / action |
| --- | --- | --- | --- |
| #51 | `8e97a90...` | All four software matrix cells reached Rocky suite then failed; Arduino passed | First full integration run. New focused failures not yet isolated. |
| #52 | `191906a...` | Same Rocky-suite failure across Windows/Linux 3.12/3.13; Arduino passed | EXP-002 regex corrected, but aggregate failure remained. |
| #53 | `116e412...` | New focused EXP-002, prosody, and persistent-translation groups passed; aggregate Rocky discovery failed | Established that new functional groups themselves were green. |
| #54 | `33ac1dc...` | Every legacy Rocky test module also passed independently; aggregate discovery failed | Narrowed to suite/discovery process, not one legacy module. |
| #55-#57 | diagnostic heads | Full explicit module order, root individual discovery, and root cumulative module order passed | Narrowed further to the custom discovery wrapper. |
| #58 | `efeed07...` | Standard `python -m unittest discover` and a fresh `unittest.TestLoader()` pass where the shared `unittest.defaultTestLoader` wrapper fails | Root cause: reusable singleton loader state in custom CI wrapper. |
| next clean run | `5f11a2e...` + documentation | **PENDING at time of this commit** | Workflow restored to normal shape and uses a fresh `unittest.TestLoader()`; temporary bisection steps removed. |

Failed runs are intentionally retained as engineering evidence. Do not rewrite or hide them.

## Manual Windows acceptance — exact operator steps

All subjective sound rows begin **NOT RUN**. Do not convert them to PASS from unit tests or CI.

1. Pull/checkout PR #14 branch in the current `rpa-1-rocky-pentapod` checkout. Confirm the desktop shortcut points to this checkout, not the old `-v11` directory.
2. Launch with the normal desktop shortcut or `Rocky.bat`. Confirm the environment line points inside the current checkout's `.venv-rocky\Scripts\python.exe`.
3. Start the real local model using the normal launcher path.
4. Enter `/status`. Confirm `motion=DISABLED`, `language=exp002`, and translation is off.
5. Enter `/language exp002`, then `/translate on`. Confirm Rocky reports persistent translation ON rather than only translating one prior line.
6. Ask: **"What is your name and are we friends?"** Confirm the reply uses third-person Rocky style. Confirm English text is shown and an English voice is actually audible.
7. Ask a second unrelated question without repeating `/translate on`. Confirm English is again displayed and spoken. This is the persistence acceptance check.
8. Ask: **"Rocky think yes. Question difficult?"** Judge whether the English voice has sensible question delivery. **SUBJECTIVE: NOT RUN until user confirms.**
9. Ask for/exercise an excited reply such as **"Say: Amaze amaze amaze!"** Judge excited delivery. **SUBJECTIVE: NOT RUN.**
10. Say something sad or ask for reassurance. Confirm a response in the desired style (for example, Rocky here / we team) and judge whether delivery is softer/supportive. **SUBJECTIVE: NOT RUN.**
11. Ask: **"What does a derivative measure?"** Judge calm/direct technical delivery. **SUBJECTIVE: NOT RUN.**
12. After any reply, note the printed Chordic estimated duration. After English speech completes, note the measured spoken-English duration and combined duration. Keep these as three separate metrics.
13. Enter `/language ct2`, ask a routine question, record the Chordic duration; switch back with `/language exp002`, ask an equivalent routine question, and compare. Do not change `/speed` for this comparison.
14. Enter `/replay`. Confirm tones replay and, because translation remains on, the current English voice replays.
15. Enter `/mute`; send/replay a response. Confirm neither tones nor spoken English is audible. Enter `/unmute`; confirm future audio returns.
16. Start a response and enter `/cancel` while audio/voice is pending or playing. Confirm pending/current audio stops promptly and does not return later.
17. Enter `/stop`. Confirm audio stops and stop latches. Enter `/reset`. Confirm normal operation recovers and cancelled/old speech is not replayed.
18. Enter `/clear`, then `/translate status`. Confirm history is cleared but persistent translation remains ON by design. Ask another question and confirm English still displays/speaks.
19. Enter `/translate off`. Ask another question. Confirm Chordic tones still play but automatic English display/voice no longer occurs.
20. Disconnect the PC from the internet. With the already-installed local model and Windows voice, repeat a short `/language exp002` + `/translate on` conversation. Confirm both tones and English speech still work locally. Do not install anything during this offline check.
21. Enter `/quit` cleanly.

## Manual acceptance state

- Desktop shortcut current-checkout verification: **NOT RUN for PR #14**
- Real local model with this branch: **NOT RUN**
- Persistent translation over multiple real-model questions: **NOT RUN**
- Audible English TTS: **NOT RUN**
- Question inflection: **NOT RUN**
- Excited inflection: **NOT RUN**
- Supportive/soft inflection: **NOT RUN**
- Technical delivery: **NOT RUN**
- CT2-vs-EXP-002 real conversation timing comparison: **NOT RUN**
- Replay/mute/unmute/cancel/stop/reset with real Windows speech: **NOT RUN**
- Offline local TTS with network disconnected: **NOT RUN**
- Raspberry Pi / physical robot / microphone recognition: **NOT RUN / outside this iteration**

## Known limitations / audit targets

- Windows voice naturalness depends on the locally installed System.Speech voice. Unit tests cannot establish acoustic quality.
- Current config uses the Windows default enabled voice; the renderer supports an explicit voice name internally but no user-facing voice-selection command/config is exposed yet.
- Free-form EXP-002 coverage is intentionally incomplete. Unsupported spans fall back exactly to CT2, so highly technical/novel replies can still exceed the 4-10 second routine target.
- EXP-002 runtime aliases must not drift into a second independent vocabulary source; Astra should audit that all aliases resolve only to token IDs present in the pinned authoritative Chordic export.
- Runtime scheduling uses Chordic estimated duration to delay English TTS. Manual Windows acceptance should verify that English does not overlap the tail of actual tone playback on the real device.
- Acoustic recognition/noise tolerance of EXP-002 is still unvalidated.
