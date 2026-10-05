# Real EXP-002 free-form Rocky baseline — 2026-10-04

This is manual Windows evidence from the real local-model desktop path after explicitly switching from CT2 to EXP-002.

## Active state

The operator ran:

- /language exp002
- /status

Status confirmed:
- language=exp002
- translation=True
- tone=resonant
- duration_multiplier=3

## Real free-form samples

### Simple math

Prompt:
what is 8 times 8?

Rocky English reply:
8 times 8 is 64. Rocky calculate. Good.

Runtime:
- representation reported: EXP-002
- Chordic estimated duration: 20.48 s
- English measured duration: 6.77 s
- English lead-in: 0.75 s
- Chordic outlasted English by 12.96 s

### Food preference

Prompt:
what is your favorite food?

Rocky English reply:
Rocky no eat. Rocky think food is energy. Rocky use energy to think and build.

Runtime:
- representation reported: EXP-002
- Chordic estimated duration: 36.41 s
- English measured duration: 8.38 s
- English lead-in: 0.75 s
- Chordic outlasted English by 27.28 s
- runtime warning: fallback is exact but not fluent speech

## Root-cause evidence from current adapter

The Rocky EXP-002 runtime surface registry does not currently define ordinary mappings for:
- times
- numeric values used by the math reply
- food
- eat
- energy
- build

The EXP-002 benchmark corpus also does not include math or food-domain conversational cases.

Therefore the published EXP-002 benchmark result and the production free-form result answer different questions:

- benchmark: registered compact semantic cases can meet the timing target;
- production runtime: unsupported free-form spans still fall back to exact CT2/UTF-8 and can become much longer.

Do not report the 20.48 s or 36.41 s results as proof that the compact registered EXP-002 token sequences themselves are that slow. They are evidence that current vocabulary/parser coverage is insufficient for ordinary conversation.

## Architectural implication

Rocky currently carries a hard-coded English-surface-to-Chordic mapping in software/csp/exp002.py.

Future work should move authoritative surface/semantic mapping into versioned Chordic-Language data and make Rocky a pinned consumer.

The next candidate/EXP-003 work should explicitly measure:
- semantic-token coverage;
- fallback bytes/spans;
- fallback percentage;
- duration attributable to semantic tokens versus fallback;
- real free-form conversational coverage.

## Decision

EXP-002 remains useful evidence for compact compositional structure, but its current Rocky free-form integration is not sufficient as a general conversational language.

This real baseline justifies a successor experiment focused on broader semantic coverage, lower fallback dependence, and a more natural vocal acoustic representation.
