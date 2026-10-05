# EXP-003 coverage/contour integration evidence — 2026-10-05

Status: draft experimental integration. No merge performed. Human listening, human vocal production, microphone recognition, and streaming acoustic recognition are **NOT RUN**.

## Source-of-truth boundary

Chordic language semantics remain authoritative in `whkoerner/Chordic-Language`.

This Rocky branch pins Chordic commit:

`654deaa0ab7c77efe4d36876936a73ec0890065c`

from draft Chordic PR #4 and consumes:

- `language/runtime/exp-003-runtime-export.json` -> `experiments/chordic/exp-003-runtime.json`
- `language/runtime/exp-002-runtime-export.json` -> `experiments/chordic/exp-002-surfaces.json`
- `benchmarks/exp-003-open-conversation.json` -> `experiments/chordic/exp-003-benchmark.json`

Rocky no longer owns the EXP-002 English surface dictionary. `software/csp/exp002.py` loads the pinned Chordic surface export. Runtime adapter code remains local, but semantic mappings do not.

## Correct interpretation of real EXP-002 evidence

The first production-style free-form EXP-002 Windows evidence was:

| reply | EXP-002/Chordic | English | relation |
| --- | ---: | ---: | --- |
| `8 times 8 is 64. Rocky calculate. Good.` | 20.48 s | 6.77 s | Chordic +12.96 s |
| `Rocky no eat. Rocky think food is energy. Rocky use energy to think and build.` | 36.41 s | 8.38 s | Chordic +27.28 s |

These are **not** evidence that supported EXP-002 semantic tokens inherently take 20-36 seconds. The former Rocky-local EXP-002 surface registry did not contain ordinary math/numeric or food/eat/energy/build concepts, so exact CT2/UTF-8 fallback dominated those replies.

Earlier 22-25 second Windows measurements from the prior session used `language=ct2`, not EXP-002, and must not be reported as EXP-002 performance.

## EXP-003 integration

Rocky now supports:

- `/language exp003`
- `/language exp002`
- `/language ct2`
- `/language ct1`

EXP-003:
- reads the pinned Chordic runtime export;
- composes digits and arithmetic instead of using sentence IDs;
- treats configured low-information English glue as grammar omission;
- uses explicit exact CT2 fallback for unsupported lexical spans;
- reports semantic token count, semantic coverage, fallback span count, and fallback bytes in runtime representation telemetry;
- preserves exact English round-trip for translation verification.

The real math and food responses now encode at 100% semantic coverage in the deterministic EXP-003 parser with zero fallback spans.

## Timing and coverage benchmark

The pinned Chordic benchmark contains 11 open-conversation samples plus 8 historical seed samples.

At the unchanged 3x learning/benchmark multiplier, non-seed simulation is:

- count: 11
- mean: 4.441 s
- median: 4.185 s
- max: 9.825 s
- count >10 s: 0
- mean semantic coverage: 100.0%
- fallback spans: 0
- fallback bytes: 0

Every stored benchmark row includes:
- semantic token count;
- unsupported spans;
- fallback span count;
- fallback bytes;
- semantic coverage percent;
- fallback percent;
- semantic duration;
- fallback duration;
- total duration.

The unseen phrase `Rocky calibrate spectrometer` is a negative coverage control: `Rocky` is semantic while `calibrate` and `spectrometer` remain explicit fallback spans.

These are deterministic parser/timing-model results, not measured Windows acoustic wall times.

## Acoustic integration

`contour-v1` is now an A/B tone mode.

It consumes the Chordic-owned EXP-003 contour registry:
- four relative pitch anchors per token;
- five speaker-relative levels: -4, -2, 0, +2, +4 semitones;
- continuous cosine-smoothed log-frequency glides inside each semantic token;
- gentle token boundary silence/amplitude separation;
- restrained harmonic body and subtle vibrational modulation.

The symbolic code registry has:
- 106 assigned semantic tokens;
- 0 exact contour collisions;
- minimum Hamming distance 2;
- minimum summed anchor-separation proxy 4 semitones.

The renderer does not establish that the result sounds natural. Human acoustic acceptance is still required.

## Human-vocalizability analysis

Computational register checks from the Chordic candidate:

| baseline | minimum | maximum | span |
| ---: | ---: | ---: | ---: |
| 110 Hz | 87.3 Hz | 138.6 Hz | 8 semitones |
| 180 Hz | 142.9 Hz | 226.8 Hz | 8 semitones |
| 260 Hz | 206.4 Hz | 327.6 Hz | 8 semitones |

