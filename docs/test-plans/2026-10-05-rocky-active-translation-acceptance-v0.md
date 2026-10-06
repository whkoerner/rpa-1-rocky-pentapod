# Active translation acceptance matrix V0

**Date:** 2026-10-05  
**Branch:** `test/rocky-active-translation-acceptance-v0`  
**Base:** portable restore V0 stacked head

## Purpose

Golden-lock the existing adaptive overlap scheduler without changing its policy.

Policy under test:

- Chordic starts first;
- English start delay is never less than the configured 0.75 s lead;
- when English is short enough, delay is selected so measured English ends 0.75 s after estimated Chordic;
- when English itself is longer than Chordic, the lead cannot be negative, so English starts at the minimum lead and naturally finishes farther after Chordic;
- unavailable local voice fails before persistent translation is enabled.

## Automated cases

- Chordic 10.0 s / English 3.0 s -> English start 7.75 s, finish margin +0.75 s;
- Chordic 6.0 s / English 6.0 s -> start 0.75 s, finish margin +0.75 s;
- Chordic 4.0 s / English 8.0 s -> start 0.75 s, finish margin +4.75 s;
- very short Chordic 0.5 s / English 0.2 s -> start 1.05 s, finish margin +0.75 s;
- voice unavailable -> translation remains OFF and no voice request is queued.

Existing tests remain responsible for persistent two-turn translation, OFF behavior, mute/unmute, cancel, STOP/reset, replay, surfaced voice backend failure, and bounded voice tuning.

## Manual NOT RUN

These deterministic tests use measured-duration fixtures, not speakers.

Still manual:

- real System.Speech timing by ear;
- real Piper timing by ear;
- perceived overlap quality;
- cancellation during actual audible speech;
- replay/mute/STOP while real audio is active;
- whether the +0.75 s target sounds natural across real long/short sentences.

No acoustic quality PASS is inferred from timing arithmetic.
