# Post-merge Windows acoustic feedback and next iteration — 2026-10-04

Baseline: merged PR #14 at `2c7573e12326a8de28c2bc399d9787f95f1c75e7`.

This document preserves operator-observed Windows evidence and the next design requirements. It intentionally separates **functional audibility** from **subjective acoustic quality**.

## Manual evidence supplied by operator

The operator launched Rocky from the current Windows checkout and reported:

- spoken English translation was actually audible;
- Chordic pitch playback was actually audible;
- the feature worked across multiple conversational turns;
- `/replay` replayed the prior response and the English voice completed;
- `/speed 2` and `/speed 1` changed subsequent/replayed tonal timing;
- both the human voice and Chordic tones are still acoustically "off a bit" and require tuning;
- desired near-term change: spoken English should play **over** the Chordic response instead of waiting until the Chordic response ends.

The supplied terminal transcript showed **CT2**, so these observations are valid CT2 desktop acoustic evidence. They are **not** evidence that EXP-002 free-form timing or subjective sound quality has passed.

## Observed timing samples from the supplied Windows transcript

| Case | Profile visible in transcript | Chordic estimated | Spoken English measured | Sequential combined shown |
| --- | --- | ---: | ---: | ---: |
| "Rocky here. You friend. Good." | CT2 | 13.10 s | 7.23 s | 20.32 s |
| favorite-color response at `/speed 2` | CT2 | 22.65 s | 10.33 s | 32.98 s |
| follow-up after "yes" | CT2 | 16.01 s | 8.69 s | 24.70 s |
| derivative response | CT2 | 25.36 s | 14.33 s | 39.69 s |
| `/speed 1` + `/replay` | CT2 | 12.68 s | 14.29 s | 26.97 s |

The current implementation delays English speech until after the estimated Chordic duration, so perceived wall time is approximately the sum of the two streams. The requested overlap mode should instead begin the English voice when Chordic playback begins. For simultaneous starts, the useful wall-time estimate becomes approximately `max(Chordic duration, English duration)`, not their sum.

## Manual acceptance state after this feedback

- Audible Windows English TTS: **PASS — operator personally heard it**
- Audible Chordic pitches: **PASS — operator personally heard them**
- Multi-turn translated speech functioning: **PASS — operator reports it worked well**
- Replay with spoken translation: **PASS in supplied transcript**
- `/speed 2` and `/speed 1`: **PASS in supplied transcript**
- Human-voice naturalness: **NEEDS TUNING**
- Chordic-tone naturalness: **NEEDS TUNING**
- EXP-002 subjective listening in this session: **NOT ESTABLISHED; transcript shows CT2**
- Offline acceptance in this session: **NOT ESTABLISHED**
- Mute/cancel/stop/reset in this session: **NOT ESTABLISHED from supplied evidence**

## New near-term requirements

### 1. Concurrent translation playback

When persistent translation is enabled, validated English speech should begin when Chordic playback begins rather than after Chordic finishes.

Requirements:
- Chordic remains the primary generated communication output.
- English TTS remains an application-owned translation layer.
- both streams must still obey mute/cancel/stop/reset;
- replay should replay both concurrently when translation is enabled;
- no model-generated text may gain direct audio-control authority;
- timing telemetry must stop labeling simultaneous playback as a sum.

### 2. Learn and naturally reuse the conversation partner's name

Rocky should conservatively remember an explicitly supplied session name, for example:

```text
User: hello rocky.
Rocky: Hello. Rocky here. Name question?
User: My name is Wyatt
Rocky: Wyatt. Rocky. Friend question?
```

Desired behavior:
- capture explicit forms such as `My name is Wyatt` or `Call me Wyatt`;
- use the person's name naturally and fairly often, especially greetings, questions, reassurance, and direct responses;
- do not force the name into every sentence;
- name memory is session/conversation context, not hardware authority;
- `/clear` should clear the remembered name together with conversation history unless a later persistent-profile feature is explicitly designed.

### 3. Human voice tuning

Expose bounded user controls for the local Windows translation voice rather than hard-coding one presentation.

Desired tunable properties:
- installed voice selection;
- speech rate;
- speech volume;
- later pitch/prosody tuning where the local engine supports it reliably;
- contextual question/excitement/reassurance/technical delivery remains application-owned and bounded.