At 3x timing, the fastest token class has a worst-case contour-segment slope proxy of about 61.5 semitones/second.

This supports only computational feasibility across multiple registers. It does **not** prove that an ordinary human can comfortably reproduce or recognize the gestures.

## Future recognition orientation

The candidate is intentionally compatible with a future pipeline:

microphone -> speaker-baseline estimate -> contour tracking -> token boundary detection -> four-anchor quantization -> parity/distance validation -> incremental semantic token -> incremental English translation.

No microphone recognizer was implemented or tested in this work.

## CI/debug ledger

| run | head | observed failure/status | root cause | fix / evidence |
| --- | --- | --- | --- | --- |
| #76 | `a2d677a` | all software cells failed at Brain v0.2 | generated edit placed literal `\\n` characters in Python import lines; code could not import | corrected controller/translation imports and EXP-003 TaskController dispatch in `d2bdb0e` |
| #77 | `d2bdb0e` | all software cells still failed at Brain v0.2 | a second literal `\\n` remained in the EXP-002 exported-surface adapter | subsequent inspection isolated `surface_registry()\\n    for ...` |
| #78 | `0320295` | all software cells still failed at Brain v0.2 | EXP-002 adapter syntax was still malformed; this rerun preserved the failure rather than hiding it | repaired EXP-002 adapter syntax/boundary regex in `a050871` |
| #79 | `a050871` | Brain v0.2 passed; all software cells then failed at Conversational Brain V1 | `pcm_chunks()` still allowed only `pure|resonant`, so the new contour PCM test correctly rejected `contour-v1` | diagnosed renderer dispatch/allowlist mismatch |
| #80 | `ffb4098` | all software cells failed at Conversational Brain V1 | telemetry commit did not yet fix the contour renderer dispatch | fixed `pcm_chunks()` contour-v1 route in `dc1729b` |
| #81 | `dc1729b` | **PASS** | none | Windows/Linux Python 3.12/3.13 + Arduino all green |

No application test was weakened to obtain the green run.

## Automated evidence on run #81

Green:
- deterministic codec tests
- RPA-Link tests
- simulator tests
- Brain v0.2 tests
- Conversational Brain V1 tests including new EXP-003 authority/coverage/timing/PCM tests
- browser protocol tests
- Windows Python 3.12
- Windows Python 3.13
- Ubuntu Python 3.12
- Ubuntu Python 3.13
- Arduino Uno compilation

New focused EXP-003 coverage checks include:
- Chordic source pin and no Rocky `_SURFACES` dictionary;
- real math response has no fallback;
- real food/energy/build response has no fallback;
- benchmark coverage and timing reproduction;
- unseen-word explicit fallback;
- compositional arithmetic, no whole-expression mapping;
- deterministic/bounded contour-v1 PCM;
- CT2 and EXP-002 compatibility.

## Manual Windows acceptance — NOT RUN

Run these from the normal Rocky launcher/session. Keep `/translate on` enabled if you want the English overlap evidence.

### Same-prompt profile comparison

```text
/translate on
/speed 3

/language ct2
what is 8 times 8?

/language exp002
what is 8 times 8?

/language exp003
what is 8 times 8?

/language ct2
what is your favorite food?

/language exp002
what is your favorite food?

/language exp003
what is your favorite food?
```

For each reply, record:
- `Representation:` line;
- Chordic estimated/measured duration shown by Rocky;
- spoken English measured duration;
- whether Chordic finishes before/after English;
- whether any fallback spans/bytes are reported.

### EXP-003 acoustic A/B

Use one fixed EXP-003 prompt for all three modes:

```text
/language exp003
/tone pure
what is 8 times 8?
/replay

/tone resonant
/replay

/tone contour-v1
/replay
```

Then repeat with:

```text
what is your favorite food?
```

Report which mode sounds:
- least like separate beeps;
- most continuous;
- easiest to follow;
- most plausible to hum/voice;
- too jumpy, buzzy, alarm-like, robotic, or tiring.

### Human vocalizability spot check

After hearing `contour-v1`, attempt to hum one short reply such as:

```text
/language exp003
/tone contour-v1
hello rocky
```

Only report whether the contour feels practically reproducible. Do not treat one attempt as recognition validation.

## Still NOT RUN

- subjective Windows listening acceptance of contour-v1;
- actual human reproduction across multiple vocal ranges;
- microphone/token recognition;
- noisy-room tests;
- streaming recognition/translation latency;
- final acoustic token-boundary recognition;
- final volume balance acceptance;
- final 0.5-1.0 second translation lead-in acceptance;
- physical robot motion changes (intentionally out of scope).