### 4. More organic Chordic acoustic character

Current pure tones are too robotic for the intended species communication aesthetic.

Target impression:
- evolved biological/alien communication rather than a computer beep protocol;
- whale-like / resonant / vibrating character;
- smooth, musical, physically resonant feel;
- still pitch-discernible and machine-recognizable;
- preserve semantic note/pattern distinctions even if timbre/envelope/vibrato changes;
- provide A/B-selectable synthesis modes while tuning so the old deterministic tone remains available as a reference.

Possible experimental dimensions to measure independently:
- gentle vibrato depth/rate;
- harmonic content;
- amplitude modulation / pulsing;
- attack/release shape;
- glide/portamento between adjacent notes;
- resonance/low-frequency body;
- token-boundary rhythm.

Do not call a candidate "natural" or "whale-like" based on unit tests. Subjective listening must be recorded separately.

## Longer-term translator direction

Future goal: a computer/phone application should listen to Chordic in real time, recognize the compact language quickly, and display/speak translation with low enough latency to feel like live conversation.

This future path should favor:
- compact semantic tokens over spelling English through tones;
- streaming recognition rather than waiting for an entire long utterance;
- incremental translation as token boundaries are recognized;
- noise-tolerant acoustic features;
- phone/laptop microphones as first targets before physical robot integration;
- latency measurements split into recognition, semantic decode, translation, synthesis, and total wall time.

This is a future architecture direction, not a claim that real-time acoustic recognition exists today.

## Required regression evidence for this iteration

Automated:
- concurrent TTS is queued with zero post-Chordic delay but still gated until actual tonal playback begins;
- overlap wall-time metric is `max(tone, voice)` rather than a sum;
- mute/cancel/stop/reset/replay still affect both streams;
- explicit session-name capture works and false positives such as `I am sad` are not treated as names;
- provider context receives the remembered name;
- `/clear` removes the remembered name;
- safety/Brain boundaries remain unchanged.

Manual Windows:
- confirm English and Chordic are genuinely simultaneous;
- check whether simultaneous playback is understandable or needs relative-volume tuning;
- A/B test old pure tones against each new organic candidate;
- judge whether name use feels frequent but not repetitive;
- record exact timing and acoustic feedback, including failures.


## PR #15 implementation status

Draft PR #15 implements the first follow-up candidate from this feedback.

Implemented:
- spoken English is gated on actual Chordic playback start but now uses zero post-start delay, so the two streams are intended to overlap;
- wall-time telemetry uses the longer of the two stream durations instead of adding them;
- explicit session-name capture for `My name is X` and `Call me X`;
- name is supplied to provider context with an instruction to use it naturally/often, not every sentence;
- `/clear` clears the remembered name;
- bounded local English voice controls: installed voice selection and rate/pitch/volume offsets from -2 to +2;
- `/tone pure|resonant` for A/B listening;
- resonant synthesis preserves the fundamental note frequencies while adding bounded harmonic content, amplitude pulse, slower attack/release, and subtle phase vibration;
- default branch config for this experimental PR selects `resonant`, while `pure` remains available;
- duplicate `/translate on|off` status printing found during implementation was fixed;
- duplicate terminal prompt printing after completed responses was found and fixed.

Automated verification:
- GitHub Actions run #68 at `98c7ae67409f5d542fd567f8dd02ddcfa844a71d` passed Windows Python 3.12/3.13, Ubuntu Python 3.12/3.13, and Arduino.
- Added tests cover zero-delay overlap scheduling gated on real playback start, max-based overlap wall-time, explicit name capture and clearing, bounded voice tuning, tone command validation, resonant PCM determinism/bounds, and existing safety/regression suites.

Manual status:
- simultaneous Chordic + English audibility: **NOT RUN on PR #15**
- relative volume/intelligibility while overlapping: **NOT RUN**
- resonant-vs-pure subjective comparison: **NOT RUN**
- best voice rate/pitch/volume offsets: **NOT RUN**
- name-use naturalness/frequency with real model: **NOT RUN**

Do not promote the resonant renderer into a stable Chordic acoustic specification from automated tests alone.
